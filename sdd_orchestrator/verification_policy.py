from __future__ import annotations

import re
import shlex

from .errors import CodexAdapterError


class VerificationCommandPolicy:
    FORBIDDEN_TOKENS = {"&&", "||", ";", "|", ">", ">>", "<", "2>", "&"}
    STATIC_ALLOWED_FIRST = {"pytest", "npm", "pnpm", "yarn", "ruff", "mypy", "go", "cargo", "dotnet"}
    EXACT_WINDOWS_PYTHON = r".\.venv\Scripts\python.exe"

    @classmethod
    def argv(cls, command: str) -> list[str]:
        exact_prefix = cls.EXACT_WINDOWS_PYTHON + " "
        if command.startswith(exact_prefix):
            remainder_text = command[len(exact_prefix):]
            if re.search(r"&&|\|\||>>|[;|<>&]", remainder_text):
                raise CodexAdapterError(f"Shell operators are forbidden in verification command: {command}")
            try:
                remainder = shlex.split(remainder_text)
            except ValueError as exc:
                raise CodexAdapterError(f"Invalid verification command: {command}") from exc
            argv = [cls.EXACT_WINDOWS_PYTHON, *remainder]
            if any(token in cls.FORBIDDEN_TOKENS for token in argv):
                raise CodexAdapterError(f"Shell operators are forbidden in verification command: {command}")
            if len(argv) >= 4 and argv[1:3] == ["-m", "pytest"]:
                return argv
            raise CodexAdapterError(f"Python verification command is not allowlisted: {command}")

        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise CodexAdapterError(f"Invalid verification command: {command}") from exc
        if not argv or any(token in cls.FORBIDDEN_TOKENS for token in argv):
            raise CodexAdapterError(f"Shell operators are forbidden in verification command: {command}")

        first = argv[0]
        if first in {"python", "python3"}:
            if len(argv) >= 3 and argv[1:3] == ["-m", "pytest"]:
                return argv
            if argv == [first, "-m", "pip", "install", "-e", "."]:
                return argv
            if len(argv) == 3 and argv[1] == "-c" and re.fullmatch(r"import\s+[A-Za-z_][A-Za-z0-9_.]*", argv[2]):
                return argv
            if len(argv) == 4 and argv[1] == "-m" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", argv[2]) and argv[3] == "--help":
                return argv
            raise CodexAdapterError(f"Python verification command is not allowlisted: {command}")

        if first in cls.STATIC_ALLOWED_FIRST:
            return argv

        if len(argv) == 2 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", first) and argv[1] == "--help":
            return argv
        if argv == ["git", "status", "--short"]:
            return argv
        if argv == ["git", "diff", "--check"]:
            return argv
        if (
            len(argv) == 5
            and argv[:4] == ["git", "log", "--oneline", "--decorate"]
            and re.fullmatch(r"-\d+", argv[4])
        ):
            return argv
        raise CodexAdapterError(f"Verification command is not allowlisted: {command}")
