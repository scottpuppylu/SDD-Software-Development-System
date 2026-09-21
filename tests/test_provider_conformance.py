import unittest

from sdd_orchestrator.executor import StageExecutionRequest, StageExecutionResult
from sdd_orchestrator.provider_conformance import (
    ConformanceStatus,
    ProviderCapabilityManifest,
    ProviderConformanceContext,
    ProviderConformanceError,
    ProviderConformanceGate,
)
from sdd_orchestrator.providers import (
    CodexExecReasoningExecutor,
    PreparedCodexExecution,
    ReasoningInvocation,
    ReasoningProviderBoundary,
)


class _Provider:
    def __init__(self):
        self.called = False

    def execute(self, request):
        self.called = True
        return StageExecutionResult(status="COMPLETED", artifacts={})


def _manifest(*, provider="provider-a", model="model-a", adapter="adapter-a", runtime="local", **changes):
    values = {
        "schema_version": "1.0",
        "provider_id": provider,
        "model_id": model,
        "adapter_id": adapter,
        "runtime": runtime,
        "capabilities": frozenset({"REASON", "STRUCTURED_OUTPUT"}),
        "structured_execution": True,
        "timeout_interruption_normalized": True,
        "verification_independent": True,
        "governance_compatible": True,
        "security_compatible": True,
        "resource_policy_compatible": True,
    }
    values.update(changes)
    return ProviderCapabilityManifest(**values)


def _context(manifest, *, default="provider-a", **changes):
    values = {
        "provider_id": manifest.provider_id,
        "model_id": manifest.model_id,
        "adapter_id": manifest.adapter_id,
        "runtime": manifest.runtime,
        "baseline_commit": "a" * 40,
        "default_provider_id": default,
        "governance_reference": "AGENTS.md:14",
        "security_reference": "TASK-022",
        "resource_policy_reference": "TASK-023:policy-1",
        "authorization_reference": "stage07:T024",
    }
    values.update(changes)
    return ProviderConformanceContext(**values)


