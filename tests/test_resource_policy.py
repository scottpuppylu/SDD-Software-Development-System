from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import subprocess

import pytest

from sdd_orchestrator.codex_cli import CodexCLI
from sdd_orchestrator.governance_envelope import (
    CapabilityClass,
    DispatchRequest,
    GovernanceEnvelopeError,
    GovernanceEnvelopeValidator,
    IdentityBinding,
    create_dispatch_envelope,
)
from sdd_orchestrator.resource_policy import (
    BudgetIncreaseApproval,
    BudgetState,
    DeploymentGrant,
    MeasurementTruth,
    ResourceController,
    ResourceDimension as D,
    ResourceLimit,
    ResourceMeasurement,
    ResourceObservation,
    ResourcePolicy,
    ResourcePolicyError,
    ResourceRequest,
)


def policy(
    *limits: ResourceLimit,
    required: tuple[D, ...] = (D.PROVIDER_CALLS,),
    provider: str = "codex",
    model: str = "codex-config-default",
    runtime: str = "codex_cli",
    grants: tuple[DeploymentGrant, ...] = (),
) -> ResourcePolicy:
    return ResourcePolicy(
        "budget-1", provider, model, runtime, "task:T023", limits,
        required, grants,
    )


def request(**overrides) -> ResourceRequest:
    values = {
        "dispatch_id": "dispatch-1",
        "provider": "codex",
        "model": "codex-config-default",
        "runtime": "codex_cli",
        "scope": "task:T023",
        "reservation": {D.PROVIDER_CALLS: 1},
    }
    values.update(overrides)
    return ResourceRequest(**values)


def measurement(dimension: D, value, truth=MeasurementTruth.ACTUAL, source="runtime_meter"):
    return ResourceMeasurement(dimension, value, truth, source, "dispatch-1")


def observation(*measurements: ResourceMeasurement, dispatch_id: str = "dispatch-1"):
    return ResourceObservation(dispatch_id, measurements, "completed", f"evidence:{dispatch_id}")


def test_truth_classes_do_not_fabricate_actual_usage():
    unavailable = ResourceMeasurement(
        D.ACTUAL_TOKENS, None, MeasurementTruth.UNAVAILABLE,
        "codex_cli_unavailable", "dispatch-1",
    )
    context = ResourceMeasurement(
        D.CONTEXT_BYTES, 42, MeasurementTruth.CONTEXT_SIZE,
        "utf8_measurement", "dispatch-1",
    )
    estimate = ResourceMeasurement(
        D.ESTIMATED_TOKENS, 12, MeasurementTruth.ESTIMATED,
        "tokenizer", "dispatch-1", method="tokenizer", method_version="1",
        model_assumption="model-a", input_scope="complete-request",
        observed_at="2026-09-18T00:00:00Z",
    )
    assert unavailable.value is None
    assert context.truth is MeasurementTruth.CONTEXT_SIZE
    assert estimate.truth is MeasurementTruth.ESTIMATED
    with pytest.raises(ResourcePolicyError, match="UNTRUSTED_ACTUAL_USAGE"):
        ResourceMeasurement(
            D.ACTUAL_TOKENS, 12, MeasurementTruth.ACTUAL,
            "codex_cli_human_text", "dispatch-1",
        )
    with pytest.raises(ResourcePolicyError, match="INVALID_ESTIMATE"):
        ResourceMeasurement(
            D.ESTIMATED_TOKENS, 12, MeasurementTruth.ESTIMATED,
            "tokenizer", "dispatch-1",
        )


def test_hard_limit_is_checked_before_dispatch_and_soft_limit_warns():
    controller = ResourceController(policy(ResourceLimit(D.PROVIDER_CALLS, 2, 1)))
    decision = controller.reserve(request())
    assert decision.state is BudgetState.WARNING
    controller.settle(observation(measurement(D.PROVIDER_CALLS, 1)))
    with pytest.raises(ResourcePolicyError, match="BUDGET_BLOCKED"):
        controller.reserve(request(dispatch_id="dispatch-2", reservation={D.PROVIDER_CALLS: 2}))
    assert controller.totals[D.PROVIDER_CALLS] == 1


def test_required_limit_and_complete_context_fail_closed():
    controller = ResourceController(
        policy(
            ResourceLimit(D.PROVIDER_CALLS, 2),
            ResourceLimit(D.RUNTIME_MS, 1000),
            required=(D.PROVIDER_CALLS, D.RUNTIME_MS),
        )
    )
    with pytest.raises(ResourcePolicyError, match="INSUFFICIENT_RESERVATION"):
        controller.reserve(request())
    with pytest.raises(ResourcePolicyError, match="BUDGET_OR_CAPABILITY_BLOCKED"):
        controller.reserve(
            request(
                reservation={D.PROVIDER_CALLS: 1, D.RUNTIME_MS: 100},
                complete_context=False,
            )
        )


