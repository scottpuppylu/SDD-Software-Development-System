"""Durable, scoped Human Decision records (TASK-006 / DES-005)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid

import yaml

from .core import Orchestrator, SDDOrchestratorError


class DecisionGatewayError(SDDOrchestratorError):
    pass


PENDING = "PENDING"
FINAL_STATUSES = {"APPROVED", "REJECTED", "REVISION_REQUESTED", "WITHDRAWN"}
ALL_STATUSES = {PENDING, *FINAL_STATUSES}


@dataclass
class DecisionEvent:
    sequence: int
    status: str
    result: str | None
    actor: str
    reference: str
    recorded_at: str
    record_version: int
    reason: str | None = None
    invalidated_dependents: list[str] = field(default_factory=list)


@dataclass
class DecisionRequest:
    decision_id: str
    status: str
    created_at: str
    resolved_at: str | None
    decision_type: str
    source_stage: str
    authority_domains: list[str]
    owner_stages: list[str]
    question: str
    context: str
    options: list[str]
    risk: str
    affected_artifacts: list[str]
    resolution: str | None
    resolution_note: str | None
    consequence: str = "Affected work remains paused until an explicit decision is recorded."
    dependencies: list[str] = field(default_factory=list)
    independent_scope: list[str] = field(default_factory=list)
    invalidated_dependents: list[str] = field(default_factory=list)
    target_version: str = "UNSPECIFIED"
    record_version: int = 1
    events: list[DecisionEvent] = field(default_factory=list)

    @property
    def subject(self) -> str:
        return self.question

    @property
    def affected_scope(self) -> list[str]:
        return self.affected_artifacts

    def presentation(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "subject": self.subject,
            "needed_from": self.owner_stages,
            "why": self.context,
            "effect": self.consequence,
            "choices": list(self.options),
            "status": self.status,
            "result": self.resolution,
            "affected_scope": list(self.affected_scope),
        }


class DecisionGateway:
    ALLOWED_TYPES = {
        "PRODUCT_DECISION", "AUTHORITY_CONFLICT", "BLOCKING_TBD",
        "HIGH_RISK_OPERATION", "RELEASE_DECISION",
    }
    ALLOWED_RISK = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.repo_root = orchestrator.repo_root
        self.root = self.repo_root / ".sdd" / "decisions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.failures: list[dict[str, Any]] = []

    def create(self, *, decision_type: str, source_stage: str,
               authority_domains: list[str], question: str, context: str,
               options: list[str] | None = None, risk: str = "MEDIUM",
               affected_artifacts: list[str] | None = None,
               consequence: str | None = None, dependencies: list[str] | None = None,
               independent_scope: list[str] | None = None,
               target_version: str = "UNSPECIFIED",
               decision_id: str | None = None) -> DecisionRequest:
        decision_type, risk = decision_type.upper(), risk.upper()
        scope = self._bounded(affected_artifacts, "Affected scope")
        choices = self._bounded(options, "Available choices")
        domains = self._bounded(authority_domains, "Authority domains")
        if decision_type not in self.ALLOWED_TYPES:
            raise DecisionGatewayError(f"Unsupported decision type: {decision_type}")
        if risk not in self.ALLOWED_RISK:
            raise DecisionGatewayError(f"Unsupported decision risk: {risk}")
        if not question.strip():
            raise DecisionGatewayError("Decision subject is required")
        if not context.strip():
            raise DecisionGatewayError("Decision reason is required")
        owners = sorted({self.orchestrator.authority_owner(d) for d in domains})
        identity = decision_id or f"HD-{uuid.uuid4().hex.upper()}"
        path = self.root / f"{identity}.yaml"
        if not identity.startswith("HD-") or path.exists():
            raise DecisionGatewayError(f"Human Decision identity collision or invalid identity: {identity}")
        now = self._now()
        req = DecisionRequest(
            identity, PENDING, now, None, decision_type, source_stage.zfill(2),
            domains, owners, question.strip(), context.strip(), choices, risk, scope,
            None, None, consequence.strip() if consequence else
            "Affected work is paused; the recorded outcome governs only this named condition.",
            self._clean(dependencies), self._clean(independent_scope), [],
            str(target_version).strip() or "UNSPECIFIED", 1,
            [DecisionEvent(1, PENDING, None, source_stage.zfill(2),
                           f"CREATE:{identity}", now, 1, context.strip())],
        )
        self._write(req)
        self._mark_project_waiting(req)
        return req

    def create_authority_conflict(self, *, source_stage: str, domains: list[str],
                                  question: str, context: str,
                                  affected_artifacts: list[str] | None = None) -> DecisionRequest:
        return self.create(decision_type="AUTHORITY_CONFLICT", source_stage=source_stage,
                           authority_domains=domains, question=question, context=context,
                           options=["APPROVE", "REJECT", "REQUEST_REVISION"], risk="HIGH",
                           affected_artifacts=affected_artifacts)

    def list(self, *, status: str | None = None) -> list[DecisionRequest]:
        requested = status.upper() if status else None
        records = [self._read(path) for path in sorted(self.root.glob("HD-*.yaml"))]
        if requested == "OPEN":
            requested = PENDING
        if requested == "RESOLVED":
            return [record for record in records if record.status in FINAL_STATUSES]
        return [record for record in records if requested is None or record.status == requested]

    def get(self, decision_id: str) -> DecisionRequest:
        path = self.root / f"{decision_id}.yaml"
        if not path.exists():
            raise DecisionGatewayError(f"Human Decision not found: {decision_id}")
        return self._read(path)

    def resolve(self, decision_id: str, *, resolution: str, actor: str | None = None,
                reference: str | None = None, expected_version: int | None = None,
                expected_target_version: str | None = None,
                note: str | None = None) -> DecisionRequest:
        req = self.get(decision_id)
        if req.status not in {PENDING, "APPROVED"}:
            raise DecisionGatewayError(f"Human Decision cannot transition from {req.status}: {decision_id}")
        if expected_version != req.record_version:
            raise DecisionGatewayError("Stale Human Decision record version")
        if expected_target_version != req.target_version:
            raise DecisionGatewayError("Stale Human Decision target")
        actor_id = str(actor or "").zfill(2)
        if actor_id not in req.owner_stages:
            raise DecisionGatewayError("Decision actor is not an authoritative owner")
        if not reference or not reference.strip():
            raise DecisionGatewayError("Decision actor reference is required")
        raw = resolution.strip().upper()
        aliases = {"APPROVE": "APPROVED", "REJECT": "REJECTED",
                   "REQUEST_REVISION": "REVISION_REQUESTED", "WITHDRAW": "WITHDRAWN"}
        status = aliases.get(raw, raw)
        if status not in FINAL_STATUSES:
            raise DecisionGatewayError(f"Ambiguous Human Decision result: {resolution!r}")
        if req.status == "APPROVED" and status not in {"REVISION_REQUESTED", "WITHDRAWN"}:
            raise DecisionGatewayError("An approved decision may only be revised or withdrawn")
        declared = {aliases.get(choice.upper(), choice.upper()) for choice in req.options}
        if declared and status not in declared:
            raise DecisionGatewayError(f"Result must be one of the declared choices: {req.options}")
        now = self._now()
        invalidated = list(req.dependencies) if status in {"REVISION_REQUESTED", "WITHDRAWN"} else []
        updated = DecisionRequest(**{**asdict(req), "status": status, "resolution": status,
            "resolution_note": note.strip() if note else None, "resolved_at": now,
            "record_version": req.record_version + 1,
            "invalidated_dependents": invalidated,
            "events": [*req.events, DecisionEvent(len(req.events) + 1, status, status,
                actor_id, reference.strip(), now, req.record_version + 1,
                note.strip() if note else None, invalidated)]})
        self._write(updated)
        self._record_resolution_for_owner(updated)
        self._refresh_project_waiting_state(updated)
        return updated

    def semantic_input_for_owner(self, decision_id: str) -> dict[str, Any]:
        req = self.get(decision_id)
        if req.status not in FINAL_STATUSES:
            raise DecisionGatewayError("Decision must have an explicit result")
        return {"HUMAN_DECISION_ID": req.decision_id, "DECISION_REQUEST_ID": req.decision_id,
                "DECISION_TYPE": req.decision_type, "AUTHORITY_DOMAINS": req.authority_domains,
                "HUMAN_RESOLUTION": req.resolution, "RESOLUTION_NOTE": req.resolution_note,
                "AFFECTED_ARTIFACTS": req.affected_artifacts,
                "IMPLEMENTATION_AUTHORIZATION": False}

    def _record_resolution_for_owner(self, req: DecisionRequest) -> None:
        state = self.orchestrator.authority_state
        state.setdefault("resolved_human_decisions", []).append({
            "decision_id": req.decision_id, "status": req.status,
            "authority_domains": req.authority_domains, "owner_stages": req.owner_stages,
            "resolution": req.resolution, "record_version": req.record_version,
            "resolved_at": req.resolved_at, "invalidated_dependents": req.invalidated_dependents,
        })
        self.orchestrator._save_yaml(self.orchestrator.authority_state_path, state)

    def _mark_project_waiting(self, req: DecisionRequest) -> None:
        state = self.orchestrator.project_state
        state["blocking"]["is_blocked"] = True
        reasons = list(state["blocking"].get("reasons", []))
        marker = f"HUMAN_DECISION:{req.decision_id}"
        if marker not in reasons:
            reasons.append(marker)
        state["blocking"]["reasons"] = reasons
        state["lifecycle"]["next_action"] = "WAIT_FOR_HUMAN_DECISION"
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)

    def _refresh_project_waiting_state(self, req: DecisionRequest) -> None:
        pending = {d.decision_id for d in self.list(status=PENDING)}
        state = self.orchestrator.project_state
        state["blocking"]["reasons"] = [r for r in state["blocking"].get("reasons", [])
            if not (str(r).startswith("HUMAN_DECISION:") and str(r).split(":", 1)[1] not in pending)]
        if req.status in {"REJECTED", "REVISION_REQUESTED", "WITHDRAWN"}:
            state["blocking"]["reasons"].append(f"HUMAN_DECISION_{req.status}:{req.decision_id}")
        state["blocking"]["is_blocked"] = bool(state["blocking"]["reasons"])
        state["lifecycle"]["next_action"] = (
            "RERUN_AUTHORITATIVE_OWNER" if req.status in {"APPROVED", "REVISION_REQUESTED", "WITHDRAWN"}
            else "STOP_REJECTED")
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)

    def _write(self, req: DecisionRequest) -> None:
        path = self.root / f"{req.decision_id}.yaml"
        temporary: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=self.root)
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                yaml.safe_dump(asdict(req), stream, sort_keys=False, allow_unicode=True)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
        except Exception as exc:
            self.failures.append({"decision_id": req.decision_id, "status": "BLOCKED",
                                  "failure": "PERSISTENCE_FAILURE",
                                  "route": "RETRY_OR_ROUTE_TO_REPOSITORY_OWNER"})
            raise DecisionGatewayError(f"Human Decision persistence failed; prior state retained: {exc}") from exc
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    @staticmethod
    def _read(path: Path) -> DecisionRequest:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["events"] = [DecisionEvent(**event) for event in data.get("events", [])]
        return DecisionRequest(**data)

    @staticmethod
    def _clean(values: list[str] | None) -> list[str]:
        return list(dict.fromkeys(str(value).strip() for value in (values or []) if str(value).strip()))

    @classmethod
    def _bounded(cls, values: list[str] | None, label: str) -> list[str]:
        clean = cls._clean(values)
        if not clean:
            raise DecisionGatewayError(f"{label} must be explicit and non-empty")
        return clean

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
