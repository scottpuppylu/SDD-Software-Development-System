from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import time
from uuid import uuid4
from dataclasses import dataclass

from .errors import CodexAdapterError
from .codex_results import CodexOutcome, normalize_codex_outcome
from .telemetry.measurement import measure_provider_call
from .telemetry.models import Component, OutcomeCategory
from .resource_policy import (
    MeasurementTruth,
    ResourceController,
    ResourceDimension,
    ResourceMeasurement,
    ResourceObservation,
    ResourcePolicyError,
    ResourceRequest,
)


@dataclass(frozen=True)
class NormalizedCodexExecution:
    outcome: CodexOutcome
    process: subprocess.CompletedProcess[str] | None
    exception_type: str | None = None


class CodexCLI:
    def __init__(
        self,
        *,
        executable: str = "codex",
        sandbox: str = "workspace-write",
        approval_policy: str = "never",
        timeout_seconds: int = 1800,
        ephemeral: bool = True,
        telemetry_recorder=None,
        resource_controller: ResourceController | None = None,
    ):
        self.executable = executable
        self.sandbox = sandbox
        self.approval_policy = approval_policy
        self.timeout_seconds = timeout_seconds
        self.ephemeral = ephemeral
        self.telemetry_recorder = telemetry_recorder
        self.resource_controller = resource_controller

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

    def _reserve(self, prompt: str, dispatch_id: str) -> None:
        controller = self.resource_controller
        if controller is None:
            return
        known = {
            ResourceDimension.PROVIDER_CALLS: 1,
            ResourceDimension.RUNTIME_MS: self.timeout_seconds * 1000,
            ResourceDimension.PROCESS_COUNT: 1,
            ResourceDimension.CONTEXT_BYTES: len(prompt.encode("utf-8")),
        }
        missing = set(controller.policy.required_dimensions) - set(known)
        if missing:
            raise ResourcePolicyError(
                "UNKNOWN_REQUIRED_BUDGET",
                "BUDGET_POLICY_OWNER",
                ",".join(sorted(item.value for item in missing)),
            )
        controller.reserve(
            ResourceRequest(
                dispatch_id=dispatch_id,
                provider="codex",
                model="codex-config-default",
                runtime="codex_cli",
                scope=controller.policy.scope,
                reservation={
                    item: value
                    for item, value in known.items()
                    if item in controller.policy.by_dimension
                },
            )
        )

    def _settle(self, dispatch_id: str, prompt: str, duration_ms: int, outcome: OutcomeCategory) -> None:
        controller = self.resource_controller
        if controller is None:
            return
        measurements = [
            ResourceMeasurement(
                ResourceDimension.PROVIDER_CALLS, 1, MeasurementTruth.ACTUAL,
                "runtime_meter", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.RUNTIME_MS, duration_ms, MeasurementTruth.ACTUAL,
                "runtime_meter", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.PROCESS_COUNT, 1, MeasurementTruth.ACTUAL,
                "runtime_meter", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.CONTEXT_BYTES, len(prompt.encode("utf-8")),
                MeasurementTruth.CONTEXT_SIZE, "utf8_measurement", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.ACTUAL_TOKENS, None, MeasurementTruth.UNAVAILABLE,
                "codex_cli_unavailable", dispatch_id,
            ),
            ResourceMeasurement(
                ResourceDimension.ACTUAL_COST_USD, None, MeasurementTruth.UNAVAILABLE,
                "codex_cli_unavailable", dispatch_id,
            ),
        ]
        controller.settle(
            ResourceObservation(
                dispatch_id=dispatch_id,
                measurements=tuple(
                    item for item in measurements
                    if item.dimension in controller.policy.by_dimension
                ),
                outcome=outcome.value,
                evidence_reference=f"codex-cli-dispatch:{dispatch_id}",
            )
        )

    def execute(
        self, repo_root: Path, prompt: str, *, resource_dispatch_id: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        executable = self.resolved_executable()
        if not executable:
            raise CodexAdapterError(
                "Codex CLI is not installed or not on PATH. Install/authenticate Codex before Stage 08 execution."
            )
        dispatch_id = resource_dispatch_id or f"codex-cli:{uuid4()}"
        self._reserve(prompt, dispatch_id)
        started = time.monotonic()
        outcome = OutcomeCategory.FAILED
        try:
            result = subprocess.run(
                self.command(prompt, executable=executable),
                cwd=repo_root,
                input=prompt,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.timeout_seconds,
            )
            if result.returncode == 0:
                outcome = OutcomeCategory.COMPLETED
            return result
        except (subprocess.TimeoutExpired, TimeoutError):
            outcome = OutcomeCategory.TIMEOUT
            raise
        finally:
            duration_ms = max(0, round((time.monotonic() - started) * 1000))
            self._settle(dispatch_id, prompt, duration_ms, outcome)
            if self.telemetry_recorder is not None:
                try:
                    event = measure_provider_call(
                        stage_id="08",
                        rendered=[(prompt, Component.USER_INPUT)],
                        wire=None,
                        outcome_category=outcome,
                        metadata={
                            "provider": "codex",
                            "model": "codex-config-default",
                            "adapter": "codex_stage08",
                            "interface": "subprocess_stdin",
                            "duration_ms": duration_ms,
                        },
                    )
                    self.telemetry_recorder.record(event)
                except Exception:
                    pass

    def execute_normalized(self, repo_root: Path, prompt: str) -> NormalizedCodexExecution:
        """Return interruption identity without deciding whether pausing is safe."""
        try:
            process = self.execute(repo_root, prompt)
        except (subprocess.TimeoutExpired, TimeoutError, KeyboardInterrupt, InterruptedError) as exc:
            return NormalizedCodexExecution(
                normalize_codex_outcome(exception=exc), None, type(exc).__name__
            )
        return NormalizedCodexExecution(
            normalize_codex_outcome(
                returncode=process.returncode, stderr=process.stderr
            ),
            process,
        )
