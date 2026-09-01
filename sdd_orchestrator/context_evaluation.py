"""Pure, non-persistent M4.2 evaluation-local measurements.

This module observes exact context primitives.  It does not select, dispatch,
persist, or grant reuse authority.
"""

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

from .context_compiler import (
    ComponentDeltaKind,
    ComponentSelection,
    ContextDelta,
    ExactContextComponent,
    ReconstructionResult,
)


PROVIDER_USAGE_SCHEMA = "1.0.4"
OPENAI_RESPONSES_ACTUAL_PROVIDER_USAGE = (
    "AVAILABLE_WHEN_VALID_RESPONSE_USAGE_PRESENT"
)
CODEX_ACTUAL_PROVIDER_USAGE = "UNAVAILABLE"
CODEX_CLI_TOKENS_USED_IS_PROVIDER_EVIDENCE = "NO"
ESTIMATED_TOKENS_ARE_PROVIDER_EVIDENCE = "NO"
MISSING_VALID_PROVIDER_USAGE = "UNAVAILABLE_NOT_ZERO"
PROVIDER_TOKEN_CLAIM_WITHOUT_VALID_USAGE = "INCOMPLETE"
M4_2_SAFETY_PASS_REQUIRES_PROVIDER_USAGE = "NO"
MACHINE_EVALUATION_METADATA = "NON_PERSISTENT"


class ReuseEligibilityReason(str, Enum):
    SAME_IDENTITY_EXACT_BYTES = "SAME_IDENTITY_EXACT_BYTES"
    EXACT_RECONSTRUCTION_ELIGIBLE = "EXACT_RECONSTRUCTION_ELIGIBLE"
    ALWAYS_REQUIRED = "ALWAYS_REQUIRED"
    AUTHORITY_PROTECTED = "AUTHORITY_PROTECTED"
    UNKNOWN = "UNKNOWN"
    MIXED_AUTHORITY = "MIXED_AUTHORITY"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_CHANGED = "CONTENT_CHANGED"
    COMPONENT_ADDED = "COMPONENT_ADDED"
    COMPONENT_REMOVED = "COMPONENT_REMOVED"
    COMPONENT_REORDERED = "COMPONENT_REORDERED"
    DUPLICATE_IDENTITY = "DUPLICATE_IDENTITY"
    IDENTITY_COLLISION = "IDENTITY_COLLISION"
    BASELINE_INVALID = "BASELINE_INVALID"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    PROVIDER_REUSE_UNSUPPORTED = "PROVIDER_REUSE_UNSUPPORTED"


_REASON_PRECEDENCE = (
    ReuseEligibilityReason.AUTHORITY_CONFLICT,
    ReuseEligibilityReason.DUPLICATE_IDENTITY,
    ReuseEligibilityReason.IDENTITY_COLLISION,
    ReuseEligibilityReason.BASELINE_INVALID,
    ReuseEligibilityReason.IDENTITY_MISMATCH,
    ReuseEligibilityReason.COMPONENT_ADDED,
    ReuseEligibilityReason.COMPONENT_REMOVED,
    ReuseEligibilityReason.CONTENT_CHANGED,
    ReuseEligibilityReason.COMPONENT_REORDERED,
    ReuseEligibilityReason.UNKNOWN,
    ReuseEligibilityReason.MIXED_AUTHORITY,
    ReuseEligibilityReason.AUTHORITY_PROTECTED,
    ReuseEligibilityReason.ALWAYS_REQUIRED,
    ReuseEligibilityReason.PROVIDER_REUSE_UNSUPPORTED,
    ReuseEligibilityReason.SAME_IDENTITY_EXACT_BYTES,
    ReuseEligibilityReason.EXACT_RECONSTRUCTION_ELIGIBLE,
)


def primary_reuse_reason(
    applicable: Iterable[ReuseEligibilityReason],
) -> ReuseEligibilityReason:
    """Return the single deterministic primary reason, failing closed."""
    reasons = frozenset(applicable)
    if not reasons:
        raise ValueError("at least one reuse reason is required")
    for reason in _REASON_PRECEDENCE:
        if reason in reasons:
            return reason
    raise ValueError("unrecognized reuse reason")


@dataclass(frozen=True)
class ProviderUsageValidity:
    available: bool
    actual: bool
    usage_source: str | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    @classmethod
    def unavailable(cls) -> "ProviderUsageValidity":
        return cls(False, False, None)


