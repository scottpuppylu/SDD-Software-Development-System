from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess

import yaml


class GitRuntimeError(RuntimeError):
    pass


@dataclass
class GitSnapshot:
    is_repository: bool
    branch: str | None
    head_commit: str | None
    dirty_paths: list[str]
    recent_commits: list[dict[str, str]]


@dataclass
class RecoverySnapshot:
    git: GitSnapshot
    implementation_state: dict[str, Any]
    inferred: dict[str, Any]
    warnings: list[str]


class GitRepository:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if check and proc.returncode != 0:
            raise GitRuntimeError(
                f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        return proc

    def is_repository(self) -> bool:
        proc = self._run(["rev-parse", "--is-inside-work-tree"], check=False)
        return proc.returncode == 0 and proc.stdout.strip() == "true"

    def is_tracked(self, path: str) -> bool:
        """Return True only when path is already tracked by Git."""
        proc = self._run(["ls-files", "--error-unmatch", "--", path], check=False)
        return proc.returncode == 0

    def commit_subject(self, commit: str = "HEAD") -> str:
        return self._run(["show", "-s", "--format=%s", commit]).stdout.strip()

    def commit_paths(self, commit: str = "HEAD") -> list[str]:
        return self._run(
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit]
        ).stdout.splitlines()

    def read_committed_file(self, path: str, commit: str = "HEAD") -> str:
        normalized = Path(path).as_posix()
        return self._run(["show", f"{commit}:{normalized}"]).stdout

    def snapshot(self, *, recent_limit: int = 10) -> GitSnapshot:
        if not self.is_repository():
            return GitSnapshot(False, None, None, [], [])
        branch = self._run(["branch", "--show-current"]).stdout.strip() or None
        head_proc = self._run(["rev-parse", "HEAD"], check=False)
        head = head_proc.stdout.strip() if head_proc.returncode == 0 else None
        status = self._run(["status", "--porcelain=v1", "--untracked-files=all"]).stdout.splitlines()
        dirty = []
        for line in status:
            if not line:
                continue
            path = line[3:] if len(line) > 3 else line
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            dirty.append(path)
        commits: list[dict[str, str]] = []
        if head:
            log = self._run(
                ["log", f"-{recent_limit}", "--pretty=format:%H%x09%s"],
                check=False,
            ).stdout or ""
            for line in log.splitlines():
                if "\t" in line:
                    sha, subject = line.split("\t", 1)
                    commits.append({"commit": sha, "subject": subject})
        return GitSnapshot(True, branch, head, dirty, commits)

    def checkpoint(
        self,
        *,
        task_id: str,
        summary: str,
        paths: list[str],
        commit_type: str = "chore",
        scope: str = "sdd",
        allow_unrelated_dirty: bool = False,
    ) -> str:
        if not self.is_repository():
            raise GitRuntimeError("Repository is not initialized with Git")
        if not task_id.strip():
            raise GitRuntimeError("task_id is required")
        if not summary.strip():
            raise GitRuntimeError("summary is required")
        if not paths:
            raise GitRuntimeError(
                "Explicit checkpoint paths are required; automatic git add -A is intentionally forbidden"
            )

        root = self.repo_root
        normalized: list[str] = []
        for rel in paths:
            target = (root / rel).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise GitRuntimeError(f"Checkpoint path escapes repository: {rel}") from exc
            normalized.append(Path(rel).as_posix())

        before = self.snapshot()
        unrelated = [p for p in before.dirty_paths if not self._covered_by_paths(p, normalized)]
        if unrelated and not allow_unrelated_dirty:
            raise GitRuntimeError(
                "Unrelated dirty paths exist; refusing checkpoint: " + ", ".join(unrelated)
            )

        self._run(["add", "--", *normalized])
        staged = self._run(["diff", "--cached", "--name-only"]).stdout.splitlines()
        if not staged:
            raise GitRuntimeError("No staged changes for checkpoint")

        message = f"{commit_type}({scope}): [{task_id}] {summary}"
        self._run(["commit", "-m", message])
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    @staticmethod
    def _covered_by_paths(dirty_path: str, paths: list[str]) -> bool:
        for rel in paths:
            rel = rel.rstrip("/")
            if dirty_path == rel or dirty_path.startswith(rel + "/"):
                return True
        return False


class RecoveryManager:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.git = GitRepository(self.repo_root)
        self.implementation_state_path = (
            self.repo_root / ".sdd" / "state" / "implementation-state.yaml"
        )

    def _load_state(self) -> dict[str, Any]:
        if not self.implementation_state_path.exists():
            return {}
        data = yaml.safe_load(self.implementation_state_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def snapshot(self) -> RecoverySnapshot:
        git = self.git.snapshot(recent_limit=20)
        state = self._load_state()
        warnings: list[str] = []

        last_verified = state.get("last_verified_commit")
        if last_verified and git.head_commit and last_verified != git.head_commit:
            warnings.append(
                "Git HEAD differs from implementation-state last_verified_commit; inspect commits before resuming."
            )
        if git.dirty_paths:
            warnings.append("Repository has uncommitted changes; inspect before resuming execution.")
        if not git.is_repository:
            warnings.append("Git repository is unavailable; execution recovery evidence is incomplete.")

        current_task = state.get("current_task")
        next_task = state.get("next_task")
        last_completed = state.get("last_completed_task")
        inferred = {
            "last_completed_task": last_completed,
            "current_task": current_task,
            "next_task": next_task,
            "resume_ready": bool(git.is_repository) and not bool(state.get("blocked_status", {}).get("blocked")),
            "recommended_action": (
                "INSPECT_DIRTY_WORKTREE"
                if git.dirty_paths
                else "RESUME_CURRENT_TASK"
                if current_task
                else "SELECT_NEXT_TASK"
                if next_task
                else "RECONCILE_TASK_STATE"
            ),
        }
        return RecoverySnapshot(git, state, inferred, warnings)

    def record_checkpoint(
        self,
        *,
        commit: str,
        completed_task: str,
        next_task: str | None = None,
        test_status: str = "PASS",
    ) -> None:
        state = self._load_state()
        state["last_completed_task"] = completed_task
        state["current_task"] = next_task
        state["next_task"] = None
        state["last_verified_commit"] = commit
        state.setdefault("test_status", {})["overall"] = test_status
        state.setdefault("blocked_status", {})["blocked"] = False
        self.implementation_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.implementation_state_path.write_text(
            yaml.safe_dump(state, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
