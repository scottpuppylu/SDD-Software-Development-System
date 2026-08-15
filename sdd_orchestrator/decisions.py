from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re
import uuid

import yaml

from .core import Orchestrator, SDDOrchestratorError


class DecisionGatewayError(SDDOrchestratorError):
    pass


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


class DecisionGateway:
    ALLOWED_TYPES = {
        "PRODUCT_DECISION",
        "AUTHORITY_CONFLICT",
        "BLOCKING_TBD",
        "HIGH_RISK_OPERATION",
        "RELEASE_DECISION",
    }
    ALLOWED_RISK = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.repo_root = orchestrator.repo_root
        self.root = self.repo_root / ".sdd" / "decisions"
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        decision_type: str,
        source_stage: str,
        authority_domains: list[str],
        question: str,
        context: str,
        options: list[str] | None = None,
        risk: str = "MEDIUM",
        affected_artifacts: list[str] | None = None,
    ) -> DecisionRequest:
        decision_type = decision_type.upper()
        risk = risk.upper()
        if decision_type not in self.ALLOWED_TYPES:
            raise DecisionGatewayError(f"Unsupported decision type: {decision_type}")
        if risk not in self.ALLOWED_RISK:
            raise DecisionGatewayError(f"Unsupported decision risk: {risk}")
        if not question.strip():
            raise DecisionGatewayError("Decision question is required")
        if not authority_domains:
            raise DecisionGatewayError("At least one authority domain is required")

        owners = sorted({self.orchestrator.authority_owner(d) for d in authority_domains})
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        short = uuid.uuid4().hex[:8].upper()
        decision_id = f"DR-{stamp}-{short}"
        req = DecisionRequest(
            decision_id=decision_id,
            status="OPEN",
            created_at=datetime.now(timezone.utc).isoformat(),
            resolved_at=None,
            decision_type=decision_type,
            source_stage=source_stage.zfill(2),
            authority_domains=authority_domains,
            owner_stages=owners,
            question=question.strip(),
            context=context.strip(),
            options=options or [],
            risk=risk,
            affected_artifacts=affected_artifacts or [],
            resolution=None,
            resolution_note=None,
        )
        self._write(req)
        self._mark_project_waiting(req)
        return req

    def create_authority_conflict(
        self,
        *,
        source_stage: str,
        domains: list[str],
        question: str,
        context: str,
        affected_artifacts: list[str] | None = None,
    ) -> DecisionRequest:
        return self.create(
            decision_type="AUTHORITY_CONFLICT",
            source_stage=source_stage,
            authority_domains=domains,
            question=question,
            context=context,
            risk="HIGH",
            affected_artifacts=affected_artifacts,
        )

    def list(self, *, status: str | None = None) -> list[DecisionRequest]:
        out: list[DecisionRequest] = []
        for path in sorted(self.root.glob("DR-*.yaml")):
            req = self._read(path)
            if status is None or req.status == status.upper():
                out.append(req)
        return out

    def get(self, decision_id: str) -> DecisionRequest:
        path = self.root / f"{decision_id}.yaml"
        if not path.exists():
            raise DecisionGatewayError(f"Decision request not found: {decision_id}")
        return self._read(path)

    def resolve(
        self,
        decision_id: str,
        *,
        resolution: str,
        note: str | None = None,
    ) -> DecisionRequest:
        req = self.get(decision_id)
        if req.status != "OPEN":
            raise DecisionGatewayError(f"Decision request is not OPEN: {decision_id}")
        if not resolution.strip():
            raise DecisionGatewayError("Resolution is required")
        if req.options and resolution not in req.options:
            raise DecisionGatewayError(
                f"Resolution must be one of the declared options: {req.options}"
            )
        req.status = "RESOLVED"
        req.resolution = resolution.strip()
        req.resolution_note = note.strip() if note else None
        req.resolved_at = datetime.now(timezone.utc).isoformat()
        self._write(req)
        self._record_resolution_for_owner(req)
        self._refresh_project_waiting_state()
        return req

    def semantic_input_for_owner(self, decision_id: str) -> dict[str, Any]:
        req = self.get(decision_id)
        if req.status != "RESOLVED":
            raise DecisionGatewayError("Decision must be resolved before it can be supplied to a stage")
        return {
            "DECISION_REQUEST_ID": req.decision_id,
            "DECISION_TYPE": req.decision_type,
            "AUTHORITY_DOMAINS": req.authority_domains,
            "HUMAN_RESOLUTION": req.resolution,
            "RESOLUTION_NOTE": req.resolution_note,
            "AFFECTED_ARTIFACTS": req.affected_artifacts,
        }

    def _record_resolution_for_owner(self, req: DecisionRequest) -> None:
        state = self.orchestrator.authority_state
        state.setdefault("resolved_human_decisions", [])
        state["resolved_human_decisions"].append({
            "decision_id": req.decision_id,
            "decision_type": req.decision_type,
            "authority_domains": req.authority_domains,
            "owner_stages": req.owner_stages,
            "resolution": req.resolution,
            "resolved_at": req.resolved_at,
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

    def _refresh_project_waiting_state(self) -> None:
        open_ids = {d.decision_id for d in self.list(status="OPEN")}
        state = self.orchestrator.project_state
        reasons = [
            r for r in state["blocking"].get("reasons", [])
            if not (str(r).startswith("HUMAN_DECISION:") and str(r).split(":", 1)[1] not in open_ids)
        ]
        state["blocking"]["reasons"] = reasons
        if not open_ids:
            state["blocking"]["is_blocked"] = bool(reasons)
            if not reasons:
                # A resolved decision does not itself authorize implementation;
                # rerun the authoritative owner stage.
                state["lifecycle"]["next_action"] = "RERUN_AUTHORITATIVE_OWNER"
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)

    def _write(self, req: DecisionRequest) -> None:
        path = self.root / f"{req.decision_id}.yaml"
        path.write_text(yaml.safe_dump(asdict(req), sort_keys=False, allow_unicode=True), encoding="utf-8")

    @staticmethod
    def _read(path: Path) -> DecisionRequest:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return DecisionRequest(**data)
