from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import shutil
import subprocess
import tempfile
import time
import re
from uuid import uuid4
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .executor import (
    SharedExecutorPrerequisiteError,
    StageExecutionRequest,
    StageExecutionResult,
)
from .telemetry.measurement import measure_provider_call
from .telemetry.models import (
    Availability,
    Component,
    OutcomeCategory,
    Quality,
    Usage,
    UsageSource,
)
from .task_parser import SealedExecutionEnvelope
from .governance_envelope import (
    DispatchObservation,
    DispatchRequest,
    GovernanceEnvelope,
    GovernanceEnvelopeError,
    GovernanceEnvelopeValidator,
    IdentityBinding,
)
from .security_policy import redact_security_value
from .resource_policy import (
    MeasurementTruth,
    ResourceController,
    ResourceDimension,
    ResourceMeasurement,
    ResourceObservation,
    ResourcePolicyError,
    ResourceRequest,
)
from .provider_conformance import (
    ProviderCapabilityManifest,
    ProviderConformanceContext,
    ProviderConformanceError,
    ProviderConformanceEvidence,
    ProviderConformanceGate,
)


class ReasoningProviderError(RuntimeError):
    pass


class SharedReasoningProviderPrerequisiteError(
    ReasoningProviderError, SharedExecutorPrerequisiteError
):
    pass


class ProviderUnavailableError(ReasoningProviderError):
    """The selected adapter cannot service this bounded invocation."""


class ProviderPolicyViolationError(ReasoningProviderError):
    """The provider refused or violated the declared policy boundary."""


REASONING_CAPABILITIES = frozenset(
    {
        "ANALYZE",
        "ASK_QUESTIONS",
        "PROPOSE",
        "DRAFT",
        "REASON",
        "AUTHORIZED_STAGE08_ASSISTANCE",
        "VERIFICATION_ASSISTANCE",
    }
)
WRITE_CAPABILITY = "AUTHORIZED_STAGE08_ASSISTANCE"


def _conformance_metadata(
    evidence: ProviderConformanceEvidence | None,
) -> dict[str, Any]:
    """Expose only machine-visible, non-secret conformance evidence to owners."""
    return {} if evidence is None else {"provider_conformance": evidence.payload()}


class ReasoningProvider(Protocol):
    """Replaceable adapter; governance semantics live in the boundary below."""

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        ...


@dataclass(frozen=True)
class ReasoningInvocation:
    """Bounded, attributable input to a replaceable reasoning provider."""

    attempt_id: str
    operation: str
    request: StageExecutionRequest
    authoritative_context_refs: tuple[str, ...]
    permitted_capabilities: frozenset[str]
    affected_scope: tuple[str, ...]
    expected_result: str = "STAGE_EXECUTION_RESULT"
    validation_inputs: Mapping[str, Any] = field(default_factory=dict)
    authorization_envelope: SealedExecutionEnvelope | None = None
    governance_envelope: GovernanceEnvelope | None = None
    governance_request: DispatchRequest | None = None
    current_identity: IdentityBinding | None = None
    resource_request: ResourceRequest | None = None


@dataclass(frozen=True)
class ProviderFailure:
    category: str
    attempt_id: str
    operation: str
    affected_scope: tuple[str, ...]
    detail: str
    eligible_routes: tuple[str, ...]
    prior_state_preserved: bool = True
    unsafe_continuation_stopped: bool = True


@dataclass(frozen=True)
class ReasoningBoundaryResult:
    status: str
    attempt_id: str
    operation: str
    proposed_output: StageExecutionResult | None = None
    failure: ProviderFailure | None = None
    authoritative: bool = False
    persisted: bool = False


_FAILURE_ROUTES = {
    "UNAVAILABLE": ("RETRY", "ALTERNATE_PROVIDER", "ESCALATION"),
    "TIMEOUT": ("RETRY", "ALTERNATE_PROVIDER", "ESCALATION"),
    "MALFORMED": ("RETRY", "ALTERNATE_PROVIDER", "REMEDIATION", "ESCALATION"),
    "POLICY_VIOLATION": (
        "ALTERNATE_PROVIDER",
        "REMEDIATION",
        "ESCALATION",
        "HUMAN_DECISION",
    ),
    "OUT_OF_SCOPE": ("REVISION", "ESCALATION"),
    "AUTHORITY_CROSSING": ("ESCALATION", "HUMAN_DECISION"),
    "NO_AUTHORIZATION": ("ESCALATION", "HUMAN_DECISION"),
}


