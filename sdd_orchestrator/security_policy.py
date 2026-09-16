from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping


class SecurityPolicyError(PermissionError):
    """A dispatch is not covered by the declared security policy."""

    def __init__(self, code: str, route: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.route = route
        self.detail = detail


class DataClass(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    PROHIBITED = "PROHIBITED"


class SandboxClass(str, Enum):
    S0_READ_ONLY_REASONING = "S0_READ_ONLY_REASONING"
    S1_WORKSPACE_WRITE = "S1_WORKSPACE_WRITE"
    S2_STAGING_OPERATION = "S2_STAGING_OPERATION"
    S3_PROTECTED_PRODUCTION_ACTION = "S3_PROTECTED_PRODUCTION_ACTION"


class FilesystemAccess(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class NetworkAccess(str, Enum):
    PACKAGE_REGISTRY_ONLY = "PACKAGE_REGISTRY_ONLY"
    DOCUMENTATION_READ_ONLY = "DOCUMENTATION_READ_ONLY"
    APPROVED_API_READ_ONLY = "APPROVED_API_READ_ONLY"
    APPROVED_SERVICE_WRITE = "APPROVED_SERVICE_WRITE"
    PROTECTED_PRODUCTION_ENDPOINT = "PROTECTED_PRODUCTION_ENDPOINT"


_SECRET_VALUE = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._~+/=-]+|sk-[a-z0-9_-]{8,}|"
    r"(?:password|passwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)\s*[:=]\s*\S+)"
)
_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,511}$")
_PRODUCTION_CREDENTIAL = re.compile(r"(?i)(?:^|[_:-])prod(?:uction)?(?:$|[_:-])")


def contains_secret_value(value: Any) -> bool:
    """Conservatively identify secret-shaped values in governance payloads."""

    if isinstance(value, str):
        return bool(_SECRET_VALUE.search(value))
    if isinstance(value, Mapping):
        return any(contains_secret_value(key) or contains_secret_value(item) for key, item in value.items())
    if isinstance(value, (tuple, list, set, frozenset)):
        return any(contains_secret_value(item) for item in value)
    if is_dataclass(value):
        return any(contains_secret_value(getattr(value, item.name)) for item in fields(value))
    return False


