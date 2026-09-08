from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from pathlib import Path
from typing import Any, Protocol
import fnmatch
import yaml


class SDDOrchestratorError(Exception):
    pass


class StageNotFoundError(SDDOrchestratorError):
    pass


class LifecycleInvariantError(SDDOrchestratorError):
    """A proposed lifecycle state is missing or contradicts governed facts."""


LIFECYCLE_CONDITIONS = {"PAUSED", "BLOCKED", "INCOMPLETE"}
AUTHORITY_STATUSES = {
    "ABSENT",
    "DRAFT",
    "APPROVED_CURRENT_AUTHORITY",
    "STALE_AFFECTED",
    "CONFLICTING",
}

PROTECTED_AUTHORITY_ARTIFACTS = {
    "PRODUCT_INTENT": ("01", "docs/proposal.md"),
    "PRODUCT_REQUIREMENT": ("02", "docs/PRD.md"),
    "TECHNICAL_CONTRACT": ("03", "docs/spec.md"),
    "IMPLEMENTATION_DECISION": ("04", "docs/Design.md"),
    "AGENT_REPOSITORY_GOVERNANCE": ("05", "AGENTS.md"),
    "EXECUTION_DECOMPOSITION": ("06", "tasks.md"),
    "PRE_IMPLEMENTATION_GATE_DECISION": ("07", "docs/handoff/pre-implementation-gate-report.md"),
    "IMPLEMENTATION_EVIDENCE": ("08", ".sdd/state/implementation-state.yaml"),
    "VERIFICATION_DECISION": ("09", "docs/handoff/verification-report.md"),
    "RELEASE_DECISION": ("10", "docs/handoff/handoff-report.md"),
}


@dataclass(frozen=True)
class AuthorityEntry:
    domain: str
    scope: tuple[str, ...]
    source: str
    version: str | None
    status: str
    approved: bool = False
    fresh: bool = True
    unresolved_condition: str | None = None
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in AUTHORITY_STATUSES:
            raise LifecycleInvariantError(f"unsupported authority status: {self.status}")
        if not self.domain or not self.scope or not self.source:
            raise LifecycleInvariantError("authority entries require domain, scope, and source")
        if self.approved != (self.status == "APPROVED_CURRENT_AUTHORITY"):
            raise LifecycleInvariantError("approval and authority status must agree")
        if self.approved and (not self.version or not self.fresh or self.unresolved_condition):
            raise LifecycleInvariantError("current authority requires an unambiguous fresh version")


@dataclass(frozen=True)
class ConflictRecord:
    identity: str
    domains: tuple[str, ...]
    affected_scope: tuple[str, ...]
    condition: str
    owner_stages: tuple[str, ...]
    safe_references: tuple[str, ...]
    protocol: tuple[str, ...] = (
        "DETECT", "REPORT", "BLOCK", "ROUTE_TO_AUTHORITATIVE_OWNER"
    )
    status: str = "BLOCKED"


@dataclass(frozen=True)
class AuthorityResolution:
    domain: str
    owner_stage: str
    source: str | None
    version: str | None
    status: str
    approved: bool
    unresolved_condition: str | None
    affected_scope: tuple[str, ...]
    unaffected_scope: tuple[str, ...]
    permitted_route: str
    conflict_identity: str | None = None


