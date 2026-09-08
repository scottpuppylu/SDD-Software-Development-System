from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
import json
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
