from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

from .core import (
    LifecycleAggregate,
    LifecycleGovernor,
    LifecycleInvariantError,
    Orchestrator,
    ScopedCondition,
)
from .executor import StageExecutor
from .runner import StageRunner
from .codex_adapter import Stage08CodexRunner
from .decisions import DecisionGateway
from .git_runtime import GitRepository
from .context_compiler import CompilationMode


@dataclass
class SystemRunSummary:
    start_stage: str
    end_stage: str
    status: str
    events: list[dict[str, Any]] = field(default_factory=list)
    open_decisions: list[dict[str, Any]] = field(default_factory=list)


LIFECYCLE_ACTIONS = {
    "PAUSE",
    "RESUME",
    "REQUEST_REVISION",
    "REJECT_PROPOSAL",
    "APPROVE_DECISION",
}

GOVERNED_OPERATIONS = frozenset({
    "SUBMIT_REQUEST", "INSPECT_STATUS", "CONTINUE_OR_RESUME", "PAUSE",
    "RECEIVE_DECISION", "APPROVE", "REJECT", "REQUEST_REVISION",
    "RECEIVE_FAILURE_OR_BLOCKER", "RECEIVE_VERIFICATION_SUMMARY",
})

APPROVED_INTAKE_FORMS = frozenset({
    "PLAIN_LANGUAGE", "DOCUMENT", "IMAGE_OR_UI_REFERENCE",
    "WEBSITE_OR_SYSTEM_REFERENCE", "MODIFICATION_REQUEST",
})


@dataclass(frozen=True)
class GovernedOperationRequest:
    journey_identity: str
    command_identity: str
    operation: str
    target_identity: str
    payload: dict[str, Any] = field(default_factory=dict)
    expected_snapshot_identity: str | None = None


@dataclass(frozen=True)
class GovernedOperationResult:
    journey_identity: str
    command_identity: str
    operation: str
    target_identity: str
    snapshot_identity: str
    accepted: bool
    command_committed: bool
    duplicate: bool
    delivery_succeeded: bool
    situation: str
    consequence: str
    required_user_action: str
    next_route: str
    data: dict[str, Any] = field(default_factory=dict)


