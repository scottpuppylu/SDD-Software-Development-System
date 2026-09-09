import json
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from sdd_orchestrator.governed_state import (
    AuthorityReference,
    GitIdentity,
    GovernedRecord,
    ImpactAmbiguity,
    ImpactLedgerStore,
    ImpactRisk,
    InvalidGovernedRecord,
    ModificationImpactLedger,
    ObservationReference,
    PublicationError,
    RepositoryStateStore,
    TraceLink,
    TraceabilityIndex,
    VerificationReference,
)


def record(*, version="v1", links=()):
    return GovernedRecord(
        lifecycle_position="08",
        current_work="TASK-001",
        next_work="TASK-002",
        completed_work=("TASK-000",),
        authorities=(AuthorityReference("SPEC-001", "docs/spec.md", "03", "APPROVED"),),
        human_decisions=("HD-001",),
        affected_scope=("governed-state",),
        task_execution_state={"TASK-001": "IN_PROGRESS"},
        verification=(VerificationReference("TEST-001", "NOT RUN", gap="awaiting execution"),),
        failures=("failure-001",),
        invalidations=("invalidation-001",),
        recovery_gate_provenance=("NOT_EVALUATED",),
        git=GitIdentity(version, "change-001", "checkpoint-001"),
        governing_decisions=("S07-PASS",),
        links=tuple(links),
    )


def chain(version="v1"):
    identities = ("G-01", "FR-11", "AC-11", "SPEC-001", "DES-008", "TASK-001")
    kinds = ("G", "FR", "AC", "SPEC", "DES", "TASK")
    return tuple(
        TraceLink(source, source_kind, target, target_kind, "governed-state", "S07-PASS", version)
        for source, source_kind, target, target_kind in zip(identities, kinds, identities[1:], kinds[1:])
    )


def impact_ledger(**overrides):
    links = (
        TraceLink("FR-18", "FR", "AC-18", "AC", "account-name", "PRD-APPROVED", "v1"),
        TraceLink("AC-18", "AC", "SPEC-011", "SPEC", "account-name", "PRD-APPROVED", "v1"),
        TraceLink("NFR-05", "NFR", "AC-27", "AC", "account-name", "PRD-APPROVED", "v1"),
        TraceLink("AC-27", "AC", "SPEC-011", "SPEC", "account-name", "PRD-APPROVED", "v1"),
        TraceLink("SPEC-011", "SPEC", "DES-014", "DES", "account-name", "DESIGN-APPROVED", "v1"),
        TraceLink("DES-014", "DES", "TASK-013", "TASK", "account-name", "S07-PASS", "v1"),
    )
    values = {
        "modification_id": "MOD-001",
        "request_reference": "requests/MOD-001",
        "requested_change": ("account-name",),
        "authorized_change_scope": ("account-name",),
        "affected_behavior_data": ("account-name display", "stored account name"),
        "preservation_expectations": ("account identifier", "login behavior"),
        "authority_basis": (
            AuthorityReference("FR-18", "docs/PRD.md", "Stage02", "APPROVED"),
            AuthorityReference("SPEC-011", "docs/spec.md", "Stage03", "APPROVED"),
        ),
        "observed_evidence": (
            ObservationReference("OBS-001", "src/account.py:20", "account-name display"),
        ),
        "ambiguities": (),
        "risks": (),
        "governing_requirements": ("FR-18", "NFR-05"),
        "governing_contracts": ("SPEC-011",),
        "governing_designs": ("DES-014",),
        "governing_tasks": ("TASK-013",),
        "links": links,
        "input_version": "v1",
        "current_version": "v1",
    }
    values.update(overrides)
    return ModificationImpactLedger(**values)


def test_repository_record_survives_session_loss_and_is_immutable(tmp_path):
    path = tmp_path / "owned" / "state.json"
    RepositoryStateStore(path).publish(record(links=chain()), affected_scope="governed-state")

    reconstructed = RepositoryStateStore(path).load()

    assert reconstructed == record(links=chain())
    assert reconstructed.git.checkpoint == "checkpoint-001"
    assert reconstructed.human_decisions == ("HD-001",)
    assert reconstructed.recovery_gate_provenance == ("NOT_EVALUATED",)
    with pytest.raises((FrozenInstanceError, TypeError)):
        reconstructed.task_execution_state["TASK-001"] = "DONE"


def test_projection_rebuilds_forward_and_backward_without_becoming_canonical(tmp_path):
    path = tmp_path / "state.json"
    store = RepositoryStateStore(path)
    store.publish(record(links=chain()), affected_scope="governed-state")
    index = TraceabilityIndex.rebuild(store.load())

    assert index.forward("SPEC-001")[0].target == "DES-008"
    assert index.backward("SPEC-001")[0].source == "AC-11"
    assert index.require_path(
        ("G-01", "FR-11", "AC-11", "SPEC-001", "DES-008", "TASK-001"),
        affected_scope="governed-state",
    ) == "PASS"
    assert set(json.loads(path.read_text(encoding="utf-8"))) >= {"links", "git", "authorities"}
    assert not list(tmp_path.glob("*index*"))


def test_missing_path_is_explicitly_incomplete():
    incomplete = chain()[:-1]
    index = TraceabilityIndex.rebuild(record(links=incomplete))
    assert index.require_path(
        ("G-01", "FR-11", "AC-11", "SPEC-001", "DES-008", "TASK-001"),
        affected_scope="governed-state",
    ) == "INCOMPLETE"


