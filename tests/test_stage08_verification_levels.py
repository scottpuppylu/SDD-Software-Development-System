from __future__ import annotations

from pathlib import Path
import sys

import pytest

from sdd_orchestrator.codex_results import VerificationResult
from sdd_orchestrator.errors import CodexAdapterError
from sdd_orchestrator.task_parser import AtomicTask, TaskFileParser
from sdd_orchestrator.verification_execution import execute_local_verification_plan
from sdd_orchestrator.verification_policy import (
    VerificationCommandPolicy,
    VerificationLevel,
)
from sdd_orchestrator.verification_runtime import build_local_verification_runtime


def task(**overrides) -> AtomicTask:
    values = {
        "task_id": "T026",
        "title": "verification levels",
        "status": "TODO",
        "raw_markdown": "TASK-026",
        "traceability": ["SPEC-019", "DES-020"],
        "allowed_paths": ["src/worker.py"],
        "verification_commands": ["python -m pytest -q tests/test_target.py"],
        "behavior_scope": "Run local verification.",
    }
    values.update(overrides)
    return AtomicTask(**values)


def test_legacy_verification_commands_map_to_target_and_are_never_skipped():
    plan = VerificationCommandPolicy.plan_for_task(task())
    assert plan.fast == ()
    assert plan.full == ()
    assert [step.level for step in plan.target] == [VerificationLevel.TARGET]
    assert [step.command for step in plan.target] == [
        "python -m pytest -q tests/test_target.py"
    ]
    assert plan.target[0].legacy_required is True


def test_parser_supports_versioned_levels_and_explicit_full_authority():
    parsed = TaskFileParser(r"""
## TASK-026 - levels
- **Status:** TODO
- **Authority trace:** `SPEC-019 -> DES-020 -> TASK-026`; `ARCH-AC-01`.
- **Allowed files:** `src/worker.py`.
- **Allowed implementation scope:** Local checks.
- **Verification Commands:** `python -m pytest -q tests/test_target.py`.
- **FAST Verification Commands:** `python -c "import worker"`.
- **FULL Verification Commands:** `python -m pytest -q`.
- **FULL Verification Authorized:** YES
""").parse()[0]
    plan = VerificationCommandPolicy.plan_for_task(parsed)

    assert parsed.relevant_spec == ["SPEC-019"]
    assert parsed.relevant_design == ["DES-020"]
    assert plan.full_authorized is True
    assert [step.command for step in plan.fast] == ['python -c "import worker"']
    assert [step.command for step in plan.target] == [
        "python -m pytest -q tests/test_target.py"
    ]
    assert [step.command for step in plan.full] == ["python -m pytest -q"]
    assert [step.level for step in plan.ordered_steps()] == [
        VerificationLevel.FAST,
        VerificationLevel.TARGET,
        VerificationLevel.FULL,
    ]


def test_full_never_runs_implicitly_and_fails_without_exact_authority():
    unapproved = task(
        verification_levels={"FULL": ["python -m pytest -q"]},
        full_verification_authorized=False,
    )
    with pytest.raises(CodexAdapterError, match="explicit"):
        VerificationCommandPolicy.plan_for_task(unapproved)

    normal = VerificationCommandPolicy.plan_for_task(task())
    assert all(step.level is not VerificationLevel.FULL for step in normal.ordered_steps())


def test_explicit_stronger_full_classification_does_not_duplicate_legacy_target():
    command = "python -m pytest -q tests/test_target.py"
    plan = VerificationCommandPolicy.plan_for_task(
        task(
            verification_commands=[command],
            verification_levels={"FULL": [command]},
            full_verification_authorized=True,
        )
    )
    assert plan.target == ()
    assert [step.command for step in plan.full] == [command]
    assert plan.full[0].legacy_required is True


def test_local_execution_has_no_provider_dependency_and_stops_on_failure():
    plan = VerificationCommandPolicy.plan_for_task(
        task(
            verification_levels={
                "FAST": ["python -c \"import worker\""],
                "TARGET": ["python -m pytest -q tests/test_extra.py"],
            }
        )
    )
    observed = []

    def execute(step):
        observed.append(step.level)
        return VerificationResult(
            step.command,
            1 if step.level is VerificationLevel.FAST else 0,
            "",
            "fast failed" if step.level is VerificationLevel.FAST else "",
        )

    results = execute_local_verification_plan(plan, execute)
    assert observed == [VerificationLevel.FAST]
    assert len(results) == 1
    assert results[0].passed is False


def test_successful_local_plan_runs_fast_then_all_target_without_provider_session():
    plan = VerificationCommandPolicy.plan_for_task(
        task(
            verification_levels={
                "FAST": ["python -c \"import worker\""],
                "TARGET": ["python -m pytest -q tests/test_extra.py"],
            }
        )
    )
    observed = []

    def execute(step):
        observed.append((step.level, step.command))
        return VerificationResult(step.command, 0, "passed", "")

    results = execute_local_verification_plan(plan, execute)
    assert [level for level, _ in observed] == [
        VerificationLevel.FAST,
        VerificationLevel.TARGET,
        VerificationLevel.TARGET,
    ]
    assert all(item.passed for item in results)


def test_runtime_is_local_and_explicitly_requires_no_provider_session(tmp_path: Path):
    runtime = build_local_verification_runtime(tmp_path, sys.executable)
    assert Path(runtime.project_python).resolve() == Path(sys.executable).resolve()
    assert runtime.provider_session_required is False
    assert len(runtime.identity) == 64
    assert runtime.environment["SDD_PROJECT_PYTHON"] == runtime.project_python


def test_missing_verification_contract_fails_closed():
    with pytest.raises(CodexAdapterError, match="no executable command"):
        VerificationCommandPolicy.plan_for_task(task(verification_commands=[]))
