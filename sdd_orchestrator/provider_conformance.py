"""Bounded provider conformance decisions for TASK-024.

This module deliberately evaluates providers; it does not register, route, or
construct them.  A conformant candidate is only eligible for a separately
governed dispatch, fallback, or promotion decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Mapping


class ProviderConformanceError(PermissionError):
    """A required provider conformance binding is missing or invalid."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class ConformanceStatus(str, Enum):
    CONFORMANT = "CONFORMANT"
    NON_CONFORMANT = "NON_CONFORMANT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _required(values: Iterable[str], label: str) -> tuple[str, ...]:
    normalized = tuple(sorted({str(item).strip() for item in values if str(item).strip()}))
    if not normalized:
        raise ProviderConformanceError("MISSING_CONFORMANCE_BINDING", label)
    return normalized


@dataclass(frozen=True)
class ProviderCapabilityManifest:
    """Versioned, machine-evaluable facts declared by one adapter."""

    schema_version: str
    provider_id: str
    model_id: str
    adapter_id: str
    runtime: str
    capabilities: frozenset[str]
    structured_execution: bool
    timeout_interruption_normalized: bool
    verification_independent: bool
    governance_compatible: bool
    security_compatible: bool
    resource_policy_compatible: bool
    filesystem_mode: str = "DECLARED"
    network_mode: str = "DECLARED"
    usage_accounting: str = "UNAVAILABLE"

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ProviderConformanceError("UNSUPPORTED_MANIFEST_VERSION", self.schema_version)
        if not all((self.provider_id, self.model_id, self.adapter_id, self.runtime)):
            raise ProviderConformanceError("INVALID_MANIFEST", "provider/model/adapter/runtime identity is required")
        object.__setattr__(self, "capabilities", frozenset(_required(self.capabilities, "capabilities")))
        if not self.filesystem_mode or not self.network_mode or not self.usage_accounting:
            raise ProviderConformanceError("INVALID_MANIFEST", "capability assumptions are required")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "adapter_id": self.adapter_id,
            "runtime": self.runtime,
            "capabilities": sorted(self.capabilities),
            "structured_execution": self.structured_execution,
            "timeout_interruption_normalized": self.timeout_interruption_normalized,
            "verification_independent": self.verification_independent,
            "governance_compatible": self.governance_compatible,
            "security_compatible": self.security_compatible,
            "resource_policy_compatible": self.resource_policy_compatible,
            "filesystem_mode": self.filesystem_mode,
            "network_mode": self.network_mode,
            "usage_accounting": self.usage_accounting,
        }

    @property
    def digest(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True)
class ProviderConformanceContext:
    """Current governed context that makes evidence stale when it changes."""

    provider_id: str
    model_id: str
    adapter_id: str
    runtime: str
    baseline_commit: str
    default_provider_id: str
    governance_reference: str
    security_reference: str
    resource_policy_reference: str
    authorization_reference: str
    environment: str = "local"

    def __post_init__(self) -> None:
        if not all((
            self.provider_id, self.model_id, self.adapter_id, self.runtime,
            self.baseline_commit, self.default_provider_id,
            self.governance_reference, self.security_reference,
            self.resource_policy_reference, self.authorization_reference,
            self.environment,
        )):
            raise ProviderConformanceError("MISSING_CONFORMANCE_CONTEXT", "current governed context is incomplete")

    def payload(self) -> dict[str, str]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "adapter_id": self.adapter_id,
            "runtime": self.runtime,
            "baseline_commit": self.baseline_commit,
            "default_provider_id": self.default_provider_id,
            "governance_reference": self.governance_reference,
            "security_reference": self.security_reference,
            "resource_policy_reference": self.resource_policy_reference,
            "authorization_reference": self.authorization_reference,
            "environment": self.environment,
        }

    @property
    def digest(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True)
