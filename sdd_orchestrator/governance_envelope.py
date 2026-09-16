from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping


class GovernanceEnvelopeError(PermissionError):
    """A dispatch is not covered by a current, exact governance grant."""

    def __init__(self, code: str, route: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.route = route
        self.detail = detail


class CapabilityClass(str, Enum):
    REPOSITORY_READ = "REPOSITORY_READ"
    AUTHORITY_ARTIFACT_WRITE = "AUTHORITY_ARTIFACT_WRITE"
    WORKSPACE_IMPLEMENTATION_WRITE = "WORKSPACE_IMPLEMENTATION_WRITE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    NETWORK_ACCESS = "NETWORK_ACCESS"
    CREDENTIAL_REFERENCE_ACCESS = "CREDENTIAL_REFERENCE_ACCESS"
    GIT_READ = "GIT_READ"
    GIT_WRITE = "GIT_WRITE"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"
    DEPLOYMENT = "DEPLOYMENT"
    PROTECTED_PRODUCTION_ACTION = "PROTECTED_PRODUCTION_ACTION"


APPROVAL_CLASSES = frozenset({"A0", "A1", "A2", "A3"})
_PROTECTED_CAPABILITIES = frozenset(
    {
        CapabilityClass.AUTHORITY_ARTIFACT_WRITE,
        CapabilityClass.EXTERNAL_SIDE_EFFECT,
        CapabilityClass.DEPLOYMENT,
        CapabilityClass.PROTECTED_PRODUCTION_ACTION,
    }
)


def _utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise GovernanceEnvelopeError("MALFORMED", "ENVELOPE_ISSUER", f"invalid {label}") from exc
    if parsed.tzinfo is None:
        raise GovernanceEnvelopeError("MALFORMED", "ENVELOPE_ISSUER", f"{label} must include timezone")
    return parsed.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tuple(value: Iterable[str]) -> tuple[str, ...]:
    return tuple(str(item) for item in value)


def _canonical(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, Mapping):
        value = {str(key): value[key] for key in sorted(value, key=str)}
    elif isinstance(value, (tuple, list, set, frozenset)):
        value = list(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def argument_digest(arguments: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(arguments).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdentityBinding:
    actor_id: str
    project_id: str
    environment: str
    repository: str
    branch: str
    baseline: str
    stage_id: str
    attempt_id: str
    provider_id: str | None = None
    adapter_id: str | None = None
    session_id: str | None = None
    task_id: str | None = None


@dataclass(frozen=True)
class AuthenticationReference:
    reference: str
    method: str
    actor_id: str
    project_id: str
    environment: str
    verified: bool
    current: bool = True
    expires_at: str | None = None


@dataclass(frozen=True)
class ApprovalBinding:
    approval_class: str
    reference: str
    action: str
    target: str
    scope: tuple[str, ...]
    baseline: str
    environment: str
    risk: str
    provider_capability: str
    approved: bool = True
    expires_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", _tuple(self.scope))


@dataclass(frozen=True)
class CapabilityGrant:
    grant_id: str
    capability_class: CapabilityClass | str
    actions: tuple[str, ...]
    tools: tuple[str, ...]
    argument_digests: tuple[str, ...]
    targets: tuple[str, ...]
    scope: tuple[str, ...]
    side_effects: tuple[str, ...]
    issuer: str
    approval_reference: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        try:
            capability = CapabilityClass(self.capability_class)
        except ValueError as exc:
            raise GovernanceEnvelopeError(
                "UNKNOWN_CAPABILITY", "SECURITY_OR_AUTHORITY_OWNER", str(self.capability_class)
            ) from exc
        object.__setattr__(self, "capability_class", capability)
        for name in ("actions", "tools", "argument_digests", "targets", "scope", "side_effects"):
            object.__setattr__(self, name, _tuple(getattr(self, name)))


@dataclass(frozen=True)
class GovernanceEnvelope:
    envelope_id: str
    identity: IdentityBinding
    authentication: AuthenticationReference
    authority_references: tuple[str, ...]
    gate_references: tuple[str, ...]
    grants: tuple[CapabilityGrant, ...]
    approval: ApprovalBinding
    policy_references: tuple[str, ...]
    limit_references: tuple[str, ...]
    audit_obligations: tuple[str, ...]
    evidence_obligations: tuple[str, ...]
    prohibited_operations: tuple[str, ...]
    issued_at: str
    expires_at: str
    sealed_stage08_envelope_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "authority_references", "gate_references", "grants", "policy_references",
            "limit_references", "audit_obligations", "evidence_obligations",
            "prohibited_operations",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))


@dataclass(frozen=True)
class DispatchRequest:
    action: str
    tool: str
    arguments: Mapping[str, Any]
    target: str
    scope: tuple[str, ...]
    side_effects: tuple[str, ...]
    required_capabilities: tuple[CapabilityClass | str, ...]
    approval_class: str
    approval_reference: str
    provider_authority_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))
        object.__setattr__(self, "scope", _tuple(self.scope))
        object.__setattr__(self, "side_effects", _tuple(self.side_effects))
        object.__setattr__(self, "required_capabilities", tuple(self.required_capabilities))
        object.__setattr__(self, "provider_authority_claims", _tuple(self.provider_authority_claims))


