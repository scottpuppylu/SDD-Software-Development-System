from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import shlex
from typing import Any, Iterable

from .errors import CodexAdapterError


class VerificationLevel(str, Enum):
    FAST = "FAST"
    TARGET = "TARGET"
    FULL = "FULL"


@dataclass(frozen=True)
class VerificationStep:
    level: VerificationLevel
    command: str
    legacy_required: bool = False


@dataclass(frozen=True)
class VerificationPlan:
    """Controller-owned, provider-independent Stage08 verification contract."""

    fast: tuple[VerificationStep, ...] = ()
    target: tuple[VerificationStep, ...] = ()
    full: tuple[VerificationStep, ...] = ()
    full_authorized: bool = False
    schema_version: str = "1.0"

    def ordered_steps(self) -> tuple[VerificationStep, ...]:
        if self.full and not self.full_authorized:
            raise CodexAdapterError(
                "Stage08 FULL verification is declared without explicit current authority"
            )
        return self.fast + self.target + (self.full if self.full_authorized else ())

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(item.command for item in self.ordered_steps())

    def steps_for(self, level: VerificationLevel) -> tuple[VerificationStep, ...]:
        return {
            VerificationLevel.FAST: self.fast,
            VerificationLevel.TARGET: self.target,
            VerificationLevel.FULL: self.full if self.full_authorized else (),
        }[level]


class VerificationCommandPolicy:
    FORBIDDEN_TOKENS = {"&&", "||", ";", "|", ">", ">>", "<", "2>", "&"}
    STATIC_ALLOWED_FIRST = {"pytest", "npm", "pnpm", "yarn", "ruff", "mypy", "go", "cargo", "dotnet"}
    EXACT_WINDOWS_PYTHON = r".\.venv\Scripts\python.exe"

    @classmethod
    def plan_for_task(cls, task: Any) -> VerificationPlan:
        """Map legacy commands to TARGET and require explicit authority for FULL."""

        declared = getattr(task, "verification_levels", {}) or {}
        normalized: dict[VerificationLevel, list[str]] = {
            level: cls._unique(declared.get(level.value, ()))
            for level in VerificationLevel
        }
        legacy = cls._unique(getattr(task, "verification_commands", ()) or ())
        full_authorized = bool(getattr(task, "full_verification_authorized", False))
        if normalized[VerificationLevel.FULL] and not full_authorized:
            raise CodexAdapterError(
                "Stage08 FULL verification requires an explicit task/Stage07 authority binding"
            )

        # Existing single-list contracts remain authoritative. A command may be
        # classified more strongly only when exact FULL authority exists.
        target = list(normalized[VerificationLevel.TARGET])
        full = normalized[VerificationLevel.FULL]
        for command in legacy:
            if command in full and full_authorized:
                continue
            if command not in target:
                target.append(command)

        for command in (*normalized[VerificationLevel.FAST], *target, *full):
            cls.argv(command)

        plan = VerificationPlan(
            fast=tuple(
                VerificationStep(VerificationLevel.FAST, command)
                for command in normalized[VerificationLevel.FAST]
            ),
            target=tuple(
                VerificationStep(
                    VerificationLevel.TARGET,
                    command,
                    legacy_required=command in legacy,
                )
                for command in target
            ),
            full=tuple(
                VerificationStep(
                    VerificationLevel.FULL,
                    command,
                    legacy_required=command in legacy,
                )
                for command in full
            ),
            full_authorized=full_authorized,
        )
        ordered = plan.ordered_steps()
        included = {item.command for item in ordered}
        missing_legacy = [command for command in legacy if command not in included]
        if missing_legacy:
            raise CodexAdapterError(
                f"Required legacy Verification Commands were omitted: {missing_legacy}"
            )
        if not ordered:
            raise CodexAdapterError("Stage08 verification plan has no executable command")
        return plan

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))

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
