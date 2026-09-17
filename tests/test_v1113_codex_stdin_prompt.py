from pathlib import Path
from unittest.mock import patch
import subprocess

from sdd_orchestrator.codex_adapter import CodexCLI, Stage08CodexRunner
from sdd_orchestrator.stage08_work_package import (
    Stage08WorkPackageBuilder,
    build_diff_provenance,
)
from sdd_orchestrator.task_parser import SealedExecutionEnvelope


def test_codex_exec_uses_forced_stdin_for_multiline_prompt():
    cli = CodexCLI(executable="codex", sandbox="workspace-write")
    prompt = "line one\nline two\nTASK CONTRACT:\n- do work"
    fake = subprocess.CompletedProcess(["codex"], 0, "done", "")
    with patch.object(cli, "resolved_executable", return_value="codex.cmd"), patch(
        "sdd_orchestrator.codex_adapter.subprocess.run", return_value=fake
    ) as run:
        cli.execute(Path("."), prompt)
    argv = run.call_args.args[0]
    kwargs = run.call_args.kwargs
    assert argv[-1] == "-"
    assert prompt not in argv
    assert kwargs["input"] == prompt
    assert kwargs["encoding"] == "utf-8"


def test_stage08_prompt_explicitly_requires_execution(tmp_path):
    # Build prompt without needing a repository preflight.
    from sdd_orchestrator.codex_adapter import AtomicTask
    task = AtomicTask(
        task_id="T001",
        title="setup",
        status="TODO",
        raw_markdown="### T001\n- **Allowed files:** `a.py`",
        traceability=["SPEC-001"],
        allowed_paths=["a.py"],
        verification_commands=["python -m pytest -q"],
    )
    runner = object.__new__(Stage08CodexRunner)
    prompt = Stage08CodexRunner.build_prompt(runner, task)
    assert "BEGIN EXECUTION NOW" in prompt
    assert "Do not merely acknowledge" in prompt
    assert "T001" in prompt


def test_structured_prompt_keeps_codex_in_worker_only_boundary(tmp_path):
    from sdd_orchestrator.codex_adapter import AtomicTask

    task = AtomicTask(
        task_id="T026",
        title="bounded worker",
        status="TODO",
        raw_markdown="TASK-026 SPEC-019 DES-020",
        traceability=["SPEC-019", "DES-020"],
        allowed_paths=["worker.py"],
        verification_commands=["python -m pytest -q tests/test_worker.py"],
        behavior_scope="Create a bounded package.",
        objective="Produce an authorized patch only.",
        forbidden_scope="`GIT_COMMIT`, `STATE_MUTATION`, `FULL_WITHOUT_AUTHORITY`",
        expected_behavior="The controller verifies locally.",
        acceptance_criteria=["WORKER_ONLY"],
        relevant_spec=["SPEC-019"],
        relevant_design=["DES-020"],
    )
    envelope = SealedExecutionEnvelope(
        envelope_id="e" * 64,
        task_id="T026",
        task_contract_sha256="t" * 64,
        authority_versions=(("tasks.md", "a" * 64),),
        stage07_report_sha256="r" * 64,
        repository=str(tmp_path),
        branch="main",
        baseline_commit="b" * 40,
        allowed_paths=("worker.py",),
        behavior_scope=task.behavior_scope,
        verification_commands=tuple(task.verification_commands),
        checkpoint_conditions=("verification_pass",),
    )
    package = Stage08WorkPackageBuilder(
        task=task,
        envelope=envelope,
        spec_text="### SPEC-019 - Worker\nBounded worker only.\n",
        design_text="### DES-020 - Package\nProvider-neutral package.\n",
        current_state={"branch": "main"},
        entry_head="b" * 40,
        authorized_baseline="a" * 40,
        diff_provenance=build_diff_provenance(
            tmp_path,
            attempt_id=envelope.envelope_id,
            entry_head="b" * 40,
            dirty_paths=(),
            attribution="CLEAN_ENTRY_NO_IMPLEMENTATION_DIFF",
        ),
    ).initial()
    runner = object.__new__(Stage08CodexRunner)
    prompt = Stage08CodexRunner.build_prompt(runner, task, envelope, package)

    assert package.package_id in prompt
    assert "bounded coding worker" in prompt
    assert "Do not run authoritative FAST, TARGET, or FULL verification" in prompt
    assert "Do not perform Git commits" in prompt
    assert "MANDATORY START/RESUME" not in prompt
    assert "Read .sdd/state/implementation-state.yaml" not in prompt