def redact_security_value(value: Any) -> Any:
    """Return a minimum-disclosure copy suitable for audit/evidence output."""

    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    if isinstance(value, Mapping):
        return {
            str(redact_security_value(key)): redact_security_value(item)
            for key, item in value.items()
        }
    if is_dataclass(value):
        return {
            item.name: redact_security_value(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, tuple):
        return tuple(redact_security_value(item) for item in value)
    if isinstance(value, list):
        return [redact_security_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return tuple(redact_security_value(item) for item in value)
    return value


def _tuple(value: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(value)


def _utc(value: str, label: str) -> datetime:
    try:
        if not isinstance(value, str):
            raise TypeError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError) as exc:
        raise SecurityPolicyError("SECURITY_POLICY_MALFORMED", "SECURITY_OWNER", f"invalid {label}") from exc
    if parsed.tzinfo is None:
        raise SecurityPolicyError(
            "SECURITY_POLICY_MALFORMED", "SECURITY_OWNER", f"{label} must include timezone"
        )
    return parsed.astimezone(timezone.utc)


def _enum(enum_type: type[Enum], value: Enum | str, code: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise SecurityPolicyError(
            code,
            "SECURITY_OWNER",
            f"unsupported {enum_type.__name__} value",
        ) from exc


def _reference(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or not _SAFE_REFERENCE.fullmatch(value)
        or contains_secret_value(value)
    ):
        raise SecurityPolicyError(
            "UNSAFE_SECURITY_REFERENCE", "SECURITY_OWNER", f"{label} must be a bounded non-secret reference"
        )


def _path(value: str) -> str:
    if not isinstance(value, str):
        raise SecurityPolicyError(
            "FILESYSTEM_PATH_DENIED",
            "SECURITY_OWNER",
            "filesystem path must be a repository-relative string",
        )
    candidate = value.replace("\\", "/")
    parts = candidate.split("/")
    if (
        not candidate
        or candidate.startswith("/")
        or re.match(r"^[A-Za-z]:", candidate)
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise SecurityPolicyError(
            "FILESYSTEM_PATH_DENIED", "SECURITY_OWNER", "filesystem path is not a clean repository-relative path"
        )
    return candidate


@dataclass(frozen=True)
class DataHandlingBinding:
    data_class: DataClass | str
    classification_reference: str
    policy_reference: str
    redaction_reference: str
    retention_reference: str
    encryption_reference: str
    allowed_environments: tuple[str, ...]
    transmission_allowed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_class", _enum(DataClass, self.data_class, "UNKNOWN_DATA_CLASS"))
        object.__setattr__(self, "allowed_environments", _tuple(self.allowed_environments))


@dataclass(frozen=True)
class FilesystemGrant:
    path: str
    access: FilesystemAccess | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path(self.path))
        object.__setattr__(self, "access", _enum(FilesystemAccess, self.access, "FILESYSTEM_ACCESS_DENIED"))


@dataclass(frozen=True)
class NetworkGrant:
    destination: str
    purpose: str
    access: NetworkAccess | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "access", _enum(NetworkAccess, self.access, "NETWORK_POLICY_DENIED"))


@dataclass(frozen=True)
class CredentialGrant:
    credential_class: str
    reference: str
    project_id: str
    environment: str
    session_id: str
    target: str
    purpose: str
    expires_at: str


@dataclass(frozen=True)
class SecretReferenceGrant:
    reference: str
    project_id: str
    environment: str
    session_id: str
    purpose: str


@dataclass(frozen=True)
class SecurityEnvelope:
    data_handling: DataHandlingBinding
    sandbox_class: SandboxClass | str
    project_id: str
    environment: str
    session_id: str
    provider_session_id: str | None
    filesystem_grants: tuple[FilesystemGrant, ...]
    network_grants: tuple[NetworkGrant, ...]
    credential_grants: tuple[CredentialGrant, ...]
    secret_reference_grants: tuple[SecretReferenceGrant, ...]
    process_grants: tuple[str, ...]
    production_action_granted: bool
    audit_reference: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "sandbox_class", _enum(SandboxClass, self.sandbox_class, "UNKNOWN_SANDBOX_CLASS"))
        for name in (
            "filesystem_grants", "network_grants", "credential_grants",
            "secret_reference_grants", "process_grants",
        ):
            object.__setattr__(self, name, _tuple(getattr(self, name)))


@dataclass(frozen=True)
class SecurityRequest:
    data_class: DataClass | str
    transmit_data: bool
    sandbox_class: SandboxClass | str
    project_id: str
    environment: str
    session_id: str
    provider_session_id: str | None = None
    filesystem: tuple[FilesystemGrant, ...] = ()
    network: tuple[NetworkGrant, ...] = ()
    credentials: tuple[CredentialGrant, ...] = ()
    secret_references: tuple[SecretReferenceGrant, ...] = ()
    processes: tuple[str, ...] = ()
    production_action: bool = False
    approval_class: str = "A0"
    untrusted_instruction_findings: tuple[str, ...] = ()
    malicious_tool_findings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_class", _enum(DataClass, self.data_class, "UNKNOWN_DATA_CLASS"))
        object.__setattr__(self, "sandbox_class", _enum(SandboxClass, self.sandbox_class, "UNKNOWN_SANDBOX_CLASS"))
        for name in (
            "filesystem", "network", "credentials", "secret_references", "processes",
            "untrusted_instruction_findings", "malicious_tool_findings",
        ):
            object.__setattr__(self, name, _tuple(getattr(self, name)))


@dataclass(frozen=True)
class SecurityObservation:
    filesystem: tuple[FilesystemGrant, ...] = ()
    network: tuple[NetworkGrant, ...] = ()
    credential_references: tuple[str, ...] = ()
    secret_references: tuple[str, ...] = ()
    processes: tuple[str, ...] = ()
    production_action: bool = False
    suspected_secret_exposure: bool = False
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "filesystem", "network", "credential_references", "secret_references", "processes",
        ):
            object.__setattr__(self, name, _tuple(getattr(self, name)))


@dataclass(frozen=True)
class SecurityDecision:
    outcome: str
    audit_record: Mapping[str, Any]


def _safe_categories(envelope: SecurityEnvelope, request: SecurityRequest) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            "data_class": request.data_class.value,
            "classification_reference": envelope.data_handling.classification_reference,
            "handling_policy_reference": envelope.data_handling.policy_reference,
            "sandbox_class": request.sandbox_class.value,
            "environment": request.environment,
            "filesystem_paths": tuple(item.path for item in request.filesystem),
            "network_destinations": tuple(item.destination for item in request.network),
            "network_purposes": tuple(item.purpose for item in request.network),
            "credential_classes": tuple(item.credential_class for item in request.credentials),
            "credential_references": tuple(item.reference for item in request.credentials),
            "secret_references": tuple(item.reference for item in request.secret_references),
            "processes": request.processes,
            "production_action": request.production_action,
            "audit_reference": envelope.audit_reference,
        }
    )