def _actual_token(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def validate_openai_actual_usage(payload: Any) -> ProviderUsageValidity:
    """Validate only structured OpenAI response usage under the frozen rule."""
    if not isinstance(payload, Mapping):
        return ProviderUsageValidity.unavailable()
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return ProviderUsageValidity.unavailable()
    input_tokens = _actual_token(usage.get("input_tokens"))
    output_tokens = _actual_token(usage.get("output_tokens"))
    total_tokens = _actual_token(usage.get("total_tokens"))
    if input_tokens is output_tokens is total_tokens is None:
        return ProviderUsageValidity.unavailable()
    return ProviderUsageValidity(
        True,
        True,
        "openai_responses_usage",
        input_tokens,
        output_tokens,
        total_tokens,
    )


def unavailable_provider_usage() -> ProviderUsageValidity:
    """Represent CLI counters, estimates, missing usage, and Codex usage."""
    return ProviderUsageValidity.unavailable()


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class M42EvaluationMetrics:
    source_context_utf8_bytes: int
    source_component_count: int
    selected_context_utf8_bytes: int
    selected_component_count: int
    authority_required_component_count: int
    authority_present_component_count: int
    authority_coverage: Fraction
    authority_byte_mismatch_count: int
    unchanged_component_count: int
    changed_component_count: int
    added_component_count: int
    removed_component_count: int
    reordered_component_count: int
    unchanged_utf8_bytes: int
    delta_utf8_bytes: int
    reconstruction_exact_match: bool
    provider_boundary_reuse_supported: bool
    provider_bytes_avoided: int | None
    provider_usage: ProviderUsageValidity
    semantic_regression_count: int
    lifecycle_regression_count: int
    gate_regression_count: int


Component = ComponentSelection | ExactContextComponent


def _validate_count(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def measure_evaluation(
    source: Sequence[Component],
    selected: Sequence[Component],
    *,
    delta: ContextDelta | None = None,
    reconstruction: ReconstructionResult | None = None,
    provider_boundary_reuse_supported: bool = False,
    provider_bytes_avoided: int | None = None,
    provider_usage: ProviderUsageValidity | None = None,
    semantic_regression_count: int = 0,
    lifecycle_regression_count: int = 0,
    gate_regression_count: int = 0,
) -> M42EvaluationMetrics:
    """Measure distinct evaluation lenses without inferring provider savings."""
    for name, value in (
        ("semantic_regression_count", semantic_regression_count),
        ("lifecycle_regression_count", lifecycle_regression_count),
        ("gate_regression_count", gate_regression_count),
    ):
        _validate_count(value, name)
    if provider_bytes_avoided is not None:
        _validate_count(provider_bytes_avoided, "provider_bytes_avoided")
        if not provider_boundary_reuse_supported:
            raise ValueError("provider bytes avoided are not demonstrable")

    source_tuple = tuple(source)
    selected_tuple = tuple(selected)
    selected_positions: dict[object, list[int]] = {}
    for position, component in enumerate(selected_tuple):
        selected_positions.setdefault(component.identity, []).append(position)

    required = [
        (position, component) for position, component in enumerate(source_tuple)
        if component.authority_protected
    ]
    present = 0
    mismatches = 0
    for position, component in required:
        positions = selected_positions.get(component.identity, [])
        if positions == [position]:
            present += 1
            if selected_tuple[position].canonical_bytes != component.canonical_bytes:
                mismatches += 1
    coverage = (
        Fraction(100, 1) if not required
        else Fraction(present * 100, len(required))
    )

    changes = delta.changes if delta is not None else ()
    reordered_ids = {
        change.identity for change in changes
        if change.kind is ComponentDeltaKind.REORDERED
    }
    unchanged_changes = tuple(
        change for change in changes
        if change.kind is ComponentDeltaKind.UNCHANGED
        and change.identity not in reordered_ids
    )
    changed_changes = tuple(
        change for change in changes if change.kind is ComponentDeltaKind.CHANGED
    )
    added_changes = tuple(
        change for change in changes if change.kind is ComponentDeltaKind.ADDED
    )
    removed_changes = tuple(
        change for change in changes if change.kind is ComponentDeltaKind.REMOVED
    )
    delta_bytes = sum(
        len(change.current_component.canonical_bytes)
        for change in changed_changes + added_changes
        if change.current_component is not None
    )

    return M42EvaluationMetrics(
        sum(len(component.canonical_bytes) for component in source_tuple),
        len(source_tuple),
        sum(len(component.canonical_bytes) for component in selected_tuple),
        len(selected_tuple),
        len(required),
        present,
        coverage,
        mismatches,
        len(unchanged_changes),
        len(changed_changes),
        len(added_changes),
        len(removed_changes),
        len(reordered_ids),
        sum(
            len(change.current_component.canonical_bytes)
            for change in unchanged_changes
            if change.current_component is not None
        ),
        delta_bytes,
        bool(reconstruction is not None
             and reconstruction.reconstructed
             and reconstruction.exact_match),
        provider_boundary_reuse_supported,
        provider_bytes_avoided,
        provider_usage or ProviderUsageValidity.unavailable(),
        semantic_regression_count,
        lifecycle_regression_count,
        gate_regression_count,
    )


@dataclass(frozen=True)
class EvaluationCaseResult:
    metrics: M42EvaluationMetrics
    mandatory_case_outcomes: tuple[bool | None, ...]
    reconstruction_exercised: bool = False
    provider_token_claim: bool = False

    @property
    def status(self) -> EvaluationStatus:
        mandatory_failure = (
            self.metrics.authority_coverage != 100
            or self.metrics.authority_byte_mismatch_count != 0
            or (self.reconstruction_exercised
                and not self.metrics.reconstruction_exact_match)
            or self.metrics.semantic_regression_count != 0
            or self.metrics.lifecycle_regression_count != 0
            or self.metrics.gate_regression_count != 0
            or any(outcome is False for outcome in self.mandatory_case_outcomes)
        )
        if mandatory_failure:
            return EvaluationStatus.FAIL
        missing = (
            any(outcome is None for outcome in self.mandatory_case_outcomes)
            or (self.provider_token_claim and not self.metrics.provider_usage.available)
        )
        return EvaluationStatus.INCOMPLETE if missing else EvaluationStatus.PASS