class ReasoningProviderBoundary:
    """Provider-independent guard for SPEC-006 / SPEC-009 / DES-006.

    This port does not persist output or grant authority. It validates the
    provider exchange and returns proposed output for an owning boundary to
    validate further and, when authorized, persist.
    """

    def __init__(
        self,
        provider: ReasoningProvider,
        *,
        authorization_validator: Callable[[SealedExecutionEnvelope], bool] | None = None,
        governance_validator: GovernanceEnvelopeValidator | None = None,
        require_governance: bool = False,
        resource_controller: ResourceController | None = None,
        require_resource_policy: bool = False,
        conformance_gate: ProviderConformanceGate | None = None,
        conformance_manifest: ProviderCapabilityManifest | None = None,
        conformance_evidence: ProviderConformanceEvidence | None = None,
        conformance_context: ProviderConformanceContext | None = None,
    ):
        self.provider = provider
        self.authorization_validator = authorization_validator
        self.governance_validator = governance_validator or GovernanceEnvelopeValidator()
        self.require_governance = require_governance
        self.resource_controller = resource_controller
        self.require_resource_policy = require_resource_policy
        self.conformance_gate = conformance_gate
        self.conformance_manifest = conformance_manifest
        self.conformance_evidence = conformance_evidence
        self.conformance_context = conformance_context

    @staticmethod
    def _safe_detail(detail: str) -> str:
        bounded = detail[:1000]
        legacy_redacted = re.sub(
            r"(?i)(authorization\s*[:=]\s*bearer|api[_-]?key\s*[:=])\s*[^\s,;]+",
            r"\1 [REDACTED]",
            bounded,
        )
        return str(redact_security_value(legacy_redacted))

    @staticmethod
    def _failure(invocation: ReasoningInvocation, category: str, detail: str) -> ReasoningBoundaryResult:
        return ReasoningBoundaryResult(
            status="BLOCKED",
            attempt_id=invocation.attempt_id,
            operation=invocation.operation,
            failure=ProviderFailure(
                category=category,
                attempt_id=invocation.attempt_id,
                operation=invocation.operation,
                affected_scope=invocation.affected_scope,
                detail=ReasoningProviderBoundary._safe_detail(detail),
                eligible_routes=_FAILURE_ROUTES[category],
            ),
        )

    def _envelope_covers(self, invocation: ReasoningInvocation) -> bool:
        envelope = invocation.authorization_envelope
        if envelope is None or invocation.request.stage_id != "08":
            return False
        if not envelope.envelope_id or not envelope.task_id or not envelope.baseline_commit:
            return False
        allowed = set(envelope.allowed_paths)
        if not allowed or not all(path in allowed for path in invocation.affected_scope):
            return False
        if self.authorization_validator is None:
            return False
        try:
            return self.authorization_validator(envelope) is True
        except Exception:
            return False

    def _preflight(self, invocation: ReasoningInvocation) -> ReasoningBoundaryResult | None:
        if not invocation.attempt_id.strip() or not invocation.operation.strip():
            return self._failure(invocation, "MALFORMED", "attempt_id and operation are required")
        if not invocation.authoritative_context_refs:
            return self._failure(
                invocation,
                "AUTHORITY_CROSSING",
                "authoritative context references are required; chat context is not authority",
            )
        if not invocation.affected_scope:
            return self._failure(invocation, "OUT_OF_SCOPE", "affected scope must be declared")
        unknown = invocation.permitted_capabilities - REASONING_CAPABILITIES
        if unknown or not invocation.permitted_capabilities:
            return self._failure(
                invocation,
                "POLICY_VIOLATION",
                f"undeclared or unsupported capabilities: {sorted(unknown)}",
            )
        if invocation.expected_result != "STAGE_EXECUTION_RESULT":
            return self._failure(invocation, "MALFORMED", "unsupported expected structured result")
        if WRITE_CAPABILITY in invocation.permitted_capabilities and not self._envelope_covers(invocation):
            return self._failure(
                invocation,
                "NO_AUTHORIZATION",
                "write-capable invocation requires a sealed Stage08 envelope covering affected scope",
            )
        if self.conformance_gate is not None:
            try:
                self.conformance_gate.require_dispatch(
                    self.conformance_manifest,
                    self.conformance_evidence,
                    self.conformance_context,
                )
            except ProviderConformanceError as exc:
                return self._failure(
                    invocation, "POLICY_VIOLATION", f"{exc.code}: {exc.detail}"
                )
        resource_bound = bool(
            invocation.governance_request is not None
            and invocation.governance_request.resource_policy_reference
        )
        if self.require_resource_policy or resource_bound or invocation.resource_request is not None:
            if self.resource_controller is None or invocation.resource_request is None:
                return self._failure(
                    invocation,
                    "POLICY_VIOLATION",
                    "complete resource policy bindings are required before dispatch",
                )
            if (
                invocation.governance_request is not None
                and invocation.governance_request.resource_policy_reference
                and invocation.governance_request.resource_policy_reference
                != self.resource_controller.policy.policy_id
            ):
                return self._failure(
                    invocation,
                    "POLICY_VIOLATION",
                    "resource policy identity does not match the governance envelope",
                )
        governance_fields = (
            invocation.governance_envelope,
            invocation.governance_request,
            invocation.current_identity,
        )
        if self.require_governance or any(item is not None for item in governance_fields):
            if any(item is None for item in governance_fields):
                return self._failure(
                    invocation, "NO_AUTHORIZATION",
                    "complete unified governance envelope bindings are required",
                )
            try:
                self.governance_validator.validate_pre_dispatch(
                    invocation.governance_envelope,
                    invocation.governance_request,
                    current_identity=invocation.current_identity,
                )
            except GovernanceEnvelopeError as exc:
                category = (
                    "AUTHORITY_CROSSING"
                    if exc.code in {"PROVIDER_AUTHORITY_CLAIM", "APPROVAL_MISMATCH"}
                    else "POLICY_VIOLATION"
                )
                return self._failure(invocation, category, f"{exc.code}: {exc.detail}")
        return None

    def _settle_resource(
        self,
        invocation: ReasoningInvocation,
        *,
        started: float,
        outcome: str,
    ) -> ReasoningBoundaryResult | None:
        if self.resource_controller is None or invocation.resource_request is None:
            return None
        dispatch_id = invocation.resource_request.dispatch_id
        duration_ms = max(0, round((time.monotonic() - started) * 1000))
        measurements = (
            ResourceMeasurement(
                ResourceDimension.PROVIDER_CALLS, 1, MeasurementTruth.ACTUAL,
                "runtime_meter", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.RUNTIME_MS, duration_ms, MeasurementTruth.ACTUAL,
                "runtime_meter", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.PROCESS_COUNT, 1, MeasurementTruth.ACTUAL,
                "runtime_meter", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.ACTUAL_TOKENS, None, MeasurementTruth.UNAVAILABLE,
                "provider_interface_unavailable", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.ACTUAL_COST_USD, None, MeasurementTruth.UNAVAILABLE,
                "provider_interface_unavailable", dispatch_id,
            ),
        )
        try:
            self.resource_controller.settle(
                ResourceObservation(
                    dispatch_id=dispatch_id,
                    measurements=tuple(
                        item for item in measurements
                        if item.dimension in self.resource_controller.policy.by_dimension
                    ),
                    outcome=outcome,
                    evidence_reference=f"reasoning-boundary:{invocation.attempt_id}",
                )
            )
        except ResourcePolicyError as exc:
            return self._failure(invocation, "POLICY_VIOLATION", f"{exc.code}: {exc.detail}")
        return None

    def _validate_output(
        self, invocation: ReasoningInvocation, output: Any
    ) -> ReasoningBoundaryResult | None:
        if not isinstance(output, StageExecutionResult):
            return self._failure(invocation, "MALFORMED", "provider returned no StageExecutionResult")
        if output.status not in {"COMPLETED", "BLOCKED"}:
            return self._failure(invocation, "MALFORMED", "provider returned an invalid status")
        if not isinstance(output.artifacts, dict) or any(
            not isinstance(path, str) or not isinstance(content, str)
            for path, content in output.artifacts.items()
        ):
            return self._failure(invocation, "MALFORMED", "provider returned invalid artifacts")
        if not isinstance(output.metadata, dict):
            return self._failure(invocation, "MALFORMED", "provider returned invalid metadata")
        if not isinstance(output.remediation_reasons, list) or any(
            not isinstance(reason, str) for reason in output.remediation_reasons
        ):
            return self._failure(
                invocation, "MALFORMED", "provider returned invalid remediation reasons"
            )
        result_vocabulary = set(
            invocation.request.contract.get("result_vocabulary", []) or []
        )
        if output.result is not None and result_vocabulary and output.result not in result_vocabulary:
            return self._failure(
                invocation, "MALFORMED", "provider returned a result outside the stage vocabulary"
            )
        allowed_outputs = set(_allowed_output_paths(invocation.request))
        unexpected = set(output.artifacts) - allowed_outputs
        if unexpected:
            return self._failure(
                invocation,
                "OUT_OF_SCOPE",
                f"provider emitted artifacts outside declared outputs: {sorted(unexpected)}",
            )
        forbidden_claims = {
            "authority_created",
            "approval_created",
            "evidence_created",
            "qualification_committed",
            "gate_bypassed",
        }
        claims = {key for key in forbidden_claims if output.metadata.get(key)}
        if claims:
            return self._failure(
                invocation,
                "AUTHORITY_CROSSING",
                f"provider attempted governed-core claims: {sorted(claims)}",
            )
        return None

    def invoke(self, invocation: ReasoningInvocation) -> ReasoningBoundaryResult:
        reserved = False
        if self.resource_controller is not None and invocation.resource_request is not None:
            try:
                self.resource_controller.reserve(invocation.resource_request)
                reserved = True
            except ResourcePolicyError as exc:
                return self._failure(
                    invocation, "POLICY_VIOLATION", f"{exc.code}: {exc.detail}"
                )
        blocked = self._preflight(invocation)
        if blocked is not None:
            if reserved:
                self.resource_controller.cancel(invocation.resource_request.dispatch_id)
            return blocked
        resource_started = time.monotonic()
        try:
            output = self.provider.execute(invocation.request)
        except (TimeoutError, subprocess.TimeoutExpired) as exc:
            accounting = self._settle_resource(
                invocation, started=resource_started, outcome="timeout"
            )
            if accounting is not None:
                return accounting
            return self._failure(invocation, "TIMEOUT", str(exc) or "provider timed out")
        except (ProviderUnavailableError, SharedReasoningProviderPrerequisiteError) as exc:
            accounting = self._settle_resource(
                invocation, started=resource_started, outcome="unavailable"
            )
            if accounting is not None:
                return accounting
            return self._failure(invocation, "UNAVAILABLE", str(exc))
        except ProviderPolicyViolationError as exc:
            accounting = self._settle_resource(
                invocation, started=resource_started, outcome="blocked"
            )
            if accounting is not None:
                return accounting
            return self._failure(invocation, "POLICY_VIOLATION", str(exc))
        except Exception as exc:
            accounting = self._settle_resource(
                invocation, started=resource_started, outcome="failed"
            )
            if accounting is not None:
                return accounting
            return self._failure(invocation, "MALFORMED", f"{type(exc).__name__}: {exc}")

        accounting = self._settle_resource(
            invocation, started=resource_started, outcome="completed"
        )
        if accounting is not None:
            return accounting

        try:
            blocked = self._validate_output(invocation, output)
        except Exception as exc:
            return self._failure(
                invocation, "MALFORMED", f"output validation failed: {type(exc).__name__}: {exc}"
            )
        if blocked is not None:
            return blocked
        if invocation.governance_envelope is not None:
            assert invocation.governance_request is not None
            try:
                self.governance_validator.reconcile_post_dispatch(
                    invocation.governance_envelope,
                    invocation.governance_request,
                    DispatchObservation(
                        outcome="PASS",
                        actual_scope=tuple(sorted(output.artifacts)),
                        actual_side_effects=invocation.governance_request.side_effects,
                        evidence_references=(f"provider-attempt:{invocation.attempt_id}",),
                    ),
                )
            except GovernanceEnvelopeError as exc:
                return self._failure(invocation, "OUT_OF_SCOPE", f"{exc.code}: {exc.detail}")
        metadata = dict(output.metadata)
        metadata.update(
            {
                "provider_output_status": "PROPOSED_UNVALIDATED",
                "provider_attempt_id": invocation.attempt_id,
                "provider_operation": invocation.operation,
            }
        )
        metadata.update(_conformance_metadata(self.conformance_evidence))
        proposed = replace(output, metadata=metadata)
        return ReasoningBoundaryResult(
            status="PROPOSED",
            attempt_id=invocation.attempt_id,
            operation=invocation.operation,
            proposed_output=proposed,
        )


