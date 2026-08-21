from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import subprocess
import tempfile
import fnmatch

from .core import Orchestrator, SDDOrchestratorError
from .executor import StageExecutionRequest, StageExecutionResult, StageExecutor


class StageExecutionValidationError(SDDOrchestratorError):
    pass


class StageRunner:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.repo_root = orchestrator.repo_root

    def build_request(
        self,
        stage_id: str | None = None,
        *,
        semantic_inputs: dict[str, Any] | None = None,
        stage_instructions: str | None = None,
    ) -> StageExecutionRequest:
        sid = (stage_id or self.orchestrator.current_stage_id).zfill(2)
        stage = self.orchestrator.get_stage(sid)
        semantic_inputs = semantic_inputs or {}

        check = self.orchestrator.check_required_inputs(
            sid, set(semantic_inputs.keys())
        )
        if not check.ready:
            raise StageExecutionValidationError(
                "Stage input check failed: "
                f"missing_files={check.missing_files}, "
                f"missing_semantic_inputs={check.missing_semantic_inputs}, "
                f"entry_condition_failures={check.entry_condition_failures}"
            )

        artifacts: dict[str, str] = {}
        for rel in stage.get("required_inputs", {}).get("files", []) or []:
            path = self.repo_root / rel
            if path.is_file():
                artifacts[rel] = path.read_text(encoding="utf-8")

        # Authoring-stage reruns are read-modify-write operations. If the stage's
        # own authoritative output already exists, include it in the reasoning
        # packet so the executor can preserve stable IDs, dependencies, scope,
        # and prior approved decisions instead of reconstructing them from
        # upstream artifacts. This is intentionally limited to Stages 02-06;
        # gate reports (07/09/10) are fresh decisions and must not treat a prior
        # report as an authoritative input to the next decision.
        if sid in {"02", "03", "04", "05", "06"}:
            for rel in stage.get("outputs", {}).get("files", []) or []:
                path = self.repo_root / rel
                if path.is_file() and rel not in artifacts:
                    artifacts[rel] = path.read_text(encoding="utf-8")

        # Stage 09 should consume the bounded Stage 08 evidence index when present.
        # The index is intentionally supplemental rather than a required input so
        # repositories created before the evidence-index task remain diagnosable.
        if sid == "09":
            for rel in (
                ".sdd/state/post-implementation-verification.md",
                ".sdd/state/implementation-state.md",
            ):
                path = self.repo_root / rel
                if path.is_file() and rel not in artifacts:
                    artifacts[rel] = path.read_text(encoding="utf-8")

        # Stage 10 release evidence is often produced after the Stage 09 gate and
        # therefore cannot be modeled as a static required-input list in older
        # repositories.  Collect a bounded, release-specific supplemental packet
        # so the release gate can inspect explicit applicability decisions instead
        # of reporting that repository documentation was never supplied.
        if sid == "10":
            artifacts.update(self._collect_stage10_release_artifacts(existing=artifacts))

        runtime_inputs = self._collect_runtime_inputs(stage, stage_id=sid)
        instructions = stage_instructions or self._load_stage_instructions(sid)

        return StageExecutionRequest(
            stage_id=sid,
            stage_name=stage["name"],
            stage_type=stage.get("type", "UNKNOWN"),
            core_question=stage.get("core_question"),
            contract=stage,
            artifacts=artifacts,
            semantic_inputs=semantic_inputs,
            runtime_inputs=runtime_inputs,
            stage_instructions=instructions,
        )

    def _load_stage_instructions(self, stage_id: str) -> str | None:
        for suffix in ("md", "txt"):
            path = self.repo_root / ".sdd" / "instructions" / f"stage-{stage_id}.{suffix}"
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None

    _STAGE10_RELEASE_ARTIFACTS = (
        "README.md",
        "pyproject.toml",
        "docs/handoff/release-profile.md",
        "docs/handoff/release-notes.md",
        "RELEASE_NOTES.md",
        "docs/handoff/known-issues.md",
        "docs/handoff/recovery.md",
        "docs/handoff/runbook.md",
    )

    def _collect_stage10_release_artifacts(
        self,
        *,
        existing: dict[str, str] | None = None,
        max_total_bytes: int = 160_000,
        max_file_bytes: int = 64_000,
    ) -> dict[str, str]:
        """Collect bounded release-relevant repository artifacts for Stage 10.

        This is supplemental evidence, not authority.  Stage 10 still owns the
        release decision and may reject incomplete or contradictory documents.
        """
        existing = existing or {}
        out: dict[str, str] = {}
        used = 0
        for rel in self._STAGE10_RELEASE_ARTIFACTS:
            if rel in existing:
                continue
            path = self.repo_root / rel
            if not path.is_file():
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if len(raw) > max_file_bytes:
                raw = raw[:max_file_bytes]
                text = raw.decode("utf-8", errors="replace") + "\n<omitted: Stage 10 file limit>"
                raw = text.encode("utf-8")
            else:
                text = raw.decode("utf-8", errors="replace")
            if used + len(raw) > max_total_bytes:
                continue
            out[rel] = text
            used += len(raw)
        return out

    def _collect_runtime_inputs(
        self, stage: dict[str, Any], *, stage_id: str | None = None
    ) -> dict[str, Any]:
        requested = set(stage.get("required_inputs", {}).get("runtime", []) or [])
        out: dict[str, Any] = {}
        if "GIT_STATUS" in requested:
            out["GIT_STATUS"] = self._git(["status", "--porcelain=v1"])
        if "CURRENT_BRANCH" in requested:
            out["CURRENT_BRANCH"] = self._git(["branch", "--show-current"])
        if "RECENT_COMMITS" in requested or "GIT_HISTORY" in requested:
            out["GIT_HISTORY"] = self._git(
                ["log", "-20", "--pretty=format:%H%x09%s"], allow_failure=True
            )
        if "SOURCE_CODE" in requested:
            out["SOURCE_CODE"] = self._collect_tree_text("src")
        if "TEST_EVIDENCE" in requested:
            out["TEST_EVIDENCE"] = self._collect_tree_text("tests")
        if "BUILD_LINT_TYPECHECK_EVIDENCE_IF_APPLICABLE" in requested:
            evidence = self.repo_root / ".sdd" / "evidence"
            out["BUILD_LINT_TYPECHECK_EVIDENCE_IF_APPLICABLE"] = (
                self._collect_evidence_summary(evidence) if evidence.exists() else {}
            )
        if str(stage_id or "").zfill(2) == "10":
            out["RELEASE_GIT_IDENTITY"] = {
                "branch": self._git(["branch", "--show-current"], allow_failure=True),
                "head_commit": self._git(["rev-parse", "HEAD"], allow_failure=True),
                "head_tags": self._git(["tag", "--points-at", "HEAD"], allow_failure=True),
                "working_tree_status": self._git(["status", "--porcelain=v1"], allow_failure=True),
                "recent_commits": self._git(
                    ["log", "-10", "--pretty=format:%H%x09%s"], allow_failure=True
                ),
                "semantics": (
                    "Live Git release identity supplied for Stage 10 inspection. "
                    "A dirty tree is evidence to assess, not an automatic release decision."
                ),
            }
            out["STAGE10_CONTEXT_POLICY"] = (
                "Stage 10 receives only bounded release-relevant repository artifacts "
                "plus live Git identity. Presence of a document is evidence, not an "
                "automatic READY decision; explicit N/A statements must be evaluated "
                "against the release target and authoritative contracts."
            )
        return out

    _EVIDENCE_NOISY_KEYS = frozenset({
        "stdout",
        "stderr",
        "prompt",
        "request",
        "response",
        "provider_output",
        "provider_stdout",
        "provider_stderr",
        "codex_output",
        "codex_stdout",
        "codex_stderr",
        "transcript",
        "diff",
        "patch",
        "raw_output",
    })

    def _compact_evidence_value(
        self,
        value: Any,
        *,
        depth: int = 0,
        max_depth: int = 6,
        max_string_chars: int = 2000,
        max_list_items: int = 50,
    ) -> Any:
        """Return a bounded evidence projection suitable for Stage 09 reasoning.

        Stage 08 evidence files may contain complete Codex transcripts, diffs and
        command streams. Re-injecting those payloads into Stage 09 can exceed the
        reasoning provider context window and is unnecessary when task/result,
        verification and checkpoint metadata are available. This projection keeps
        structured audit facts while explicitly marking omitted verbose payloads.
        """
        if depth >= max_depth:
            return "<omitted: max evidence depth>"
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                if key_text.lower() in self._EVIDENCE_NOISY_KEYS:
                    if isinstance(item, str):
                        out[key_text] = f"<omitted verbose evidence: {len(item)} chars>"
                    elif isinstance(item, (list, dict)):
                        out[key_text] = f"<omitted verbose evidence: {len(item)} items>"
                    else:
                        out[key_text] = "<omitted verbose evidence>"
                    continue
                out[key_text] = self._compact_evidence_value(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_string_chars=max_string_chars,
                    max_list_items=max_list_items,
                )
            return out
        if isinstance(value, list):
            compacted = [
                self._compact_evidence_value(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_string_chars=max_string_chars,
                    max_list_items=max_list_items,
                )
                for item in value[:max_list_items]
            ]
            if len(value) > max_list_items:
                compacted.append(f"<omitted {len(value) - max_list_items} list items>")
            return compacted
        if isinstance(value, str) and len(value) > max_string_chars:
            return value[:max_string_chars] + f"\n<omitted {len(value) - max_string_chars} chars>"
        return value

    def _collect_evidence_summary(
        self,
        evidence_root: Path,
        *,
        max_total_bytes: int = 200_000,
        max_file_bytes: int = 16_000,
    ) -> dict[str, str]:
        """Collect compact Stage 08 evidence without raw provider transcripts."""
        out: dict[str, str] = {}
        used = 0
        skipped_limit: list[str] = []
        parse_failures: list[str] = []
        for path in sorted(p for p in evidence_root.rglob("*.json") if p.is_file()):
            rel = path.relative_to(self.repo_root).as_posix()
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                compact = self._compact_evidence_value(payload)
                text = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                parse_failures.append(rel)
                continue
            raw = text.encode("utf-8")
            if len(raw) > max_file_bytes:
                raw = raw[:max_file_bytes]
                # Decode on a character boundary and make truncation explicit.
                text = raw.decode("utf-8", errors="ignore") + "\n<omitted: evidence summary file limit>"
                raw = text.encode("utf-8")
            if used + len(raw) > max_total_bytes:
                skipped_limit.append(rel)
                continue
            out[rel] = text
            used += len(raw)
        if parse_failures:
            out["__unreadable_evidence__"] = "\n".join(parse_failures)
        if skipped_limit:
            out["__skipped_evidence_size_limit__"] = "\n".join(skipped_limit)
        out["__context_diet__"] = (
            "Stage 09 evidence is a bounded projection: verbose Codex/provider "
            "transcripts, raw stdout/stderr, prompts, patches and diffs are omitted. "
            "Use the Stage 08 evidence index, task checkpoints, verification fields, "
            "source/tests and Git history for conformance reasoning."
        )
        return out

    def _collect_tree_text(self, rel_root: str, *, max_total_bytes: int = 1_000_000) -> dict[str, str]:
        root = self.repo_root / rel_root
        if not root.exists():
            return {}
        out: dict[str, str] = {}
        used = 0
        skipped_binary: list[str] = []
        skipped_limit: list[str] = []
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(self.repo_root).as_posix()
            if any(part in {"__pycache__", ".git", "node_modules", "dist", "build"} for part in path.parts):
                continue
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8")
            except (UnicodeDecodeError, OSError):
                skipped_binary.append(rel)
                continue
            if used + len(raw) > max_total_bytes:
                skipped_limit.append(rel)
                continue
            out[rel] = text
            used += len(raw)
        if skipped_binary:
            out["__skipped_binary__"] = "\n".join(skipped_binary)
        if skipped_limit:
            out["__skipped_size_limit__"] = "\n".join(skipped_limit)
        return out

    def _git(self, args: list[str], *, allow_failure: bool = False) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            if allow_failure:
                return ""
            stderr = (proc.stderr or "").strip()
            raise StageExecutionValidationError(
                f"Git runtime input failed: git {' '.join(args)}: {stderr}"
            )
        return (proc.stdout or "").strip()

    def create_execution_packet(
        self,
        stage_id: str | None = None,
        *,
        semantic_inputs: dict[str, Any] | None = None,
        stage_instructions: str | None = None,
    ) -> Path:
        request = self.build_request(
            stage_id,
            semantic_inputs=semantic_inputs,
            stage_instructions=stage_instructions,
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.repo_root / ".sdd" / "runs" / f"{stamp}-stage-{request.stage_id}"
        run_dir.mkdir(parents=True, exist_ok=False)
        packet = run_dir / "request.json"
        packet.write_text(
            json.dumps(request.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return packet

    def _prepare_explicit_rerun(self, stage_id: str | None) -> None:
        """Reconcile lifecycle state before an explicitly requested upstream rerun.

        Historical run records and Git checkpoints remain untouched. The mutable
        lifecycle projection, however, must describe the new attempt: the rerun
        stage becomes IN_PROGRESS and downstream stages are invalidated back to
        TODO so stale authorization/progress cannot leak across remediation.
        """
        if stage_id is None:
            return
        sid = str(stage_id).zfill(2)
        if sid not in self.orchestrator.project_state.get("stages", {}):
            return

        state = self.orchestrator.project_state
        current = str(state.get("lifecycle", {}).get("current_stage", sid)).zfill(2)
        downstream_has_progress = any(
            str(ds).isdigit()
            and int(ds) > int(sid)
            and (info.get("status") not in {None, "TODO"} or info.get("result") is not None)
            for ds, info in state.get("stages", {}).items()
            if str(ds).isdigit()
        )
        # Normal controller execution supplies the current stage explicitly too.
        # Do not rewrite state unless this is actually a rerun/recovery scenario.
        if current == sid and not downstream_has_progress:
            return

        state["lifecycle"]["current_stage"] = sid
        state["lifecycle"]["current_stage_name"] = self.orchestrator.get_stage(sid)["name"]
        state["lifecycle"]["next_action"] = "RUN_STAGE"
        state["stages"][sid]["status"] = "IN_PROGRESS"
        state["stages"][sid]["result"] = None

        for ds, info in state.get("stages", {}).items():
            if str(ds).isdigit() and int(ds) > int(sid):
                info["status"] = "TODO"
                info["result"] = None

        if int(sid) <= 7:
            state["authorizations"]["implementation"] = False
        if int(sid) <= 10:
            state["authorizations"]["release"] = False

        # A previous gate/blocking projection is historical once an authorized
        # remediation rerun has begun. Authority-state conflict/TBD records remain
        # separate and are not erased here.
        state["blocking"]["is_blocked"] = False
        state["blocking"]["reasons"] = []
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)

    def run(
        self,
        executor: StageExecutor,
        stage_id: str | None = None,
        *,
        semantic_inputs: dict[str, Any] | None = None,
        stage_instructions: str | None = None,
    ) -> dict[str, Any]:
        self._prepare_explicit_rerun(stage_id)
        request = self.build_request(
            stage_id,
            semantic_inputs=semantic_inputs,
            stage_instructions=stage_instructions,
        )
        result = executor.execute(request)
        self._validate_result(request, result)
        written = self._write_outputs_atomically(result.artifacts)
        convergence_written = self._persist_convergence_tasks(request, result)
        transition = self._apply_transition(request, result)
        self._record_run(request, result, transition)
        self._update_artifact_registry(written)
        return {
            "stage_id": request.stage_id,
            "stage_name": request.stage_name,
            "executor_status": result.status,
            "written_artifacts": written,
            "convergence_tasks": convergence_written,
            "stage_result": result.result,
            "classification": result.classification,
            "transition": transition,
        }

    def _persist_convergence_tasks(
        self, request: StageExecutionRequest, result: StageExecutionResult
    ) -> list[str]:
        if not result.convergence_tasks:
            return []
        if not (request.stage_id == "09" and result.result == "FAIL" and result.classification == "IMPLEMENTATION_GAP"):
            raise StageExecutionValidationError(
                "Convergence tasks are only allowed for Stage 09 IMPLEMENTATION_GAP"
            )
        root = self.repo_root / ".sdd" / "convergence"
        root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        import yaml
        import re
        for task in result.convergence_tasks:
            task_id = str(task.get("task_id", "")).upper()
            if not re.fullmatch(r"TC\d{3,5}", task_id):
                raise StageExecutionValidationError(f"Invalid convergence task id: {task_id}")
            if not task.get("allowed_paths") or not task.get("verification_commands"):
                raise StageExecutionValidationError(
                    f"{task_id} requires explicit allowed_paths and verification_commands"
                )
            payload = dict(task)
            payload["status"] = "TODO"
            payload["source_stage"] = "09"
            rel = f".sdd/convergence/{task_id}.yaml"
            (self.repo_root / rel).write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            written.append(rel)
        return written

    def _validate_result(
        self, request: StageExecutionRequest, result: StageExecutionResult
    ) -> None:
        if result.status not in {"COMPLETED", "BLOCKED"}:
            raise StageExecutionValidationError(
                f"Unsupported executor status: {result.status}"
            )

        declared_files = request.contract.get("outputs", {}).get("files", []) or []
        if result.status == "COMPLETED":
            missing_outputs = [p for p in declared_files if p not in result.artifacts]
            if missing_outputs:
                raise StageExecutionValidationError(
                    f"Executor omitted required declared outputs: {missing_outputs}"
                )
        self._validate_write_scope(request, result)

        vocab = request.contract.get("result_vocabulary", []) or []
        if vocab:
            if result.result is None:
                raise StageExecutionValidationError(
                    f"Stage {request.stage_id} must return a formal result from {vocab}"
                )
            if result.result not in vocab:
                raise StageExecutionValidationError(
                    f"Invalid Stage {request.stage_id} result {result.result!r}; allowed={vocab}"
                )

        if request.stage_id == "09" and result.result == "FAIL":
            if result.classification not in {
                "IMPLEMENTATION_GAP",
                "AUTHORITY_CONTRACT_CONFLICT",
            }:
                raise StageExecutionValidationError(
                    "Stage 09 FAIL requires IMPLEMENTATION_GAP or AUTHORITY_CONTRACT_CONFLICT classification"
                )
            if result.classification == "IMPLEMENTATION_GAP" and not result.convergence_tasks:
                raise StageExecutionValidationError(
                    "Stage 09 IMPLEMENTATION_GAP requires at least one TC convergence task"
                )
            if result.classification == "AUTHORITY_CONTRACT_CONFLICT" and result.convergence_tasks:
                raise StageExecutionValidationError(
                    "Authority/contract conflict must not be converted into TC convergence tasks"
                )


    def _validate_write_scope(
        self, request: StageExecutionRequest, result: StageExecutionResult
    ) -> None:
        if request.stage_id == "08":
            # Stage 08 file-scope enforcement belongs to the Codex/AGENTS adapter (M5).
            return
        allowed_exact = set(request.contract.get("outputs", {}).get("files", []) or [])
        allowed_patterns = set(request.contract.get("outputs", {}).get("optional_files", []) or [])
        allowed_patterns.update(request.contract.get("optional_files", []) or [])
        for rel in result.artifacts:
            if rel in allowed_exact:
                continue
            if any(fnmatch.fnmatch(rel, pat) for pat in allowed_patterns):
                continue
            raise StageExecutionValidationError(
                f"Stage {request.stage_id} executor attempted unauthorized output: {rel}"
            )

    def _write_outputs_atomically(self, artifacts: dict[str, str]) -> list[str]:
        written: list[str] = []
        for rel, content in artifacts.items():
            target = (self.repo_root / rel).resolve()
            try:
                target.relative_to(self.repo_root)
            except ValueError as exc:
                raise StageExecutionValidationError(
                    f"Executor attempted write outside repository: {rel}"
                ) from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", dir=target.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_name, target)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            written.append(rel)
        return written

    def _apply_transition(
        self, request: StageExecutionRequest, result: StageExecutionResult
    ) -> dict[str, Any]:
        sid = request.stage_id
        stage_type = request.stage_type

        if result.status == "BLOCKED":
            state = self.orchestrator.project_state
            state["stages"][sid]["status"] = "BLOCKED"
            if sid == "10":
                state["authorizations"]["release"] = False
            state["blocking"]["is_blocked"] = True
            state["blocking"]["reasons"] = result.remediation_reasons or ["EXECUTOR_BLOCKED"]
            state["lifecycle"]["next_action"] = "REMEDIATION_ROUTER"
            self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)
            return {"next": "REMEDIATION_ROUTER", "blocked": True}

        if stage_type in {"GATE", "GATE_WITH_CONVERGENCE", "RELEASE_GATE"}:
            return self.orchestrator.record_stage_result(
                sid, result.result, classification=result.classification
            )

        if sid == "08":
            return self._advance(sid, request.contract.get("next", {}).get("completed", "09"))

        return self._advance(sid, request.contract.get("next", {}).get("success"))

    def _advance(self, sid: str, next_stage: str | None) -> dict[str, Any]:
        state = self.orchestrator.project_state
        state["stages"][sid]["status"] = "DONE"
        state["stages"][sid]["result"] = "COMPLETED"
        if next_stage and str(next_stage).isdigit():
            nxt = str(next_stage).zfill(2)
            state["lifecycle"]["last_completed_stage"] = sid
            state["lifecycle"]["current_stage"] = nxt
            state["lifecycle"]["current_stage_name"] = self.orchestrator.get_stage(nxt)["name"]
            state["lifecycle"]["next_action"] = "RUN_STAGE"
            state["stages"][nxt]["status"] = "IN_PROGRESS"
            route = nxt
        else:
            state["lifecycle"]["next_action"] = str(next_stage or "STOP")
            route = str(next_stage or "STOP")
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)
        return {"stage_id": sid, "result": "COMPLETED", "next": route}

    def _record_run(
        self,
        request: StageExecutionRequest,
        result: StageExecutionResult,
        transition: dict[str, Any],
    ) -> None:
        runs = self.repo_root / ".sdd" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        path = runs / f"{stamp}-stage-{request.stage_id}.json"
        payload = {
            "request_summary": {
                "stage_id": request.stage_id,
                "stage_name": request.stage_name,
                "artifact_paths": sorted(request.artifacts.keys()),
                "semantic_input_keys": sorted(request.semantic_inputs.keys()),
                "has_stage_instructions": bool(request.stage_instructions),
            },
            "result": asdict(result),
            "transition": transition,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _update_artifact_registry(self, written: list[str]) -> None:
        key_by_path = {
            "docs/proposal.md": "proposal",
            "docs/PRD.md": "prd",
            "docs/spec.md": "spec",
            "docs/Design.md": "design",
            "AGENTS.md": "agents",
            "tasks.md": "tasks",
            "docs/handoff/pre-implementation-gate-report.md": "pre_implementation_gate_report",
            "docs/handoff/verification-report.md": "verification_report",
            "docs/handoff/handoff-report.md": "handoff_report",
        }
        state = self.orchestrator.project_state
        changed = False
        for rel in written:
            key = key_by_path.get(rel)
            if key:
                state.setdefault("artifacts", {})[key] = rel
                changed = True
        if changed:
            self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)