class ProviderConformanceEvidence:
    """Durable, content-bound result that can be stored in existing evidence."""

    schema_version: str
    provider_id: str
    manifest_digest: str
    context_digest: str
    status: ConformanceStatus
    evaluated_requirements: tuple[str, ...]
    failure_reasons: tuple[str, ...] = ()
    approval_reference: str | None = None
    evidence_id: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != "1.0" or not all((self.provider_id, self.manifest_digest, self.context_digest)):
            raise ProviderConformanceError("INVALID_CONFORMANCE_EVIDENCE", "schema and identity bindings are required")
        object.__setattr__(self, "evaluated_requirements", _required(self.evaluated_requirements, "evaluated requirements"))
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(self.failure_reasons))))
        if self.status is ConformanceStatus.CONFORMANT and self.failure_reasons:
            raise ProviderConformanceError("INVALID_CONFORMANCE_EVIDENCE", "conformant evidence cannot contain failures")
        if self.status is not ConformanceStatus.CONFORMANT and not self.failure_reasons:
            raise ProviderConformanceError("INVALID_CONFORMANCE_EVIDENCE", "non-conformant evidence needs failure reasons")
        if not self.evidence_id:
            object.__setattr__(self, "evidence_id", _digest(self.payload(include_id=False)))

    def payload(self, *, include_id: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "manifest_digest": self.manifest_digest,
            "context_digest": self.context_digest,
            "status": self.status.value,
            "evaluated_requirements": list(self.evaluated_requirements),
            "failure_reasons": list(self.failure_reasons),
            "approval_reference": self.approval_reference,
        }
        if include_id:
            payload["evidence_id"] = self.evidence_id
        return payload


@dataclass(frozen=True)
class ProviderConformanceDecision:
    action: str
    status: ConformanceStatus
    provider_id: str
    evidence_id: str | None
    prior_default_provider_id: str
    approval_required: bool
    reasons: tuple[str, ...] = ()

    @property
    def eligible(self) -> bool:
        return self.status is ConformanceStatus.CONFORMANT