class AuthorityRegistry:
    """Domain-scoped authority resolution; it never edits authority artifacts."""

    def __init__(self, entries: tuple[AuthorityEntry, ...] = (), *, conflict_store: Path | None = None):
        self._entries = entries
        self.conflict_store = conflict_store

    def _mapping(self, domain: str) -> tuple[str, str]:
        try:
            return PROTECTED_AUTHORITY_ARTIFACTS[domain]
        except KeyError as exc:
            raise LifecycleInvariantError(f"unknown authority domain: {domain}") from exc

    def resolve(self, domain: str, question_scope: tuple[str, ...]) -> AuthorityResolution:
        owner, configured_source = self._mapping(domain)
        candidates = [e for e in self._entries if e.domain == domain and set(e.scope) & set(question_scope)]
        mismapped = [e for e in candidates if e.source != configured_source]
        if mismapped:
            return self._blocked_resolution(domain, question_scope, "out-of-scope-authority-source", mismapped)
        applicable = [e for e in candidates if e.status == "APPROVED_CURRENT_AUTHORITY"]
        if len(applicable) == 1:
            entry = applicable[0]
            affected = tuple(s for s in question_scope if s in entry.scope)
            return AuthorityResolution(domain, owner, entry.source, entry.version, entry.status, True, None, affected, tuple(s for s in question_scope if s not in affected), f"OWNER_STAGE_{owner}")

        if len(applicable) > 1:
            return self._blocked_resolution(domain, question_scope, "ambiguous-current-version", candidates)
        if not candidates:
            absent = AuthorityEntry(domain, question_scope, configured_source, None, "ABSENT")
            return self._blocked_resolution(domain, question_scope, "missing-authority", [absent])

        strongest = next((e for e in candidates if e.status == "CONFLICTING"), candidates[0])
        condition = strongest.unresolved_condition or {
            "DRAFT": "authority-not-approved",
            "STALE_AFFECTED": "stale-authority",
            "CONFLICTING": "authority-conflict",
            "ABSENT": "missing-authority",
        }[strongest.status]
        return self._blocked_resolution(domain, question_scope, condition, candidates)

    def record_cross_domain_conflict(self, identity: str, domains: tuple[str, ...], affected_scope: tuple[str, ...], *, condition: str, safe_references: tuple[str, ...]) -> ConflictRecord:
        if len(set(domains)) < 2:
            raise LifecycleInvariantError("cross-domain conflict requires distinct domains")
        return self._record(ConflictRecord(identity, domains, affected_scope, condition, tuple(sorted(self._mapping(d)[0] for d in set(domains))), safe_references))

    def _blocked_resolution(self, domain: str, scope: tuple[str, ...], condition: str, entries: list[AuthorityEntry]) -> AuthorityResolution:
        owner, _ = self._mapping(domain)
        affected = tuple(
            s for s in scope
            if any(s in e.scope or s in e.dependencies for e in entries)
        ) or scope
        unaffected = tuple(s for s in scope if s not in affected)
        identity = f"AUTH-{domain}-{'-'.join(affected)}-{len(self.conflicts()) + 1}"
        record = self._record(ConflictRecord(identity, (domain,), affected, condition, (owner,), tuple(dict.fromkeys(e.source for e in entries))))
        entry = entries[0]
        return AuthorityResolution(domain, owner, entry.source, entry.version, entry.status, False, condition, affected, unaffected, f"ROUTE_TO_STAGE_{owner}", record.identity)

    def _record(self, record: ConflictRecord) -> ConflictRecord:
        prior = self.conflicts()
        if any(item.identity == record.identity for item in prior):
            raise LifecycleInvariantError("conflict identity already exists; blockers cannot self-clear or be rewritten")
        if self.conflict_store:
            self.conflict_store.parent.mkdir(parents=True, exist_ok=True)
            data = {"conflicts": [item.__dict__ for item in prior + (record,)]}
            temporary = self.conflict_store.with_suffix(self.conflict_store.suffix + ".tmp")
            temporary.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            temporary.replace(self.conflict_store)
        return record

    def conflicts(self) -> tuple[ConflictRecord, ...]:
        if not self.conflict_store or not self.conflict_store.exists():
            return ()
        data = yaml.safe_load(self.conflict_store.read_text(encoding="utf-8")) or {}
        return tuple(ConflictRecord(**{**item, "domains": tuple(item["domains"]), "affected_scope": tuple(item["affected_scope"]), "owner_stages": tuple(item["owner_stages"]), "safe_references": tuple(item["safe_references"]), "protocol": tuple(item["protocol"])}) for item in data.get("conflicts", []))

    @staticmethod
    def normal_implementation_authorized(*, stage07_result: str | None, implementation_authorization: bool) -> bool:
        return stage07_result == "PASS" and implementation_authorization is True

    @staticmethod
    def reject_global_precedence() -> None:
        raise LifecycleInvariantError("global authority precedence is forbidden; resolve by owning domain")