class ChannelNeutralOperationPort:
    """Repository-backed governed operations, independent of presentation channel."""

    SCHEMA_VERSION = "1.0"
    MAX_TEXT = 100_000

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.repo_root = orchestrator.repo_root
        self.journal_path = self.repo_root / ".sdd" / "state" / "local-mvp-operations.json"
        self.decisions = DecisionGateway(orchestrator)

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _identity(cls, value: Any) -> str:
        return hashlib.sha256(cls._canonical(value).encode("utf-8")).hexdigest()

    def _load(self) -> dict[str, Any]:
        if not self.journal_path.exists():
            return {"schema_version": self.SCHEMA_VERSION, "journeys": {}, "commands": {}}
        value = json.loads(self.journal_path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != self.SCHEMA_VERSION
            or not isinstance(value.get("journeys"), dict)
            or not isinstance(value.get("commands"), dict)
        ):
            raise LifecycleInvariantError("local operation journal is malformed or unsupported")
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(
            prefix=".local-mvp-operations-", suffix=".tmp", dir=self.journal_path.parent
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.journal_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _snapshot_identity(self, journal: dict[str, Any]) -> str:
        implementation_path = self.repo_root / ".sdd" / "state" / "implementation-state.yaml"
        implementation = implementation_path.read_text(encoding="utf-8") if implementation_path.exists() else ""
        durable = {
            "project_state": self.orchestrator.project_state,
            "implementation_state_sha256": hashlib.sha256(implementation.encode("utf-8")).hexdigest(),
            "journeys": journal["journeys"],
            "decisions": [asdict(item) for item in self.decisions.list()],
        }
        return self._identity(durable)

    def _validate(self, request: GovernedOperationRequest) -> str:
        required = (
            request.journey_identity, request.command_identity,
            request.operation, request.target_identity,
        )
        if not all(isinstance(item, str) and item.strip() for item in required):
            raise LifecycleInvariantError("malformed governed operation identity")
        operation = request.operation.strip().upper()
        if operation not in GOVERNED_OPERATIONS:
            raise LifecycleInvariantError(f"unsupported governed operation: {operation}")
        if not isinstance(request.payload, dict):
            raise LifecycleInvariantError("operation payload must be an object")
        if len(self._canonical(request.payload)) > self.MAX_TEXT:
            raise LifecycleInvariantError("operation payload exceeds the bounded local limit")
        return operation

    def execute(self, request: GovernedOperationRequest) -> GovernedOperationResult:
        operation = self._validate(request)
        journal = self._load()
        fingerprint = self._identity({
            "journey_identity": request.journey_identity,
            "command_identity": request.command_identity,
            "operation": operation,
            "target_identity": request.target_identity,
            "payload": request.payload,
            "expected_snapshot_identity": request.expected_snapshot_identity,
        })
        prior = journal["commands"].get(request.command_identity)
        if prior is not None:
            if prior.get("fingerprint") != fingerprint:
                raise LifecycleInvariantError("command identity was already used for different content")
            return GovernedOperationResult(**{**prior["result"], "duplicate": True})

        before_identity = self._snapshot_identity(journal)
        if (
            request.expected_snapshot_identity is not None
            and request.expected_snapshot_identity != before_identity
        ):
            raise LifecycleInvariantError(
                f"stale operation snapshot: {request.expected_snapshot_identity} != {before_identity}"
            )

        working = copy.deepcopy(journal)
        situation, consequence, action, route, data = self._apply(
            operation, request, working
        )
        snapshot_identity = self._snapshot_identity(working)
        result = GovernedOperationResult(
            request.journey_identity, request.command_identity, operation,
            request.target_identity, snapshot_identity, True, True, False, True,
            situation, consequence, action, route, data,
        )
        working["commands"][request.command_identity] = {
            "fingerprint": fingerprint,
            "result": asdict(result),
        }
        self._write(working)
        return result

    def _journey(self, journal: dict[str, Any], request: GovernedOperationRequest) -> dict[str, Any]:
        journey = journal["journeys"].get(request.journey_identity)
        if not isinstance(journey, dict):
            raise LifecycleInvariantError("journey is not repository-backed; submit it first")
        return journey

    def _implementation_state(self) -> dict[str, Any]:
        path = self.repo_root / ".sdd" / "state" / "implementation-state.yaml"
        if not path.exists():
            return {}
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _governed_status(self, journey: dict[str, Any]) -> dict[str, Any]:
        project = self.orchestrator.project_state
        implementation = self._implementation_state()
        blocking = copy.deepcopy(project.get("blocking", {}))
        pending = [item.presentation() for item in self.decisions.list(status="PENDING")]
        qualifications = implementation.get("task_qualifications") or {}
        current = implementation.get("current_task")
        next_task = implementation.get("next_task")
        authorized = bool(project.get("authorizations", {}).get("implementation"))
        return {
            "current_stage": self.orchestrator.stage_summary(),
            "completed_work": sorted(qualifications),
            "current_work": [current] if current else [],
            "next_work": [next_task] if next_task else [],
            "journey_status": journey["status"],
            "blocked_or_incomplete": blocking,
            "pending_human_decisions": pending,
            "authority": {
                "approved": copy.deepcopy(project.get("provenance", {}).get("current_authority_package", {})),
                "unapproved_or_conflicting": {
                    "conflicts": copy.deepcopy(self.orchestrator.authority_state.get("unresolved_conflicts", [])),
                    "blocking_tbds": copy.deepcopy(self.orchestrator.authority_state.get("blocking_tbds", [])),
                },
            },
            "implementation_authorized": authorized,
            "execution_may_continue": bool(
                authorized and not blocking.get("is_blocked") and journey["status"] != "PAUSED"
            ),
            "next_action": project["lifecycle"]["next_action"],
        }

    def _apply(
        self, operation: str, request: GovernedOperationRequest,
        journal: dict[str, Any],
    ) -> tuple[str, str, str, str, dict[str, Any]]:
        payload = request.payload
        if operation == "SUBMIT_REQUEST":
            intake = str(payload.get("intake_form", "")).upper()
            content = payload.get("content")
            if intake not in APPROVED_INTAKE_FORMS or not isinstance(content, str) or not content.strip():
                raise LifecycleInvariantError("submit requires a supported intake_form and non-empty content")
            if request.journey_identity in journal["journeys"]:
                raise LifecycleInvariantError("journey identity already exists")
            missing = list(payload.get("missing_information") or ["desired outcome", "success criteria"])
            questions = list(payload.get("clarification_questions") or [
                "What outcome should this request achieve?",
                "How will you decide that the result is acceptable?",
            ])
            journal["journeys"][request.journey_identity] = {
                "target_identity": request.target_identity,
                "status": "CLARIFICATION_REQUIRED",
                "intake_form": intake,
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "missing_information": missing,
                "clarification_questions": questions,
                "failures": [],
            }
            return (
                "Your request was accepted and clarification has started.",
                "Implementation cannot begin until the listed material gaps are resolved.",
                "Answer the focused clarification questions.", "CLARIFY_REQUIREMENTS",
                {"intake_form": intake, "missing_information": missing,
                 "clarification_questions": questions},
            )

        journey = self._journey(journal, request)
        if operation == "INSPECT_STATUS":
            status = self._governed_status(journey)
            return (
                f"Journey {request.journey_identity} is {journey['status']}.",
                "The displayed lifecycle, authority, and blocker facts control what may continue.",
                "Follow the reported next route.", str(self.orchestrator.project_state["lifecycle"]["next_action"]),
                {"journey": copy.deepcopy(journey), "governed_status": status},
            )
        if operation == "PAUSE":
            journey["status"] = "PAUSED"
            return ("The journey is paused.", "No journey progression is eligible while paused.",
                    "Resume when you want eligible work to continue.", "WAIT_FOR_RESUME", {})
        if operation == "CONTINUE_OR_RESUME":
            blockers = self.orchestrator.project_state.get("blocking", {})
            if blockers.get("is_blocked"):
                raise LifecycleInvariantError("governed blockers prevent continuation")
            journey["status"] = "ACTIVE"
            return ("The journey is active.", "Only currently authorized and eligible work may continue.",
                    "Continue with the reported governed next step.",
                    str(self.orchestrator.project_state["lifecycle"]["next_action"]), {})
        if operation == "RECEIVE_DECISION":
            decision = self.decisions.get(request.target_identity)
            return ("A Human Decision requires attention.", decision.consequence,
                    "Choose only one of the displayed options.", "WAIT_FOR_HUMAN_DECISION",
                    {"decision": decision.presentation()})
        if operation in {"APPROVE", "REJECT", "REQUEST_REVISION"}:
            decision = self.decisions.get(request.target_identity)
            resolution = {"APPROVE": "APPROVE", "REJECT": "REJECT",
                          "REQUEST_REVISION": "REQUEST_REVISION"}[operation]
            updated = self.decisions.resolve(
                request.target_identity, resolution=resolution,
                actor=str(payload.get("actor", "")),
                reference=str(payload.get("reference", "")),
                expected_version=payload.get("expected_version"),
                expected_target_version=payload.get("expected_target_version"),
                note=payload.get("note"),
            )
            journey["status"] = (
                "DECISION_APPROVED" if updated.status == "APPROVED"
                else "REVISION_REQUIRED" if updated.status == "REVISION_REQUESTED"
                else "REJECTED"
            )
            return (f"The decision was recorded as {updated.status}.", updated.consequence,
                    "Follow the owner route shown in governed status.",
                    str(self.orchestrator.project_state["lifecycle"]["next_action"]),
                    {"decision": updated.presentation()})
        if operation == "RECEIVE_FAILURE_OR_BLOCKER":
            blockers = copy.deepcopy(self.orchestrator.project_state.get("blocking", {}))
            return ("The current failure or blocker state was retrieved.",
                    "Blocked scope must not continue; valid prior work remains preserved.",
                    "Use the named retry, owner, revision, or decision route.",
                    str(self.orchestrator.project_state["lifecycle"]["next_action"]),
                    {"blocking": blockers, "journey_failures": list(journey.get("failures", []))})
        implementation = self._implementation_state()
        outcome = str((implementation.get("test_status") or {}).get("overall") or "NOT RUN").upper()
        if outcome not in {"PASS", "FAIL", "NOT RUN"}:
            outcome = "NOT RUN"
        checks = payload.get("checks")
        if checks is None:
            checks = [{"check": "repository task verification", "outcome": outcome,
                       "behaviors": list(payload.get("requirements_with_evidence") or [])}]
        if not isinstance(checks, list) or not checks:
            raise LifecycleInvariantError("verification summary requires one or more checks")
        normalized_checks = []
        for item in checks:
            if not isinstance(item, dict) or not str(item.get("check", "")).strip():
                raise LifecycleInvariantError("verification check identity is required")
            check_outcome = str(item.get("outcome", "NOT RUN")).upper()
            if check_outcome not in {"PASS", "FAIL", "NOT RUN"}:
                raise LifecycleInvariantError("verification outcomes must be PASS, FAIL, or NOT RUN")
            normalized_checks.append({
                "check": str(item["check"]), "outcome": check_outcome,
                "behaviors": list(item.get("behaviors") or []),
            })
        evidence_behaviors = sorted({
            behavior for item in normalized_checks if item["outcome"] == "PASS"
            for behavior in item["behaviors"]
        })
        return ("The verification summary was retrieved.",
                "Verification evidence does not itself create Stage09 or release qualification.",
                "Review evidence gaps and the next governed gate.", "REVIEW_VERIFICATION_SUMMARY",
                {"outcome": "FAIL" if any(item["outcome"] == "FAIL" for item in normalized_checks)
                            else "NOT RUN" if any(item["outcome"] == "NOT RUN" for item in normalized_checks)
                            else "PASS",
                 "checks": normalized_checks,
                 "executed_checks": [item["check"] for item in normalized_checks if item["outcome"] != "NOT RUN"],
                 "unexecuted_checks": [item["check"] for item in normalized_checks if item["outcome"] == "NOT RUN"],
                 "requirements_with_evidence": evidence_behaviors,
                 "evidence_gaps": list(payload.get("evidence_gaps") or []),
                 "regression_risk": str(payload.get("regression_risk") or "Not established by this summary."),
                 "qualification": "NOT_EVALUATED_BY_STAGE09"})


class LocalMVPAdapter:
    """Local delivery adapter; delivery failure never rewrites committed effects."""

    def __init__(self, port: ChannelNeutralOperationPort):
        self.port = port

    def invoke(
        self, request: GovernedOperationRequest,
        *, deliver: Callable[[GovernedOperationResult], None] | None = None,
    ) -> GovernedOperationResult:
        result = self.port.execute(request)
        if deliver is None:
            return result
        try:
            deliver(result)
        except Exception:
            return replace(
                result, delivery_succeeded=False,
                consequence=(result.consequence + " The command committed, but local delivery failed."),
                required_user_action="Retry delivery with the same command identity or inspect status locally.",
                next_route="RETRY_DELIVERY_OR_INSPECT_STATUS",
            )
        return result


@dataclass(frozen=True)
class LifecycleOperationContext:
    actor_identity: str
    context_reference: str
    allowed_actions: tuple[str, ...]
    allowed_targets: tuple[str, ...]
    allowed_scope: tuple[str, ...]


@dataclass(frozen=True)
class LifecycleCommand:
    identity: str
    action: str
    target: str
    affected_scope: tuple[str, ...]
    expected_state_identity: str
    new_state_identity: str
    reason: str
    operation_context: LifecycleOperationContext
    dependent_scope: tuple[str, ...] = ()
    prerequisites_satisfied: bool = True


@dataclass(frozen=True)
class LifecycleCommandResult:
    command_identity: str
    action: str
    state_identity: str
    affected_scope: tuple[str, ...]
    next_route: str
    duplicate: bool = False


class LifecycleCommandProcessor:
    """Validate and apply explicit lifecycle commands against a fresh snapshot."""

    def __init__(self, governor: LifecycleGovernor):
        self.governor = governor

    @staticmethod
    def _metadata(command: LifecycleCommand) -> tuple[str, ...]:
        context = command.operation_context
        return (
            f"ACTION:{command.action}",
            f"TARGET:{command.target}",
            f"ACTOR:{context.actor_identity}",
            f"CONTEXT:{context.context_reference}",
            f"DEPENDENTS:{','.join(command.dependent_scope)}",
            f"PREREQUISITES:{command.prerequisites_satisfied}",
            "TASK-003",
            "SPEC-002",
            "DES-002",
        )

    def _validate(self, command: LifecycleCommand) -> None:
        context = command.operation_context
        required = (
            command.identity,
            command.action,
            command.target,
            command.affected_scope,
            command.expected_state_identity,
            command.new_state_identity,
            command.reason,
            context.actor_identity,
            context.context_reference,
        )
        if not all(required):
            raise LifecycleInvariantError("malformed lifecycle command")
        if command.action not in LIFECYCLE_ACTIONS:
            raise LifecycleInvariantError(f"unsupported lifecycle action: {command.action}")
        if command.action not in context.allowed_actions:
            raise LifecycleInvariantError("actor is not authorized for this lifecycle action")
        if command.target not in context.allowed_targets:
            raise LifecycleInvariantError("target is outside the authorized operation context")
        commanded_scope = set(command.affected_scope) | set(command.dependent_scope)
        if not commanded_scope <= set(context.allowed_scope):
            raise LifecycleInvariantError("affected scope is outside the authorized operation context")

    def process(self, command: LifecycleCommand) -> LifecycleCommandResult:
        self._validate(command)
        current = self.governor.snapshot()
        metadata = self._metadata(command)
        prior = next((t for t in current.transitions if t.identity == command.identity), None)
        if prior is not None:
            if (
                prior.affected_scope != command.affected_scope
                or prior.reason != command.reason
                or prior.sources != metadata
                or prior.prior_state_identity != command.expected_state_identity
                or prior.new_state_identity != command.new_state_identity
            ):
                raise LifecycleInvariantError("command identity was already used for different content")
            return LifecycleCommandResult(
                command.identity, command.action, prior.new_state_identity,
                command.affected_scope, prior.next_route, True,
            )
        if current.identity != command.expected_state_identity:
            raise LifecycleInvariantError(
                f"stale prior-state identity: {command.expected_state_identity} != {current.identity}"
            )

        proposed, route = self._project(current, command)
        accepted = self.governor.transition(
            proposed,
            expected_prior_identity=command.expected_state_identity,
            transition_identity=command.identity,
            affected_scope=command.affected_scope,
            reason=command.reason,
            sources=metadata,
            next_route=route,
        )
        return LifecycleCommandResult(
            command.identity, command.action, accepted.identity,
            command.affected_scope, route,
        )

    def _project(
        self, current: LifecycleAggregate, command: LifecycleCommand
    ) -> tuple[LifecycleAggregate, str]:
        metadata = self._metadata(command)
        affected = set(command.affected_scope)
        conditions = list(current.conditions)
        eligible = set(current.eligible_scope)
        invalidated = set(current.invalidated_scope)
        rerun = set(current.rerun_required)
        completed = set(current.completed_work)
        current_work = set(current.current_work)
        pending = list(current.pending_decisions)

        if command.action == "PAUSE":
            if any(c.status == "PAUSED" and c.scope in affected for c in conditions):
                raise LifecycleInvariantError("affected scope is already paused")
            conditions.extend(
                ScopedCondition("PAUSED", scope, command.reason, "RESUME", metadata)
                for scope in command.affected_scope
            )
            eligible -= affected
            route = "WAIT_FOR_RESUME"
        elif command.action == "RESUME":
            paused = {c.scope for c in conditions if c.status == "PAUSED"}
            if not affected <= paused:
                raise LifecycleInvariantError("resume target is not paused")
            if not command.prerequisites_satisfied:
                raise LifecycleInvariantError("resume prerequisites are not satisfied")
            if any(
                c.status == "PAUSED"
                and c.scope in affected
                and set(c.sources).intersection(pending)
                for c in conditions
            ):
                raise LifecycleInvariantError("pending decision still blocks affected scope")
            conditions = [
                c for c in conditions
                if not (c.status == "PAUSED" and c.scope in affected)
            ]
            still_affected = {c.scope for c in conditions} | invalidated
            eligible |= affected - still_affected
            route = "CONTINUE_ELIGIBLE_WORK"
        elif command.action in {"REQUEST_REVISION", "REJECT_PROPOSAL"}:
            all_affected = affected | set(command.dependent_scope)
            invalidated |= all_affected
            rerun |= all_affected
            eligible -= all_affected
            completed -= all_affected
            current_work -= all_affected
            conditions.extend(
                ScopedCondition(
                    "PAUSED", scope, command.reason,
                    "REVISE_AND_REVIEW" if command.action == "REQUEST_REVISION" else "SUBMIT_NEW_PROPOSAL",
                    metadata,
                )
                for scope in sorted(all_affected)
                if not any(c.scope == scope and c.status == "PAUSED" for c in conditions)
            )
            route = "REVISE_AND_REVIEW" if command.action == "REQUEST_REVISION" else "SUBMIT_NEW_PROPOSAL"
        else:  # APPROVE_DECISION
            if command.target not in pending:
                raise LifecycleInvariantError("approval target is not a pending decision")
            if affected.intersection(completed):
                raise LifecycleInvariantError("retrospective approval is prohibited")
            if not command.prerequisites_satisfied:
                raise LifecycleInvariantError("approval prerequisites are not satisfied")
            pending.remove(command.target)
            conditions = [
                c for c in conditions
                if not (
                    c.status == "PAUSED"
                    and c.scope in affected
                    and command.target in c.sources
                )
            ]
            still_affected = {c.scope for c in conditions} | invalidated
            eligible |= affected - still_affected
            route = "CONTINUE_ELIGIBLE_WORK" if affected <= eligible else "REVIEW_REMAINING_GATES"

        proposed = replace(
            current,
            identity=command.new_state_identity,
            eligible_scope=tuple(sorted(eligible)),
            conditions=tuple(conditions),
            pending_decisions=tuple(pending),
            completed_work=tuple(item for item in current.completed_work if item in completed),
            current_work=tuple(item for item in current.current_work if item in current_work),
            invalidated_scope=tuple(sorted(invalidated)),
            rerun_required=tuple(sorted(rerun)),
        )
        return proposed, route


class FullSystemController:
    """Single entry point that routes reasoning stages, Codex Stage 08, and human waits."""

    REASONING_STAGES = {"01", "02", "03", "04", "05", "06", "07", "09", "10"}

    def __init__(
        self,
        orchestrator: Orchestrator,
        reasoning_executor: StageExecutor,
        codex_runner: Stage08CodexRunner,
        telemetry_recorder: Any = None,
        *,
        compilation_mode: CompilationMode = CompilationMode.BASELINE,
    ):
        self.orchestrator = orchestrator
        self.runner = StageRunner(
            orchestrator,
            telemetry_recorder=telemetry_recorder,
            compilation_mode=compilation_mode,
        )
        self.reasoning_executor = reasoning_executor
        self.codex_runner = codex_runner
        self.decisions = DecisionGateway(orchestrator)
        self.git = GitRepository(orchestrator.repo_root)

    def _repo_structure(self, max_entries: int = 500) -> str:
        ignored = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
        entries = []
        for path in sorted(self.orchestrator.repo_root.rglob("*")):
            rel = path.relative_to(self.orchestrator.repo_root)
            if any(part in ignored for part in rel.parts):
                continue
            entries.append(rel.as_posix() + ("/" if path.is_dir() else ""))
            if len(entries) >= max_entries:
                entries.append("... [truncated]")
                break
        return "\n".join(entries)

    def _reconcile_pre_stage07_runtime_state(self) -> dict[str, Any]:
        """Prepare a truthful, recoverable Stage 07 rerun state.

        Runtime-owned state is reconciled without changing Product/Spec/Design
        authority. A previous Stage 07 FAIL is historical evidence, not a blocker
        by itself: the new attempt is represented as IN_PROGRESS and the old result
        remains preserved in .sdd/runs Git history.

        ``project_state.git.head_commit`` is a persisted recovery-base observation,
        not a self-referential promise that it equals the commit containing the state
        file. The current Git HEAD is always supplied separately as live runtime
        evidence after the preflight checkpoint.
        """
        before = self.git.snapshot(recent_limit=10)
        state = self.orchestrator.project_state
        state.setdefault("git", {})
        state["git"]["branch"] = before.branch
        state["git"]["head_commit"] = before.head_commit
        state["git"].setdefault("last_verified_commit", None)

        # Rebuild blockers only from currently authoritative runtime sources.
        reasons: list[str] = []
        for decision in self.decisions.list(status="OPEN"):
            reasons.append(f"HUMAN_DECISION:{decision.decision_id}")

        authority = self.orchestrator.authority_state
        for item in authority.get("unresolved_conflicts", []) or []:
            if isinstance(item, dict):
                ident = item.get("conflict_id") or item.get("id") or json.dumps(item, ensure_ascii=False, sort_keys=True)
            else:
                ident = str(item)
            reasons.append(f"AUTHORITY_CONFLICT:{ident}")
        for item in authority.get("blocking_tbds", []) or []:
            if isinstance(item, dict):
                ident = item.get("tbd_id") or item.get("id") or json.dumps(item, ensure_ascii=False, sort_keys=True)
            else:
                ident = str(item)
            reasons.append(f"BLOCKING_TBD:{ident}")

        state.setdefault("blocking", {})
        state["blocking"]["reasons"] = reasons
        state["blocking"]["is_blocked"] = bool(reasons)

        # A gate rerun is a new attempt. Do not let the previous FAIL become a
        # circular blocker for the rerun; history remains in .sdd/runs and Git.
        state.setdefault("stages", {}).setdefault("07", {})
        state["stages"]["07"]["status"] = "IN_PROGRESS"
        state["stages"]["07"]["result"] = None
        state.setdefault("authorizations", {})["implementation"] = False
        provenance_reconciliation = (
            self.orchestrator.reconcile_current_stage08_authorization_provenance(
                preparing_stage07_rerun=True
            )
        )
        state.setdefault("lifecycle", {})["current_stage"] = "07"
        state["lifecycle"]["current_stage_name"] = "PRE_IMPLEMENTATION_GATE"
        state["lifecycle"]["next_action"] = "RERUN_STAGE"
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)

        # Preserve legitimate orchestrator bookkeeping before asking the gate to
        # judge worktree cleanliness. This never stages application/source files.
        runtime_paths = [".sdd/state/project-state.yaml"]
        runs_dir = self.orchestrator.repo_root / ".sdd" / "runs"
        if runs_dir.exists():
            runtime_paths.append(".sdd/runs")
        snap_after_state = self.git.snapshot(recent_limit=10)
        covered = [
            p for p in snap_after_state.dirty_paths
            if any(p == rel.rstrip("/") or p.startswith(rel.rstrip("/") + "/") for rel in runtime_paths)
        ]
        preflight_commit = None
        if covered:
            preflight_commit = self.git.checkpoint(
                task_id="S07-PREFLIGHT",
                summary="reconcile Stage 07 runtime state",
                paths=runtime_paths,
                commit_type="chore",
                scope="sdd",
                allow_unrelated_dirty=True,
            )

        current = self.git.snapshot(recent_limit=10)
        unrelated_dirty = [
            p for p in current.dirty_paths
            if not (p.startswith(".sdd/runs/") or p == ".sdd/state/project-state.yaml")
        ]
        return {
            "repository_initialized": current.is_repository,
            "branch": current.branch,
            "current_head_commit": current.head_commit,
            # Backward-compatible alias: persisted recovery-base observation.
            "head_commit": before.head_commit,
            "recorded_recovery_base_commit": before.head_commit,
            "preflight_reconciliation_commit": preflight_commit,
            "working_tree_clean": not bool(current.dirty_paths),
            "dirty_paths": current.dirty_paths,
            "unrelated_dirty_paths": unrelated_dirty,
            "recent_commits": current.recent_commits,
            "last_verified_commit": state["git"].get("last_verified_commit"),
            "last_verified_commit_semantics": (
                "No verified implementation checkpoint exists yet"
                if not state["git"].get("last_verified_commit")
                else "Recorded verified implementation checkpoint"
            ),
            "project_state_head_semantics": (
                "project-state git.head_commit is the persisted recovery-base observation "
                "taken before the Stage 07 preflight reconciliation commit; current_head_commit "
                "is the authoritative live Git HEAD for this gate execution"
            ),
            "prior_stage07_result_semantics": (
                "Any previous Stage 07 FAIL is historical run evidence, not a blocker by itself; "
                "this request represents a fresh rerun after runtime-state reconciliation"
            ),
            "stage08_provenance_reconciliation": provenance_reconciliation,
        }

    def _semantics(self, sid: str, supplied: dict[str, dict[str, Any]]) -> dict[str, Any]:
        repo = self._repo_structure()
        defaults = {
            "02": {"APPROVED_PRODUCT_DECISIONS": "Use only proposal and explicitly resolved human decisions."},
            "03": {"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "No additional constraints unless present in authoritative artifacts."},
            "04": {"REPOSITORY_STRUCTURE_IF_EXISTING": repo, "APPROVED_CONSTRAINTS": "Only upstream-approved constraints.", "APPROVED_ADRS_IF_ANY": "Use repository ADRs if present."},
            "05": {"REPOSITORY_STRUCTURE": repo},
            "06": {"REPOSITORY_STRUCTURE": repo},
            "07": {"REPOSITORY_STRUCTURE": repo, "GIT_READINESS": "Runtime Git evidence is supplied by the controller immediately before Stage 07."},
            "10": {
                "RELEASE_IDENTITY": "Derive from repository/version inputs; mark incomplete if unavailable.",
                "TARGET_ENVIRONMENT": "Use explicit repository/deployment evidence only.",
                "DEPLOYMENT_TARGET": "Use explicit repository/deployment evidence only.",
                "BUILD_CI_EVIDENCE": "Use available CI/build evidence; do not assume.",
                "SECURITY_EVIDENCE": "Use available security evidence; do not assume.",
                "DOCUMENTATION_READINESS": "Inspect repository docs.",
                "MIGRATION_READINESS_IF_APPLICABLE": "Inspect migrations; N/A only with reason.",
                "DEPLOYMENT_READINESS": "Inspect deployment configuration/evidence.",
                "ROLLBACK_RECOVERY_READINESS": "Require explicit rollback/recovery evidence when applicable.",
            },
        }
        out = defaults.get(sid, {}).copy()
        out.update(supplied.get(sid, {}))
        return out

    def _checkpoint_reasoning_stage(self, sid: str, event: dict[str, Any]) -> str | None:
        paths = list(event.get("written_artifacts", []) or [])
        paths += list(event.get("convergence_tasks", []) or [])
        # The stage transition/authorization state is part of the deterministic
        # repository recovery point and should travel with the artifact checkpoint.
        state_rel = ".sdd/state/project-state.yaml"
        if (self.orchestrator.repo_root / state_rel).exists():
            paths.append(state_rel)
        # Run records are durable audit evidence produced by the stage execution
        # itself. Checkpoint them with the stage so they do not accumulate as
        # unrelated dirty governance files before the next gate/task.
        runs_rel = ".sdd/runs"
        if (self.orchestrator.repo_root / runs_rel).exists():
            paths.append(runs_rel)
        if not paths or not self.git.is_repository():
            return None
        return self.git.checkpoint(
            task_id=f"S{sid}",
            summary=f"complete Stage {sid} artifacts",
            paths=paths,
            commit_type="docs" if sid not in {"09", "10"} else "chore",
            scope="sdd",
            allow_unrelated_dirty=True,
        )

    def run(self, *, max_steps: int = 100, semantic_by_stage: dict[str, dict[str, Any]] | None = None) -> SystemRunSummary:
        semantic_by_stage = semantic_by_stage or {}
        start = self.orchestrator.current_stage_id
        events: list[dict[str, Any]] = []
        for _ in range(max_steps):
            open_decisions = self.decisions.list(status="OPEN")
            if open_decisions:
                return SystemRunSummary(start, self.orchestrator.current_stage_id, "WAIT_FOR_HUMAN_DECISION", events, [asdict(d) for d in open_decisions])

            sid = self.orchestrator.current_stage_id
            if sid == "08":
                result = self.codex_runner.run_until_complete(max_tasks=max_steps)
                events.append(result)
                if result.get("status") != "COMPLETED":
                    return SystemRunSummary(start, sid, result.get("status", "BLOCKED"), events)
                if max_steps == 1:
                    current_stage = self.orchestrator.current_stage_id
                    if current_stage == "09":
                        return SystemRunSummary(start, current_stage, "COMPLETED", events)
                continue

            if sid not in self.REASONING_STAGES:
                return SystemRunSummary(start, sid, "STOP", events)


            stage_semantics = self._semantics(sid, semantic_by_stage)
            if sid == "07":
                runtime_git = self._reconcile_pre_stage07_runtime_state()
                stage_semantics["GIT_READINESS"] = json.dumps(runtime_git, ensure_ascii=False, indent=2)
            event = self.runner.run(self.reasoning_executor, sid, semantic_inputs=stage_semantics)
            checkpoint = self._checkpoint_reasoning_stage(sid, event)
            if checkpoint:
                event["artifact_checkpoint_commit"] = checkpoint
            events.append(event)
            transition = event.get("transition", {})
            if transition.get("blocked"):
                return SystemRunSummary(start, sid, "BLOCKED", events)
            nxt = str(transition.get("next", ""))
            if sid == "10" and nxt in {"DEPLOY", "DEPLOY_WITH_RECORDED_NON_BLOCKING_ISSUES"}:
                return SystemRunSummary(start, sid, nxt, events)
            if not nxt.isdigit():
                return SystemRunSummary(start, sid, nxt or "STOP", events)

        return SystemRunSummary(start, self.orchestrator.current_stage_id, "MAX_STEPS_REACHED", events)