def test_stale_and_ambiguous_links_are_rejected():
    stale = chain("old")
    with pytest.raises(InvalidGovernedRecord, match="stale link"):
        record(version="current", links=stale)
    duplicated = chain() + (chain()[0],)
    with pytest.raises(InvalidGovernedRecord, match="duplicate link"):
        record(links=duplicated)


def test_failed_atomic_replace_does_not_advance_visible_state(tmp_path):
    path = tmp_path / "state.json"
    store = RepositoryStateStore(path)
    original = record()
    store.publish(original, affected_scope="governed-state")

    with patch("sdd_orchestrator.governed_state.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(PublicationError, match="failed write") as failure:
            store.publish(record(version="v2"), affected_scope="TASK-001")

    assert failure.value.affected_scope == "TASK-001"
    assert store.load() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_truthful_verification_vocabulary_and_required_gap():
    with pytest.raises(InvalidGovernedRecord, match="invalid verification result"):
        GovernedRecord.from_dict({**record().to_dict(), "verification": [{"identity": "x", "result": "SKIPPED"}]})
    with pytest.raises(InvalidGovernedRecord, match="requires a gap"):
        GovernedRecord.from_dict({**record().to_dict(), "verification": [{"identity": "x", "result": "NOT RUN"}]})


def test_authority_references_require_complete_repository_identity():
    malformed = record().to_dict()
    malformed["authorities"] = [
        {"identity": "SPEC-001", "artifact": "", "owner": "03", "status": "APPROVED"}
    ]
    with pytest.raises(InvalidGovernedRecord, match="authority references require"):
        GovernedRecord.from_dict(malformed)


def test_verification_identities_are_required_and_unambiguous():
    missing = record().to_dict()
    missing["verification"] = [
        {"identity": "", "result": "NOT RUN", "gap": "awaiting execution"}
    ]
    with pytest.raises(InvalidGovernedRecord, match="verification identity is required"):
        GovernedRecord.from_dict(missing)

    duplicated = record().to_dict()
    duplicated["verification"] = [
        {"identity": "TEST-001", "result": "PASS"},
        {"identity": "TEST-001", "result": "FAIL"},
    ]
    with pytest.raises(InvalidGovernedRecord, match="duplicate verification identity"):
        GovernedRecord.from_dict(duplicated)


def test_impact_ledger_separates_classifications_authority_and_observation(tmp_path):
    ledger = impact_ledger()
    path = tmp_path / "impact" / "MOD-001.json"
    ImpactLedgerStore(path).publish(ledger)

    reconstructed = ImpactLedgerStore(path).load()
    assessment = reconstructed.assess()

    assert reconstructed.requested_change == ("account-name",)
    assert reconstructed.affected_behavior_data == ("account-name display", "stored account name")
    assert reconstructed.preservation_expectations == ("account identifier", "login behavior")
    assert reconstructed.authority_basis[0].artifact == "docs/PRD.md"
    assert reconstructed.observed_evidence[0].reference == "src/account.py:20"
    assert not isinstance(reconstructed.observed_evidence[0], AuthorityReference)
    assert assessment.status == "READY"
    assert assessment.dependent_completion_allowed is True


@pytest.mark.parametrize(
    ("overrides", "expected_gap"),
    [
        ({"authority_basis": ()}, "missing authority basis"),
        ({"affected_behavior_data": ()}, "affected behavior/data scope is materially unknown"),
        ({"preservation_expectations": ()}, "preservation scope is materially unknown"),
        ({"authorized_change_scope": ()}, "requested scope exceeds authorized change scope"),
        ({"input_version": "old"}, "stale impact input"),
    ],
)
def test_impact_gaps_withhold_dependent_completion(overrides, expected_gap):
    assessment = impact_ledger(**overrides).assess()

    assert assessment.status == "BLOCKED"
    assert assessment.dependent_completion_allowed is False
    assert any(expected_gap in gap for gap in assessment.gaps)
    assert assessment.owner_routes


def test_material_product_ambiguity_and_high_risk_route_to_their_owners():
    ledger = impact_ledger(
        ambiguities=(
            ImpactAmbiguity(
                "AMB-001", "whether aliases also change", "account aliases", "Stage02 product owner"
            ),
        ),
        risks=(
            ImpactRisk(
                "RISK-001", "destructive account rewrite", "stored accounts", "security owner", True
            ),
        ),
    )

    assessment = ledger.assess()

    assert assessment.dependent_completion_allowed is False
    assert any("whether aliases also change" in gap for gap in assessment.gaps)
    assert assessment.risks == ("RISK-001: destructive account rewrite (scope: stored accounts)",)
    assert "Stage02 product owner" in assessment.owner_routes
    assert "TASK-011 safety interlock" in assessment.owner_routes


def test_conflicting_classifications_and_missing_trace_are_not_normalized():
    with pytest.raises(InvalidGovernedRecord, match="conflicting requested/preserved"):
        impact_ledger(preservation_expectations=("account-name",)).assess()

    assessment = impact_ledger(links=impact_ledger().links[:-1]).assess()
    assert assessment.dependent_completion_allowed is False
    assert any("TASK-013" in gap for gap in assessment.gaps)
    assert "traceability owner" in assessment.owner_routes


def test_impact_ledger_persistence_failure_preserves_prior_record(tmp_path):
    path = tmp_path / "MOD-001.json"
    store = ImpactLedgerStore(path)
    original = impact_ledger()
    store.publish(original)
    changed = impact_ledger(affected_behavior_data=("changed impact",))

    with patch("sdd_orchestrator.governed_state.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(PublicationError, match="failed write") as failure:
            store.publish(changed)

    assert "changed impact" in failure.value.affected_scope
    assert store.load() == original
    assert not list(tmp_path.glob("*.tmp"))