class SecurityPolicyValidator:
    """Fail-closed security policy validation before and after dispatch."""

    def __init__(self) -> None:
        self._pending: set[tuple[str, str, str]] = set()

    @staticmethod
    def _deny(code: str, route: str, detail: str) -> None:
        raise SecurityPolicyError(code, route, detail)

    def validate_pre_dispatch(
        self,
        envelope: SecurityEnvelope | None,
        request: SecurityRequest | None,
        *,
        now: datetime | None = None,
    ) -> SecurityDecision:
        if envelope is None or request is None:
            self._deny("SECURITY_BINDING_MISSING", "SECURITY_OWNER", "security envelope and request are required")
        assert envelope is not None and request is not None
        instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if _utc(envelope.issued_at, "security.issued_at") > instant or _utc(
            envelope.expires_at, "security.expires_at"
        ) <= instant:
            self._deny("SECURITY_POLICY_STALE", "SECURITY_OWNER", "security policy is not current")
        if contains_secret_value(envelope) or contains_secret_value(request):
            self._deny("SECRET_VALUE_FORBIDDEN", "SECURITY_OWNER", "secret-shaped values are not governance payloads")

        handling = envelope.data_handling
        for label, reference in (
            ("classification", handling.classification_reference),
            ("handling policy", handling.policy_reference),
            ("redaction", handling.redaction_reference),
            ("retention", handling.retention_reference),
            ("encryption", handling.encryption_reference),
            ("audit", envelope.audit_reference),
        ):
            _reference(reference, label)
        if request.data_class is DataClass.PROHIBITED or handling.data_class is DataClass.PROHIBITED:
            self._deny("DATA_CLASS_PROHIBITED", "SECURITY_OWNER", "prohibited data cannot be dispatched")
        if request.data_class is not handling.data_class:
            self._deny("DATA_CLASS_MISMATCH", "SECURITY_OWNER", "classification does not match its handling policy")
        if request.transmit_data and not handling.transmission_allowed:
            self._deny("DATA_TRANSMISSION_DENIED", "SECURITY_OWNER", "handling policy forbids transmission")
        if request.environment not in handling.allowed_environments:
            self._deny("DATA_ENVIRONMENT_DENIED", "SECURITY_OWNER", "handling policy does not allow this environment")

        if (request.project_id, request.environment, request.session_id) != (
            envelope.project_id, envelope.environment, envelope.session_id,
        ):
            self._deny("SECURITY_IDENTITY_MISMATCH", "SECURITY_OWNER", "project/environment/session binding changed")
        if request.provider_session_id != envelope.provider_session_id:
            self._deny("PROVIDER_SESSION_MISMATCH", "SECURITY_OWNER", "provider session is not bound to this dispatch")
        if request.sandbox_class is not envelope.sandbox_class:
            self._deny("SANDBOX_CLASS_MISMATCH", "SECURITY_OWNER", "requested sandbox differs from policy")
        if request.untrusted_instruction_findings:
            self._deny(
                "SUSPECTED_PROMPT_INJECTION", "SECURITY_REVIEW",
                "untrusted instruction finding requires review before any side effect",
            )
        if request.malicious_tool_findings:
            self._deny(
                "MALICIOUS_TOOL_ESCALATION", "SECURITY_REVIEW",
                "tool escalation or confused-deputy finding requires review",
            )

        environment = request.environment.casefold()
        if request.sandbox_class is SandboxClass.S0_READ_ONLY_REASONING:
            if any(item.access is FilesystemAccess.WRITE for item in request.filesystem) or request.production_action:
                self._deny("SANDBOX_POLICY_DENIED", "SECURITY_OWNER", "S0 is read-only")
        elif request.sandbox_class is SandboxClass.S1_WORKSPACE_WRITE:
            if environment in {"production", "prod"} or request.production_action:
                self._deny("PRODUCTION_BOUNDARY_DENIED", "HUMAN_DECISION", "general Stage08 sandbox cannot act on production")
        elif request.sandbox_class is SandboxClass.S2_STAGING_OPERATION:
            if environment != "staging" or request.production_action:
                self._deny("SANDBOX_POLICY_DENIED", "SECURITY_OWNER", "S2 is restricted to staging")
        elif request.sandbox_class is SandboxClass.S3_PROTECTED_PRODUCTION_ACTION:
            if environment not in {"production", "prod"} or not request.production_action:
                self._deny("PRODUCTION_BOUNDARY_DENIED", "HUMAN_DECISION", "S3 requires an exact production action")
            if request.approval_class not in {"A2", "A3"} or not envelope.production_action_granted:
                self._deny("PRODUCTION_APPROVAL_REQUIRED", "HUMAN_DECISION", "S3 requires exact A2/A3 authority")

        if len(set(request.filesystem)) != len(request.filesystem) or set(request.filesystem) != set(
            envelope.filesystem_grants
        ):
            self._deny("FILESYSTEM_PATH_DENIED", "SECURITY_OWNER", "filesystem request is absent, duplicate, or unlisted")
        if len(set(request.network)) != len(request.network) or set(request.network) != set(envelope.network_grants):
            self._deny("NETWORK_POLICY_DENIED", "SECURITY_OWNER", "network destination/purpose/access is unlisted")
        if len(set(request.credentials)) != len(request.credentials) or set(request.credentials) != set(
            envelope.credential_grants
        ):
            self._deny("CREDENTIAL_SCOPE_MISMATCH", "SECURITY_OWNER", "credential class/reference is unlisted")
        if len(set(request.secret_references)) != len(request.secret_references) or set(
            request.secret_references
        ) != set(envelope.secret_reference_grants):
            self._deny("SECRET_ACCESS_DENIED", "SECURITY_OWNER", "secret reference is unlisted")
        if len(set(request.processes)) != len(request.processes) or set(request.processes) != set(
            envelope.process_grants
        ):
            self._deny("PROCESS_EXECUTION_DENIED", "SECURITY_OWNER", "process is unlisted")

        for grant in request.network:
            _reference(grant.purpose, "network purpose")
            if not grant.destination or "*" in grant.destination or any(char.isspace() for char in grant.destination):
                self._deny("NETWORK_POLICY_DENIED", "SECURITY_OWNER", "network destination must be exact")
            if (
                request.sandbox_class is SandboxClass.S0_READ_ONLY_REASONING
                and grant.access
                not in {
                    NetworkAccess.DOCUMENTATION_READ_ONLY,
                    NetworkAccess.APPROVED_API_READ_ONLY,
                }
            ):
                self._deny(
                    "SANDBOX_POLICY_DENIED",
                    "SECURITY_OWNER",
                    "S0 permits only explicitly granted read-only network access",
                )
            if grant.access is NetworkAccess.PROTECTED_PRODUCTION_ENDPOINT and request.sandbox_class is not SandboxClass.S3_PROTECTED_PRODUCTION_ACTION:
                self._deny("PRODUCTION_BOUNDARY_DENIED", "HUMAN_DECISION", "production endpoint requires S3")
        for grant in request.credentials:
            for label, value in (
                ("credential class", grant.credential_class),
                ("credential reference", grant.reference),
                ("credential target", grant.target),
                ("credential purpose", grant.purpose),
            ):
                _reference(value, label)
            if (grant.project_id, grant.environment, grant.session_id) != (
                request.project_id, request.environment, request.session_id,
            ):
                self._deny("CREDENTIAL_SCOPE_MISMATCH", "SECURITY_OWNER", "credential crosses project/environment/session")
            if _utc(grant.expires_at, "credential.expires_at") <= instant:
                self._deny("CREDENTIAL_UNAVAILABLE", "SECURITY_OWNER", "credential reference is expired")
            if _PRODUCTION_CREDENTIAL.search(grant.credential_class) and request.sandbox_class is not SandboxClass.S3_PROTECTED_PRODUCTION_ACTION:
                self._deny("PRODUCTION_CREDENTIAL_DENIED", "HUMAN_DECISION", "production credential cannot enter a general sandbox")
        for grant in request.secret_references:
            _reference(grant.reference, "secret reference")
            _reference(grant.purpose, "secret purpose")
            if (grant.project_id, grant.environment, grant.session_id) != (
                request.project_id, request.environment, request.session_id,
            ):
                self._deny("SECRET_ACCESS_DENIED", "SECURITY_OWNER", "secret reference crosses project/environment/session")
        for process in request.processes:
            _reference(process, "process")

        key = (request.project_id, request.session_id, envelope.audit_reference)
        if key in self._pending:
            self._deny("SECURITY_DISPATCH_REUSED", "SECURITY_OWNER", "security policy is already pending")
        self._pending.add(key)
        return SecurityDecision("PASS", _safe_categories(envelope, request))

    def reconcile_post_dispatch(
        self,
        envelope: SecurityEnvelope,
        request: SecurityRequest,
        observation: SecurityObservation | None,
    ) -> SecurityDecision:
        key = (request.project_id, request.session_id, envelope.audit_reference)
        if key not in self._pending:
            self._deny("SECURITY_DISPATCH_NOT_AUTHORIZED", "SECURITY_OWNER", "no successful security preflight exists")
        self._pending.remove(key)
        if observation is None:
            self._deny("SECURITY_OBSERVATION_MISSING", "SECURITY_OWNER", "post-dispatch boundary evidence is required")
        if observation.suspected_secret_exposure:
            self._deny(
                "SUSPECTED_SECRET_EXPOSURE", "SECURITY_INCIDENT_RESPONSE",
                "affected flow stopped; preserve redacted evidence and revoke/rotate as applicable",
            )
        if contains_secret_value(observation):
            self._deny("SECRET_VALUE_FORBIDDEN", "SECURITY_INCIDENT_RESPONSE", "post-dispatch evidence contains a secret-shaped value")
        if not set(observation.filesystem).issubset(set(request.filesystem)):
            self._deny("ACTUAL_FILESYSTEM_OVERRUN", "SECURITY_OWNER", "actual filesystem access exceeded its grant")
        if not set(observation.network).issubset(set(request.network)):
            self._deny("ACTUAL_NETWORK_OVERRUN", "SECURITY_OWNER", "actual network access exceeded its grant")
        allowed_credentials = {item.reference for item in request.credentials}
        if not set(observation.credential_references).issubset(allowed_credentials):
            self._deny("ACTUAL_CREDENTIAL_OVERRUN", "SECURITY_OWNER", "actual credential access exceeded its grant")
        allowed_secrets = {item.reference for item in request.secret_references}
        if not set(observation.secret_references).issubset(allowed_secrets):
            self._deny("ACTUAL_SECRET_OVERRUN", "SECURITY_OWNER", "actual secret access exceeded its grant")
        if not set(observation.processes).issubset(set(request.processes)):
            self._deny("ACTUAL_PROCESS_OVERRUN", "SECURITY_OWNER", "actual process exceeded its grant")
        if observation.production_action and not request.production_action:
            self._deny("ACTUAL_PRODUCTION_OVERRUN", "HUMAN_DECISION", "unapproved production action observed")
        if not observation.evidence_reference:
            self._deny("SAFE_AUDIT_PATH_MISSING", "EVIDENCE_OWNER", "security reconciliation needs a safe evidence reference")
        _reference(observation.evidence_reference, "security evidence")
        audit = dict(_safe_categories(envelope, request))
        audit.update(
            {
                "outcome": "RECONCILED",
                "actual_filesystem_paths": tuple(item.path for item in observation.filesystem),
                "actual_network_destinations": tuple(item.destination for item in observation.network),
                "actual_credential_references": observation.credential_references,
                "actual_secret_references": observation.secret_references,
                "actual_processes": observation.processes,
                "evidence_reference": observation.evidence_reference,
            }
        )
        return SecurityDecision("PASS", MappingProxyType(audit))


