from __future__ import annotations

import fnmatch
from typing import Callable


def generated_verification_dirty(
    path: str,
    *,
    is_tracked: Callable[[str], bool],
) -> bool:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    generated = (
        any(part == "__pycache__" for part in parts)
        or normalized.endswith(".pyc")
        or any(part.endswith(".egg-info") for part in parts)
    )
    if not generated:
        return False
    return not is_tracked(path)


def covered(path: str, allowed_paths: list[str]) -> bool:
    for allowed in allowed_paths:
        normalized = allowed.rstrip("/")
        if "*" in normalized or "?" in normalized or "[" in normalized:
            if fnmatch.fnmatch(path, normalized):
                return True
        elif path == normalized or path.startswith(normalized + "/"):
            return True
    return False


def runtime_dirty(path: str, runtime_dirty_prefixes: tuple[str, ...]) -> bool:
    return path.startswith(runtime_dirty_prefixes)


def ignorable_runtime_dirty(
    path: str,
    allowed_paths: list[str],
    *,
    runtime_dirty_prefixes: tuple[str, ...],
    task_writable_sdd_exact: set[str],
) -> bool:
    if path in task_writable_sdd_exact and covered(path, allowed_paths):
        return False
    return runtime_dirty(path, runtime_dirty_prefixes)


def is_protected(
    path: str,
    *,
    task_authorized: bool,
    protected_exact: set[str],
    task_writable_sdd_exact: set[str],
) -> bool:
    if path in protected_exact:
        return True
    if path.startswith("docs/handoff/"):
        return True
    if path.startswith(".sdd/"):
        return not (task_authorized and path in task_writable_sdd_exact)
    return False
