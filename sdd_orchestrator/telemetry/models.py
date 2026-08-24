"""Frozen v1 measurement schema models."""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


SCHEMA_ID = "sdd.measurement.stage_execution"
SCHEMA_VERSION = "1.0.2"
CANONICALIZATION_ID = "sdd.canonical.utf8-sorted-compact-v1"


class EventType(str, Enum):
    STAGE_REQUEST = "stage_request"
    PROVIDER_CALL = "provider_call"
    STAGE08_TASK = "stage08_task"


class Component(str, Enum):
    GOVERNANCE = "governance"
    STAGE_INSTRUCTION = "stage_instruction"
    STAGE_CONTRACT = "stage_contract"
    AUTHORITY_ARTIFACTS = "authority_artifacts"
    OPERATIONAL_STATE = "operational_state"
    REPO_STRUCTURE = "repo_structure"
    CODE = "code"
    TESTS = "tests"
    EVIDENCE = "evidence"
    HISTORY = "history"
    USER_INPUT = "user_input"
    OTHER = "other"


class Layer(str, Enum):
    REQUEST = "request"
    SYSTEM_PROMPT = "system_prompt"
    USER_PROMPT = "user_prompt"
    RENDERED = "rendered"
    WIRE = "wire"
    TOOL_CONTEXT = "tool_context"


class Availability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Quality(str, Enum):
    ACTUAL = "actual"
    UNAVAILABLE = "unavailable"


class UsageSource(str, Enum):
    OPENAI_RESPONSES_USAGE = "openai_responses_usage"
    OPENAI_RESPONSES_UNAVAILABLE = "openai_responses_unavailable"
    CODEX_CLI_UNAVAILABLE = "codex_cli_unavailable"


class OutcomeCategory(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    TIMEOUT = "timeout"


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _non_negative_integer(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class ContentMetric:
    classification: Component
    classification_reason: str | None
    layer: Layer
    chars: int
    utf8_bytes: int
    sha256: str
    canonicalization_id: str
    source_count: int
    source_paths: list[str] | None
    truncated: bool
    omitted_items: int

    def __post_init__(self) -> None:
        try:
            classification = Component(self.classification)
            layer = Layer(self.layer)
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown component or layer") from exc
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "layer", layer)
        reason = self.classification_reason
        if classification is Component.OTHER:
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("other requires a non-empty classification_reason")
        elif reason is not None:
            raise ValueError("known components require classification_reason=None")
        for name in ("chars", "utf8_bytes", "source_count", "omitted_items"):
            _non_negative_integer(getattr(self, name), name)
        if not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        if self.canonicalization_id != CANONICALIZATION_ID:
            raise ValueError("unknown canonicalization_id")
        if not isinstance(self.truncated, bool):
            raise TypeError("truncated must be a boolean")
        if self.source_paths is not None:
            if not isinstance(self.source_paths, list) or not all(isinstance(path, str) for path in self.source_paths):
                raise TypeError("source_paths must be a list of strings or None")
            if len(self.source_paths) != self.source_count:
                raise ValueError("source_paths length must equal source_count")
            if self.source_paths != sorted(set(self.source_paths)):
                raise ValueError("source_paths must be sorted and deduplicated")

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "classification_reason": self.classification_reason,
            "layer": self.layer.value,
            "chars": self.chars,
            "utf8_bytes": self.utf8_bytes,
            "sha256": self.sha256,
            "canonicalization_id": self.canonicalization_id,
            "source_count": self.source_count,
            "source_paths": self.source_paths,
            "truncated": self.truncated,
            "omitted_items": self.omitted_items,
        }


@dataclass(frozen=True)
class Usage:
    availability: Availability
    quality: Quality
    usage_source: UsageSource
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    component_tokens: dict[str, int | None] | None

    def __post_init__(self) -> None:
        try:
            availability = Availability(self.availability)
            quality = Quality(self.quality)
            source = UsageSource(self.usage_source)
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown usage vocabulary") from exc
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "quality", quality)
        object.__setattr__(self, "usage_source", source)
        token_fields = (self.input_tokens, self.output_tokens, self.total_tokens, self.component_tokens)
        if availability is Availability.UNAVAILABLE:
            unavailable_sources = {
                UsageSource.OPENAI_RESPONSES_UNAVAILABLE,
                UsageSource.CODEX_CLI_UNAVAILABLE,
            }
            if quality is not Quality.UNAVAILABLE or source not in unavailable_sources:
                raise ValueError("unavailable usage requires unavailable quality and source")
            if any(value is not None for value in token_fields):
                raise ValueError("unavailable usage requires null token fields")
        else:
            if quality is not Quality.ACTUAL or source is not UsageSource.OPENAI_RESPONSES_USAGE:
                raise ValueError("available usage requires actual provider usage")
            if not isinstance(self.component_tokens, dict):
                raise TypeError("available usage requires component_tokens to be an object")
            expected_component_tokens = {
                "cached_input_tokens",
                "reasoning_output_tokens",
            }
            if set(self.component_tokens) != expected_component_tokens:
                raise ValueError("component_tokens must contain exactly the canonical members")
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, name)
            if value is not None:
                _non_negative_integer(value, name)
        if self.component_tokens is not None:
            if not isinstance(self.component_tokens, dict):
                raise TypeError("component_tokens must be an object or None")
            for value in self.component_tokens.values():
                if value is not None:
                    _non_negative_integer(value, "component token count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability": self.availability.value,
            "quality": self.quality.value,
            "usage_source": self.usage_source.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "component_tokens": self.component_tokens,
        }


@dataclass(frozen=True)
class MeasurementEvent:
    event_type: EventType
    event_id: str
    observed_at: str
    stage_id: str | None
    run_id: str | None
    outcome_category: OutcomeCategory | None
    metrics: list[ContentMetric]
    usage: Usage | None
    metadata: dict[str, Any]
    schema_id: str = field(default=SCHEMA_ID, init=False)
    schema_version: str = field(default=SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        try:
            event_type = EventType(self.event_type)
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown event_type") from exc
        object.__setattr__(self, "event_type", event_type)
        if event_type is EventType.PROVIDER_CALL:
            if not isinstance(self.usage, Usage):
                raise ValueError("provider_call requires Usage")
        elif self.usage is not None:
            raise ValueError(f"{event_type.value} requires usage=None")
        if self.outcome_category is not None:
            try:
                object.__setattr__(self, "outcome_category", OutcomeCategory(self.outcome_category))
            except (TypeError, ValueError) as exc:
                raise ValueError("unknown outcome_category") from exc
        if not isinstance(self.metrics, list) or not all(isinstance(metric, ContentMetric) for metric in self.metrics):
            raise TypeError("metrics must be a list of ContentMetric")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be an object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "observed_at": self.observed_at,
            "stage_id": self.stage_id,
            "run_id": self.run_id,
            "outcome_category": _enum_value(self.outcome_category),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "usage": None if self.usage is None else self.usage.to_dict(),
            "metadata": self.metadata,
        }