@dataclass(frozen=True)
class DispatchObservation:
    outcome: str
    actual_scope: tuple[str, ...]
    actual_side_effects: tuple[str, ...]
    evidence_references: tuple[str, ...]
    failure_route: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "actual_scope", _tuple(self.actual_scope))
        object.__setattr__(self, "actual_side_effects", _tuple(self.actual_side_effects))
        object.__setattr__(self, "evidence_references", _tuple(self.evidence_references))


@dataclass(frozen=True)
class GovernanceDecision:
    outcome: str
    envelope_id: str
    audit_record: Mapping[str, Any]


def _envelope_payload(envelope: GovernanceEnvelope) -> dict[str, Any]:
    def grant(item: CapabilityGrant) -> dict[str, Any]:
        return {
            "grant_id": item.grant_id, "capability_class": item.capability_class.value,
            "actions": item.actions, "tools": item.tools,
            "argument_digests": item.argument_digests, "targets": item.targets,
            "scope": item.scope, "side_effects": item.side_effects, "issuer": item.issuer,
            "approval_reference": item.approval_reference, "issued_at": item.issued_at,
            "expires_at": item.expires_at,
        }
    return {
        "identity": vars(envelope.identity),
        "authentication": vars(envelope.authentication),
        "authority_references": envelope.authority_references,
        "gate_references": envelope.gate_references,
        "grants": tuple(grant(item) for item in envelope.grants),
        "approval": vars(envelope.approval),
        "policy_references": envelope.policy_references,
        "limit_references": envelope.limit_references,
        "audit_obligations": envelope.audit_obligations,
        "evidence_obligations": envelope.evidence_obligations,
        "prohibited_operations": envelope.prohibited_operations,
        "issued_at": envelope.issued_at,
        "expires_at": envelope.expires_at,
        "sealed_stage08_envelope_id": envelope.sealed_stage08_envelope_id,
    }


def seal_governance_envelope(**values: Any) -> GovernanceEnvelope:
    candidate = GovernanceEnvelope(envelope_id="", **values)
    seal = hashlib.sha256(_canonical(_envelope_payload(candidate)).encode("utf-8")).hexdigest()
    return replace(candidate, envelope_id=seal)


