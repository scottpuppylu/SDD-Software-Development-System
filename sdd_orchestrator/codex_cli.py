from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess

from .errors import CodexAdapterError


class CodexCLI:
    def __init__(
        self,
        *,
        executable: str = "codex",
        sandbox: str = "workspace-write",
        approval_policy: str = "never",
        timeout_seconds: int = 1800,
        ephemeral: bool = True,
    ):
        self.executable = executable
        self.sandbox = sandbox
        self.approval_policy = approval_policy
        self.timeout_seconds = timeout_seconds
        self.ephemeral = ephemeral

    def resolved_executable(self) -> str | None:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        if os.name == "nt" and not self.executable.lower().endswith((".cmd", ".exe", ".bat")):
            return shutil.which(self.executable + ".cmd")
        return None

    def available(self) -> bool:
        return self.resolved_executable() is not None

    def command(self, prompt: str, *, executable: str | None = None) -> list[str]:
        # `codex exec` is the non-interactive execution surface. Pass the
        # Stage 08 prompt through forced UTF-8 stdin (`codex exec -`) instead
        # of as a positional argv value. This avoids Windows multiline/large
        # prompt transport issues and follows Codex's documented stdin mode.
        # The `prompt` parameter remains in the signature for compatibility;
        # its content is supplied by `execute()` via subprocess stdin.
        cmd = [
            executable or self.executable,
            "exec",
            "--sandbox",
            self.sandbox,
        ]
        if self.ephemeral:
            cmd.append("--ephemeral")
        cmd.append("-")
        return cmd

    def execute(self, repo_root: Path, prompt: str) -> subprocess.CompletedProcess[str]:
        executable = self.resolved_executable()
        if not executable:
            raise CodexAdapterError(
                "Codex CLI is not installed or not on PATH. Install/authenticate Codex before Stage 08 execution."
            )
        return subprocess.run(
            self.command(prompt, executable=executable),
            cwd=repo_root,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=self.timeout_seconds,
        )
