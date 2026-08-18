from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import fnmatch
import yaml


class SDDOrchestratorError(Exception):
    pass


class StageNotFoundError(SDDOrchestratorError):
    pass


@dataclass
class InputCheck:
    stage_id: str
    missing_files: list[str] = field(default_factory=list)
    missing_semantic_inputs: list[str] = field(default_factory=list)
    entry_condition_failures: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not (
            self.missing_files
            or self.missing_semantic_inputs
            or self.entry_condition_failures
        )


class Orchestrator:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.sdd_root = self.repo_root / ".sdd"
        self.system = self._load_yaml(self.sdd_root / "system.yaml")
        self.registry = self._load_yaml(self.sdd_root / "stages.yaml")
        self.project_state_path = self.sdd_root / "state" / "project-state.yaml"
        self.authority_state_path = self.sdd_root / "state" / "authority-state.yaml"
        self.implementation_state_path = self.sdd_root / "state" / "implementation-state.yaml"
        self.project_state = self._load_yaml(self.project_state_path)
        self.authority_state = self._load_yaml(self.authority_state_path)
        self.implementation_state = self._load_yaml(self.implementation_state_path)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise SDDOrchestratorError(f"Required SDD runtime file missing: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SDDOrchestratorError(f"Invalid YAML root object: {path}")
        return data

    @staticmethod
    def _save_yaml(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    @property
    def current_stage_id(self) -> str:
        return str(self.project_state["lifecycle"]["current_stage"]).zfill(2)

    def get_stage(self, stage_id: str | None = None) -> dict[str, Any]:
        sid = (stage_id or self.current_stage_id).zfill(2)
        stage = self.registry.get("stages", {}).get(sid)
        if stage is None:
            raise StageNotFoundError(f"Unknown stage: {sid}")
        return stage

    def stage_summary(self, stage_id: str | None = None) -> dict[str, Any]:
        sid = (stage_id or self.current_stage_id).zfill(2)
        stage = self.get_stage(sid)
        return {
            "stage_id": sid,
            "name": stage["name"],
            "phase": stage.get("phase"),
            "type": stage.get("type"),
            "core_question": stage.get("core_question"),
            "authority_domains": stage.get("authority_domains", {}),
            "outputs": stage.get("outputs", {}),
        }

    def _glob_exists(self, pattern: str) -> bool:
        if "*" not in pattern and "?" not in pattern and "[" not in pattern:
            return (self.repo_root / pattern).exists()
        for p in self.repo_root.rglob("*"):
            rel = p.relative_to(self.repo_root).as_posix()
            if fnmatch.fnmatch(rel, pattern):
                return True
        return False

    def check_required_inputs(
        self,
        stage_id: str | None = None,
        semantic_inputs: set[str] | None = None,
    ) -> InputCheck:
        sid = (stage_id or self.current_stage_id).zfill(2)
        stage = self.get_stage(sid)
        semantic_inputs = semantic_inputs or set()
        result = InputCheck(stage_id=sid)

        required = stage.get("required_inputs", {})
        for rel_path in required.get("files", []) or []:
            if not self._glob_exists(rel_path):
                result.missing_files.append(rel_path)

        for semantic in required.get("semantic", []) or []:
            if semantic not in semantic_inputs:
                result.missing_semantic_inputs.append(semantic)

        for cond in stage.get("entry_conditions", {}).get("all", []) or []:
            if not self._evaluate_condition(cond):
                result.entry_condition_failures.append(cond)

        return result

    def _evaluate_condition(self, condition: str) -> bool:
        condition = condition.strip()

        if condition == "stage_07_result == PASS":
            return self.project_state["stages"]["07"].get("result") == "PASS"

        if condition == "stage_02_result == COMPLETED":
            return self.project_state["stages"]["02"].get("result") == "COMPLETED"

        if condition == "implementation_authorization == true":
            return bool(self.project_state["authorizations"].get("implementation"))

        if condition == "stage_09_result == PASS":
            return self.project_state["stages"]["09"].get("result") == "PASS"

        raise SDDOrchestratorError(
            f"Unsupported entry condition expression: {condition}"
        )

    def missing_input_gate_result(self, stage_id: str | None = None) -> str | None:
        sid = (stage_id or self.current_stage_id).zfill(2)
        stage = self.get_stage(sid)
        check = self.check_required_inputs(sid)
        if check.ready:
            return None
        return stage.get("missing_required_artifact_result", "BLOCKED")

    def record_stage_result(
        self,
        stage_id: str,
        result: str,
        *,
        classification: str | None = None,
    ) -> dict[str, Any]:
        sid = stage_id.zfill(2)
        stage = self.get_stage(sid)
        allowed = (
            stage.get("result_vocabulary")
            or list(stage.get("result_semantics", {}).keys())
            or []
        )
        if allowed and result not in allowed:
            raise SDDOrchestratorError(
                f"Invalid result {result!r} for Stage {sid}; allowed={allowed}"
            )

        stage_state = self.project_state["stages"][sid]
        stage_state["status"] = "DONE"
        stage_state["result"] = result

        route = self._resolve_route(stage, result, classification)

        if sid == "07":
            authorized = result == "PASS"
            self.project_state["authorizations"]["implementation"] = authorized

        if sid == "10":
            self.project_state["authorizations"]["release"] = result in {
                "READY",
                "READY_WITH_KNOWN_ISSUES",
            }

        if route and route.isdigit():
            self.project_state["lifecycle"]["last_completed_stage"] = sid
            self.project_state["lifecycle"]["current_stage"] = route
            self.project_state["lifecycle"]["current_stage_name"] = self.get_stage(route)["name"]
            self.project_state["lifecycle"]["next_action"] = "RUN_STAGE"
            self.project_state["stages"][route]["status"] = "IN_PROGRESS"
        else:
            self.project_state["lifecycle"]["next_action"] = route or "STOP"

        self._save_yaml(self.project_state_path, self.project_state)
        return {
            "stage_id": sid,
            "result": result,
            "classification": classification,
            "next": route,
            "implementation_authorization": self.project_state["authorizations"]["implementation"],
            "release_authorization": self.project_state["authorizations"]["release"],
        }

    def _resolve_route(
        self,
        stage: dict[str, Any],
        result: str,
        classification: str | None,
    ) -> str | None:
        semantics = stage.get("result_semantics", {})
        if result in semantics:
            nxt = semantics[result].get("next")
            if nxt == "CLASSIFICATION_ROUTER":
                if not classification:
                    return "CLASSIFICATION_REQUIRED"
                rules = self.registry["routers"]["CLASSIFICATION_ROUTER"]["rules"]
                rule = rules.get(classification)
                return str(rule.get("route_to")) if rule else "CLASSIFICATION_UNKNOWN"
            return str(nxt) if nxt is not None else None

        nxt = stage.get("next", {}).get(result.lower())
        return str(nxt) if nxt is not None else None

    def authority_owner(self, domain: str) -> str:
        owners = self.authority_state.get("domain_owners", {})
        if domain not in owners:
            raise SDDOrchestratorError(f"No authority owner registered for domain: {domain}")
        return str(owners[domain]).zfill(2)

    def route_conflict(self, domains: list[str]) -> dict[str, Any]:
        owners = sorted({self.authority_owner(d) for d in domains})
        return {
            "action": ["DETECT", "REPORT", "BLOCK", "ROUTE_TO_AUTHORITATIVE_OWNER"],
            "domains": domains,
            "owner_stages": owners,
            "human_decision_required": len(owners) > 1,
        }

    def status(self) -> dict[str, Any]:
        sid = self.current_stage_id
        return {
            "project": self.project_state.get("project", {}),
            "current_stage": self.stage_summary(sid),
            "authorizations": self.project_state.get("authorizations", {}),
            "blocking": self.project_state.get("blocking", {}),
            "stage_state": self.project_state["stages"][sid],
        }
