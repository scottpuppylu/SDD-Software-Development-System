from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class CodexTaskRunResult:
    task_id: str
    title: str
    codex_returncode: int
    codex_stdout: str
    codex_stderr: str
    changed_paths: list[str]
    verification: list[VerificationResult]
    checkpoint_commit: str | None
    next_task: str | None
    status: str
    evidence_file: str | None
