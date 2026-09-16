from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from sdd_orchestrator.governance_envelope import (
    CapabilityClass,
    DispatchObservation,
    DispatchRequest,
    GovernanceEnvelopeError,
    GovernanceEnvelopeValidator,
    IdentityBinding,
    create_dispatch_envelope,
)
from sdd_orchestrator.security_policy import (
    CredentialGrant,
    DataClass,
    DataHandlingBinding,
    FilesystemAccess,
    FilesystemGrant,
    NetworkAccess,
    NetworkGrant,
    SandboxClass,
    SecretReferenceGrant,
    SecurityEnvelope,
    SecurityObservation,
    SecurityPolicyError,
    SecurityPolicyValidator,
    SecurityRequest,
    contains_secret_value,
    create_security_envelope,
    redact_security_value,
)


NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


class SecurityPolicyTests(unittest.TestCase):
    def request(
        self,
        *,
        sandbox: SandboxClass = SandboxClass.S1_WORKSPACE_WRITE,
        environment: str = "workspace",
        audit: str = "base",
        **changes,
    ) -> tuple[SecurityRequest, SecurityEnvelope]:
        access = (
            FilesystemAccess.READ
            if sandbox is SandboxClass.S0_READ_ONLY_REASONING
            else FilesystemAccess.WRITE
        )
        values = {
            "data_class": DataClass.INTERNAL,
            "transmit_data": True,
            "sandbox_class": sandbox,
            "project_id": "project-1",
            "environment": environment,
            "session_id": f"session-{audit}",
            "provider_session_id": f"provider-{audit}",
            "filesystem": (FilesystemGrant("src/app.py", access),),
            "processes": ("provider-adapter",),
            "production_action": sandbox is SandboxClass.S3_PROTECTED_PRODUCTION_ACTION,
            "approval_class": "A2" if sandbox is SandboxClass.S3_PROTECTED_PRODUCTION_ACTION else "A0",
        }
        values.update(changes)
        request = SecurityRequest(**values)
        envelope = create_security_envelope(
            request=request,
            classification_reference="classification:T022",
            policy_reference="policy:security-v1",
            redaction_reference="policy:redaction-v1",
            retention_reference="policy:retention-v1",
            encryption_reference="policy:encryption-v1",
            audit_reference=f"audit:T022:{audit}",
            now=NOW,
        )
        return request, envelope

    def validate(self, request, envelope):
        return SecurityPolicyValidator().validate_pre_dispatch(envelope, request, now=NOW)

    def assert_denied(self, request, envelope, code):
        with self.assertRaises(SecurityPolicyError) as raised:
            SecurityPolicyValidator().validate_pre_dispatch(envelope, request, now=NOW)
        self.assertEqual(raised.exception.code, code)

    def test_all_sandbox_classes_have_exact_environment_and_capability_boundaries(self):
        cases = (
            (SandboxClass.S0_READ_ONLY_REASONING, "development"),
            (SandboxClass.S1_WORKSPACE_WRITE, "workspace"),
            (SandboxClass.S2_STAGING_OPERATION, "staging"),
            (SandboxClass.S3_PROTECTED_PRODUCTION_ACTION, "production"),
        )
        for index, (sandbox, environment) in enumerate(cases):
            with self.subTest(sandbox=sandbox):
                request, envelope = self.request(
                    sandbox=sandbox, environment=environment, audit=f"sandbox-{index}"
                )
                decision = self.validate(request, envelope)
                self.assertEqual(decision.outcome, "PASS")
                self.assertEqual(decision.audit_record["sandbox_class"], sandbox.value)

        request, envelope = self.request(sandbox=SandboxClass.S0_READ_ONLY_REASONING)
        self.assert_denied(
            replace(request, filesystem=(FilesystemGrant("src/app.py", "WRITE"),)),
            envelope,
            "SANDBOX_POLICY_DENIED",
        )
        request, envelope = self.request(
            sandbox=SandboxClass.S2_STAGING_OPERATION, environment="workspace"
        )
        self.assert_denied(request, envelope, "SANDBOX_POLICY_DENIED")

    def test_data_classification_and_all_handling_references_fail_closed(self):
        request, envelope = self.request()
        self.assertEqual(self.validate(request, envelope).audit_record["data_class"], "INTERNAL")
        for field_name in (
            "classification_reference", "policy_reference", "redaction_reference",
            "retention_reference", "encryption_reference",
        ):
            with self.subTest(field=field_name):
                handling = replace(envelope.data_handling, **{field_name: ""})
                self.assert_denied(request, replace(envelope, data_handling=handling), "UNSAFE_SECURITY_REFERENCE")
        prohibited = replace(
            request, data_class=DataClass.PROHIBITED
        )
        prohibited_envelope = replace(
            envelope,
            data_handling=replace(envelope.data_handling, data_class=DataClass.PROHIBITED),
        )
        self.assert_denied(prohibited, prohibited_envelope, "DATA_CLASS_PROHIBITED")
        self.assert_denied(
            replace(request, data_class=DataClass.CONFIDENTIAL), envelope, "DATA_CLASS_MISMATCH"
        )
        with self.assertRaises(SecurityPolicyError) as raised:
            replace(request, data_class="UNKNOWN")
        self.assertEqual(raised.exception.code, "UNKNOWN_DATA_CLASS")

    def test_prompt_injection_and_confused_deputy_stop_before_dispatch(self):
        request, envelope = self.request()
        self.assert_denied(
            replace(request, untrusted_instruction_findings=("embedded-authority-override",)),
            envelope,
            "SUSPECTED_PROMPT_INJECTION",
        )
        self.assert_denied(
            replace(request, malicious_tool_findings=("request-unlisted-secret-tool",)),
            envelope,
            "MALICIOUS_TOOL_ESCALATION",
        )

    def test_network_is_default_deny_and_destination_purpose_access_are_exact(self):
        request, envelope = self.request()
        network = NetworkGrant(
            "https://docs.example.test", "read-approved-docs", NetworkAccess.DOCUMENTATION_READ_ONLY
        )
        self.assert_denied(replace(request, network=(network,)), envelope, "NETWORK_POLICY_DENIED")

        allowed_request = replace(request, network=(network,))
        allowed_envelope = replace(envelope, network_grants=(network,))
        self.assertEqual(self.validate(allowed_request, allowed_envelope).outcome, "PASS")
        changed_purpose = replace(network, purpose="publish-data")
        self.assert_denied(
            replace(request, network=(changed_purpose,)), allowed_envelope, "NETWORK_POLICY_DENIED"
        )
        wildcard = NetworkGrant("https://*.example.test", "read-approved-docs", "DOCUMENTATION_READ_ONLY")
        self.assert_denied(
            replace(request, network=(wildcard,)),
            replace(envelope, network_grants=(wildcard,)),
            "NETWORK_POLICY_DENIED",
        )

        read_request, read_envelope = self.request(
            sandbox=SandboxClass.S0_READ_ONLY_REASONING,
            environment="development",
            audit="read-network",
        )
        write_network = NetworkGrant(
            "https://service.example.test",
            "publish-result",
            NetworkAccess.APPROVED_SERVICE_WRITE,
        )
        self.assert_denied(
            replace(read_request, network=(write_network,)),
            replace(read_envelope, network_grants=(write_network,)),
            "SANDBOX_POLICY_DENIED",
        )

    def test_credential_and_secret_access_are_reference_only_and_session_scoped(self):
        request, envelope = self.request()
        credential = CredentialGrant(
            credential_class="development-read",
            reference="credential-ref:docs",
            project_id=request.project_id,
            environment=request.environment,
            session_id=request.session_id,
            target="docs-service",
            purpose="read-docs",
            expires_at="2100-01-01T00:00:00Z",
        )
        secret = SecretReferenceGrant(
            reference="secret-ref:docs",
            project_id=request.project_id,
            environment=request.environment,
            session_id=request.session_id,
            purpose="read-docs",
        )
        granted_request = replace(request, credentials=(credential,), secret_references=(secret,))
        granted_envelope = replace(
            envelope, credential_grants=(credential,), secret_reference_grants=(secret,)
        )
        self.assertEqual(self.validate(granted_request, granted_envelope).outcome, "PASS")

        crossed = replace(credential, project_id="project-2")
        self.assert_denied(
            replace(request, credentials=(crossed,)),
            replace(envelope, credential_grants=(crossed,)),
            "CREDENTIAL_SCOPE_MISMATCH",
        )
        production = replace(credential, credential_class="production-write")
        self.assert_denied(
            replace(request, credentials=(production,)),
            replace(envelope, credential_grants=(production,)),
            "PRODUCTION_CREDENTIAL_DENIED",
        )
        unsafe = replace(credential, reference="api_key=super-secret-value")
        self.assert_denied(
            replace(request, credentials=(unsafe,)),
            replace(envelope, credential_grants=(unsafe,)),
            "SECRET_VALUE_FORBIDDEN",
        )
        unsafe_target = replace(credential, target="https://*.example.test")
        self.assert_denied(
            replace(request, credentials=(unsafe_target,)),
            replace(envelope, credential_grants=(unsafe_target,)),
            "UNSAFE_SECURITY_REFERENCE",
        )

    def test_cross_project_and_provider_session_reuse_is_denied(self):
        request, envelope = self.request()
        self.assert_denied(
            replace(request, project_id="project-2"), envelope, "SECURITY_IDENTITY_MISMATCH"
        )
        self.assert_denied(
            replace(request, provider_session_id="provider-other"),
            envelope,
            "PROVIDER_SESSION_MISMATCH",
        )

    def test_path_traversal_and_actual_post_dispatch_overrun_are_contained(self):
        with self.assertRaises(SecurityPolicyError) as raised:
            FilesystemGrant("../outside.txt", FilesystemAccess.WRITE)
        self.assertEqual(raised.exception.code, "FILESYSTEM_PATH_DENIED")

        request, envelope = self.request()
        validator = SecurityPolicyValidator()
        validator.validate_pre_dispatch(envelope, request, now=NOW)
        with self.assertRaises(SecurityPolicyError) as raised:
            validator.reconcile_post_dispatch(
                envelope,
                request,
                SecurityObservation(
                    filesystem=(FilesystemGrant("outside.txt", FilesystemAccess.WRITE),),
                    evidence_reference="evidence:T022",
                ),
            )
        self.assertEqual(raised.exception.code, "ACTUAL_FILESYSTEM_OVERRUN")

    def test_post_dispatch_boundary_and_suspected_exposure_are_minimum_disclosure(self):
        request, envelope = self.request()
        validator = SecurityPolicyValidator()
        validator.validate_pre_dispatch(envelope, request, now=NOW)
        decision = validator.reconcile_post_dispatch(
            envelope,
            request,
            SecurityObservation(
                filesystem=request.filesystem,
                processes=request.processes,
                evidence_reference="evidence:T022",
            ),
        )
        self.assertEqual(decision.audit_record["outcome"], "RECONCILED")
        self.assertNotIn("content", decision.audit_record)

        request, envelope = self.request(audit="exposure")
        validator = SecurityPolicyValidator()
        validator.validate_pre_dispatch(envelope, request, now=NOW)
        with self.assertRaises(SecurityPolicyError) as raised:
            validator.reconcile_post_dispatch(
                envelope,
                request,
                SecurityObservation(
                    suspected_secret_exposure=True,
                    evidence_reference="evidence:exposure",
                ),
            )
        self.assertEqual(raised.exception.code, "SUSPECTED_SECRET_EXPOSURE")
        self.assertTrue(contains_secret_value("authorization: Bearer abcdefghijk"))
        self.assertEqual(
            redact_security_value("authorization: Bearer abcdefghijk"),
            "authorization: [REDACTED]",
        )
        redacted = redact_security_value(
            {"api_key=super-secret-value": {"Bearer abcdefghijk"}}
        )
        self.assertEqual(redacted, {"[REDACTED]": ("[REDACTED]",)})

    def test_malformed_policy_values_fail_closed_without_secret_echo(self):
        with self.assertRaises(SecurityPolicyError) as raised:
            SecurityRequest(
                data_class="api_key=super-secret-value",
                transmit_data=True,
                sandbox_class=SandboxClass.S1_WORKSPACE_WRITE,
                project_id="project-1",
                environment="workspace",
                session_id="session-malformed",
            )
        self.assertEqual(raised.exception.code, "UNKNOWN_DATA_CLASS")
        self.assertNotIn("super-secret-value", str(raised.exception))

        request, envelope = self.request(audit="malformed-time")
        self.assert_denied(
            request,
            replace(envelope, expires_at=None),
            "SECURITY_POLICY_MALFORMED",
        )

    def test_unified_governance_requires_security_and_reconciles_safe_audit(self):
        identity = IdentityBinding(
            actor_id="actor", project_id="project-1", environment="workspace",
            repository="repo", branch="main", baseline="a" * 40, stage_id="08",
            attempt_id="attempt-governance", session_id="session-governance", task_id="T022",
        )
        security_request, security_envelope = self.request(audit="governance")
        security_request = replace(
            security_request,
            project_id=identity.project_id,
            environment=identity.environment,
            session_id=identity.session_id,
            provider_session_id=identity.session_id,
        )
        security_envelope = create_security_envelope(
            request=security_request,
            classification_reference="classification:T022",
            policy_reference="policy:security-v1",
            redaction_reference="policy:redaction-v1",
            retention_reference="policy:retention-v1",
            encryption_reference="policy:encryption-v1",
            audit_reference="audit:T022:governance",
            now=NOW,
        )
        dispatch = DispatchRequest(
            action="EXECUTE", tool="provider-adapter", arguments={"task": "T022"},
            target="repo", scope=("src/app.py",), side_effects=("WORKSPACE_WRITE",),
            required_capabilities=(CapabilityClass.WORKSPACE_IMPLEMENTATION_WRITE,),
            approval_class="A0", approval_reference="stage07:T022",
            security_request=security_request,
        )
        governance = create_dispatch_envelope(
            identity=identity,
            request=dispatch,
            authentication_reference="saved-session:opaque",
            authentication_method="saved_session",
            authority_references=("tasks.md:T022",),
            gate_references=("stage07:T022",),
            policy_references=("AGENTS.md:14",),
            limit_references=("timeout:300",),
            security_envelope=security_envelope,
            sealed_stage08_envelope_id="sealed:T022",
            now=NOW,
        )
        validator = GovernanceEnvelopeValidator(require_security=True)
        pre = validator.validate_pre_dispatch(governance, dispatch, current_identity=identity, now=NOW)
        self.assertEqual(pre.audit_record["security"]["data_class"], "INTERNAL")
        post = validator.reconcile_post_dispatch(
            governance,
            dispatch,
            DispatchObservation(
                outcome="PASS", actual_scope=("src/app.py",),
                actual_side_effects=("WORKSPACE_WRITE",), evidence_references=("evidence:T022",),
                security_observation=SecurityObservation(
                    filesystem=security_request.filesystem,
                    processes=security_request.processes,
                    evidence_reference="evidence:T022",
                ),
            ),
        )
        self.assertEqual(post.audit_record["security"]["outcome"], "RECONCILED")

        missing_dispatch = replace(dispatch, security_request=None)
        missing_governance = create_dispatch_envelope(
            identity=replace(identity, attempt_id="attempt-missing"),
            request=missing_dispatch,
            authentication_reference="saved-session:opaque",
            authentication_method="saved_session",
            authority_references=("tasks.md:T022",), gate_references=("stage07:T022",),
            policy_references=("AGENTS.md:14",), limit_references=("timeout:300",),
            sealed_stage08_envelope_id="sealed:T022",
            now=NOW,
        )
        with self.assertRaises(GovernanceEnvelopeError) as raised:
            GovernanceEnvelopeValidator(require_security=True).validate_pre_dispatch(
                missing_governance,
                missing_dispatch,
                current_identity=missing_governance.identity,
                now=NOW,
            )
        self.assertEqual(raised.exception.code, "SECURITY_BINDING_MISSING")


if __name__ == "__main__":
    unittest.main()
