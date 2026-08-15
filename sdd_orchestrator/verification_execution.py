from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .codex_results import VerificationResult


def execute_verification_command(
    command: str,
    argv: list[str],
    repo_root: Path,
    verify_env: dict[str, str],
    *,
    run_command: Callable[..., Any],
    call_with_heartbeat: Callable[[str, Callable[[], Any]], Any],
    heartbeat_label: str,
) -> VerificationResult:
    try:
        proc = call_with_heartbeat(
            heartbeat_label,
            lambda: run_command(
                argv,
                cwd=repo_root,
                env=verify_env,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            ),
        )
    except FileNotFoundError as exc:
        return VerificationResult(
            command,
            127,
            "",
            f"verification executable not found: {argv[0]} ({exc})",
        )
    return VerificationResult(command, proc.returncode, proc.stdout, proc.stderr)