@dataclass(frozen=True)
class PreparedCodexExecution:
    request: StageExecutionRequest
    executable: str
    schema_json: str
    prompt: str


@dataclass(frozen=True)
class PreparedOpenAIExecution:
    request: StageExecutionRequest
    wire: bytes
    instructions: str
    user_input: str


def _allowed_output_paths(request: StageExecutionRequest) -> list[str]:
    paths = list(request.contract.get("outputs", {}).get("files", []) or [])
    # Optional output globs cannot be represented safely as arbitrary paths in a
    # strict JSON schema. They remain available through the external-command
    # executor and can be added to provider-specific adapters later.
    return paths


def _result_schema(request: StageExecutionRequest) -> dict[str, Any]:
    paths = _allowed_output_paths(request)
    result_vocab = request.contract.get("result_vocabulary", []) or []

    result_schema: dict[str, Any]
    if result_vocab:
        result_schema = {"type": ["string", "null"], "enum": [*result_vocab, None]}
    else:
        result_schema = {"type": ["string", "null"]}

    # Only Stage 09 owns implementation-gap / authority-conflict classification.
    # Other stages must keep classification null and describe blockers through
    # the stage report + remediation_reasons. This prevents Stage 07 readiness
    # failures from being mislabeled as Stage 09 IMPLEMENTATION_GAP.
    classification_values = (
        ["IMPLEMENTATION_GAP", "AUTHORITY_CONTRACT_CONFLICT", None]
        if request.stage_id == "09"
        else [None]
    )

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["COMPLETED", "BLOCKED"]},
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "enum": paths or ["__NO_OUTPUT__"]},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
            "result": result_schema,
            "classification": {
                "type": ["string", "null"],
                "enum": classification_values,
            },
            "remediation_reasons": {
                "type": "array",
                "items": {"type": "string"},
            },
            "provider_notes": {"type": ["string", "null"]},
        },
        "required": [
            "status",
            "artifacts",
            "result",
            "classification",
            "remediation_reasons",
            "provider_notes",
        ],
        "additionalProperties": False,
    }

    if request.stage_id == "09":
        schema["properties"]["convergence_tasks"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                    "traceability": {"type": "array", "items": {"type": "string"}},
                    "allowed_paths": {"type": "array", "items": {"type": "string"}},
                    "verification_commands": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "task_id",
                    "title",
                    "objective",
                    "traceability",
                    "allowed_paths",
                    "verification_commands",
                ],
                "additionalProperties": False,
            },
        }
        schema["required"].append("convergence_tasks")

    return schema


