from pathlib import Path
from unittest.mock import patch
import subprocess

from sdd_orchestrator.codex_adapter import CodexCLI


def test_stage08_codex_subprocess_forces_utf8_decode():
    cli = CodexCLI(executable="codex", sandbox="workspace-write")
    fake = subprocess.CompletedProcess(["codex"], 0, "✓ done", "")
    with patch.object(cli, "resolved_executable", return_value="codex.cmd"), patch(
        "sdd_orchestrator.codex_adapter.subprocess.run", return_value=fake
    ) as run:
        result = cli.execute(Path("."), "implement T001")
    assert result.stdout == "✓ done"
    kwargs = run.call_args.kwargs
    assert kwargs["input"] == "implement T001"
    assert run.call_args.args[0][-1] == "-"
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["capture_output"] is True