def test_retry_consumes_declared_budget_and_is_idempotent():
    controller = ResourceController(
        policy(
            ResourceLimit(D.PROVIDER_CALLS, 3),
            ResourceLimit(D.RETRIES, 1),
            required=(D.PROVIDER_CALLS, D.RETRIES),
        )
    )
    retry = request(
        retry=True,
        reservation={D.PROVIDER_CALLS: 1, D.RETRIES: 1},
    )
    controller.reserve(retry)
    observed = observation(measurement(D.PROVIDER_CALLS, 1))
    first = controller.settle(observed)
    second = controller.settle(observed)
    assert first == second
    assert controller.totals[D.RETRIES] == 1
    with pytest.raises(ResourcePolicyError, match="DISPATCH_ALREADY_ACCOUNTED"):
        controller.reserve(retry)


def test_atomic_accounting_failure_preserves_reservation_and_totals():
    controller = ResourceController(policy(ResourceLimit(D.PROVIDER_CALLS, 2)))
    controller.reserve(request())
    bad = observation(
        measurement(D.PROVIDER_CALLS, 1),
        measurement(D.PROVIDER_CALLS, 1),
    )
    with pytest.raises(ResourcePolicyError, match="ACCOUNTING_CONFLICT"):
        controller.settle(bad)
    assert dict(controller.totals) == {}
    controller.settle(observation(measurement(D.PROVIDER_CALLS, 1)))
    assert controller.totals[D.PROVIDER_CALLS] == 1


def test_unavailable_actual_is_unknown_not_zero_and_required_actual_blocks_settlement():
    controller = ResourceController(
        policy(
            ResourceLimit(D.PROVIDER_CALLS, 2),
            ResourceLimit(D.ACTUAL_TOKENS, 100),
        )
    )
    controller.reserve(request())
    result = controller.settle(
        observation(
            measurement(D.PROVIDER_CALLS, 1),
            ResourceMeasurement(
                D.ACTUAL_TOKENS, None, MeasurementTruth.UNAVAILABLE,
                "codex_cli_unavailable", "dispatch-1",
            ),
        )
    )
    assert result.state is BudgetState.UNKNOWN
    assert D.ACTUAL_TOKENS not in controller.totals

    strict = ResourceController(
        policy(
            ResourceLimit(D.PROVIDER_CALLS, 2),
            ResourceLimit(D.ACTUAL_TOKENS, 100, actual_required=True),
        )
    )
    strict.reserve(request())
    with pytest.raises(ResourcePolicyError, match="INCOMPLETE_ACTUAL_USAGE"):
        strict.settle(
            observation(
                measurement(D.PROVIDER_CALLS, 1),
                ResourceMeasurement(
                    D.ACTUAL_TOKENS, None, MeasurementTruth.UNAVAILABLE,
                    "codex_cli_unavailable", "dispatch-1",
                ),
            )
        )


def test_budget_increase_requires_bound_a2_or_a3_approval():
    original = policy(ResourceLimit(D.PROVIDER_CALLS, 2))
    with pytest.raises(ResourcePolicyError, match="BUDGET_INCREASE_REQUIRES_APPROVAL"):
        original.with_increased_limits((ResourceLimit(D.PROVIDER_CALLS, 3),), None)
    approved = original.with_increased_limits(
        (ResourceLimit(D.PROVIDER_CALLS, 3),),
        BudgetIncreaseApproval("HD-BUDGET-1", "A2", "budget-1", (D.PROVIDER_CALLS,)),
    )
    assert approved.by_dimension[D.PROVIDER_CALLS].hard == 3
    assert approved.approval_reference == "HD-BUDGET-1"


def test_deployment_is_denied_without_exact_separate_grant():
    grant = DeploymentGrant(
        "HD-DEPLOY-1", "service-a", "production", "A2", "release-abc"
    )
    controller = ResourceController(
        policy(
            ResourceLimit(D.PROVIDER_CALLS, 2),
            ResourceLimit(D.DEPLOYMENTS, 1),
            grants=(grant,),
        )
    )
    deployment = request(
        reservation={D.PROVIDER_CALLS: 1, D.DEPLOYMENTS: 1},
        deployment_target="service-a",
        environment="production",
        release_identity="release-abc",
    )
    with pytest.raises(ResourcePolicyError, match="DEPLOYMENT_GRANT_MISMATCH"):
        controller.reserve(deployment)
    controller.reserve(replace(deployment, deployment_grant_reference="HD-DEPLOY-1"))