def _provider_system_instructions(request: StageExecutionRequest) -> str:
    base = """You are a governed SDD stage executor inside a repository-first software development system.

You MUST follow the stage contract and authority boundaries supplied in the request. Never use linear document priority such as PRD > Spec > Design. Resolve authority by domain. If authoritative artifacts conflict, do not choose a winner or invent a workaround: report BLOCKED and provide remediation reasons. Do not claim to have run repository commands unless runtime evidence is present in the request.

Return only the structured result required by the response schema. Artifact content must be complete file content, not commentary around the file. Do not emit files outside the declared output paths.
"""
    if request.stage_instructions:
        base += "\nSTAGE-SPECIFIC INSTRUCTIONS:\n" + request.stage_instructions
    else:
        base += (
            "\nNo separate stage instruction file is installed. Treat the machine-readable "
            "stage contract in the request as binding and do not expand authority beyond it."
        )
    return base


def _provider_user_input(request: StageExecutionRequest) -> str:
    payload = request.to_dict()
    return (
        "Execute this SDD stage using only the supplied authoritative context. "
        "Preserve traceability and mark unresolved critical uncertainty as blocked/TBD rather than guessing.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    for item in response.get("output", []) or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    raise ReasoningProviderError("OpenAI response did not contain output text")


def _non_negative_int(value: Any) -> int | None:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )


