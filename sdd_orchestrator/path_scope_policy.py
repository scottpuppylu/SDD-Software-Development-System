from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


RISK_LEVELS = {"LOW", "DESTRUCTIVE", "HIGH_RISK", "SECURITY", "AUTHORITY_CONFLICT"}
_SENSITIVE_KEYS = ("token", "password", "secret", "api_key", "api-key", "credential")


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


def _bounded(values: tuple[str, ...]) -> bool:
    return bool(values) and all(bool(value.strip()) and value not in {"*", "/", "."} for value in values)


def _safe_reference(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.lower()
    if any(key in lowered for key in _SENSITIVE_KEYS) or "=" in value:
        return "[REDACTED_REFERENCE]"
    return value


def safety_preflight(request: SafetyPreflightRequest, *, now: datetime | None = None) -> SafetyPreflightResult:
    """Fail-closed, minimum-disclosure preflight for TASK-011 / DES-013."""
    categories: list[str] = []
    blocking = [item for item in request.blockers if not item.resolved]
    risk = request.risk_level.upper()
    protected = risk in RISK_LEVELS - {"LOW"} or request.resume_blocked_scope

    if risk not in RISK_LEVELS:
        categories.append("UNKNOWN_RISK")
    if (not request.operation.strip() or not request.target.strip()
            or request.target in {"*", "/", "."} or not _bounded(request.scope)):
        categories.append("AMBIGUOUS_TARGET_OR_SCOPE")
    if not request.authority_identity.strip() or not request.snapshot_identity.strip():
        categories.append("STALE_OR_MISSING_CURRENT_IDENTITY")

    authorization = request.authorization
    if protected:
        if authorization is None:
            categories.append("MISSING_EXPLICIT_AUTHORIZATION")
        else:
            current_time = now or datetime.now(timezone.utc)
            expiry = authorization.expires_at
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if authorization.status != "APPROVED" or (expiry is not None and expiry <= current_time):
                categories.append("EXPIRED_OR_INACTIVE_AUTHORIZATION")
            if not authorization.reference.strip():
                categories.append("MISSING_EXPLICIT_AUTHORIZATION")
            if authorization.actor != request.actor:
                categories.append("UNAUTHORIZED_ACTOR")
            if authorization.target != request.target or set(authorization.scope) != set(request.scope):
                categories.append("MISMATCHED_AUTHORIZATION_SCOPE")
            if (authorization.authority_identity != request.authority_identity
                    or authorization.snapshot_identity != request.snapshot_identity):
                categories.append("STALE_AUTHORIZATION")

    if blocking:
        categories.extend("AUTHORITY_CONFLICT" if b.category == "AUTHORITY_CONFLICT" else "UNRESOLVED_SECURITY_CONCERN"
                          for b in blocking)

    independent = request.independent_scope
    if independent and (not request.dependency_finding_reference or set(independent) & set(request.scope)):
        categories.append("UNPROVEN_SCOPE_ISOLATION")
        independent = ()

    blocked = bool(categories)
    first = blocking[0] if blocking else None
    conflict = any(item.category == "AUTHORITY_CONFLICT" for item in blocking)
    return SafetyPreflightResult(
        status="BLOCKED" if blocked else "ELIGIBLE",
        safe_to_continue=not blocked,
        affected_scope=request.scope,
        independent_scope=independent,
        finding_categories=tuple(dict.fromkeys(categories)),
        blocker_references=tuple(filter(None, (_safe_reference(item.reference) for item in blocking))),
        authorization_reference=_safe_reference(authorization.reference) if authorization else None,
        required_owner=_safe_reference(first.owner) if first else ("AUTHORIZATION_OWNER" if blocked else None),
        required_decision=_safe_reference(first.required_decision) if first else ("EXPLICIT_AUTHORIZATION" if blocked else None),
        route="ROUTE_TO_AUTHORITATIVE_OWNER" if conflict else ("ROUTE_TO_REQUIRED_OWNER" if blocked else None),
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
