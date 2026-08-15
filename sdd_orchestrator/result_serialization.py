from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .codex_results import CodexTaskRunResult, VerificationResult


def serialize_verification_result(result: VerificationResult) -> dict[str, Any]:
    return asdict(result) | {"passed": result.passed}


def serialize_task_run_result(result: CodexTaskRunResult) -> dict[str, Any]:
    data = asdict(result)
    data["verification"] = [
        serialize_verification_result(item) for item in result.verification
    ]
    return data