def _openai_response_usage(payload: Any) -> Usage | None:
    if not isinstance(payload, dict):
        return None
    raw_usage = payload.get("usage")
    if not isinstance(raw_usage, dict):
        return None

    input_tokens = _non_negative_int(raw_usage.get("input_tokens"))
    output_tokens = _non_negative_int(raw_usage.get("output_tokens"))
    total_tokens = _non_negative_int(raw_usage.get("total_tokens"))
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    input_details = raw_usage.get("input_tokens_details")
    output_details = raw_usage.get("output_tokens_details")
    cached_input_tokens = (
        _non_negative_int(input_details.get("cached_tokens"))
        if isinstance(input_details, dict)
        else None
    )
    reasoning_output_tokens = (
        _non_negative_int(output_details.get("reasoning_tokens"))
        if isinstance(output_details, dict)
        else None
    )
    return Usage(
        availability=Availability.AVAILABLE,
        quality=Quality.ACTUAL,
        usage_source=UsageSource.OPENAI_RESPONSES_USAGE,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        component_tokens={
            "cached_input_tokens": cached_input_tokens,
            "reasoning_output_tokens": reasoning_output_tokens,
        },
    )


def _reserve_provider_dispatch(
    controller: ResourceController | None,
    *,
    dispatch_id: str,
    provider: str,
    model: str,
    runtime: str,
    context_bytes: int,
    timeout_ms: int,
    declared: Mapping[ResourceDimension | str, Any] | None,
) -> None:
    if controller is None:
        return
    known: dict[ResourceDimension | str, Any] = {
        ResourceDimension.PROVIDER_CALLS: 1,
        ResourceDimension.RUNTIME_MS: timeout_ms,
        ResourceDimension.PROCESS_COUNT: 1,
        ResourceDimension.CONTEXT_BYTES: context_bytes,
    }
    known.update(dict(declared or {}))
    normalized = {ResourceDimension(key): value for key, value in known.items()}
    missing = set(controller.policy.required_dimensions) - set(normalized)
    if missing:
        raise ResourcePolicyError(
            "UNKNOWN_REQUIRED_BUDGET",
            "BUDGET_POLICY_OWNER",
            ",".join(sorted(item.value for item in missing)),
        )
    controller.reserve(
        ResourceRequest(
            dispatch_id=dispatch_id,
            provider=provider,
            model=model,
            runtime=runtime,
            scope=controller.policy.scope,
            reservation={
                item: value
                for item, value in normalized.items()
                if item in controller.policy.by_dimension
            },
        )
    )