class GovernanceEnvelopeValidator:
    """Fail-closed exact-match validator with post-dispatch effect reconciliation."""

    REQUIRED_AUDIT = frozenset({"ENVELOPE_ID", "OUTCOME", "OBSERVED_EFFECTS", "FAILURE_ROUTE", "APPROVAL_BINDING"})
    REQUIRED_EVIDENCE = frozenset({"DISPATCH_RESULT"})

    def __init__(self) -> None:
        self._consumed_protected_approvals: set[str] = set()
        self._pending_envelopes: set[str] = set()
        self._completed_envelopes: set[str] = set()

    @staticmethod
    def _deny(code: str, route: str, detail: str) -> None:
        raise GovernanceEnvelopeError(code, route, detail)

    def validate_pre_dispatch(
        self,
        envelope: GovernanceEnvelope | None,
        request: DispatchRequest,
        *,
        current_identity: IdentityBinding,
        now: datetime | None = None,
    ) -> GovernanceDecision:
        if envelope is None:
            self._deny("MISSING_ENVELOPE", "AUTHORIZATION_OWNER", "a governance envelope is required")
        assert envelope is not None
        if not envelope.envelope_id or hashlib.sha256(
            _canonical(_envelope_payload(envelope)).encode("utf-8")
        ).hexdigest() != envelope.envelope_id:
            self._deny("INVALID_SEAL", "ENVELOPE_ISSUER", "envelope is malformed or mutated")
        instant = (now or _now()).astimezone(timezone.utc)
        if _utc(envelope.issued_at, "issued_at") > instant or _utc(envelope.expires_at, "expires_at") <= instant:
            self._deny("EXPIRED_OR_STALE", "AUTHORIZATION_OWNER", "envelope is not currently valid")
        if envelope.identity != current_identity:
            self._deny("IDENTITY_MISMATCH", "IDENTITY_OWNER", "actor/project/environment/repository binding changed")
        required_identity = (
            current_identity.actor_id, current_identity.project_id,
            current_identity.environment, current_identity.repository,
            current_identity.branch, current_identity.baseline,
            current_identity.stage_id, current_identity.attempt_id,
        )
        if not all(isinstance(item, str) and item.strip() for item in required_identity):
            self._deny("IDENTITY_MISSING", "IDENTITY_OWNER", "current dispatch identity is incomplete")
        if current_identity.stage_id == "08" and not current_identity.task_id:
            self._deny("IDENTITY_MISSING", "IDENTITY_OWNER", "Stage08 task identity is required")
        auth = envelope.authentication
        if not all((auth.reference, auth.method, auth.actor_id, auth.project_id, auth.environment)):
            self._deny("AUTHENTICATION_MISSING", "IDENTITY_OWNER", "non-secret authentication reference is incomplete")
        if re.search(r"(?i)(bearer\s+|api[_-]?key\s*[:=]|password\s*[:=]|secret\s*[:=]|sk-[a-z0-9])", auth.reference):
            self._deny("SECRET_VALUE_FORBIDDEN", "SECURITY_OWNER", "authentication must use a non-secret reference")
        if not auth.verified or not auth.current:
            self._deny("AUTHENTICATION_INVALID", "IDENTITY_OWNER", "authentication reference is unverified or stale")
        if (auth.actor_id, auth.project_id, auth.environment) != (
            current_identity.actor_id, current_identity.project_id, current_identity.environment,
        ):
            self._deny("AUTHENTICATION_MISMATCH", "IDENTITY_OWNER", "authentication binding does not match dispatch identity")
        if auth.expires_at and _utc(auth.expires_at, "authentication.expires_at") <= instant:
            self._deny("AUTHENTICATION_EXPIRED", "IDENTITY_OWNER", "authentication reference expired")
        if not envelope.authority_references or not envelope.policy_references or not envelope.limit_references:
            self._deny("MISSING_BINDING", "AUTHORITATIVE_OWNER", "authority, policy, and limit references are mandatory")
        invalid_refs = tuple(
            ref for ref in (*envelope.authority_references, *envelope.gate_references)
            if not ref.strip() or any(marker in ref.upper() for marker in ("STALE", "CONFLICT", "AMBIGUOUS", "UNVERIFIED"))
        )
        if invalid_refs:
            self._deny("INVALID_AUTHORITY_BINDING", "AUTHORITATIVE_OWNER", "authority or gate reference is not current and unambiguous")
        if not self.REQUIRED_AUDIT.issubset(envelope.audit_obligations):
            self._deny("MISSING_AUDIT_OBLIGATION", "EVIDENCE_OWNER", "material audit fields are incomplete")
        if not self.REQUIRED_EVIDENCE.issubset(envelope.evidence_obligations):
            self._deny("MISSING_EVIDENCE_OBLIGATION", "EVIDENCE_OWNER", "dispatch evidence obligation is absent")
        if request.approval_class not in APPROVAL_CLASSES:
            self._deny("UNKNOWN_APPROVAL_CLASS", "HUMAN_DECISION_OWNER", request.approval_class)
        approval = envelope.approval
        if not all((approval.reference, approval.risk, approval.provider_capability)):
            self._deny("APPROVAL_MISSING", "HUMAN_DECISION_OWNER", "approval binding is incomplete")
        exact_approval = (
            approval.approval_class == request.approval_class
            and approval.reference == request.approval_reference
            and approval.action == request.action
            and approval.target == request.target
            and approval.scope == request.scope
            and approval.baseline == current_identity.baseline
            and approval.environment == current_identity.environment
            and approval.approved
        )
        if not exact_approval:
            self._deny("APPROVAL_MISMATCH", "HUMAN_DECISION_OWNER", "approval does not bind the exact current dispatch")
        if approval.expires_at and _utc(approval.expires_at, "approval.expires_at") <= instant:
            self._deny("APPROVAL_EXPIRED", "HUMAN_DECISION_OWNER", "approval expired")
        if request.provider_authority_claims:
            self._deny("PROVIDER_AUTHORITY_CLAIM", "AUTHORITATIVE_OWNER", "provider output cannot create authority")
        requested_capabilities: list[CapabilityClass] = []
        for item in request.required_capabilities:
            try:
                requested_capabilities.append(CapabilityClass(item))
            except ValueError:
                self._deny("UNKNOWN_CAPABILITY", "SECURITY_OR_AUTHORITY_OWNER", str(item))
        if not requested_capabilities or len(set(requested_capabilities)) != len(requested_capabilities):
            self._deny("CAPABILITY_DENIED", "SECURITY_OR_AUTHORITY_OWNER", "capability request is absent or ambiguous")
        digest = argument_digest(request.arguments)
        for capability in requested_capabilities:
            matches = [
                grant for grant in envelope.grants
                if grant.capability_class is capability
                and grant.actions == (request.action,)
                and grant.tools == (request.tool,)
                and grant.argument_digests == (digest,)
                and grant.targets == (request.target,)
                and grant.scope == request.scope
                and grant.side_effects == request.side_effects
                and grant.approval_reference == approval.reference
                and _utc(grant.issued_at, "grant.issued_at") <= instant
                and _utc(grant.expires_at, "grant.expires_at") > instant
            ]
            if len(matches) != 1:
                self._deny(
                    "CAPABILITY_DENIED" if not matches else "AMBIGUOUS_GRANT",
                    "SECURITY_OR_AUTHORITY_OWNER",
                    f"{capability.value} is not covered by one exact current grant",
                )
        if current_identity.stage_id == "08" and (
            not envelope.sealed_stage08_envelope_id or not envelope.gate_references
        ):
            self._deny("STAGE07_BINDING_MISSING", "STAGE07", "Stage08 requires its existing sealed envelope and gate reference")
        if request.action in envelope.prohibited_operations:
            self._deny("PROHIBITED_OPERATION", "SECURITY_OR_AUTHORITY_OWNER", request.action)
        if approval.reference in self._consumed_protected_approvals:
            self._deny("APPROVAL_REUSED", "HUMAN_DECISION_OWNER", "protected approval was already consumed")
        if envelope.envelope_id in self._pending_envelopes or envelope.envelope_id in self._completed_envelopes:
            self._deny("ENVELOPE_REUSED", "AUTHORIZATION_OWNER", "dispatch envelope is single-use")
        self._pending_envelopes.add(envelope.envelope_id)
        return GovernanceDecision(
            "PASS", envelope.envelope_id,
            MappingProxyType({
                "envelope_id": envelope.envelope_id, "outcome": "AUTHORIZED",
                "approval_class": approval.approval_class,
                "approval_reference": approval.reference,
                "action": request.action, "target": request.target,
                "scope": request.scope, "failure_route": None,
            }),
        )

    def reconcile_post_dispatch(
        self,
        envelope: GovernanceEnvelope,
        request: DispatchRequest,
        observation: DispatchObservation,
    ) -> GovernanceDecision:
        if envelope.envelope_id not in self._pending_envelopes:
            self._deny("DISPATCH_NOT_AUTHORIZED", "AUTHORIZATION_OWNER", "no matching successful pre-dispatch decision")
        self._pending_envelopes.remove(envelope.envelope_id)
        self._completed_envelopes.add(envelope.envelope_id)
        scope_overrun = set(observation.actual_scope) - set(request.scope)
        effect_overrun = set(observation.actual_side_effects) - set(request.side_effects)
        if scope_overrun or effect_overrun:
            self._deny(
                "ACTUAL_SCOPE_EFFECT_MISMATCH", "SECURITY_OR_AUTHORITY_OWNER",
                f"scope={sorted(scope_overrun)} effects={sorted(effect_overrun)}",
            )
        if not observation.evidence_references:
            self._deny("MISSING_POST_DISPATCH_EVIDENCE", "EVIDENCE_OWNER", "dispatch result has no durable evidence reference")
        if observation.outcome != "PASS" and not observation.failure_route:
            self._deny("MISSING_FAILURE_ROUTE", "AUTHORITATIVE_OWNER", "non-PASS dispatch requires an exact failure route")
        if envelope.approval.approval_class in {"A2", "A3"} or any(
            grant.capability_class in _PROTECTED_CAPABILITIES for grant in envelope.grants
        ):
            self._consumed_protected_approvals.add(envelope.approval.reference)
        return GovernanceDecision(
            "PASS", envelope.envelope_id,
            MappingProxyType({
                "envelope_id": envelope.envelope_id, "outcome": observation.outcome,
                "observed_scope": observation.actual_scope,
                "observed_effects": observation.actual_side_effects,
                "evidence_references": observation.evidence_references,
                "failure_route": observation.failure_route,
                "approval_class": envelope.approval.approval_class,
                "approval_reference": envelope.approval.reference,
            }),
        )


