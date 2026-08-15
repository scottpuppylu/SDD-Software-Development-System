from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Protocol
import json
import shlex
import subprocess


@dataclass
class StageExecutionRequest:
    stage_id: str
    stage_name: str
    stage_type: str
    core_question: str | None
    contract: dict[str, Any]
    artifacts: dict[str, str]
    semantic_inputs: dict[str, Any] = field(default_factory=dict)
    runtime_inputs: dict[str, Any] = field(default_factory=dict)
    stage_instructions: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StageExecutionResult:
    status: str
    artifacts: dict[str, str] = field(default_factory=dict)
    result: str | None = None
    classification: str | None = None
    remediation_reasons: list[str] = field(default_factory=list)
    convergence_tasks: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageExecutionResult":
        return cls(
            status=data.get("status", "COMPLETED"),
            artifacts=dict(data.get("artifacts", {})),
            result=data.get("result"),
            classification=data.get("classification"),
            remediation_reasons=list(data.get("remediation_reasons", [])),
            convergence_tasks=list(data.get("convergence_tasks", [])),
            metadata=dict(data.get("metadata", {})),
        )


class StageExecutor(Protocol):
    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        ...


class ExternalCommandExecutor:
    """Adapter for a future LLM/OpenClaw/Codex executor.

    The request is sent as JSON to stdin. The command must return exactly one
    JSON object on stdout matching StageExecutionResult.
    """

    def __init__(self, command: list[str] | str, *, timeout_seconds: int = 600):
        self.command = shlex.split(command) if isinstance(command, str) else command
        self.timeout_seconds = timeout_seconds

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        proc = subprocess.run(
            self.command,
            input=json.dumps(request.to_dict(), ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Stage executor failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Stage executor did not return valid JSON") from exc
        return StageExecutionResult.from_dict(data)


class StaticExecutor:
    """Deterministic executor used by tests and smoke tests."""

    def __init__(self, result: StageExecutionResult):
        self.result = result
        self.last_request: StageExecutionRequest | None = None

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        self.last_request = request
        return self.result