def _settle_provider_dispatch(
    controller: ResourceController | None,
    *,
    dispatch_id: str,
    duration_ms: int,
    context_bytes: int,
    outcome: OutcomeCategory,
    usage: Usage | None,
    usage_source: str,
) -> None:
    if controller is None:
        return
    measurements = [
        ResourceMeasurement(
            ResourceDimension.PROVIDER_CALLS, 1, MeasurementTruth.ACTUAL,
            "runtime_meter", dispatch_id,
        ),
        ResourceMeasurement(
            ResourceDimension.RUNTIME_MS, duration_ms, MeasurementTruth.ACTUAL,
            "runtime_meter", dispatch_id,
        ),
        ResourceMeasurement(
            ResourceDimension.PROCESS_COUNT, 1, MeasurementTruth.ACTUAL,
            "runtime_meter", dispatch_id,
        ),
        ResourceMeasurement(
            ResourceDimension.CONTEXT_BYTES, context_bytes, MeasurementTruth.CONTEXT_SIZE,
            "utf8_measurement", dispatch_id,
        ),
    ]
    if usage is not None and usage.total_tokens is not None:
        measurements.append(
            ResourceMeasurement(
                ResourceDimension.ACTUAL_TOKENS, usage.total_tokens,
                MeasurementTruth.ACTUAL, usage_source, dispatch_id,
            )
        )
    else:
        measurements.append(
            ResourceMeasurement(
                ResourceDimension.ACTUAL_TOKENS, None, MeasurementTruth.UNAVAILABLE,
                usage_source, dispatch_id,
            )
        )
    measurements.append(
        ResourceMeasurement(
            ResourceDimension.ACTUAL_COST_USD, None, MeasurementTruth.UNAVAILABLE,
            usage_source, dispatch_id,
        )
    )
    controller.settle(
        ResourceObservation(
            dispatch_id=dispatch_id,
            measurements=tuple(
                item for item in measurements
                if item.dimension in controller.policy.by_dimension
            ),
            outcome=outcome.value,
            evidence_reference=f"provider-dispatch:{dispatch_id}",
        )
    )

