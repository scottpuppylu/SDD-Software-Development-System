from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any, Mapping

from .codex_results import CodexTaskRunResult, VerificationResult
from .security_policy import redact_security_value


def serialize_verification_result(result: VerificationResult) -> dict[str, Any]:
    return asdict(result) | {"passed": result.passed}


def serialize_task_run_result(result: CodexTaskRunResult) -> dict[str, Any]:
    data = asdict(result)
    data["verification"] = [
        serialize_verification_result(item) for item in result.verification
    ]
    return data


def stage08_phase_projection(
    *,
    attempt_id: str,
    phase: str | None,
    status: str,
    resume_eligible: bool,
    safe_references: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Minimum-disclosure status only; never an implementation qualification."""
    return {
        "attempt_id": attempt_id,
        "phase": phase,
        "status": status,
        "resume_eligible": bool(resume_eligible),
        "safe_references": [redact_security_value(item) for item in safe_references],
        "implementation_qualified": False,
        "stage09_decision": None,
        "stage10_decision": None,
    }


_UNRESOLVED = "TBD"
_VERIFICATION_OUTCOMES = {"PASS", "FAIL", "NOT RUN"}
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


def _clean_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [deepcopy(item) for item in value]
    return [deepcopy(value)]


def _display_list(values: list[Any], *, empty: str = "none recorded") -> str:
    if not values:
        return empty
    labels: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            label = next(
                (
                    value.get(key)
                    for key in ("summary", "subject", "reason", "identity", "id", "scope")
                    if value.get(key)
                ),
                _UNRESOLVED,
            )
        else:
            label = value
        labels.append(str(label))
    return ", ".join(labels)


def _redact(value: Any, *, key: str = "") -> Any:
    normalized = key.lower().replace("-", "_")
    if any(part in normalized for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): _redact(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return deepcopy(redact_security_value(value))


def _verification_projection(raw_checks: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, raw in enumerate(raw_checks, start=1):
        if isinstance(raw, Mapping):
            check = _redact(raw)
        else:
            check = {"identity": str(raw)}
        identity = str(check.get("identity") or check.get("command") or f"check-{index}")
        outcome = str(check.get("outcome") or _UNRESOLVED).upper()
        if outcome not in _VERIFICATION_OUTCOMES:
            failures.append(f"Verification {identity} has no valid PASS, FAIL, or NOT RUN outcome.")
            outcome = "NOT RUN"
        checks.append({**check, "identity": identity, "outcome": outcome})
    return checks, failures


def _qualification_conflicts(qualifications: Mapping[str, Any]) -> list[str]:
    conflicts: list[str] = []
    if qualifications.get("implementation_authorized") and (
        not qualifications.get("approved") or qualifications.get("stage07_result") != "PASS"
    ):
        conflicts.append("Implementation authorization lacks approved authority or Stage07 PASS.")
    if qualifications.get("verified") and (
        not qualifications.get("complete") or qualifications.get("stage09_result") != "PASS"
    ):
        conflicts.append("Verification qualification lacks completion or Stage09 PASS.")
    if qualifications.get("stage10_eligible") and (
        not qualifications.get("verified") or qualifications.get("stage09_result") != "PASS"
    ):
        conflicts.append("Stage10 eligibility lacks Stage09 verification qualification.")
    if qualifications.get("release_ready") and (
        not qualifications.get("stage10_eligible")
        or qualifications.get("stage10_result") not in {"READY", "READY_WITH_KNOWN_ISSUES"}
    ):
        conflicts.append("Release readiness lacks a qualifying Stage10 result.")
    if qualifications.get("released") and not qualifications.get("release_ready"):
        conflicts.append("Release status lacks release readiness.")
    return conflicts


def project_status_report(
    snapshot: Mapping[str, Any],
    *,
    observed_snapshot_identity: str | None = None,
) -> dict[str, Any]:
    """Return a plain-language, read-only projection of one governed snapshot.

    ``snapshot`` contains structured domain facts; its prose is never treated as a
    lifecycle or qualification decision.  The optional observed identity lets a
    caller prove whether the supplied snapshot is still current.
    """

    source = deepcopy(dict(snapshot))
    snapshot_identity = source.get("snapshot_identity") or source.get("identity")
    snapshot_version = source.get("snapshot_version") or source.get("version")
    stale = bool(source.get("stale")) or (
        observed_snapshot_identity is not None
        and snapshot_identity != observed_snapshot_identity
    )

    current_stage = source.get("current_stage") or _UNRESOLVED
    completed_work = _clean_list(source.get("completed_work"))
    current_work = _clean_list(source.get("current_work"))
    next_work = _clean_list(source.get("next_work"))
    pending_decisions = _clean_list(source.get("pending_decisions"))
    authorities = _clean_list(source.get("authority_state") or source.get("authorities"))
    conditions = _clean_list(source.get("conditions") or source.get("blockers"))
    affected_scope = _clean_list(source.get("affected_scope"))
    preserved_work = _clean_list(source.get("preserved_work") or completed_work)
    evidence_gaps = _clean_list(source.get("evidence_gaps"))
    regression_risk = _clean_list(source.get("regression_risk"))
    verification, reporting_failures = _verification_projection(
        _clean_list(source.get("verification"))
    )
    qualifications = _redact(source.get("qualifications") or {})
    if not isinstance(qualifications, Mapping):
        qualifications = {}
        reporting_failures.append("Qualification facts are malformed.")
    qualification_conflicts = _qualification_conflicts(qualifications)
    reporting_failures.extend(qualification_conflicts)

    missing_identity = not snapshot_identity or not snapshot_version
    if missing_identity:
        reporting_failures.append("Snapshot identity or version is missing.")
    if current_stage == _UNRESOLVED:
        reporting_failures.append("The current lifecycle stage is missing.")

    source_continuation = source.get("continuation_eligible")
    unresolved = bool(conditions or pending_decisions or reporting_failures)
    continuation_eligible = bool(source_continuation) and not (stale or unresolved)
    condition_statuses = {
        str(item.get("status", "")).upper()
        for item in conditions
        if isinstance(item, Mapping)
    }
    if stale:
        projection_status = "INCOMPLETE"
    elif "BLOCKED" in condition_statuses or qualification_conflicts:
        projection_status = "BLOCKED"
    elif "INCOMPLETE" in condition_statuses:
        projection_status = "INCOMPLETE"
    elif "PAUSED" in condition_statuses or pending_decisions:
        projection_status = "PAUSED"
    elif reporting_failures:
        projection_status = "INCOMPLETE"
    else:
        projection_status = str(source.get("status") or "CURRENT").upper()

    situation = source.get("situation") or (
        f"The governed journey is at stage {current_stage}. "
        f"Current work: {_display_list(current_work)}."
    )
    consequence = source.get("consequence") or (
        "Affected work cannot safely continue until the unresolved items are addressed."
        if not continuation_eligible
        else "The recorded eligible work may continue within its existing authority."
    )
    required_action = source.get("required_action") or (
        "Refresh the governed snapshot and resolve the reported gaps."
        if stale or reporting_failures
        else "Resolve the pending decision or blocker."
        if unresolved
        else "No user action is currently required."
    )
    next_route = (
        "REFRESH_GOVERNED_SNAPSHOT"
        if stale or reporting_failures
        else source.get("next_eligible_route") or source.get("next_route") or _UNRESOLVED
    )

    summary = {
        "situation": str(situation),
        "consequence": str(consequence),
        "affected_scope": _display_list(affected_scope, empty="no affected scope recorded"),
        "preserved_work": _display_list(preserved_work),
        "required_action": str(required_action),
        "next_eligible_route": str(next_route),
    }
    identifiers = {
        "snapshot_identity": snapshot_identity or _UNRESOLVED,
        "snapshot_version": snapshot_version or _UNRESOLVED,
        "observed_snapshot_identity": observed_snapshot_identity or snapshot_identity or _UNRESOLVED,
        "stale": stale,
        "safe_references": _redact(_clean_list(source.get("safe_references"))),
    }
    lifecycle = {
        "status": projection_status,
        "current_stage": current_stage,
        "completed_work": _redact(completed_work),
        "current_work": _redact(current_work),
        "next_work": _redact(next_work),
        "pending_decisions": _redact(pending_decisions),
        "authority_state": _redact(authorities),
        "conditions": _redact(conditions),
        "continuation_eligible": continuation_eligible,
    }
    evidence = {
        "verification": verification,
        "evidence_gaps": _redact(evidence_gaps),
        "regression_risk": _redact(regression_risk),
    }

    return {
        "summary": summary,
        "identifiers": identifiers,
        "lifecycle": lifecycle,
        "qualifications": dict(qualifications),
        "evidence": evidence,
        "reporting_failures": reporting_failures,
    }
