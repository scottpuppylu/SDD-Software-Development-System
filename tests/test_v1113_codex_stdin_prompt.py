from pathlib import Path
from unittest.mock import patch
import subprocess

from sdd_orchestrator.codex_adapter import CodexCLI, Stage08CodexRunner


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
