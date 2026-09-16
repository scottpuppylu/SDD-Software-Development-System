from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from sdd_orchestrator.governance_envelope import (
    ApprovalBinding,
    AuthenticationReference,
    CapabilityClass,
    CapabilityGrant,
    DispatchObservation,
    DispatchRequest,
    GovernanceEnvelopeError,
    GovernanceEnvelopeValidator,
    IdentityBinding,
    argument_digest,
    seal_governance_envelope,
)
from sdd_orchestrator.executor import StageExecutionRequest, StageExecutionResult
from sdd_orchestrator.providers import ReasoningInvocation, ReasoningProviderBoundary


class GovernanceEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.identity = IdentityBinding(
            actor_id="actor-1", project_id="project-1", environment="workspace",
            repository="repo-1", branch="main", baseline="a" * 40,
            stage_id="08", task_id="T021", attempt_id="attempt-1",
            provider_id="provider-1", adapter_id="adapter-1", session_id="session-1",
        )
        self.request = DispatchRequest(
            action="EXECUTE_TASK", tool="coding-agent", arguments={"task": "T021"},
            target="repo-1", scope=("allowed.py",), side_effects=("WORKSPACE_WRITE",),
            required_capabilities=(CapabilityClass.WORKSPACE_IMPLEMENTATION_WRITE,),
            approval_class="A0", approval_reference="stage07:pass:T021",
        )
        grant = CapabilityGrant(
            grant_id="grant-1", capability_class=CapabilityClass.WORKSPACE_IMPLEMENTATION_WRITE,
            actions=(self.request.action,), tools=(self.request.tool,),
            argument_digests=(argument_digest(self.request.arguments),),
            targets=(self.request.target,), scope=self.request.scope,
            side_effects=self.request.side_effects, issuer="stage07",
            approval_reference=self.request.approval_reference,
            issued_at="2020-01-01T00:00:00Z", expires_at="2100-01-01T00:00:00Z",
        )
        self.envelope = seal_governance_envelope(
            identity=self.identity,
            authentication=AuthenticationReference(
                reference="saved-session:opaque", method="saved_session",
                actor_id="actor-1", project_id="project-1", environment="workspace",
                verified=True, expires_at="2100-01-01T00:00:00Z",
            ),
            authority_references=("tasks.md@sha256:task", "AGENTS.md@sha256:agents"),
            gate_references=("stage07@sha256:pass",), grants=(grant,),
            approval=ApprovalBinding(
                approval_class="A0", reference=self.request.approval_reference,
                action=self.request.action, target=self.request.target,
                scope=self.request.scope, baseline=self.identity.baseline,
                environment=self.identity.environment, risk="ROUTINE_STAGE08",
                provider_capability="workspace-write",
            ),
            policy_references=("security-contract", "approval-matrix"),
            limit_references=("task-timeout",),
            audit_obligations=(
                "ENVELOPE_ID", "OUTCOME", "OBSERVED_EFFECTS", "FAILURE_ROUTE",
                "APPROVAL_BINDING",
            ),
            evidence_obligations=("DISPATCH_RESULT",),
            prohibited_operations=("DEPLOY",),
            issued_at="2020-01-01T00:00:00Z", expires_at="2100-01-01T00:00:00Z",
            sealed_stage08_envelope_id="sealed-stage08-1",
        )
        self.validator = GovernanceEnvelopeValidator()
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)

    def assert_denied(self, envelope=None, request=None, identity=None, code=None):
        with self.assertRaises(GovernanceEnvelopeError) as raised:
            self.validator.validate_pre_dispatch(
                self.envelope if envelope is None else envelope,
                self.request if request is None else request,
                current_identity=self.identity if identity is None else identity,
                now=self.now,
            )
        if code:
            self.assertEqual(raised.exception.code, code)

    def reseal(self, **changes):
        values = {
            "identity": self.envelope.identity,
            "authentication": self.envelope.authentication,
            "authority_references": self.envelope.authority_references,
            "gate_references": self.envelope.gate_references,
            "grants": self.envelope.grants,
            "approval": self.envelope.approval,
            "policy_references": self.envelope.policy_references,
            "limit_references": self.envelope.limit_references,
            "audit_obligations": self.envelope.audit_obligations,
            "evidence_obligations": self.envelope.evidence_obligations,
            "prohibited_operations": self.envelope.prohibited_operations,
            "issued_at": self.envelope.issued_at,
            "expires_at": self.envelope.expires_at,
            "sealed_stage08_envelope_id": self.envelope.sealed_stage08_envelope_id,
        }
        values.update(changes)
        return seal_governance_envelope(**values)

    def test_positive_least_capability_and_post_dispatch_audit(self):
        decision = self.validator.validate_pre_dispatch(
            self.envelope, self.request, current_identity=self.identity, now=self.now
        )
        self.assertEqual(decision.outcome, "PASS")
        reconciled = self.validator.reconcile_post_dispatch(
            self.envelope, self.request,
            DispatchObservation(
                outcome="PASS", actual_scope=("allowed.py",),
                actual_side_effects=("WORKSPACE_WRITE",),
                evidence_references=("evidence:T021",),
            ),
        )
        self.assertEqual(reconciled.audit_record["approval_class"], "A0")
        self.assertEqual(reconciled.audit_record["observed_effects"], ("WORKSPACE_WRITE",))

    def test_missing_envelope_unknown_capability_and_identity_mismatch_fail_closed(self):
        with self.assertRaises(GovernanceEnvelopeError) as missing:
            self.validator.validate_pre_dispatch(
                None, self.request, current_identity=self.identity, now=self.now
            )
        self.assertEqual(missing.exception.code, "MISSING_ENVELOPE")
        self.assert_denied(
            request=replace(self.request, required_capabilities=("ROOT",)),
            code="UNKNOWN_CAPABILITY",
        )
        for field_name in ("actor_id", "project_id", "environment"):
            with self.subTest(field=field_name):
                self.assert_denied(
                    identity=replace(self.identity, **{field_name: "changed"}),
                    code="IDENTITY_MISMATCH",
                )

    def test_authentication_absent_unverified_stale_or_expired_is_denied(self):
        cases = (
            replace(self.envelope.authentication, reference=""),
            replace(self.envelope.authentication, verified=False),
            replace(self.envelope.authentication, current=False),
            replace(self.envelope.authentication, expires_at="2021-01-01T00:00:00Z"),
        )
        for auth in cases:
            with self.subTest(auth=auth):
                self.assert_denied(envelope=self.reseal(authentication=auth))

    def test_stage07_approval_and_exact_call_bindings_are_mandatory(self):
        self.assert_denied(envelope=self.reseal(gate_references=()), code="STAGE07_BINDING_MISSING")
        for change in (
            {"action": "OTHER"}, {"tool": "other-tool"},
            {"arguments": {"task": "T022"}}, {"target": "other-repo"},
            {"scope": ("outside.py",)}, {"side_effects": ("DEPLOY",)},
        ):
            with self.subTest(change=change):
                self.assert_denied(request=replace(self.request, **change))

    def test_absent_or_overbroad_grant_is_denied(self):
        self.assert_denied(
            request=replace(self.request, required_capabilities=()),
            code="CAPABILITY_DENIED",
        )
        overbroad = replace(
            self.envelope.grants[0],
            scope=("allowed.py", "extra.py"),
        )
        self.assert_denied(
            envelope=self.reseal(grants=(overbroad,)),
            code="CAPABILITY_DENIED",
        )

    def test_expiry_provider_claim_and_audit_obligation_are_denied(self):
        self.assert_denied(
            envelope=self.reseal(expires_at="2021-01-01T00:00:00Z"),
            code="EXPIRED_OR_STALE",
        )
        self.assert_denied(
            request=replace(self.request, provider_authority_claims=("approval_created",)),
            code="PROVIDER_AUTHORITY_CLAIM",
        )
        self.assert_denied(
            envelope=self.reseal(audit_obligations=("ENVELOPE_ID",)),
            code="MISSING_AUDIT_OBLIGATION",
        )

    def test_actual_scope_or_side_effect_overrun_is_contained(self):
        self.validator.validate_pre_dispatch(
            self.envelope, self.request, current_identity=self.identity, now=self.now
        )
        for observation in (
            DispatchObservation("FAIL", ("outside.py",), (), ("evidence:failure",), "SECURITY_OWNER"),
            DispatchObservation("FAIL", (), ("DEPLOY",), ("evidence:failure",), "SECURITY_OWNER"),
        ):
            with self.subTest(observation=observation):
                validator = GovernanceEnvelopeValidator()
                validator.validate_pre_dispatch(
                    self.envelope, self.request, current_identity=self.identity, now=self.now
                )
                with self.assertRaises(GovernanceEnvelopeError) as raised:
                    validator.reconcile_post_dispatch(self.envelope, self.request, observation)
                self.assertEqual(raised.exception.code, "ACTUAL_SCOPE_EFFECT_MISMATCH")

    def test_protected_approval_cannot_be_reused_after_dispatch(self):
        protected_request = replace(
            self.request, approval_class="A2", approval_reference="HD-A2-EXACT"
        )
        protected_grant = replace(
            self.envelope.grants[0], approval_reference="HD-A2-EXACT"
        )
        protected = self.reseal(
            grants=(protected_grant,),
            approval=replace(
                self.envelope.approval, approval_class="A2", reference="HD-A2-EXACT"
            ),
        )
        self.validator.validate_pre_dispatch(
            protected, protected_request, current_identity=self.identity, now=self.now
        )
        self.validator.reconcile_post_dispatch(
            protected, protected_request,
            DispatchObservation("PASS", protected_request.scope,
                                protected_request.side_effects, ("evidence:protected",)),
        )
        self.assert_denied(
            envelope=protected, request=protected_request, code="APPROVAL_REUSED"
        )

    def test_reasoning_boundary_validates_before_provider_side_effect(self):
        class Provider:
            called = False

            def execute(inner_self, request):
                inner_self.called = True
                return StageExecutionResult(
                    status="COMPLETED", artifacts={"allowed.py": "proposal"}
                )

        provider = Provider()
        invocation = ReasoningInvocation(
            attempt_id="attempt-1", operation="EXECUTE_TASK",
            request=StageExecutionRequest(
                stage_id="08", stage_name="Implementation", stage_type="reasoning",
                core_question=None,
                contract={"outputs": {"files": ["allowed.py"]}}, artifacts={},
            ),
            authoritative_context_refs=("tasks.md@sha256:task",),
            permitted_capabilities=frozenset({"DRAFT"}),
            affected_scope=("allowed.py",),
            governance_envelope=self.envelope,
            governance_request=self.request,
            current_identity=replace(self.identity, environment="changed"),
        )
        blocked = ReasoningProviderBoundary(
            provider, require_governance=True
        ).invoke(invocation)
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertFalse(provider.called)

        accepted = ReasoningProviderBoundary(
            provider, require_governance=True
        ).invoke(replace(invocation, current_identity=self.identity))
        self.assertEqual(accepted.status, "PROPOSED")
        self.assertTrue(provider.called)


if __name__ == "__main__":
    unittest.main()
