from __future__ import annotations

from .core import SDDOrchestratorError


class CodexAdapterError(SDDOrchestratorError):
    pass


class NoExecutableTaskError(CodexAdapterError):
    pass
