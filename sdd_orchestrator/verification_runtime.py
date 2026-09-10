from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Callable

from .errors import CodexAdapterError
from .governed_state import ModificationImpactLedger
from .verification_execution import (
    RegressionCoverageView,
    RegressionEvidence,
    build_regression_coverage_view,
)


def evaluate_regression_completion(
    ledger: ModificationImpactLedger,
    evidence: list[RegressionEvidence] | tuple[RegressionEvidence, ...],
    *,
    current_version: str | None = None,
) -> RegressionCoverageView:
    """Fail-closed runtime boundary for the non-qualifying completion guard."""

    version = current_version or getattr(ledger, "current_version", "")
    modification_id = getattr(ledger, "modification_id", "unknown-modification")
    try:
        return build_regression_coverage_view(
            ledger, evidence, current_version=current_version
        )
    except Exception as exc:
        return RegressionCoverageView.computation_failure(
            modification_id=modification_id,
            current_version=version,
            reason=str(exc),
        )


def resolve_project_python(
    repo_root: Path, explicit_project_python: str | None = None
) -> str:
    candidates: list[str] = []
    if explicit_project_python:
        candidates.append(explicit_project_python)
    env_python = os.environ.get("SDD_PROJECT_PYTHON")
    if env_python:
        candidates.append(env_python)

    if os.name == "nt":
        candidates.append(str(repo_root / ".venv" / "Scripts" / "python.exe"))
    else:
        candidates.append(str(repo_root / ".venv" / "bin" / "python"))

    candidates.append(sys.executable)

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_absolute() and path.exists():
            return str(path)
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise CodexAdapterError(
        "No project Python interpreter is available. Supply --project-python <path> "
        "or set SDD_PROJECT_PYTHON to the project's Python executable."
    )


def build_verification_env(project_python: str) -> dict[str, str]:
    env = os.environ.copy()
    python_path = Path(project_python)
    prepend: list[str] = [str(python_path.parent)]
    if os.name == "nt":
        scripts = python_path.parent / "Scripts"
        if scripts.exists():
            prepend.append(str(scripts))
    env["PATH"] = os.pathsep.join(prepend + [env.get("PATH", "")])
    env["SDD_PROJECT_PYTHON"] = project_python
    return env


def resolve_verification_argv(
    argv: list[str],
    project_python: str,
    verify_env: dict[str, str],
    resolver: Callable[..., str | None] | None = None,
) -> list[str]:
    if argv[0] in {"python", "python3", r".\.venv\Scripts\python.exe"}:
        argv[0] = project_python
    elif argv[0] == "pytest":
        return [project_python, "-m", "pytest", *argv[1:]]
    else:
        resolved = (resolver or shutil.which)(
            argv[0], path=verify_env.get("PATH")
        )
        if resolved:
            argv[0] = resolved
    return argv
