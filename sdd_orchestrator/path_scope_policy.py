from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


RISK_LEVELS = {"LOW", "DESTRUCTIVE", "HIGH_RISK", "SECURITY", "AUTHORITY_CONFLICT"}
_SENSITIVE_KEYS = ("token", "password", "secret", "api_key", "api-key", "credential")
_BROAD_TARGETS = {"*", "/", ".", ".."}
_CONFLICT_PROTOCOL = (
    "DETECT",
    "REPORT",
    "BLOCK",
    "ROUTE_TO_AUTHORITATIVE_OWNER",
)


@dataclass(frozen=True)
class SafetyAuthorization:
    """A reference to authorization; sensitive decision payloads never belong here."""

    reference: str
    target: str
    scope: tuple[str, ...]
    actor: str
    authority_identity: str
    snapshot_identity: str
    status: str = "APPROVED"
    expires_at: datetime | None = None


@dataclass(frozen=True)
class SafetyBlocker:
    reference: str
    category: str
    severity: str
    affected_scope: tuple[str, ...]
    owner: str
    required_decision: str
    resolved: bool = False
    resolution_reference: str | None = None
    resolution_actor: str | None = None
    resolution_authority_identity: str | None = None
    resolution_snapshot_identity: str | None = None


@dataclass(frozen=True)
class SafetyPreflightRequest:
    operation: str
    risk_level: str
    target: str
    scope: tuple[str, ...]
    actor: str
    authority_identity: str
    snapshot_identity: str
    authorization: SafetyAuthorization | None = None
    blockers: tuple[SafetyBlocker, ...] = ()
    resume_blocked_scope: bool = False
    independent_scope: tuple[str, ...] = ()
    dependency_finding_reference: str | None = None


@dataclass(frozen=True)
class SafetyPreflightResult:
    status: str
    safe_to_continue: bool
    affected_scope: tuple[str, ...]
    independent_scope: tuple[str, ...]
    finding_categories: tuple[str, ...]
    blocker_references: tuple[str, ...]
    authorization_reference: str | None
    required_owner: str | None
    required_decision: str | None
    route: str | None
    risk_level: str = ""
    target: str = ""
    blocker_severities: tuple[str, ...] = ()
    dependency_finding_reference: str | None = None
    conflict_protocol: tuple[str, ...] = ()
    resolution_references: tuple[str, ...] = ()


def _bounded(values: tuple[str, ...]) -> bool:
    return bool(values) and all(
        isinstance(value, str)
        and bool(value.strip())
        and value.strip() not in _BROAD_TARGETS
        for value in values
    )


def _normalized_scope(value: str) -> str:
    return value.strip().replace("\\", "/").rstrip("/")


def _overlaps(left: str, right: str) -> bool:
    left = _normalized_scope(left)
    right = _normalized_scope(right)
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _target_is_bounded_by_scope(target: str, scope: tuple[str, ...]) -> bool:
    return any(_overlaps(target, item) for item in scope)


