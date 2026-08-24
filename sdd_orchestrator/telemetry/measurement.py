"""Exact text and JSON measurement helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

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
)


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
    wire: bytes,
    outcome_category: OutcomeCategory,
    metadata: dict[str, Any],
) -> MeasurementEvent:
    """Build a metadata-only M1.3 provider-call observation."""
    unavailable_sources = {
        "openai": UsageSource.OPENAI_RESPONSES_UNAVAILABLE,
        "codex": UsageSource.CODEX_CLI_UNAVAILABLE,
    }
    provider = metadata.get("provider")
    try:
        usage_source = unavailable_sources[provider]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown provider identity: {provider!r}") from exc

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
        usage=Usage(
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
