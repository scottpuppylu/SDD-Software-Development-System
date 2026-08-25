from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .executor import StageExecutionRequest, StageExecutionResult
from .telemetry.measurement import measure_provider_call
from .telemetry.models import (
    Availability,
    Component,
    OutcomeCategory,
    Quality,
    Usage,
    UsageSource,
)


class ReasoningProviderError(RuntimeError):
    pass


def _allowed_output_paths(request: StageExecutionRequest) -> list[str]:
    paths = list(request.contract.get("outputs", {}).get("files", []) or [])
    # Optional output globs cannot be represented safely as arbitrary paths in a
    # strict JSON schema. They remain available through the external-command
    # executor and can be added to provider-specific adapters later.
    return paths


def _result_schema(request: StageExecutionRequest) -> dict[str, Any]:
    paths = _allowed_output_paths(request)
    result_vocab = request.contract.get("result_vocabulary", []) or []

    result_schema: dict[str, Any]
    if result_vocab:
        result_schema = {"type": ["string", "null"], "enum": [*result_vocab, None]}
    else:
        result_schema = {"type": ["string", "null"]}

    # Only Stage 09 owns implementation-gap / authority-conflict classification.
    # Other stages must keep classification null and describe blockers through
    # the stage report + remediation_reasons. This prevents Stage 07 readiness
    # failures from being mislabeled as Stage 09 IMPLEMENTATION_GAP.
    classification_values = (
        ["IMPLEMENTATION_GAP", "AUTHORITY_CONTRACT_CONFLICT", None]
        if request.stage_id == "09"
        else [None]
    )

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["COMPLETED", "BLOCKED"]},
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "enum": paths or ["__NO_OUTPUT__"]},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
            "result": result_schema,
            "classification": {
                "type": ["string", "null"],
                "enum": classification_values,
            },
            "remediation_reasons": {
                "type": "array",
                "items": {"type": "string"},
            },
            "provider_notes": {"type": ["string", "null"]},
        },
        "required": [
            "status",
            "artifacts",
            "result",
            "classification",
            "remediation_reasons",
            "provider_notes",
        ],
        "additionalProperties": False,
    }

    if request.stage_id == "09":
        schema["properties"]["convergence_tasks"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                    "traceability": {"type": "array", "items": {"type": "string"}},
                    "allowed_paths": {"type": "array", "items": {"type": "string"}},
                    "verification_commands": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "task_id",
                    "title",
                    "objective",
                    "traceability",
                    "allowed_paths",
                    "verification_commands",
                ],
                "additionalProperties": False,
            },
        }
        schema["required"].append("convergence_tasks")

    return schema


def _provider_system_instructions(request: StageExecutionRequest) -> str:
    base = """You are a governed SDD stage executor inside a repository-first software development system.

You MUST follow the stage contract and authority boundaries supplied in the request. Never use linear document priority such as PRD > Spec > Design. Resolve authority by domain. If authoritative artifacts conflict, do not choose a winner or invent a workaround: report BLOCKED and provide remediation reasons. Do not claim to have run repository commands unless runtime evidence is present in the request.

Return only the structured result required by the response schema. Artifact content must be complete file content, not commentary around the file. Do not emit files outside the declared output paths.
"""
    if request.stage_instructions:
        base += "\nSTAGE-SPECIFIC INSTRUCTIONS:\n" + request.stage_instructions
    else:
        base += (
            "\nNo separate stage instruction file is installed. Treat the machine-readable "
            "stage contract in the request as binding and do not expand authority beyond it."
        )
    return base


def _provider_user_input(request: StageExecutionRequest) -> str:
    payload = request.to_dict()
    return (
        "Execute this SDD stage using only the supplied authoritative context. "
        "Preserve traceability and mark unresolved critical uncertainty as blocked/TBD rather than guessing.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    for item in response.get("output", []) or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    raise ReasoningProviderError("OpenAI response did not contain output text")


def _non_negative_int(value: Any) -> int | None:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )


