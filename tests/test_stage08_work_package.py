from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from sdd_orchestrator.stage08_work_package import (
    BoundedContextItem,
    FailureContext,
    Stage08WorkPackageBuilder,
    WorkPackageError,
    WorkPackageKind,
    build_diff_provenance,
)
from sdd_orchestrator.task_parser import AtomicTask, SealedExecutionEnvelope


SPEC = """# Spec

### SPEC-019 - Bounded worker

The local controller owns deterministic verification. The worker only patches.

### SPEC-020 - Unrelated

This section must not be disclosed.
"""

DESIGN = """# Design

### DES-020 - Provider-neutral package

Use canonical content binding and minimum disclosure.

### DES-021 - Unrelated

This section must not be disclosed.
"""


def task() -> AtomicTask:
    return AtomicTask(
        task_id="T026",
        title="bounded worker",
        status="TODO",
        raw_markdown="TASK-026 SPEC-019 DES-020",
        traceability=["SPEC-019", "DES-020", "ARCH-AC-01"],
        allowed_paths=["src/worker.py", "tests/test_worker.py"],
        verification_commands=["python -m pytest -q tests/test_worker.py"],
        behavior_scope="Build a provider-neutral package.",
        objective="Keep the provider bounded to patch work.",
        forbidden_scope="`GIT_COMMIT`, `STATE_MUTATION`, `FULL_WITHOUT_AUTHORITY`",
        expected_behavior="Local verification runs after the bounded patch.",
        acceptance_criteria=["MINIMAL_STRUCTURED_WORK_PACKAGE", "WORKER_ONLY"],
        relevant_spec=["SPEC-019"],
        relevant_design=["DES-020"],
    )


def envelope() -> SealedExecutionEnvelope:
    return SealedExecutionEnvelope(
        envelope_id="e" * 64,
        task_id="T026",
        task_contract_sha256="t" * 64,
        authority_versions=(("tasks.md", "a" * 64),),
        stage07_report_sha256="r" * 64,
        repository="repo",
        branch="main",
        baseline_commit="b" * 40,
        allowed_paths=("src/worker.py", "tests/test_worker.py"),
        behavior_scope="Build a provider-neutral package.",
        verification_commands=("python -m pytest -q tests/test_worker.py",),
        checkpoint_conditions=("verification_pass",),
    )


def builder(tmp_path: Path, **state):
    provenance = build_diff_provenance(
        tmp_path,
        attempt_id="e" * 64,
        entry_head="b" * 40,
        dirty_paths=(),
        attribution="CLEAN_ENTRY_NO_IMPLEMENTATION_DIFF",
    )
    return Stage08WorkPackageBuilder(
        task=task(),
        envelope=envelope(),
        spec_text=SPEC,
        design_text=DESIGN,
        current_state={"branch": "main", "task_status": "TODO", **state},
        entry_head="b" * 40,
        authorized_baseline="a" * 40,
        diff_provenance=provenance,
    )


def test_initial_package_is_canonical_complete_and_provider_neutral(tmp_path):
    first = builder(tmp_path).initial()
    second = builder(tmp_path).initial()

    assert first.package_kind is WorkPackageKind.INITIAL_PATCH_PACKAGE
    assert first.package_id == second.package_id
    assert first.canonical_json() == second.canonical_json()
    payload = first.transport_payload()
    assert payload["PACKAGE_ID"] == first.package_id
    for field in (
        "TASK_ID", "OBJECTIVE", "AUTHORIZED_FILES", "FORBIDDEN_SCOPE",
        "RELEVANT_SPEC", "RELEVANT_DESIGN", "CURRENT_STATE",
        "EXPECTED_BEHAVIOR", "FAILURE_CONTEXT", "REQUIRED_OUTPUT",
        "SEALED_ENVELOPE_ID", "ENTRY_HEAD", "AUTHORIZED_BASELINE",
        "DIFF_PROVENANCE",
    ):
        assert field in payload
    assert payload["FAILURE_CONTEXT"] == {
        "failed_checks": [], "errors": [], "relevant_source": [], "relevant_diff": ""
    }
    assert "Codex" not in first.canonical_json()
    assert "SPEC-020" not in first.canonical_json()
    assert "DES-021" not in first.canonical_json()


