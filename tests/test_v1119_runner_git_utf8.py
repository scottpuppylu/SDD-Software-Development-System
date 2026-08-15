from __future__ import annotations

from pathlib import Path
import subprocess

from types import SimpleNamespace
from sdd_orchestrator.runner import StageRunner


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    )


def test_runner_collects_utf8_git_history_for_stage09_inputs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "SDD Test")
    _git(repo, "config", "user.email", "sdd@example.test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    subject = "T014 完成：Stage 09 evidence ✓"
    _git(repo, "commit", "-m", subject)

    runner = StageRunner(SimpleNamespace(repo_root=repo))
    history = runner._git(["log", "-20", "--pretty=format:%H%x09%s"], allow_failure=True)

    assert subject in history


def test_runner_git_explicitly_requests_utf8_and_handles_missing_stdout(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class Proc:
        returncode = 0
        stdout = None
        stderr = None

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return Proc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = StageRunner(SimpleNamespace(repo_root=tmp_path))

    assert runner._git(["status", "--short"], allow_failure=True) == ""
    assert captured["text"] is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["capture_output"] is True