@dataclass(frozen=True)
class ScopedCondition:
    status: str
    scope: str
    reason: str
    next_route: str
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in LIFECYCLE_CONDITIONS:
            raise LifecycleInvariantError(f"unsupported scoped status: {self.status}")
        if not all((self.scope, self.reason, self.next_route, self.sources)):
            raise LifecycleInvariantError("scoped conditions require scope, reason, sources, and route")


@dataclass(frozen=True)
class QualificationState:
    approved: bool = False
    implementation_authorized: bool = False
    stage07_result: str | None = None
    complete: bool = False
    verified: bool = False
    stage09_result: str | None = None
    stage10_eligible: bool = False
    release_ready: bool = False
    stage10_result: str | None = None
    released: bool = False
    recovery_gate_passed: bool = False


@dataclass(frozen=True)
class LifecycleTransition:
    identity: str
    prior_state_identity: str
    new_state_identity: str
    affected_scope: tuple[str, ...]
    reason: str
    sources: tuple[str, ...]
    next_route: str


@dataclass(frozen=True)
class LifecycleAggregate:
    identity: str
    current_stage: str
    completed_work: tuple[str, ...]
    current_work: tuple[str, ...]
    next_work: tuple[str, ...]
    eligible_scope: tuple[str, ...]
    conditions: tuple[ScopedCondition, ...]
    pending_decisions: tuple[str, ...]
    authority_summary: tuple[str, ...]
    qualifications: QualificationState
    rerun_required: tuple[str, ...] = ()
    invalidated_scope: tuple[str, ...] = ()
    independent_scope: tuple[str, ...] = ()
    transitions: tuple[LifecycleTransition, ...] = ()

    def validate(self) -> None:
        if not self.identity or not self.current_stage or not self.authority_summary:
            raise LifecycleInvariantError("identity, current stage, and authority summary are required")
        work_sets = {
            "completed": set(self.completed_work),
            "current": set(self.current_work),
            "next": set(self.next_work),
        }
        for name, values in (
            ("completed", self.completed_work),
            ("current", self.current_work),
            ("next", self.next_work),
        ):
            if len(values) != len(set(values)):
                raise LifecycleInvariantError(f"duplicate {name} work identity")
        if work_sets["current"] & work_sets["next"]:
            raise LifecycleInvariantError("current and next work must be disjoint")
        transition_ids: set[str] = set()
        for transition in self.transitions:
            if not all((
                transition.identity,
                transition.prior_state_identity,
                transition.new_state_identity,
                transition.affected_scope,
                transition.reason,
                transition.sources,
                transition.next_route,
            )):
                raise LifecycleInvariantError("transition history contains an incomplete record")
            if transition.identity in transition_ids:
                raise LifecycleInvariantError(
                    f"duplicate transition identity: {transition.identity}"
                )
            transition_ids.add(transition.identity)
        q = self.qualifications
        if q.implementation_authorized and (not q.approved or q.stage07_result != "PASS"):
            raise LifecycleInvariantError("implementation authorization requires approval and Stage07 PASS")
        if q.verified and (not q.complete or q.stage09_result != "PASS"):
            raise LifecycleInvariantError("verification requires completion and Stage09 PASS")
        if q.stage10_eligible and (not q.verified or q.stage09_result != "PASS"):
            raise LifecycleInvariantError("Stage10 eligibility requires Stage09 verification")
        if q.release_ready and (
            not q.stage10_eligible
            or q.stage10_result not in {"READY", "READY_WITH_KNOWN_ISSUES"}
        ):
            raise LifecycleInvariantError("release readiness requires a qualifying Stage10 result")
        if q.released and not q.release_ready:
            raise LifecycleInvariantError("release requires release readiness")
        affected = {condition.scope for condition in self.conditions}
        affected.update(self.invalidated_scope)
        if affected.intersection(self.eligible_scope):
            raise LifecycleInvariantError("blocked, incomplete, paused, or invalidated scope cannot be eligible")
        if set(self.rerun_required) - set(self.invalidated_scope):
            raise LifecycleInvariantError("rerun scope must be invalidated")
        if set(self.independent_scope) & affected:
            raise LifecycleInvariantError("independent scope contradicts affected scope")
        if self.pending_decisions and not any(c.status == "PAUSED" for c in self.conditions):
            raise LifecycleInvariantError("pending decisions require a scoped PAUSED condition")


