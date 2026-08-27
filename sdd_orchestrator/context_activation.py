from __future__ import annotations

import os
from collections.abc import Mapping

from .context_compiler import CompilationMode
from .core import SDDOrchestratorError


CONTEXT_COMPILATION_MODE_ENV = "SDD_CONTEXT_COMPILATION_MODE"


class ContextCompilationModeConfigError(SDDOrchestratorError, ValueError):
    pass


def resolve_context_compilation_mode(
    environment: Mapping[str, str] | None = None,
) -> CompilationMode:
    """Resolve the sole public context-compilation activation setting."""
    source = os.environ if environment is None else environment
    value = source.get(CONTEXT_COMPILATION_MODE_ENV)
    if value is None or value == "BASELINE":
        return CompilationMode.BASELINE
    if value == "OPTIMIZED":
        return CompilationMode.OPTIMIZED
    raise ContextCompilationModeConfigError(
        f"Invalid {CONTEXT_COMPILATION_MODE_ENV} value {value!r}; "
        "accepted values are BASELINE and OPTIMIZED"
    )