class CodexExecReasoningExecutor:
    """Default reasoning adapter using Codex CLI with saved ChatGPT authentication.

    Reasoning stages run in a read-only sandbox. The SDD Orchestrator, not Codex,
    writes validated artifacts into the repository. This keeps Stage authority and
    write scope deterministic while avoiding a required OpenAI API key.
    """

    def __init__(
        self,
        *,
        executable: str = "codex",
        model: str | None = None,
        timeout_seconds: int = 1800,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
        repo_root: str | Path | None = None,
        telemetry_recorder=None,
        resource_controller: ResourceController | None = None,
        resource_reservation: Mapping[ResourceDimension | str, Any] | None = None,
        conformance_gate: ProviderConformanceGate | None = None,
        conformance_manifest: ProviderCapabilityManifest | None = None,
        conformance_evidence: ProviderConformanceEvidence | None = None,
        conformance_context: ProviderConformanceContext | None = None,
    ):
        self.executable = executable
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.ephemeral = ephemeral
        self.ignore_user_config = ignore_user_config
        self.repo_root = Path(repo_root).resolve() if repo_root is not None else Path.cwd()
        self.telemetry_recorder = telemetry_recorder
        self.resource_controller = resource_controller
        self.resource_reservation = dict(resource_reservation or {})
        self.conformance_gate = conformance_gate
        self.conformance_manifest = conformance_manifest
        self.conformance_evidence = conformance_evidence
        self.conformance_context = conformance_context

    def _validate_conformance(self) -> None:
        if self.conformance_gate is not None:
            self.conformance_gate.require_dispatch(
                self.conformance_manifest,
                self.conformance_evidence,
                self.conformance_context,
            )

    def resolved_executable(self) -> str | None:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        if os.name == "nt" and not self.executable.lower().endswith((".cmd", ".exe", ".bat")):
            return shutil.which(self.executable + ".cmd")
        return None

    def available(self) -> bool:
        return self.resolved_executable() is not None

    def command(self, schema_path: Path, output_path: Path, *, executable: str | None = None) -> list[str]:
        cmd = [
            executable or self.executable,
            "exec",
            "--sandbox",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
        ]
        if self.ephemeral:
            cmd.append("--ephemeral")
        if self.ignore_user_config:
            cmd.append("--ignore-user-config")
        if self.model:
            cmd.extend(["--model", self.model])
        # Read the complete generated prompt from stdin. This avoids command-line
        # length limits for large PRD/Spec/Design packets.
        cmd.append("-")
        return cmd

    def build_prompt(self, request: StageExecutionRequest) -> str:
        return _provider_system_instructions(request) + "\n\n" + _provider_user_input(request)

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        return self.dispatch(self.prepare(request))

    def prepare(self, request: StageExecutionRequest) -> PreparedCodexExecution:
        executable = self.resolved_executable()
        if not executable:
            raise SharedReasoningProviderPrerequisiteError(
                "Codex CLI is not installed or not on PATH. Install Codex and run `codex login` with ChatGPT before using the default reasoning provider."
            )
        schema = _result_schema(request)
        prompt = self.build_prompt(request)
        return PreparedCodexExecution(
            request=request,
            executable=executable,
            schema_json=json.dumps(schema, ensure_ascii=False, indent=2),
            prompt=prompt,
        )

    def dispatch(self, prepared: PreparedCodexExecution) -> StageExecutionResult:
        request = prepared.request
        prompt = prepared.prompt
        self._validate_conformance()
        dispatch_id = f"codex-reasoning:{uuid4()}"
        _reserve_provider_dispatch(
            self.resource_controller,
            dispatch_id=dispatch_id,
            provider="codex",
            model=self.model or "codex-config-default",
            runtime="codex_exec_reasoning",
            context_bytes=len(prompt.encode("utf-8")),
            timeout_ms=self.timeout_seconds * 1000,
            declared=self.resource_reservation,
        )
        with tempfile.TemporaryDirectory(prefix=f"sdd-stage-{request.stage_id}-") as tmp:
            tmpdir = Path(tmp)
            schema_path = tmpdir / "result.schema.json"
            output_path = tmpdir / "result.json"
            schema_path.write_text(prepared.schema_json, encoding="utf-8")

            started = time.monotonic()
            outcome = OutcomeCategory.FAILED
            try:
                proc = subprocess.run(
                    self.command(schema_path, output_path, executable=prepared.executable),
                    input=prompt,
                    text=True,
                    encoding="utf-8",
                    errors="strict",
                    capture_output=True,
                    cwd=self.repo_root,
                    timeout=self.timeout_seconds,
                )
                if proc.returncode == 0:
                    outcome = OutcomeCategory.COMPLETED
            except (subprocess.TimeoutExpired, TimeoutError):
                outcome = OutcomeCategory.TIMEOUT
                raise
            finally:
                duration_ms = max(0, round((time.monotonic() - started) * 1000))
                _settle_provider_dispatch(
                    self.resource_controller,
                    dispatch_id=dispatch_id,
                    duration_ms=duration_ms,
                    context_bytes=len(prompt.encode("utf-8")),
                    outcome=outcome,
                    usage=None,
                    usage_source="codex_cli_unavailable",
                )
                if self.telemetry_recorder is not None:
                    try:
                        event = measure_provider_call(
                            stage_id=request.stage_id,
                            rendered=[(prompt, Component.USER_INPUT)],
                            wire=None,
                            outcome_category=outcome,
                            metadata={
                                "provider": "codex",
                                "model": self.model or "codex-config-default",
                                "adapter": "codex_exec_reasoning",
                                "interface": "subprocess_stdin",
                                "duration_ms": duration_ms,
                            },
                        )
                        self.telemetry_recorder.record(event)
                    except Exception:
                        pass
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                if len(detail) > 6000:
                    detail = detail[:2500] + "\n... [middle truncated] ...\n" + detail[-3500:]
                raise ReasoningProviderError(
                    f"Codex reasoning execution failed ({proc.returncode}): {detail}"
                )
            if not output_path.exists():
                raise ReasoningProviderError(
                    "Codex did not write the expected --output-last-message file"
                )
            raw = output_path.read_text(encoding="utf-8").strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ReasoningProviderError(
                    "Codex structured final response was not valid JSON"
                ) from exc

        artifact_list = data.get("artifacts", []) or []
        artifacts = {
            item["path"]: item["content"]
            for item in artifact_list
            if item.get("path") != "__NO_OUTPUT__"
        }
        metadata = {
            "provider": "codex_exec_reasoning",
            "model": self.model or "codex-config-default",
            "sandbox": "read-only",
            "ephemeral": self.ephemeral,
            "provider_notes": data.get("provider_notes"),
        }
        metadata.update(_conformance_metadata(self.conformance_evidence))
        return StageExecutionResult(
            status=data["status"],
            artifacts=artifacts,
            result=data.get("result"),
            classification=data.get("classification"),
            remediation_reasons=list(data.get("remediation_reasons", [])),
            convergence_tasks=list(data.get("convergence_tasks", [])),
            metadata=metadata,
        )


