"""Fail-closed resource reservation and accounting for governed dispatches.

The ledger is a control-plane projection, not lifecycle or telemetry authority.
It intentionally stores only identities, bounded counters, and provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from threading import RLock
from types import MappingProxyType
from typing import Any, Iterable, Mapping


class ResourcePolicyError(PermissionError):
    def __init__(self, code: str, route: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.route = route
        self.detail = detail


class MeasurementTruth(str, Enum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    CONTEXT_SIZE = "context_size"
    UNAVAILABLE = "unavailable"


class BudgetState(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    NEAR_LIMIT = "NEAR_LIMIT"
    EXHAUSTED = "EXHAUSTED"
    UNKNOWN = "UNKNOWN"


class ResourceDimension(str, Enum):
    PROVIDER_CALLS = "provider_calls"
    TOOL_CALLS = "tool_calls"
    RETRIES = "retries"
    ACTUAL_TOKENS = "actual_tokens"
    ESTIMATED_TOKENS = "estimated_tokens"
    ACTUAL_COST_USD = "actual_cost_usd"
    ESTIMATED_COST_USD = "estimated_cost_usd"
    RUNTIME_MS = "runtime_ms"
    CPU_MS = "cpu_ms"
    MEMORY_BYTES = "memory_bytes"
    DISK_BYTES = "disk_bytes"
    PROCESS_COUNT = "process_count"
    FILESYSTEM_WRITES = "filesystem_writes"
    NETWORK_REQUESTS = "network_requests"
    GIT_WRITES = "git_writes"
    DEPLOYMENTS = "deployments"
    SECRET_ACCESSES = "secret_accesses"
    CONTEXT_BYTES = "context_bytes"


_COUNT_DIMENSIONS = frozenset(
    {
        ResourceDimension.PROVIDER_CALLS,
        ResourceDimension.TOOL_CALLS,
        ResourceDimension.RETRIES,
        ResourceDimension.ACTUAL_TOKENS,
        ResourceDimension.ESTIMATED_TOKENS,
        ResourceDimension.RUNTIME_MS,
        ResourceDimension.CPU_MS,
        ResourceDimension.MEMORY_BYTES,
        ResourceDimension.DISK_BYTES,
        ResourceDimension.PROCESS_COUNT,
        ResourceDimension.FILESYSTEM_WRITES,
        ResourceDimension.NETWORK_REQUESTS,
        ResourceDimension.GIT_WRITES,
        ResourceDimension.DEPLOYMENTS,
        ResourceDimension.SECRET_ACCESSES,
        ResourceDimension.CONTEXT_BYTES,
    }
)


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise ResourcePolicyError("INVALID_COUNTER", "BUDGET_POLICY_OWNER", label)
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ResourcePolicyError("INVALID_COUNTER", "BUDGET_POLICY_OWNER", label) from exc
    if not converted.is_finite() or converted < 0:
        raise ResourcePolicyError("INVALID_COUNTER", "BUDGET_POLICY_OWNER", label)
    return converted


def _dimension(value: ResourceDimension | str) -> ResourceDimension:
    try:
        return ResourceDimension(value)
    except (TypeError, ValueError) as exc:
        raise ResourcePolicyError(
            "UNKNOWN_RESOURCE_DIMENSION", "BUDGET_POLICY_OWNER", str(value)
        ) from exc


def _values(values: Mapping[ResourceDimension | str, Any]) -> Mapping[ResourceDimension, Decimal]:
    normalized: dict[ResourceDimension, Decimal] = {}
    for raw_dimension, raw_value in values.items():
        dimension = _dimension(raw_dimension)
        if dimension in normalized:
            raise ResourcePolicyError(
                "ACCOUNTING_CONFLICT", "BUDGET_POLICY_OWNER", dimension.value
            )
        value = _decimal(raw_value, dimension.value)
        if dimension in _COUNT_DIMENSIONS and value != value.to_integral_value():
            raise ResourcePolicyError("INVALID_COUNTER", "BUDGET_POLICY_OWNER", dimension.value)
        normalized[dimension] = value
    return MappingProxyType(normalized)


@dataclass(frozen=True)
class ResourceLimit:
    dimension: ResourceDimension | str
    hard: Decimal | int | float | str
    soft: Decimal | int | float | str | None = None
    actual_required: bool = False

    def __post_init__(self) -> None:
        dimension = _dimension(self.dimension)
        hard = _decimal(self.hard, f"{dimension.value}.hard")
        soft = hard if self.soft is None else _decimal(self.soft, f"{dimension.value}.soft")
        if soft > hard:
            raise ResourcePolicyError(
                "INVALID_LIMIT", "BUDGET_POLICY_OWNER", f"{dimension.value}: soft exceeds hard"
            )
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "hard", hard)
        object.__setattr__(self, "soft", soft)


@dataclass(frozen=True)
class DeploymentGrant:
    reference: str
    target: str
    environment: str
    approval_class: str
    release_identity: str
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if not all((self.reference, self.target, self.environment, self.release_identity)):
            raise ResourcePolicyError(
                "DEPLOYMENT_GRANT_INVALID", "HUMAN_DECISION_OWNER", "incomplete deployment grant"
            )
        if self.approval_class not in {"A0", "A1", "A2", "A3"}:
            raise ResourcePolicyError(
                "DEPLOYMENT_GRANT_INVALID", "HUMAN_DECISION_OWNER", self.approval_class
            )


@dataclass(frozen=True)
class BudgetIncreaseApproval:
    reference: str
    approval_class: str
    policy_id: str
    dimensions: tuple[ResourceDimension | str, ...]

    def __post_init__(self) -> None:
        if not self.reference or not self.policy_id or self.approval_class not in {"A2", "A3"}:
            raise ResourcePolicyError(
                "BUDGET_APPROVAL_INVALID", "HUMAN_DECISION_OWNER", "material increase requires A2/A3"
            )
        object.__setattr__(self, "dimensions", tuple(_dimension(item) for item in self.dimensions))


@dataclass(frozen=True)
class ResourcePolicy:
    policy_id: str
    provider: str
    model: str
    runtime: str
    scope: str
    limits: tuple[ResourceLimit, ...]
    required_dimensions: tuple[ResourceDimension | str, ...]
    deployment_grants: tuple[DeploymentGrant, ...] = ()
    approval_reference: str = ""

    def __post_init__(self) -> None:
        if not all((self.policy_id, self.provider, self.model, self.runtime, self.scope)):
            raise ResourcePolicyError(
                "MISSING_POLICY", "BUDGET_POLICY_OWNER", "policy identity is incomplete"
            )
        limits = tuple(self.limits)
        if not limits:
            raise ResourcePolicyError("MISSING_POLICY", "BUDGET_POLICY_OWNER", "limits are absent")
        dimensions = tuple(item.dimension for item in limits)
        if len(set(dimensions)) != len(dimensions):
            raise ResourcePolicyError(
                "ACCOUNTING_CONFLICT", "BUDGET_POLICY_OWNER", "duplicate limit dimension"
            )
        required = tuple(_dimension(item) for item in self.required_dimensions)
        if not required or len(set(required)) != len(required):
            raise ResourcePolicyError(
                "MISSING_POLICY", "BUDGET_POLICY_OWNER", "required dimensions are absent or ambiguous"
            )
        missing = set(required) - set(dimensions)
        if missing:
            raise ResourcePolicyError(
                "MISSING_REQUIRED_LIMIT",
                "BUDGET_POLICY_OWNER",
                ",".join(sorted(item.value for item in missing)),
            )
        object.__setattr__(self, "limits", limits)
        object.__setattr__(self, "required_dimensions", required)
        object.__setattr__(self, "deployment_grants", tuple(self.deployment_grants))

    @property
    def by_dimension(self) -> Mapping[ResourceDimension, ResourceLimit]:
        return MappingProxyType({item.dimension: item for item in self.limits})

    def with_increased_limits(
        self,
        replacements: Iterable[ResourceLimit],
        approval: BudgetIncreaseApproval | None,
    ) -> "ResourcePolicy":
        changed = {item.dimension: item for item in replacements}
        current = self.by_dimension
        increased = {
            dimension
            for dimension, limit in changed.items()
            if dimension in current and limit.hard > current[dimension].hard
        }
        if increased and (
            approval is None
            or approval.policy_id != self.policy_id
            or not increased.issubset(set(approval.dimensions))
        ):
            raise ResourcePolicyError(
                "BUDGET_INCREASE_REQUIRES_APPROVAL",
                "HUMAN_DECISION_OWNER",
                ",".join(sorted(item.value for item in increased)),
            )
        merged = dict(current)
        merged.update(changed)
        return ResourcePolicy(
            policy_id=self.policy_id,
            provider=self.provider,
            model=self.model,
            runtime=self.runtime,
            scope=self.scope,
            limits=tuple(merged[item] for item in sorted(merged, key=lambda value: value.value)),
            required_dimensions=self.required_dimensions,
            deployment_grants=self.deployment_grants,
            approval_reference=(approval.reference if approval is not None else self.approval_reference),
        )


@dataclass(frozen=True)
class ResourceRequest:
    dispatch_id: str
    provider: str
    model: str
    runtime: str
    scope: str
    reservation: Mapping[ResourceDimension | str, Any]
    complete_context: bool = True
    retry: bool = False
    deployment_target: str | None = None
    environment: str | None = None
    release_identity: str | None = None
    deployment_grant_reference: str | None = None

    def __post_init__(self) -> None:
        if not all((self.dispatch_id, self.provider, self.model, self.runtime, self.scope)):
            raise ResourcePolicyError(
                "MISSING_REQUEST_IDENTITY", "DISPATCH_OWNER", "resource request identity is incomplete"
            )
        object.__setattr__(self, "reservation", _values(self.reservation))


@dataclass(frozen=True)
class ResourceMeasurement:
    dimension: ResourceDimension | str
    value: Decimal | int | float | str | None
    truth: MeasurementTruth | str
    source: str
    attribution_id: str
    method: str | None = None
    method_version: str | None = None
    model_assumption: str | None = None
    input_scope: str | None = None
    observed_at: str | None = None

    def __post_init__(self) -> None:
        dimension = _dimension(self.dimension)
        try:
            truth = MeasurementTruth(self.truth)
        except (TypeError, ValueError) as exc:
            raise ResourcePolicyError(
                "INVALID_MEASUREMENT", "MEASUREMENT_OWNER", str(self.truth)
            ) from exc
        if not self.source or not self.attribution_id:
            raise ResourcePolicyError(
                "INVALID_MEASUREMENT", "MEASUREMENT_OWNER", "source and attribution are required"
            )
        value = None if self.value is None else _decimal(self.value, dimension.value)
        if truth is MeasurementTruth.UNAVAILABLE:
            if value is not None:
                raise ResourcePolicyError(
                    "INVALID_MEASUREMENT", "MEASUREMENT_OWNER", "unavailable must be null"
                )
        elif value is None:
            raise ResourcePolicyError(
                "INVALID_MEASUREMENT", "MEASUREMENT_OWNER", "measured value is required"
            )
        if truth is MeasurementTruth.ESTIMATED and not all(
            (self.method, self.method_version, self.model_assumption, self.input_scope, self.observed_at)
        ):
            raise ResourcePolicyError(
                "INVALID_ESTIMATE", "MEASUREMENT_OWNER", "estimate provenance is incomplete"
            )
        if truth is MeasurementTruth.ACTUAL and dimension in {
            ResourceDimension.ACTUAL_TOKENS,
            ResourceDimension.ACTUAL_COST_USD,
        } and self.source not in {"openai_responses_usage", "provider_invoice", "runtime_meter"}:
            raise ResourcePolicyError(
                "UNTRUSTED_ACTUAL_USAGE", "MEASUREMENT_OWNER", self.source
            )
        if dimension is ResourceDimension.CONTEXT_BYTES and truth is not MeasurementTruth.CONTEXT_SIZE:
            raise ResourcePolicyError(
                "INVALID_MEASUREMENT", "MEASUREMENT_OWNER", "context bytes are not token evidence"
            )
        if dimension in _COUNT_DIMENSIONS and value is not None and value != value.to_integral_value():
            raise ResourcePolicyError("INVALID_COUNTER", "MEASUREMENT_OWNER", dimension.value)
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "truth", truth)
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class ResourceObservation:
    dispatch_id: str
    measurements: tuple[ResourceMeasurement, ...]
    outcome: str
    evidence_reference: str

    def __post_init__(self) -> None:
        if not self.dispatch_id or not self.outcome or not self.evidence_reference:
            raise ResourcePolicyError(
                "INCOMPLETE_ACCOUNTING", "MEASUREMENT_OWNER", "observation identity is incomplete"
            )
        object.__setattr__(self, "measurements", tuple(self.measurements))


@dataclass(frozen=True)
class ResourceDecision:
    outcome: str
    state: BudgetState
    dispatch_id: str
    policy_id: str
    route: str | None
    totals: Mapping[str, str]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Reservation:
    request: ResourceRequest
    values: Mapping[ResourceDimension, Decimal]


class ResourceController:
    """Thread-safe deterministic reservation/settlement boundary."""

    def __init__(self, policy: ResourcePolicy):
        self.policy = policy
        self._totals: dict[ResourceDimension, Decimal] = {}
        self._reservations: dict[str, _Reservation] = {}
        self._completed: dict[str, tuple[ResourceObservation, ResourceDecision]] = {}
        self._unknown: set[ResourceDimension] = set()
        self._lock = RLock()

    @property
    def totals(self) -> Mapping[ResourceDimension, Decimal]:
        with self._lock:
            return MappingProxyType(dict(self._totals))

    def _identity(self, request: ResourceRequest) -> None:
        expected = (self.policy.provider, self.policy.model, self.policy.runtime, self.policy.scope)
        actual = (request.provider, request.model, request.runtime, request.scope)
        if actual != expected:
            raise ResourcePolicyError(
                "POLICY_IDENTITY_MISMATCH", "BUDGET_POLICY_OWNER", "provider/model/runtime/scope changed"
            )

    def _deployment(self, request: ResourceRequest) -> None:
        if request.deployment_target is None:
            return
        matches = [
            grant for grant in self.policy.deployment_grants
            if grant.reference == request.deployment_grant_reference
            and grant.target == request.deployment_target
            and grant.environment == request.environment
            and grant.release_identity == request.release_identity
        ]
        if len(matches) != 1:
            raise ResourcePolicyError(
                "DEPLOYMENT_GRANT_MISMATCH", "HUMAN_DECISION_OWNER", "exact deployment grant is required"
            )
        grant = matches[0]
        if grant.expires_at:
            try:
                expiry = datetime.fromisoformat(grant.expires_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ResourcePolicyError(
                    "DEPLOYMENT_GRANT_INVALID", "HUMAN_DECISION_OWNER", "invalid expiry"
                ) from exc
            if expiry.tzinfo is None or expiry.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise ResourcePolicyError(
                    "DEPLOYMENT_GRANT_EXPIRED", "HUMAN_DECISION_OWNER", grant.reference
                )

    def _reserved_total(self, dimension: ResourceDimension) -> Decimal:
        return sum(
            (item.values.get(dimension, Decimal(0)) for item in self._reservations.values()),
            Decimal(0),
        )

    def _decision(self, dispatch_id: str, *, outcome: str, route: str | None = None) -> ResourceDecision:
        states: list[BudgetState] = []
        warnings: list[str] = []
        for dimension, limit in self.policy.by_dimension.items():
            value = self._totals.get(dimension, Decimal(0)) + self._reserved_total(dimension)
            if value >= limit.hard:
                states.append(BudgetState.EXHAUSTED)
            elif dimension in self._unknown:
                states.append(BudgetState.UNKNOWN)
            elif value >= limit.soft:
                states.append(BudgetState.WARNING)
                warnings.append(dimension.value)
            else:
                states.append(BudgetState.HEALTHY)
        state = (
            BudgetState.EXHAUSTED if BudgetState.EXHAUSTED in states
            else BudgetState.UNKNOWN if BudgetState.UNKNOWN in states
            else BudgetState.WARNING if BudgetState.WARNING in states
            else BudgetState.HEALTHY
        )
        return ResourceDecision(
            outcome=outcome,
            state=state,
            dispatch_id=dispatch_id,
            policy_id=self.policy.policy_id,
            route=route,
            totals=MappingProxyType(
                {item.value: str(value) for item, value in sorted(self._totals.items(), key=lambda x: x[0].value)}
            ),
            warnings=tuple(sorted(warnings)),
        )

    def reserve(self, request: ResourceRequest) -> ResourceDecision:
        with self._lock:
            self._identity(request)
            self._deployment(request)
            if not request.complete_context:
                raise ResourcePolicyError(
                    "BUDGET_OR_CAPABILITY_BLOCKED",
                    "BUDGET_POLICY_OWNER",
                    "mandatory context/evidence cannot be truncated",
                )
            prior = self._reservations.get(request.dispatch_id)
            if prior is not None:
                if prior.request == request:
                    return self._decision(request.dispatch_id, outcome="RESERVED")
                raise ResourcePolicyError(
                    "ACCOUNTING_CONFLICT", "BUDGET_POLICY_OWNER", "dispatch id was reused"
                )
            completed = self._completed.get(request.dispatch_id)
            if completed is not None:
                raise ResourcePolicyError(
                    "DISPATCH_ALREADY_ACCOUNTED", "BUDGET_POLICY_OWNER", request.dispatch_id
                )
            required = set(self.policy.required_dimensions)
            missing = required - set(request.reservation)
            if missing:
                raise ResourcePolicyError(
                    "INSUFFICIENT_RESERVATION",
                    "BUDGET_POLICY_OWNER",
                    ",".join(sorted(item.value for item in missing)),
                )
            if request.retry and request.reservation.get(ResourceDimension.RETRIES, Decimal(0)) < 1:
                raise ResourcePolicyError(
                    "RETRY_BUDGET_REQUIRED", "BUDGET_POLICY_OWNER", request.dispatch_id
                )
            for dimension, requested in request.reservation.items():
                limit = self.policy.by_dimension.get(dimension)
                if limit is None:
                    raise ResourcePolicyError(
                        "MISSING_REQUIRED_LIMIT", "BUDGET_POLICY_OWNER", dimension.value
                    )
                projected = self._totals.get(dimension, Decimal(0)) + self._reserved_total(dimension) + requested
                if projected > limit.hard:
                    raise ResourcePolicyError(
                        "BUDGET_BLOCKED", "HUMAN_DECISION_OR_NEXT_WINDOW", dimension.value
                    )
            self._reservations[request.dispatch_id] = _Reservation(request, request.reservation)
            return self._decision(request.dispatch_id, outcome="RESERVED")

    def settle(self, observation: ResourceObservation) -> ResourceDecision:
        with self._lock:
            completed = self._completed.get(observation.dispatch_id)
            if completed is not None:
                if completed[0] == observation:
                    return completed[1]
                raise ResourcePolicyError(
                    "ACCOUNTING_CONFLICT", "BUDGET_POLICY_OWNER", "different completed observation"
                )
            reservation = self._reservations.get(observation.dispatch_id)
            if reservation is None:
                raise ResourcePolicyError(
                    "MISSING_RESERVATION", "BUDGET_POLICY_OWNER", observation.dispatch_id
                )
            measurements: dict[ResourceDimension, ResourceMeasurement] = {}
            increments: dict[ResourceDimension, Decimal] = {}
            for measurement in observation.measurements:
                if measurement.dimension in measurements:
                    raise ResourcePolicyError(
                        "ACCOUNTING_CONFLICT", "BUDGET_POLICY_OWNER", measurement.dimension.value
                    )
                measurements[measurement.dimension] = measurement
                if measurement.value is not None:
                    increments[measurement.dimension] = measurement.value
            for dimension, limit in self.policy.by_dimension.items():
                if limit.actual_required:
                    measurement = measurements.get(dimension)
                    if measurement is None or measurement.truth is not MeasurementTruth.ACTUAL:
                        raise ResourcePolicyError(
                            "INCOMPLETE_ACTUAL_USAGE", "MEASUREMENT_OWNER", dimension.value
                        )
            # Validate the entire candidate before mutating totals or releasing the reservation.
            candidate = dict(self._totals)
            candidate_unknown = set(self._unknown)
            if reservation.request.retry and ResourceDimension.RETRIES not in increments:
                increments[ResourceDimension.RETRIES] = Decimal(1)
            for dimension, measurement in measurements.items():
                if (
                    dimension in self.policy.by_dimension
                    and measurement.truth is MeasurementTruth.UNAVAILABLE
                ):
                    candidate_unknown.add(dimension)
            for dimension, value in increments.items():
                if dimension not in self.policy.by_dimension:
                    raise ResourcePolicyError(
                        "MISSING_REQUIRED_LIMIT", "BUDGET_POLICY_OWNER", dimension.value
                    )
                candidate[dimension] = candidate.get(dimension, Decimal(0)) + value
            self._totals = candidate
            self._unknown = candidate_unknown
            del self._reservations[observation.dispatch_id]
            decision = self._decision(observation.dispatch_id, outcome="ACCOUNTED")
            self._completed[observation.dispatch_id] = (observation, decision)
            return decision

    def cancel(self, dispatch_id: str) -> ResourceDecision:
        with self._lock:
            if dispatch_id not in self._reservations:
                raise ResourcePolicyError(
                    "MISSING_RESERVATION", "BUDGET_POLICY_OWNER", dispatch_id
                )
            del self._reservations[dispatch_id]
            return self._decision(dispatch_id, outcome="CANCELLED")

    def select_conformant_route(
        self,
        candidates: Iterable[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        """Choose the cheapest candidate only after all conformance flags pass."""
        eligible = [
            item for item in candidates
            if item.get("adapter_conformant") is True
            and item.get("security_equivalent") is True
            and item.get("authority_equivalent") is True
            and item.get("evidence_equivalent") is True
            and item.get("required_context_complete") is True
        ]
        if not eligible:
            raise ResourcePolicyError(
                "NO_CONFORMANT_ROUTE", "HUMAN_DECISION_OWNER", "cost cannot weaken governance"
            )
        try:
            return min(eligible, key=lambda item: _decimal(item["estimated_cost_usd"], "estimated_cost_usd"))
        except KeyError as exc:
            raise ResourcePolicyError(
                "UNKNOWN_ROUTE_COST", "BUDGET_POLICY_OWNER", "candidate cost is unavailable"
            ) from exc