def test_secret_shaped_values_are_redacted_before_transport(tmp_path):
    package = builder(tmp_path, provider_note="api_key=super-secret-value").initial()
    serialized = package.canonical_json()
    assert "super-secret-value" not in serialized
    assert "[REDACTED]" in serialized


def test_remediation_package_is_minimal_and_content_bound(tmp_path):
    failure = FailureContext(
        failed_checks=("tests/test_worker.py::test_denied",),
        errors=("assert denied; access_token=top-secret-token",),
        relevant_source=(BoundedContextItem("src/worker.py:10", "return allow"),),
        relevant_diff="- return deny\n+ return allow",
    )
    package = builder(tmp_path).remediation(failure)
    payload = package.transport_payload()

    assert package.package_kind is WorkPackageKind.REMEDIATION_PACKAGE
    assert payload["FAILURE_CONTEXT"]["failed_checks"] == [
        "tests/test_worker.py::test_denied"
    ]
    assert payload["FAILURE_CONTEXT"]["relevant_source"] == [
        {"identity": "src/worker.py:10", "content": "return allow"}
    ]
    assert "top-secret-token" not in package.canonical_json()
    assert "SPEC-020" not in package.canonical_json()


def test_initial_package_rejects_failure_context_and_remediation_requires_failure(tmp_path):
    initial = builder(tmp_path).initial()
    with pytest.raises(WorkPackageError, match="explicit empty failure context"):
        replace(
            initial,
            failure_context=FailureContext(failed_checks=("failed",)),
        )
    with pytest.raises(WorkPackageError, match="requires bounded failed checks"):
        builder(tmp_path).remediation(FailureContext(errors=("error",)))


def test_unsafe_authorized_path_and_missing_authority_section_fail_closed(tmp_path):
    unsafe_envelope = replace(envelope(), allowed_paths=("../escape.py",))
    base = builder(tmp_path)
    with pytest.raises(WorkPackageError, match="unsafe authorized path"):
        Stage08WorkPackageBuilder(
            task=replace(task(), allowed_paths=["../escape.py"]),
            envelope=unsafe_envelope,
            spec_text=SPEC,
            design_text=DESIGN,
            current_state={"branch": "main"},
            entry_head="b" * 40,
            authorized_baseline="a" * 40,
            diff_provenance=base.diff_provenance,
        ).initial()

    with pytest.raises(WorkPackageError, match="authority section is missing"):
        Stage08WorkPackageBuilder(
            task=replace(task(), relevant_spec=["SPEC-999"]),
            envelope=envelope(),
            spec_text=SPEC,
            design_text=DESIGN,
            current_state={"branch": "main"},
            entry_head="b" * 40,
            authorized_baseline="a" * 40,
            diff_provenance=base.diff_provenance,
        ).initial()


def test_diff_provenance_binds_authorized_dirty_content(tmp_path):
    target = tmp_path / "src/worker.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    first = build_diff_provenance(
        tmp_path,
        attempt_id="attempt",
        entry_head="b" * 40,
        dirty_paths=("src/worker.py",),
        attribution="AUTHORIZED_PREEXISTING_TASK_DIFF",
    )
    target.write_text("VALUE = 2\n", encoding="utf-8")
    second = build_diff_provenance(
        tmp_path,
        attempt_id="attempt",
        entry_head="b" * 40,
        dirty_paths=("src/worker.py",),
        attribution="AUTHORIZED_PREEXISTING_TASK_DIFF",
    )
    assert first.content_sha256 != second.content_sha256
    assert first.dirty_paths == ("src/worker.py",)