class ProviderConformanceTests(unittest.TestCase):
    def request(self):
        return StageExecutionRequest(
            stage_id="03",
            stage_name="TEST",
            stage_type="AUTHORING",
            core_question="test",
            contract={"outputs": {"files": ["docs/spec.md"]}},
            artifacts={},
        )

    def invocation(self):
        return ReasoningInvocation(
            attempt_id="attempt-024",
            operation="DRAFT",
            request=self.request(),
            authoritative_context_refs=("docs/PRD.md@sha256:abc",),
            permitted_capabilities=frozenset({"REASON"}),
            affected_scope=("docs/spec.md",),
        )

    def test_versioned_complete_manifest_produces_reproducible_conformant_evidence(self):
        manifest = _manifest()
        context = _context(manifest)
        evidence = ProviderConformanceGate(required_capabilities={"REASON"}).evaluate(manifest, context)
        self.assertEqual(evidence.status, ConformanceStatus.CONFORMANT)
        self.assertEqual(evidence.manifest_digest, manifest.digest)
        self.assertEqual(evidence.context_digest, context.digest)
        self.assertEqual(evidence.evidence_id, ProviderConformanceGate(required_capabilities={"REASON"}).evaluate(manifest, context).evidence_id)

    def test_missing_capability_or_security_fact_is_non_conformant(self):
        manifest = _manifest(capabilities=frozenset({"STRUCTURED_OUTPUT"}), security_compatible=False)
        evidence = ProviderConformanceGate(required_capabilities={"REASON"}).evaluate(manifest, _context(manifest))
        self.assertEqual(evidence.status, ConformanceStatus.NON_CONFORMANT)
        self.assertIn("MISSING_CAPABILITY:REASON", evidence.failure_reasons)
        self.assertIn("MISSING_SECURITY_COMPATIBILITY", evidence.failure_reasons)

    def test_missing_or_stale_evidence_blocks_before_provider_execution(self):
        provider = _Provider()
        manifest = _manifest()
        context = _context(manifest)
        boundary = ReasoningProviderBoundary(
            provider,
            conformance_gate=ProviderConformanceGate(),
            conformance_manifest=manifest,
            conformance_context=context,
        )
        blocked = boundary.invoke(self.invocation())
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertEqual(blocked.failure.category, "POLICY_VIOLATION")
        self.assertFalse(provider.called)

        evidence = ProviderConformanceGate().evaluate(manifest, context)
        stale_context = _context(manifest, baseline_commit="b" * 40)
        with self.assertRaisesRegex(ProviderConformanceError, "PROVIDER_CONFORMANCE_BLOCKED"):
            ProviderConformanceGate().require_dispatch(manifest, evidence, stale_context)

    def test_conformant_provider_can_reach_existing_boundary_without_authority_upgrade(self):
        provider = _Provider()
        manifest = _manifest()
        context = _context(manifest)
        gate = ProviderConformanceGate()
        result = ReasoningProviderBoundary(
            provider,
            conformance_gate=gate,
            conformance_manifest=manifest,
            conformance_evidence=gate.evaluate(manifest, context),
            conformance_context=context,
        ).invoke(self.invocation())
        self.assertEqual(result.status, "PROPOSED")
        self.assertFalse(result.authoritative)
        self.assertFalse(result.persisted)
        self.assertEqual(
            result.proposed_output.metadata["provider_conformance"]["evidence_id"],
            gate.evaluate(manifest, context).evidence_id,
        )
        self.assertTrue(provider.called)

    def test_default_is_not_mutated_and_promotion_requires_approval(self):
        candidate = _manifest(provider="provider-b", model="model-b", adapter="adapter-b")
        context = _context(candidate, default="provider-a")
        gate = ProviderConformanceGate()
        evidence = gate.evaluate(candidate, context)
        denied = gate.promotion_eligibility(candidate, evidence, context, approval_reference=None)
        self.assertFalse(denied.eligible)
        self.assertIn("PROMOTION_APPROVAL_REQUIRED", denied.reasons)
        accepted = gate.promotion_eligibility(candidate, evidence, context, approval_reference="A2:provider-b")
        self.assertTrue(accepted.eligible)
        self.assertEqual(accepted.prior_default_provider_id, "provider-a")
        self.assertEqual(context.default_provider_id, "provider-a")

    def test_fallback_requires_a_distinct_conformant_target_and_never_selects_automatically(self):
        candidate = _manifest(provider="provider-b", model="model-b", adapter="adapter-b")
        context = _context(candidate, default="provider-a")
        gate = ProviderConformanceGate()
        evidence = gate.evaluate(candidate, context)
        valid = gate.fallback_eligibility(candidate, evidence, context, failed_provider_id="provider-a")
        self.assertTrue(valid.eligible)
        same_target = gate.fallback_eligibility(candidate, evidence, context, failed_provider_id="provider-b")
        self.assertFalse(same_target.eligible)
        self.assertIn("FALLBACK_TARGET_MUST_DIFFER", same_target.reasons)

    def test_identity_mismatch_is_not_conformant(self):
        manifest = _manifest()
        wrong_context = _context(manifest, model_id="other-model")
        evidence = ProviderConformanceGate().evaluate(manifest, wrong_context)
        self.assertEqual(evidence.status, ConformanceStatus.NON_CONFORMANT)
        self.assertIn("PROVIDER_IDENTITY_MISMATCH", evidence.failure_reasons)

    def test_codex_adapter_blocks_before_subprocess_when_conformance_is_required(self):
        manifest = _manifest(
            provider="codex", model="codex-config-default",
            adapter="codex_exec_reasoning", runtime="codex_exec_reasoning",
        )
        context = _context(manifest, default="codex")
        executor = CodexExecReasoningExecutor(
            conformance_gate=ProviderConformanceGate(),
            conformance_manifest=manifest,
            conformance_context=context,
        )
        with self.assertRaisesRegex(ProviderConformanceError, "PROVIDER_CONFORMANCE_BLOCKED"):
            executor.dispatch(PreparedCodexExecution(
                request=self.request(), executable="must-not-run", schema_json="{}", prompt="test",
            ))


if __name__ == "__main__":
    unittest.main()
