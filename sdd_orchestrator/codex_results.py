from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import subprocess


class CodexOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CODEX_QUOTA_EXHAUSTED = "CODEX_QUOTA_EXHAUSTED"
    CODEX_INTERRUPTED = "CODEX_INTERRUPTED"
    CODEX_TIMEOUT = "CODEX_TIMEOUT"


_QUOTA_MARKERS = (
    "quota exceeded", "quota exhausted", "usage limit", "rate limit exceeded",
    "insufficient quota",
)


def normalize_codex_outcome(
    *,
    returncode: int | None = None,
    stderr: str = "",
    exception: BaseException | None = None,
) -> CodexOutcome:
    """Normalize provider/process outcomes without making a SAFE_PAUSE decision."""
    if isinstance(exception, (subprocess.TimeoutExpired, TimeoutError)):
        return CodexOutcome.CODEX_TIMEOUT
    if isinstance(exception, (KeyboardInterrupt, InterruptedError)):
        return CodexOutcome.CODEX_INTERRUPTED
    lowered = stderr.lower()
    if any(marker in lowered for marker in _QUOTA_MARKERS):
        return CodexOutcome.CODEX_QUOTA_EXHAUSTED
    if returncode == 0 and exception is None:
        return CodexOutcome.COMPLETED
    return CodexOutcome.FAILED


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
