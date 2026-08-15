from __future__ import annotations

from pathlib import Path
import subprocess

from sdd_orchestrator.git_runtime import GitRepository


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


def test_snapshot_reads_utf8_commit_subject(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "SDD Test")
    _git(repo, "config", "user.email", "sdd@example.test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    subject = "測試：中文 Git checkpoint ✓"
    _git(repo, "commit", "-m", subject)

    snapshot = GitRepository(repo).snapshot(recent_limit=5)

    assert snapshot.is_repository is True
    assert snapshot.head_commit
    assert snapshot.recent_commits
    assert snapshot.recent_commits[0]["subject"] == subject


def test_git_run_explicitly_requests_utf8(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class Proc:
        returncode = 0
        stdout = "true\n"
        stderr = ""

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return Proc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    repo = GitRepository(tmp_path)
    assert repo.is_repository() is True
    assert captured["text"] is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["capture_output"] is True