def _same_scope(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if not _bounded(left) or not _bounded(right):
        return False
    normalized_left = tuple(_normalized_scope(item) for item in left)
    normalized_right = tuple(_normalized_scope(item) for item in right)
    return (
        len(set(normalized_left)) == len(normalized_left)
        and len(set(normalized_right)) == len(normalized_right)
        and set(normalized_left) == set(normalized_right)
    )


def _safe_reference(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return "[REDACTED_REFERENCE]"
    lowered = value.lower()
    if any(key in lowered for key in _SENSITIVE_KEYS) or "=" in value:
        return "[REDACTED_REFERENCE]"
    return value


def _safe_scope(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_safe_reference(value) or "[REDACTED_REFERENCE]" for value in values)


def _resolution_is_current(blocker: SafetyBlocker, request: SafetyPreflightRequest) -> bool:
    """A component cannot self-clear a blocker with a bare boolean."""
    return bool(
        blocker.resolved
        and blocker.resolution_reference
        and blocker.resolution_actor == blocker.owner
        and blocker.resolution_authority_identity == request.authority_identity
        and blocker.resolution_snapshot_identity == request.snapshot_identity
    )


def safety_preflight(request: SafetyPreflightRequest, *, now: datetime | None = None) -> SafetyPreflightResult:
    """Fail-closed, minimum-disclosure preflight for TASK-011 / DES-013."""
    categories: list[str] = []
    blocking = [item for item in request.blockers if not _resolution_is_current(item, request)]
    risk = request.risk_level.strip().upper() if isinstance(request.risk_level, str) else ""
    protected = risk in RISK_LEVELS - {"LOW"} or request.resume_blocked_scope

    if risk not in RISK_LEVELS:
        categories.append("UNKNOWN_RISK")
    operation_valid = isinstance(request.operation, str) and bool(request.operation.strip())
    target_valid = (
        isinstance(request.target, str)
        and bool(request.target.strip())
        and request.target.strip() not in _BROAD_TARGETS
    )
    if (
        not operation_valid
        or not target_valid
        or not _bounded(request.scope)
        or (target_valid and _bounded(request.scope) and not _target_is_bounded_by_scope(request.target, request.scope))
    ):
        categories.append("AMBIGUOUS_TARGET_OR_SCOPE")
    if (
        not isinstance(request.authority_identity, str)
        or not request.authority_identity.strip()
        or not isinstance(request.snapshot_identity, str)
        or not request.snapshot_identity.strip()
    ):
        categories.append("STALE_OR_MISSING_CURRENT_IDENTITY")
    if not isinstance(request.actor, str) or not request.actor.strip():
        categories.append("UNAUTHORIZED_ACTOR")

    authorization = request.authorization
    if protected:
        if authorization is None:
            categories.append("MISSING_EXPLICIT_AUTHORIZATION")
        else:
            current_time = now or datetime.now(timezone.utc)
            expiry = authorization.expires_at
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
            if authorization.status != "APPROVED" or (expiry is not None and expiry <= current_time):
                categories.append("EXPIRED_OR_INACTIVE_AUTHORIZATION")
            if not isinstance(authorization.reference, str) or not authorization.reference.strip():
                categories.append("MISSING_EXPLICIT_AUTHORIZATION")
            if authorization.actor != request.actor:
                categories.append("UNAUTHORIZED_ACTOR")
            if (
                authorization.target != request.target
                or not _same_scope(authorization.scope, request.scope)
            ):
                categories.append("MISMATCHED_AUTHORIZATION_SCOPE")
            if (authorization.authority_identity != request.authority_identity
                    or authorization.snapshot_identity != request.snapshot_identity):
                categories.append("STALE_AUTHORIZATION")

    if blocking:
        categories.extend(
            "AUTHORITY_CONFLICT"
            if b.category.strip().upper() == "AUTHORITY_CONFLICT"
            else "UNRESOLVED_SECURITY_CONCERN"
            for b in blocking
        )
    if request.resume_blocked_scope and not request.blockers:
        categories.append("MISSING_BLOCKER_IDENTITY_OR_RESOLUTION")

    independent = request.independent_scope
    isolation_overlaps = any(
        _overlaps(candidate, affected)
        for candidate in independent
        for affected in request.scope
    ) if _bounded(independent) and _bounded(request.scope) else bool(independent)
    if independent and (
        not _bounded(independent)
        or not request.dependency_finding_reference
        or isolation_overlaps
    ):
        categories.append("UNPROVEN_SCOPE_ISOLATION")
        independent = ()

    blocked = bool(categories)
    first = blocking[0] if blocking else None
    conflict = any(item.category.strip().upper() == "AUTHORITY_CONFLICT" for item in blocking)
    return SafetyPreflightResult(
        status="BLOCKED" if blocked else "ELIGIBLE",
        safe_to_continue=not blocked,
        affected_scope=_safe_scope(request.scope),
        independent_scope=_safe_scope(independent),
        finding_categories=tuple(dict.fromkeys(categories)),
        blocker_references=tuple(filter(None, (_safe_reference(item.reference) for item in blocking))),
        authorization_reference=_safe_reference(authorization.reference) if authorization else None,
        required_owner=_safe_reference(first.owner) if first else ("AUTHORIZATION_OWNER" if blocked else None),
        required_decision=_safe_reference(first.required_decision) if first else ("EXPLICIT_AUTHORIZATION" if blocked else None),
        route="ROUTE_TO_AUTHORITATIVE_OWNER" if conflict else ("ROUTE_TO_REQUIRED_OWNER" if blocked else None),
        risk_level=risk or "UNKNOWN",
        target=_safe_reference(request.target) or "[REDACTED_REFERENCE]",
        blocker_severities=tuple(_safe_reference(item.severity) or "UNKNOWN" for item in blocking),
        dependency_finding_reference=_safe_reference(request.dependency_finding_reference),
        conflict_protocol=_CONFLICT_PROTOCOL if conflict else (),
        resolution_references=tuple(
            filter(None, (_safe_reference(item.resolution_reference) for item in request.blockers))
        ),
    )


def generated_verification_dirty(
    path: str,
    *,
    is_tracked: Callable[[str], bool],
) -> bool:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    generated = (
        any(part == "__pycache__" for part in parts)
        or normalized.endswith(".pyc")
        or any(part.endswith(".egg-info") for part in parts)
    )
    if not generated:
        return False
    return not is_tracked(path)


def covered(path: str, allowed_paths: list[str]) -> bool:
    for allowed in allowed_paths:
        normalized = allowed.rstrip("/")
        if "*" in normalized or "?" in normalized or "[" in normalized:
            if fnmatch.fnmatch(path, normalized):
                return True
        elif path == normalized or path.startswith(normalized + "/"):
            return True
    return False


@dataclass(frozen=True)
class DirtyDiffScopeResult:
    status: str
    dirty_paths: tuple[str, ...]
    unauthorized_paths: tuple[str, ...]
    unexpected_untracked_paths: tuple[str, ...]
    attributable: bool

    @property
    def safe_to_preserve(self) -> bool:
        return self.status == "AUTHORIZED_ATTRIBUTABLE_DIRTY_DIFF"


def validate_dirty_diff_scope(
    dirty_paths: tuple[str, ...],
    allowed_paths: list[str],
    *,
    attributable_paths: tuple[str, ...],
    untracked_paths: tuple[str, ...] = (),
) -> DirtyDiffScopeResult:
    """Fail closed unless every dirty path is authorized and attempt-attributable."""
    normalized = tuple(sorted(dict.fromkeys(_normalized_scope(item) for item in dirty_paths)))
    attributed = set(_normalized_scope(item) for item in attributable_paths)
    unauthorized = tuple(item for item in normalized if not covered(item, allowed_paths))
    unexpected = tuple(
        sorted(
            item for item in (_normalized_scope(path) for path in untracked_paths)
            if item not in attributed
        )
    )
    attributable = all(item in attributed for item in normalized)
    status = (
        "AUTHORIZED_ATTRIBUTABLE_DIRTY_DIFF"
        if normalized and not unauthorized and not unexpected and attributable
        else "CLEAN" if not normalized and not unexpected
        else "BLOCK"
    )
    return DirtyDiffScopeResult(
        status, normalized, unauthorized, unexpected, attributable
    )


def runtime_dirty(path: str, runtime_dirty_prefixes: tuple[str, ...]) -> bool:
    return path.startswith(runtime_dirty_prefixes)


def ignorable_runtime_dirty(
    path: str,
    allowed_paths: list[str],
    *,
    runtime_dirty_prefixes: tuple[str, ...],
    task_writable_sdd_exact: set[str],
) -> bool:
    if path in task_writable_sdd_exact and covered(path, allowed_paths):
        return False
    return runtime_dirty(path, runtime_dirty_prefixes)


def is_protected(
    path: str,
    *,
    task_authorized: bool,
    protected_exact: set[str],
    task_writable_sdd_exact: set[str],
) -> bool:
    if path in protected_exact:
        return True
    if path.startswith("docs/handoff/"):
        return True
    if path.startswith(".sdd/"):
        return not (task_authorized and path in task_writable_sdd_exact)
    return False