class LifecycleStateResponsibility(Protocol):
    def load(self) -> LifecycleAggregate: ...
    def publish(self, state: LifecycleAggregate, *, affected_scope: str) -> None: ...


class LifecycleGovernor:
    """Validates and atomically delegates lifecycle transitions to state storage."""

    def __init__(self, state: LifecycleStateResponsibility):
        self.state = state

    def snapshot(self) -> LifecycleAggregate:
        current = self.state.load()
        current.validate()
        return current

    def transition(
        self,
        proposed: LifecycleAggregate,
        *,
        expected_prior_identity: str,
        transition_identity: str,
        affected_scope: tuple[str, ...],
        reason: str,
        sources: tuple[str, ...],
        next_route: str,
    ) -> LifecycleAggregate:
        current = self.snapshot()  # Never validate against a cached snapshot.
        if current.identity != expected_prior_identity:
            raise LifecycleInvariantError(
                f"stale prior-state identity: {expected_prior_identity} != {current.identity}"
            )
        if not all((transition_identity, affected_scope, reason, sources, next_route)):
            raise LifecycleInvariantError(
                "transition requires identity, affected scope, reason, sources, and route"
            )
        if proposed.identity == current.identity:
            raise LifecycleInvariantError("accepted transition requires a new state identity")
        if proposed.transitions != current.transitions:
            raise LifecycleInvariantError("existing transition history cannot be rewritten")
        if not set(current.completed_work) <= set(proposed.completed_work):
            invalidated = set(proposed.invalidated_scope)
            removed = set(current.completed_work) - set(proposed.completed_work)
            if not removed <= invalidated:
                raise LifecycleInvariantError("valid completed work must be preserved")
        proposed.validate()
        transition = LifecycleTransition(
            identity=transition_identity,
            prior_state_identity=current.identity,
            new_state_identity=proposed.identity,
            affected_scope=affected_scope,
            reason=reason,
            sources=sources,
            next_route=next_route,
        )
        accepted = dataclass_replace(proposed, transitions=current.transitions + (transition,))
        self.state.publish(accepted, affected_scope=",".join(affected_scope))
        return accepted


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
            if result == "FAIL":
                self.reconcile_current_stage08_authorization_provenance()

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

    def reconcile_current_stage08_authorization_provenance(
        self,
        *,
        preparing_stage07_rerun: bool = False,
    ) -> dict[str, Any]:
        """Clear contradictory CURRENT Stage 08 provenance without rewriting history.

        This state-owner operation is deliberately one-way: it can only change the
        current ``stage08_authorization_created`` marker from true to false. It is
        permitted after a recorded Stage 07 FAIL, or while explicitly preparing a
        fresh Stage 07 rerun whose implementation authorization is already false.
        Historical run records, reports, evidence, and recovery state are untouched.
        """
        stage07_result = self.project_state.get("stages", {}).get("07", {}).get("result")
        implementation_authorized = bool(
            self.project_state.get("authorizations", {}).get("implementation")
        )
        eligible = stage07_result == "FAIL" or (
            preparing_stage07_rerun and not implementation_authorized
        )
        provenance = self.project_state.get("provenance", {})
        before = provenance.get("stage08_authorization_created")
        changed = bool(eligible and before is True)
        if changed:
            provenance["stage08_authorization_created"] = False
            self.project_state["provenance"] = provenance
            self._save_yaml(self.project_state_path, self.project_state)
        return {
            "changed": changed,
            "stage08_authorization_created_before": before,
            "stage08_authorization_created_after": (
                False if changed else before
            ),
            "eligible": eligible,
            "stage07_result": stage07_result,
            "implementation_authorization": implementation_authorized,
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