def create_dispatch_envelope(
    *,
    identity: IdentityBinding,
    request: DispatchRequest,
    authentication_reference: str,
    authentication_method: str,
    authority_references: Iterable[str],
    gate_references: Iterable[str],
    policy_references: Iterable[str],
    limit_references: Iterable[str],
    issuer: str = "SDD_ORCHESTRATOR",
    risk: str = "ROUTINE_GOVERNED_OPERATION",
    provider_capability: str = "declared-adapter-capability",
    sealed_stage08_envelope_id: str | None = None,
    lifetime_seconds: int = 300,
    now: datetime | None = None,
) -> GovernanceEnvelope:
    """Create the least-capability envelope for one already-authorized dispatch.

    Callers must supply repository-backed authority/gate/policy references.  This
    helper binds them; it never discovers or invents authority from credentials.
    """

    instant = (now or _now()).astimezone(timezone.utc)
    expires = instant + timedelta(seconds=max(1, lifetime_seconds))
    issued_at = instant.isoformat().replace("+00:00", "Z")
    expires_at = expires.isoformat().replace("+00:00", "Z")
    grants = tuple(
        CapabilityGrant(
            grant_id=f"{identity.attempt_id}:{CapabilityClass(item).value}",
            capability_class=CapabilityClass(item), actions=(request.action,),
            tools=(request.tool,), argument_digests=(argument_digest(request.arguments),),
            targets=(request.target,), scope=request.scope,
            side_effects=request.side_effects, issuer=issuer,
            approval_reference=request.approval_reference,
            issued_at=issued_at, expires_at=expires_at,
        )
        for item in request.required_capabilities
    )
    return seal_governance_envelope(
        identity=identity,
        authentication=AuthenticationReference(
            reference=authentication_reference, method=authentication_method,
            actor_id=identity.actor_id, project_id=identity.project_id,
            environment=identity.environment, verified=True, current=True,
            expires_at=expires_at,
        ),
        authority_references=tuple(authority_references),
        gate_references=tuple(gate_references), grants=grants,
        approval=ApprovalBinding(
            approval_class=request.approval_class,
            reference=request.approval_reference, action=request.action,
            target=request.target, scope=request.scope, baseline=identity.baseline,
            environment=identity.environment, risk=risk,
            provider_capability=provider_capability,
            expires_at=expires_at,
        ),
        policy_references=tuple(policy_references),
        limit_references=tuple(limit_references),
        audit_obligations=tuple(sorted(GovernanceEnvelopeValidator.REQUIRED_AUDIT)),
        evidence_obligations=tuple(sorted(GovernanceEnvelopeValidator.REQUIRED_EVIDENCE)),
        prohibited_operations=("AUTHORITY_OVERRIDE", "PERMISSION_ENLARGEMENT"),
        issued_at=issued_at, expires_at=expires_at,
        sealed_stage08_envelope_id=sealed_stage08_envelope_id,
    )
