"""Exact text and JSON measurement helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from typing import Any

from ..errors import CodexAdapterError
from uuid import UUID, uuid4, uuid5

from .models import (
    Availability,
    CANONICALIZATION_ID,
    Component,
    ContentMetric,
    EventType,
    Layer,
    MeasurementEvent,
    OutcomeCategory,
    Quality,
    Usage,
    UsageSource,
    STAGE08_PHASE_SCHEMA_VERSION,
)


_STAGE08_PHASE_EVENT_NAMESPACE = UUID("80f199d0-e8db-4d53-a17b-85b399a32daa")


@dataclass(frozen=True)
class TextMeasurement:
    chars: int
    utf8_bytes: int
    sha256: str
    canonicalization_id: str = CANONICALIZATION_ID


def measure_text(text: str) -> TextMeasurement:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    encoded = text.encode("utf-8")
    return TextMeasurement(
        chars=len(text),
        utf8_bytes=len(encoded),
        sha256=hashlib.sha256(encoded).hexdigest(),
    )


def measure_provider_call(
    *,
    stage_id: str | None,
    rendered: list[tuple[str, Component]],
    wire: bytes | None,
    outcome_category: OutcomeCategory,
    metadata: dict[str, Any],
    provider_usage: Usage | None = None,
) -> MeasurementEvent:
    """Build a provider-call observation, optionally with actual provider usage."""
    unavailable_sources = {
        "openai": UsageSource.OPENAI_RESPONSES_UNAVAILABLE,
        "codex": UsageSource.CODEX_CLI_UNAVAILABLE,
    }
    provider = metadata.get("provider")
    try:
        usage_source = unavailable_sources[provider]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown provider identity: {provider!r}") from exc
    compatible_sources = {
        "openai": {
            UsageSource.OPENAI_RESPONSES_USAGE,
            UsageSource.OPENAI_RESPONSES_UNAVAILABLE,
        },
        "codex": {UsageSource.CODEX_CLI_UNAVAILABLE},
    }
    if (
        provider_usage is not None
        and provider_usage.usage_source not in compatible_sources[provider]
    ):
        raise ValueError(
            f"usage provenance is incompatible with provider identity: {provider!r}"
        )

    metrics: list[ContentMetric] = []
    for text, component in rendered:
        measured = measure_text(text)
        metrics.append(
            ContentMetric(
                classification=component,
                classification_reason=None,
                layer=Layer.RENDERED,
                chars=measured.chars,
                utf8_bytes=measured.utf8_bytes,
                sha256=measured.sha256,
                canonicalization_id=measured.canonicalization_id,
                source_count=1,
                source_paths=None,
                truncated=False,
                omitted_items=0,
            )
        )
    if wire is not None:
        wire_text = wire.decode("utf-8")
        measured_wire = measure_text(wire_text)
        metrics.append(
            ContentMetric(
                classification=Component.OTHER,
                classification_reason="provider request payload",
                layer=Layer.WIRE,
                chars=measured_wire.chars,
                utf8_bytes=measured_wire.utf8_bytes,
                sha256=measured_wire.sha256,
                canonicalization_id=measured_wire.canonicalization_id,
                source_count=1,
                source_paths=None,
                truncated=False,
                omitted_items=0,
            )
        )
    return MeasurementEvent(
        event_type=EventType.PROVIDER_CALL,
        event_id=str(uuid4()),
        observed_at=datetime.now(timezone.utc).isoformat(),
        stage_id=stage_id,
        run_id=None,
        outcome_category=outcome_category,
        metrics=metrics,
        usage=provider_usage
        if provider_usage is not None
        else Usage(
            availability=Availability.UNAVAILABLE,
            quality=Quality.UNAVAILABLE,
            usage_source=usage_source,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            component_tokens=None,
        ),
        metadata=metadata,
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _content_metric(
    value: Any,
    classification: Component,
    *,
    classification_reason: str | None = None,
) -> ContentMetric:
    if isinstance(value, str):
        measured = measure_text(value)
    else:
        canonical = canonical_json_bytes(value).decode("utf-8")
        measured = measure_text(canonical)
    return ContentMetric(
        classification=classification,
        classification_reason=classification_reason,
        layer=Layer.REQUEST,
        chars=measured.chars,
        utf8_bytes=measured.utf8_bytes,
        sha256=measured.sha256,
        canonicalization_id=measured.canonicalization_id,
        source_count=1,
        source_paths=None,
        truncated=False,
        omitted_items=0,
    )


_RUNTIME_COMPONENTS = {
    "GIT_STATUS": Component.OPERATIONAL_STATE,
    "CURRENT_BRANCH": Component.OPERATIONAL_STATE,
    "RELEASE_GIT_IDENTITY": Component.OPERATIONAL_STATE,
    "STAGE10_CONTEXT_POLICY": Component.OPERATIONAL_STATE,
    "REPOSITORY_STRUCTURE": Component.REPO_STRUCTURE,
    "SOURCE_CODE": Component.CODE,
    "TEST_EVIDENCE": Component.TESTS,
    "BUILD_LINT_TYPECHECK_EVIDENCE_IF_APPLICABLE": Component.EVIDENCE,
    "GIT_HISTORY": Component.HISTORY,
}


def _runtime_component(key: str) -> tuple[Component, str | None]:
    component = _RUNTIME_COMPONENTS.get(key)
    if component is not None:
        return component, None
    return Component.OTHER, f"unrecognized runtime input role: {key}"


def measure_stage_request(request: Any) -> MeasurementEvent:
    """Measure only the content already carried by a stage request."""
    request_dict = request.to_dict()
    canonical_request = canonical_json_bytes(request_dict)
    metrics: list[ContentMetric] = []

    metrics.append(_content_metric(request.contract, Component.STAGE_CONTRACT))
    if request.stage_instructions is not None:
        metrics.append(
            _content_metric(request.stage_instructions, Component.STAGE_INSTRUCTION)
        )

    for path in sorted(request.artifacts):
        component = (
            Component.GOVERNANCE
            if path.replace("\\", "/").split("/")[-1].upper() == "AGENTS.MD"
            else Component.AUTHORITY_ARTIFACTS
        )
        metrics.append(_content_metric(request.artifacts[path], component))

    for key in sorted(request.semantic_inputs):
        metrics.append(_content_metric(request.semantic_inputs[key], Component.USER_INPUT))

    for key in sorted(request.runtime_inputs):
        component, reason = _runtime_component(key)
        value = request.runtime_inputs[key]
        if component in {Component.CODE, Component.TESTS} and isinstance(value, dict):
            for item_key in sorted(value):
                metrics.append(
                    _content_metric(
                        value[item_key], component, classification_reason=reason
                    )
                )
        else:
            metrics.append(
                _content_metric(value, component, classification_reason=reason)
            )

    return MeasurementEvent(
        event_type=EventType.STAGE_REQUEST,
        event_id=str(uuid4()),
        observed_at=datetime.now(timezone.utc).isoformat(),
        stage_id=request.stage_id,
        run_id=None,
        outcome_category=None,
        metrics=metrics,
        usage=None,
        metadata={
            "request_chars": len(canonical_request.decode("utf-8")),
            "request_utf8_bytes": len(canonical_request),
            "request_sha256": hashlib.sha256(canonical_request).hexdigest(),
        },
    )


def measure_stage08_task(
    *,
    task_id: str,
    task_contract: str | None,
    result: Any,
    run_id: str | None,
) -> MeasurementEvent | None:
    """Build a metadata-only observation for a returned Stage 08 task result."""
    outcomes = {
        "DONE": OutcomeCategory.COMPLETED,
        "CODEX_FAILED": OutcomeCategory.FAILED,
        "NO_CHANGES": OutcomeCategory.FAILED,
        "VERIFICATION_FAILED": OutcomeCategory.FAILED,
    }
    outcome = outcomes.get(result.status)
    if outcome is None:
        return None

    metrics = (
        [_content_metric(task_contract, Component.STAGE_CONTRACT)]
        if task_contract is not None
        else []
    )
    return MeasurementEvent(
        event_type=EventType.STAGE08_TASK,
        event_id=str(uuid4()),
        observed_at=datetime.now(timezone.utc).isoformat(),
        stage_id="08",
        run_id=run_id,
        outcome_category=outcome,
        metrics=metrics,
        usage=None,
        metadata={
            "task_id": task_id,
            "terminal_status": result.status,
            "verification_count": len(result.verification),
            "changed_path_count": len(result.changed_paths),
            "checkpoint_created": result.checkpoint_commit is not None,
        },
    )


def measure_stage08_task_exception(
    *,
    task_id: str,
    task_contract: str | None,
    exception: BaseException | None,
    run_id: str | None,
) -> MeasurementEvent:
    """Build the closed terminal observation for a started attempt that raised."""
    if isinstance(exception, (TimeoutError, subprocess.TimeoutExpired)):
        outcome = OutcomeCategory.TIMEOUT
    elif isinstance(exception, CodexAdapterError):
        outcome = OutcomeCategory.BLOCKED
    else:
        outcome = OutcomeCategory.FAILED

    metrics = (
        [_content_metric(task_contract, Component.STAGE_CONTRACT)]
        if task_contract is not None
        else []
    )
    return MeasurementEvent(
        event_type=EventType.STAGE08_TASK,
        event_id=str(uuid4()),
        observed_at=datetime.now(timezone.utc).isoformat(),
        stage_id="08",
        run_id=run_id,
        outcome_category=outcome,
        metrics=metrics,
        usage=None,
        metadata={
            "task_id": task_id,
            "terminal_status": None,
            "verification_count": 0,
            "changed_path_count": 0,
            "checkpoint_created": False,
        },
    )


def _utc_timestamp(value: str) -> datetime:
    normalized = value.replace("z", "Z")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Stage08 phase timestamps require UTC offsets")
    return parsed.astimezone(timezone.utc)


def _elapsed_ms(start: datetime, end: datetime) -> int:
    return max(0, round((end - start).total_seconds() * 1000))


def measure_stage08_phase_events(
    *, task_id: str, journal: dict[str, Any]
) -> list[MeasurementEvent]:
    """Project a TASK-027 journal into deterministic observational events.

    Values are cumulative per attempt. Consumers deduplicate by deterministic
    event_id/phase_event_digest and select the greatest sequence, so replaying a
    reconstructed journal never adds completed work a second time.
    """
    if not isinstance(journal, dict) or not isinstance(journal.get("binding"), dict):
        raise ValueError("Stage08 phase telemetry requires a governed journal")
    attempt_id = journal["binding"].get("attempt_id")
    journal_task_id = journal["binding"].get("task_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise ValueError("Stage08 phase telemetry requires attempt identity")
    if journal_task_id != task_id:
        raise ValueError("Stage08 phase telemetry task identity mismatch")
    raw_events = journal.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("Stage08 phase telemetry requires event history")

    seen_digests: set[str] = set()
    provider_invocations: set[str] = set()
    emitted: list[MeasurementEvent] = []
    first_at: datetime | None = None
    previous_at: datetime | None = None
    previous_phase: str | None = None
    codex_ms = 0
    fast_ms = 0
    target_ms = 0
    full_ms = 0
    remediation_count = 0
    resume_count = 0
    verification_reused = False

    for expected_sequence, raw in enumerate(raw_events, start=1):
        if not isinstance(raw, dict):
            raise ValueError("Stage08 phase telemetry event must be an object")
        sequence = raw.get("sequence")
        digest = raw.get("event_digest")
        if sequence != expected_sequence:
            raise ValueError("Stage08 phase telemetry requires contiguous sequence")
        if not isinstance(digest, str) or len(digest) != 64 or digest in seen_digests:
            raise ValueError("Stage08 phase telemetry requires unique event digests")
        seen_digests.add(digest)
        observed_at = raw.get("recorded_at")
        if not isinstance(observed_at, str):
            raise ValueError("Stage08 phase telemetry requires recorded_at")
        current_at = _utc_timestamp(observed_at)
        if previous_at is not None and current_at < previous_at:
            raise ValueError("Stage08 phase telemetry timestamps must be monotonic")
        first_at = current_at if first_at is None else first_at

        event_kind = str(raw.get("event_type", ""))
        phase = raw.get("phase")
        details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
        provider_id = raw.get("provider_invocation_id")
        if isinstance(provider_id, str) and provider_id:
            provider_invocations.add(provider_id)
        if event_kind == "RESUME":
            resume_count += 1
        if phase == "REMEDIATION_REQUIRED":
            remediation_count += 1
        verification_reused = verification_reused or details.get("reused") is True

        interval_ms = 0 if previous_at is None else _elapsed_ms(previous_at, current_at)
        if phase == "CODEX_PATCH_COMPLETE" and previous_phase in {
            "CONTEXT_READY", "REMEDIATION_REQUIRED",
        }:
            codex_ms += interval_ms
        elif phase == "FAST_VERIFY_COMPLETE" and details.get("reused") is not True:
            fast_ms += interval_ms
        elif phase == "TARGET_VERIFY_COMPLETE" and details.get("reused") is not True:
            target_ms += interval_ms
        elif phase == "FINAL_VERIFY_COMPLETE" and details.get("reused") is not True:
            levels = {
                item.get("level")
                for item in raw.get("verification", [])
                if isinstance(item, dict)
            }
            if "FULL" in levels:
                full_ms += interval_ms

        total_ms = _elapsed_ms(first_at, current_at)
        local_ms = fast_ms + target_ms + full_ms
        ratio = round(codex_ms / total_ms, 9) if total_ms > 0 else None
        metadata = {
            "phase_schema_version": STAGE08_PHASE_SCHEMA_VERSION,
            "attempt_id": attempt_id,
            "task_id": task_id,
            "event_kind": event_kind,
            "phase": phase,
            "sequence": sequence,
            "phase_event_digest": digest,
            "codex_invocation_count": len(provider_invocations),
            "codex_active_duration_ms": codex_ms,
            "local_verification_duration_ms": local_ms,
            "fast_verify_duration_ms": fast_ms,
            "target_verify_duration_ms": target_ms,
            "full_verify_duration_ms": full_ms,
            "remediation_count": remediation_count,
            "resume_count": resume_count,
            "total_stage8_duration_ms": total_ms,
            "codex_active_time_ratio": ratio,
            "verification_reused": verification_reused,
        }
        outcome = (
            OutcomeCategory.BLOCKED
            if event_kind == "SAFE_PAUSE"
            else OutcomeCategory.COMPLETED
        )
        emitted.append(MeasurementEvent(
            event_type=EventType.STAGE08_PHASE,
            event_id=str(uuid5(_STAGE08_PHASE_EVENT_NAMESPACE, f"{attempt_id}:{digest}")),
            observed_at=observed_at,
            stage_id="08",
            run_id=attempt_id,
            outcome_category=outcome,
            metrics=[],
            usage=None,
            metadata=metadata,
        ))
        previous_at = current_at
        if phase is not None:
            previous_phase = phase
    return emitted