class OpenAIResponsesExecutor:
    """Reasoning adapter using OpenAI's Responses API with Structured Outputs.

    This adapter intentionally uses the HTTP API directly so the core package
    does not require an SDK dependency. The API key is read from the environment
    and is never persisted into SDD run packets.
    """

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        *,
        model: str = "gpt-5.6",
        api_key: str | None = None,
        timeout_seconds: int = 300,
        max_output_tokens: int = 12000,
        telemetry_recorder=None,
        resource_controller: ResourceController | None = None,
        resource_reservation: Mapping[ResourceDimension | str, Any] | None = None,
        conformance_gate: ProviderConformanceGate | None = None,
        conformance_manifest: ProviderCapabilityManifest | None = None,
        conformance_evidence: ProviderConformanceEvidence | None = None,
        conformance_context: ProviderConformanceContext | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.telemetry_recorder = telemetry_recorder
        self.resource_controller = resource_controller
        self.resource_reservation = dict(resource_reservation or {})
        self.conformance_gate = conformance_gate
        self.conformance_manifest = conformance_manifest
        self.conformance_evidence = conformance_evidence
        self.conformance_context = conformance_context
        if not self.api_key:
            raise SharedReasoningProviderPrerequisiteError(
                "OPENAI_API_KEY is not set. Configure it in the environment; do not store it in repository files."
            )

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        return self.dispatch(self.prepare(request))

    def prepare(self, request: StageExecutionRequest) -> PreparedOpenAIExecution:
        schema = _result_schema(request)
        instructions = _provider_system_instructions(request)
        user_input = _provider_user_input(request)
        body = {
            "model": self.model,
            "instructions": instructions,
            "input": user_input,
            "max_output_tokens": self.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"sdd_stage_{request.stage_id}_result",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        wire = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return PreparedOpenAIExecution(
            request=request,
            wire=wire,
            instructions=instructions,
            user_input=user_input,
        )

    def dispatch(self, prepared: PreparedOpenAIExecution) -> StageExecutionResult:
        request = prepared.request
        wire = prepared.wire
        if self.conformance_gate is not None:
            self.conformance_gate.require_dispatch(
                self.conformance_manifest,
                self.conformance_evidence,
                self.conformance_context,
            )
        dispatch_id = f"openai-responses:{uuid4()}"
        _reserve_provider_dispatch(
            self.resource_controller,
            dispatch_id=dispatch_id,
            provider="openai",
            model=self.model,
            runtime="openai_responses",
            context_bytes=len(wire),
            timeout_ms=self.timeout_seconds * 1000,
            declared=self.resource_reservation,
        )
        req = urllib.request.Request(
            self.endpoint,
            data=wire,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        outcome = OutcomeCategory.FAILED
        provider_usage = None
        try:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                try:
                    provider_usage = _openai_response_usage(payload)
                except Exception:
                    provider_usage = None
                outcome = OutcomeCategory.COMPLETED
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise ReasoningProviderError(
                    f"OpenAI Responses API returned HTTP {exc.code}: {detail[:2000]}"
                ) from exc
            except urllib.error.URLError as exc:
                if isinstance(exc.reason, TimeoutError):
                    outcome = OutcomeCategory.TIMEOUT
                raise ReasoningProviderError(f"OpenAI Responses API request failed: {exc}") from exc
            except (TimeoutError, subprocess.TimeoutExpired):
                outcome = OutcomeCategory.TIMEOUT
                raise
        finally:
            duration_ms = max(0, round((time.monotonic() - started) * 1000))
            _settle_provider_dispatch(
                self.resource_controller,
                dispatch_id=dispatch_id,
                duration_ms=duration_ms,
                context_bytes=len(wire),
                outcome=outcome,
                usage=provider_usage,
                usage_source=(
                    "openai_responses_usage" if provider_usage is not None
                    else "openai_responses_unavailable"
                ),
            )
            if self.telemetry_recorder is not None:
                try:
                    event = measure_provider_call(
                        stage_id=request.stage_id,
                        rendered=[
                            (prepared.instructions, Component.STAGE_INSTRUCTION),
                            (prepared.user_input, Component.USER_INPUT),
                        ],
                        wire=wire,
                        outcome_category=outcome,
                        provider_usage=provider_usage,
                        metadata={
                            "provider": "openai",
                            "model": self.model,
                            "adapter": "openai_responses",
                            "interface": "https",
                            "duration_ms": duration_ms,
                        },
                    )
                    self.telemetry_recorder.record(event)
                except Exception:
                    pass

        text = _extract_output_text(payload)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReasoningProviderError(
                "Structured response was not valid JSON"
            ) from exc

        artifact_list = data.get("artifacts", []) or []
        artifacts = {
            item["path"]: item["content"]
            for item in artifact_list
            if item.get("path") != "__NO_OUTPUT__"
        }
        metadata = {
            "provider": "openai_responses",
            "model": self.model,
            "response_id": payload.get("id"),
            "provider_notes": data.get("provider_notes"),
        }
        metadata.update(_conformance_metadata(self.conformance_evidence))
        return StageExecutionResult(
            status=data["status"],
            artifacts=artifacts,
            result=data.get("result"),
            classification=data.get("classification"),
            remediation_reasons=list(data.get("remediation_reasons", [])),
            convergence_tasks=list(data.get("convergence_tasks", [])),
            metadata=metadata,
        )
