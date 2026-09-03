import json
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from sdd_orchestrator.governed_state import (
    AuthorityReference,
    GitIdentity,
    GovernedRecord,
    InvalidGovernedRecord,
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