def _openai_response_usage(payload: Any) -> Usage | None:
    if not isinstance(payload, dict):
        return None
    raw_usage = payload.get("usage")
    if not isinstance(raw_usage, dict):
        return None

    input_tokens = _non_negative_int(raw_usage.get("input_tokens"))
    output_tokens = _non_negative_int(raw_usage.get("output_tokens"))
    total_tokens = _non_negative_int(raw_usage.get("total_tokens"))
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    input_details = raw_usage.get("input_tokens_details")
    output_details = raw_usage.get("output_tokens_details")
    cached_input_tokens = (
        _non_negative_int(input_details.get("cached_tokens"))
        if isinstance(input_details, dict)
        else None
    )
    reasoning_output_tokens = (
        _non_negative_int(output_details.get("reasoning_tokens"))
        if isinstance(output_details, dict)
        else None
    )
    return Usage(
        availability=Availability.AVAILABLE,
        quality=Quality.ACTUAL,
        usage_source=UsageSource.OPENAI_RESPONSES_USAGE,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        component_tokens={
            "cached_input_tokens": cached_input_tokens,
            "reasoning_output_tokens": reasoning_output_tokens,
        },
    )

class CodexExecReasoningExecutor:
    """Default reasoning adapter using Codex CLI with saved ChatGPT authentication.

    Reasoning stages run in a read-only sandbox. The SDD Orchestrator, not Codex,
    writes validated artifacts into the repository. This keeps Stage authority and
    write scope deterministic while avoiding a required OpenAI API key.
    """

    def __init__(
        self,
        *,
        executable: str = "codex",
        model: str | None = None,
        timeout_seconds: int = 1800,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
        repo_root: str | Path | None = None,
        telemetry_recorder=None,
    ):
        self.executable = executable
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.ephemeral = ephemeral
        self.ignore_user_config = ignore_user_config
        self.repo_root = Path(repo_root).resolve() if repo_root is not None else Path.cwd()
        self.telemetry_recorder = telemetry_recorder

    def resolved_executable(self) -> str | None:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        if os.name == "nt" and not self.executable.lower().endswith((".cmd", ".exe", ".bat")):
            return shutil.which(self.executable + ".cmd")
        return None

    def available(self) -> bool:
        return self.resolved_executable() is not None

    def command(self, schema_path: Path, output_path: Path, *, executable: str | None = None) -> list[str]:
        cmd = [
            executable or self.executable,
            "exec",
            "--sandbox",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
        ]
        if self.ephemeral:
            cmd.append("--ephemeral")
        if self.ignore_user_config:
            cmd.append("--ignore-user-config")
        if self.model:
            cmd.extend(["--model", self.model])
        # Read the complete generated prompt from stdin. This avoids command-line
        # length limits for large PRD/Spec/Design packets.
        cmd.append("-")
        return cmd

    def build_prompt(self, request: StageExecutionRequest) -> str:
        return _provider_system_instructions(request) + "\n\n" + _provider_user_input(request)

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        executable = self.resolved_executable()
        if not executable:
            raise ReasoningProviderError(
                "Codex CLI is not installed or not on PATH. Install Codex and run `codex login` with ChatGPT before using the default reasoning provider."
            )

        schema = _result_schema(request)
        prompt = self.build_prompt(request)
        with tempfile.TemporaryDirectory(prefix=f"sdd-stage-{request.stage_id}-") as tmp:
            tmpdir = Path(tmp)
            schema_path = tmpdir / "result.schema.json"
            output_path = tmpdir / "result.json"
            schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

            started = time.monotonic()
            outcome = OutcomeCategory.FAILED
            try:
                proc = subprocess.run(
                    self.command(schema_path, output_path, executable=executable),
                    input=prompt,
                    text=True,
                    encoding="utf-8",
                    errors="strict",
                    capture_output=True,
                    cwd=self.repo_root,
                    timeout=self.timeout_seconds,
                )
                if proc.returncode == 0:
                    outcome = OutcomeCategory.COMPLETED
            except (subprocess.TimeoutExpired, TimeoutError):
                outcome = OutcomeCategory.TIMEOUT
                raise
            finally:
                if self.telemetry_recorder is not None:
                    try:
                        duration_ms = max(0, round((time.monotonic() - started) * 1000))
                        event = measure_provider_call(
                            stage_id=request.stage_id,
                            rendered=[(prompt, Component.USER_INPUT)],
                            wire=None,
                            outcome_category=outcome,
                            metadata={
                                "provider": "codex",
                                "model": self.model or "codex-config-default",
                                "adapter": "codex_exec_reasoning",
                                "interface": "subprocess_stdin",
                                "duration_ms": duration_ms,
                            },
                        )
                        self.telemetry_recorder.record(event)
                    except Exception:
                        pass
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                if len(detail) > 6000:
                    detail = detail[:2500] + "\n... [middle truncated] ...\n" + detail[-3500:]
                raise ReasoningProviderError(
                    f"Codex reasoning execution failed ({proc.returncode}): {detail}"
                )
            if not output_path.exists():
                raise ReasoningProviderError(
                    "Codex did not write the expected --output-last-message file"
                )
            raw = output_path.read_text(encoding="utf-8").strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ReasoningProviderError(
                    "Codex structured final response was not valid JSON"
                ) from exc

        artifact_list = data.get("artifacts", []) or []
        artifacts = {
            item["path"]: item["content"]
            for item in artifact_list
            if item.get("path") != "__NO_OUTPUT__"
        }
        return StageExecutionResult(
            status=data["status"],
            artifacts=artifacts,
            result=data.get("result"),
            classification=data.get("classification"),
            remediation_reasons=list(data.get("remediation_reasons", [])),
            convergence_tasks=list(data.get("convergence_tasks", [])),
            metadata={
                "provider": "codex_exec_reasoning",
                "model": self.model or "codex-config-default",
                "sandbox": "read-only",
                "ephemeral": self.ephemeral,
                "provider_notes": data.get("provider_notes"),
            },
        )