def test_cost_route_can_be_cheaper_only_when_every_control_is_conformant():
    controller = ResourceController(policy(ResourceLimit(D.PROVIDER_CALLS, 2)))
    good = {
        "name": "good", "estimated_cost_usd": "2.00",
        "adapter_conformant": True, "security_equivalent": True,
        "authority_equivalent": True, "evidence_equivalent": True,
        "required_context_complete": True,
    }
    cheap_but_unsafe = dict(good, name="unsafe", estimated_cost_usd="0.01", security_equivalent=False)
    assert controller.select_conformant_route((cheap_but_unsafe, good))["name"] == "good"
    with pytest.raises(ResourcePolicyError, match="NO_CONFORMANT_ROUTE"):
        controller.select_conformant_route((cheap_but_unsafe,))


def test_codex_cli_accounts_call_runtime_context_and_unavailable_tokens(monkeypatch):
    controller = ResourceController(
        policy(
            ResourceLimit(D.PROVIDER_CALLS, 2),
            ResourceLimit(D.RUNTIME_MS, 100000),
            ResourceLimit(D.PROCESS_COUNT, 2),
            ResourceLimit(D.CONTEXT_BYTES, 1000),
            ResourceLimit(D.ACTUAL_TOKENS, 1000),
            required=(D.PROVIDER_CALLS, D.RUNTIME_MS, D.PROCESS_COUNT, D.CONTEXT_BYTES),
        )
    )
    monkeypatch.setattr("sdd_orchestrator.codex_cli.shutil.which", lambda _: "codex")
    monkeypatch.setattr(
        "sdd_orchestrator.codex_cli.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok", ""),
    )
    result = CodexCLI(resource_controller=controller, timeout_seconds=10).execute(
        Path.cwd(), "complete governed prompt", resource_dispatch_id="codex-call-1"
    )
    assert result.returncode == 0
    assert controller.totals[D.PROVIDER_CALLS] == 1
    assert D.ACTUAL_TOKENS not in controller.totals


def _deployment_dispatch(reference: str | None):
    identity = IdentityBinding(
        actor_id="actor", project_id="project", environment="production",
        repository="repo", branch="main", baseline="abc", stage_id="10",
        attempt_id="attempt",
    )
    request = DispatchRequest(
        action="DEPLOY_RELEASE", tool="deploy-runner", arguments={"release": "abc"},
        target="service-a", scope=("service-a",), side_effects=("DEPLOYMENT",),
        required_capabilities=(CapabilityClass.DEPLOYMENT,), approval_class="A2",
        approval_reference="HD-DEPLOY-1", deployment_grant_reference=reference,
    )
    envelope = create_dispatch_envelope(
        identity=identity, request=request, authentication_reference="credential-ref",
        authentication_method="delegated", authority_references=("release:abc",),
        gate_references=("stage10:ready",), policy_references=("deployment-policy",),
        limit_references=("budget-1",), deployment_grant_reference=reference,
    )
    return identity, request, envelope


def test_governance_envelope_rejects_credential_only_deployment_and_accepts_exact_grant():
    identity, request, envelope = _deployment_dispatch(None)
    with pytest.raises(GovernanceEnvelopeError, match="DEPLOYMENT_GRANT_MISMATCH"):
        GovernanceEnvelopeValidator().validate_pre_dispatch(
            envelope, request, current_identity=identity
        )
    identity, request, envelope = _deployment_dispatch("HD-DEPLOY-1")
    decision = GovernanceEnvelopeValidator().validate_pre_dispatch(
        envelope, request, current_identity=identity
    )
    assert decision.outcome == "PASS"


def test_governance_envelope_binds_resource_policy_and_budget_increase_approval():
    identity = IdentityBinding(
        actor_id="actor", project_id="project", environment="workspace",
        repository="repo", branch="main", baseline="abc", stage_id="06",
        attempt_id="attempt",
    )
    request = DispatchRequest(
        action="MATERIAL_BUDGET_INCREASE", tool="budget-admin", arguments={"calls": 5},
        target="budget-1", scope=("budget-1",), side_effects=("BUDGET_CHANGE",),
        required_capabilities=(CapabilityClass.EXTERNAL_SIDE_EFFECT,), approval_class="A0",
        approval_reference="routine", resource_policy_reference="budget-1",
    )
    envelope = create_dispatch_envelope(
        identity=identity, request=request, authentication_reference="identity-ref",
        authentication_method="local", authority_references=("authority",),
        gate_references=(), policy_references=("cost-policy",),
        limit_references=("budget-1",), resource_policy_reference="budget-1",
    )
    with pytest.raises(GovernanceEnvelopeError, match="BUDGET_INCREASE_REQUIRES_APPROVAL"):
        GovernanceEnvelopeValidator().validate_pre_dispatch(
            envelope, request, current_identity=identity
        )