def create_security_envelope(
    *,
    request: SecurityRequest,
    classification_reference: str,
    policy_reference: str,
    redaction_reference: str,
    retention_reference: str,
    encryption_reference: str,
    audit_reference: str,
    allowed_environments: Iterable[str] | None = None,
    lifetime_seconds: int = 300,
    now: datetime | None = None,
) -> SecurityEnvelope:
    """Bind caller-declared policy references and exact grants without widening them."""

    instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires = instant + timedelta(seconds=max(1, lifetime_seconds))
    return SecurityEnvelope(
        data_handling=DataHandlingBinding(
            data_class=request.data_class,
            classification_reference=classification_reference,
            policy_reference=policy_reference,
            redaction_reference=redaction_reference,
            retention_reference=retention_reference,
            encryption_reference=encryption_reference,
            allowed_environments=tuple(allowed_environments or (request.environment,)),
            transmission_allowed=request.transmit_data,
        ),
        sandbox_class=request.sandbox_class,
        project_id=request.project_id,
        environment=request.environment,
        session_id=request.session_id,
        provider_session_id=request.provider_session_id,
        filesystem_grants=request.filesystem,
        network_grants=request.network,
        credential_grants=request.credentials,
        secret_reference_grants=request.secret_references,
        process_grants=request.processes,
        production_action_granted=request.production_action,
        audit_reference=audit_reference,
        issued_at=instant.isoformat().replace("+00:00", "Z"),
        expires_at=expires.isoformat().replace("+00:00", "Z"),
    )