class ProviderConformanceGate:
    """Evaluate or validate a candidate without selecting a provider for SDD."""

    _REQUIRED_FACTS = {
        "STRUCTURED_EXECUTION": "structured_execution",
        "TIMEOUT_INTERRUPTION_NORMALIZATION": "timeout_interruption_normalized",
        "VERIFICATION_INDEPENDENCE": "verification_independent",
        "GOVERNANCE_COMPATIBILITY": "governance_compatible",
        "SECURITY_COMPATIBILITY": "security_compatible",
        "RESOURCE_POLICY_COMPATIBILITY": "resource_policy_compatible",
    }

    def __init__(self, *, required_capabilities: Iterable[str] = ()):
        self.required_capabilities = tuple(sorted({str(item) for item in required_capabilities}))

    def evaluate(
        self,
        manifest: ProviderCapabilityManifest,
        context: ProviderConformanceContext,
        *,
        approval_reference: str | None = None,
    ) -> ProviderConformanceEvidence:
        failures: list[str] = []
        if (manifest.provider_id, manifest.model_id, manifest.adapter_id, manifest.runtime) != (
            context.provider_id, context.model_id, context.adapter_id, context.runtime,
        ):
            failures.append("PROVIDER_IDENTITY_MISMATCH")
        for requirement, field_name in self._REQUIRED_FACTS.items():
            if not getattr(manifest, field_name):
                failures.append(f"MISSING_{requirement}")
        for capability in self.required_capabilities:
            if capability not in manifest.capabilities:
                failures.append(f"MISSING_CAPABILITY:{capability}")
        status = ConformanceStatus.CONFORMANT if not failures else ConformanceStatus.NON_CONFORMANT
        return ProviderConformanceEvidence(
            schema_version="1.0",
            provider_id=manifest.provider_id,
            manifest_digest=manifest.digest,
            context_digest=context.digest,
            status=status,
            evaluated_requirements=tuple(self._REQUIRED_FACTS) + self.required_capabilities,
            failure_reasons=tuple(failures),
            approval_reference=approval_reference,
        )

    def dispatch_decision(
        self,
        manifest: ProviderCapabilityManifest | None,
        evidence: ProviderConformanceEvidence | None,
        context: ProviderConformanceContext | None,
    ) -> ProviderConformanceDecision:
        if manifest is None or evidence is None or context is None:
            return ProviderConformanceDecision(
                "DISPATCH", ConformanceStatus.INSUFFICIENT_EVIDENCE,
                manifest.provider_id if manifest else "UNIDENTIFIED", None,
                context.default_provider_id if context else "UNIDENTIFIED", False,
                ("MISSING_MANIFEST_OR_EVIDENCE",),
            )
        reasons: list[str] = []
        if evidence.provider_id != manifest.provider_id:
            reasons.append("EVIDENCE_PROVIDER_IDENTITY_MISMATCH")
        if evidence.manifest_digest != manifest.digest:
            reasons.append("STALE_MANIFEST_EVIDENCE")
        if evidence.context_digest != context.digest:
            reasons.append("STALE_CONFORMANCE_CONTEXT")
        if evidence.status is not ConformanceStatus.CONFORMANT:
            reasons.extend(evidence.failure_reasons or ("NON_CONFORMANT_EVIDENCE",))
        status = ConformanceStatus.CONFORMANT if not reasons else (
            ConformanceStatus.INSUFFICIENT_EVIDENCE
            if any(reason.startswith(("MISSING", "STALE", "EVIDENCE_")) for reason in reasons)
            else ConformanceStatus.NON_CONFORMANT
        )
        return ProviderConformanceDecision(
            "DISPATCH", status, manifest.provider_id, evidence.evidence_id,
            context.default_provider_id, False, tuple(sorted(set(reasons))),
        )

    def require_dispatch(
        self,
        manifest: ProviderCapabilityManifest | None,
        evidence: ProviderConformanceEvidence | None,
        context: ProviderConformanceContext | None,
    ) -> ProviderConformanceDecision:
        decision = self.dispatch_decision(manifest, evidence, context)
        if not decision.eligible:
            raise ProviderConformanceError("PROVIDER_CONFORMANCE_BLOCKED", ",".join(decision.reasons))
        return decision

    def fallback_eligibility(
        self,
        manifest: ProviderCapabilityManifest | None,
        evidence: ProviderConformanceEvidence | None,
        context: ProviderConformanceContext | None,
        *,
        failed_provider_id: str,
    ) -> ProviderConformanceDecision:
        decision = self.dispatch_decision(manifest, evidence, context)
        reasons = list(decision.reasons)
        if context is not None and not failed_provider_id:
            reasons.append("FAILED_PROVIDER_ID_REQUIRED")
        if manifest is not None and manifest.provider_id == failed_provider_id:
            reasons.append("FALLBACK_TARGET_MUST_DIFFER")
        status = decision.status if not reasons else ConformanceStatus.NON_CONFORMANT
        return ProviderConformanceDecision(
            "FALLBACK", status, decision.provider_id, decision.evidence_id,
            decision.prior_default_provider_id, False, tuple(sorted(set(reasons))),
        )

    def promotion_eligibility(
        self,
        manifest: ProviderCapabilityManifest | None,
        evidence: ProviderConformanceEvidence | None,
        context: ProviderConformanceContext | None,
        *,
        approval_reference: str | None,
    ) -> ProviderConformanceDecision:
        decision = self.dispatch_decision(manifest, evidence, context)
        reasons = list(decision.reasons)
        if not approval_reference:
            reasons.append("PROMOTION_APPROVAL_REQUIRED")
        status = decision.status if not reasons else ConformanceStatus.NON_CONFORMANT
        return ProviderConformanceDecision(
            "PROMOTION", status, decision.provider_id, decision.evidence_id,
            decision.prior_default_provider_id, True, tuple(sorted(set(reasons))),
        )