class OpenAIResponsesExecutor:
    """Reasoning adapter using OpenAI's Responses API with Structured Outputs.

    This adapter intentionally uses the HTTP API directly so the core package
    does not require an SDK dependency. The API key is read from the environment
    and is never persisted into SDD run packets.
    """

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        *,
        model: str = "gpt-5.6",
        api_key: str | None = None,
        timeout_seconds: int = 300,
        max_output_tokens: int = 12000,
        telemetry_recorder=None,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.telemetry_recorder = telemetry_recorder
        if not self.api_key:
            raise ReasoningProviderError(
                "OPENAI_API_KEY is not set. Configure it in the environment; do not store it in repository files."
            )

    def execute(self, request: StageExecutionRequest) -> StageExecutionResult:
        schema = _result_schema(request)
        body = {
            "model": self.model,
            "instructions": _provider_system_instructions(request),
            "input": _provider_user_input(request),
            "max_output_tokens": self.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"sdd_stage_{request.stage_id}_result",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        wire = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=wire,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        outcome = OutcomeCategory.FAILED
        provider_usage = None
        try:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                try:
                    provider_usage = _openai_response_usage(payload)
                except Exception:
                    provider_usage = None
                outcome = OutcomeCategory.COMPLETED
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise ReasoningProviderError(
                    f"OpenAI Responses API returned HTTP {exc.code}: {detail[:2000]}"
                ) from exc
            except urllib.error.URLError as exc:
                if isinstance(exc.reason, TimeoutError):
                    outcome = OutcomeCategory.TIMEOUT
                raise ReasoningProviderError(f"OpenAI Responses API request failed: {exc}") from exc
            except (TimeoutError, subprocess.TimeoutExpired):
                outcome = OutcomeCategory.TIMEOUT
                raise
        finally:
            if self.telemetry_recorder is not None:
                try:
                    duration_ms = max(0, round((time.monotonic() - started) * 1000))
                    event = measure_provider_call(
                        stage_id=request.stage_id,
                        rendered=[
                            (body["instructions"], Component.STAGE_INSTRUCTION),
                            (body["input"], Component.USER_INPUT),
                        ],
                        wire=wire,
                        outcome_category=outcome,
                        provider_usage=provider_usage,
                        metadata={
                            "provider": "openai",
                            "model": self.model,
                            "adapter": "openai_responses",
                            "interface": "https",
                            "duration_ms": duration_ms,
                        },
                    )
                    self.telemetry_recorder.record(event)
                except Exception:
                    pass

        text = _extract_output_text(payload)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReasoningProviderError(
                "Structured response was not valid JSON"
            ) from exc

        artifact_list = data.get("artifacts", []) or []
        artifacts = {
            item["path"]: item["content"]
            for item in artifact_list
            if item.get("path") != "__NO_OUTPUT__"
        }
        return StageExecutionResult(
            status=data["status"],
            artifacts=artifacts,
            result=data.get("result"),
            classification=data.get("classification"),
            remediation_reasons=list(data.get("remediation_reasons", [])),
            convergence_tasks=list(data.get("convergence_tasks", [])),
            metadata={
                "provider": "openai_responses",
                "model": self.model,
                "response_id": payload.get("id"),
                "provider_notes": data.get("provider_notes"),
            },
        )
