from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping

import yaml


SCHEMA_VERSION = "1.0"
GENESIS_DIGEST = "0" * 64


class PhaseStateError(RuntimeError):
    """A phase journal is corrupt, stale, or outside its sealed authority."""


class Stage08Phase(str, Enum):
    PRECHECK_COMPLETE = "PRECHECK_COMPLETE"
    CONTEXT_READY = "CONTEXT_READY"
    CODEX_PATCH_COMPLETE = "CODEX_PATCH_COMPLETE"
    FAST_VERIFY_COMPLETE = "FAST_VERIFY_COMPLETE"
    TARGET_VERIFY_COMPLETE = "TARGET_VERIFY_COMPLETE"
    REMEDIATION_REQUIRED = "REMEDIATION_REQUIRED"
    FINAL_VERIFY_COMPLETE = "FINAL_VERIFY_COMPLETE"
    STAGE8_COMPLETE = "STAGE8_COMPLETE"


class InterruptionReason(str, Enum):
    CODEX_QUOTA_EXHAUSTED = "CODEX_QUOTA_EXHAUSTED"
    CODEX_INTERRUPTED = "CODEX_INTERRUPTED"
    CODEX_TIMEOUT = "CODEX_TIMEOUT"


class EventType(str, Enum):
    PHASE = "PHASE"
    SAFE_PAUSE = "SAFE_PAUSE"
    RESUME = "RESUME"


_TRANSITIONS = {
    None: {Stage08Phase.PRECHECK_COMPLETE},
    Stage08Phase.PRECHECK_COMPLETE: {Stage08Phase.CONTEXT_READY},
    Stage08Phase.CONTEXT_READY: {Stage08Phase.CODEX_PATCH_COMPLETE},
    Stage08Phase.CODEX_PATCH_COMPLETE: {Stage08Phase.FAST_VERIFY_COMPLETE},
    Stage08Phase.FAST_VERIFY_COMPLETE: {Stage08Phase.TARGET_VERIFY_COMPLETE},
    Stage08Phase.TARGET_VERIFY_COMPLETE: {
        Stage08Phase.REMEDIATION_REQUIRED,
        Stage08Phase.FINAL_VERIFY_COMPLETE,
    },
    Stage08Phase.REMEDIATION_REQUIRED: {Stage08Phase.CODEX_PATCH_COMPLETE},
    Stage08Phase.FINAL_VERIFY_COMPLETE: {Stage08Phase.STAGE8_COMPLETE},
    Stage08Phase.STAGE8_COMPLETE: set(),
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def allowed_files_sha256(paths: Iterable[str]) -> str:
    normalized = sorted(dict.fromkeys(Path(item).as_posix() for item in paths))
    if not normalized or any(
        not item or Path(item).is_absolute() or ".." in Path(item).parts
        for item in normalized
    ):
        raise PhaseStateError("allowed files are empty or unbounded")
    return canonical_sha256(normalized)


@dataclass(frozen=True)
class AttemptBinding:
    attempt_id: str
    task_id: str
    stage07_report_sha256: str
    sealed_envelope_id: str
    branch: str
    entry_head: str
    authorized_baseline: str
    task_contract_sha256: str
    authority_sha256: str
    allowed_files_sha256: str
    environment_sha256: str

    def validate(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.attempt_id):
            raise PhaseStateError("attempt identity is invalid")
        if not re.fullmatch(r"T(?:ASK-)?\d{3}|T\d{3}", self.task_id, re.IGNORECASE):
            raise PhaseStateError("task identity is invalid")
        for name in (
            "stage07_report_sha256", "sealed_envelope_id", "task_contract_sha256",
            "authority_sha256", "allowed_files_sha256", "environment_sha256",
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", getattr(self, name)):
                raise PhaseStateError(f"{name} is invalid")
        for name in ("entry_head", "authorized_baseline"):
            if not re.fullmatch(r"[0-9a-f]{40}", getattr(self, name)):
                raise PhaseStateError(f"{name} is invalid")
        if not self.branch.strip():
            raise PhaseStateError("branch is required")


@dataclass(frozen=True)
class DiffProvenance:
    attempt_id: str
    phase: str
    dirty_paths: tuple[str, ...]
    diff_sha256: str
    authorized_scope_sha256: str
    scope_overrun: bool = False
    attributable: bool = True

    def validate(self, binding: AttemptBinding) -> None:
        normalized = tuple(sorted(dict.fromkeys(Path(item).as_posix() for item in self.dirty_paths)))
        if normalized != self.dirty_paths:
            raise PhaseStateError("dirty paths are not canonical")
        if self.attempt_id != binding.attempt_id:
            raise PhaseStateError("diff belongs to another attempt")
        if self.authorized_scope_sha256 != binding.allowed_files_sha256:
            raise PhaseStateError("diff scope binding is stale")
        if not re.fullmatch(r"[0-9a-f]{64}", self.diff_sha256):
            raise PhaseStateError("diff digest is invalid")
        if self.scope_overrun or not self.attributable:
            raise PhaseStateError("dirty diff provenance is unsafe")


@dataclass(frozen=True)
class VerificationFingerprint:
    level: str
    command_sha256: str
    input_sha256: str
    environment_sha256: str
    diff_sha256: str
    authority_sha256: str
    envelope_id: str
    outcome: str

    def reusable_against(self, other: "VerificationFingerprint") -> bool:
        return self.outcome == "PASS" and self == other


@dataclass(frozen=True)
class PhaseEvent:
    sequence: int
    event_type: str
    phase: str
    previous_digest: str
    recorded_at: str
    diff_provenance: Mapping[str, Any] | None = None
    verification: tuple[Mapping[str, Any], ...] = ()
    provider_invocation_id: str | None = None
    interruption_reason: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    event_digest: str = ""

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("event_digest", None)
        value["verification"] = list(self.verification)
        return value


@dataclass(frozen=True)
class ResumeContext:
    binding: AttemptBinding
    dirty_paths: tuple[str, ...]
    diff_sha256: str
    diff_attributable: bool
    scope_overrun: bool
    unexpected_untracked: tuple[str, ...] = ()
    stage07_valid: bool = True
    envelope_valid: bool = True
    task_authority_valid: bool = True
    security_valid: bool = True
    environment_valid: bool = True
    unknown_side_effects: bool = False


@dataclass(frozen=True)
class ResumeDecision:
    status: str
    phase: str | None
    skip_codex: bool
    reusable_verification_levels: tuple[str, ...]
    reasons: tuple[str, ...]


class Stage08PhaseStore:
    """Atomic, hash-chained Stage08 attempt journal; never a qualification store."""

    def __init__(self, repo_root: Path, attempt_id: str):
        if not re.fullmatch(r"[0-9a-f]{64}", attempt_id):
            raise PhaseStateError("attempt identity is invalid")
        self.repo_root = Path(repo_root).resolve()
        self.path = self.repo_root / ".sdd" / "state" / "stage08-attempts" / f"{attempt_id}.yaml"

    @staticmethod
    def _journal_payload(binding: AttemptBinding, events: list[PhaseEvent]) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "binding": asdict(binding),
            "events": [asdict(event) for event in events],
        }

    @staticmethod
    def _event_digest(event: PhaseEvent) -> str:
        return canonical_sha256(event.payload())

    def create(self, binding: AttemptBinding) -> dict[str, Any]:
        binding.validate()
        if binding.attempt_id != self.path.stem:
            raise PhaseStateError("attempt path and binding disagree")
        if self.path.exists():
            existing = self.load()
            if existing["binding"] != asdict(binding):
                raise PhaseStateError("attempt already exists with different authority")
            return existing
        return self._persist(binding, [])

    def load(self) -> dict[str, Any]:
        if not self.path.is_file() or self.path.is_symlink():
            raise PhaseStateError("phase journal is missing or unsafe")
        try:
            value = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise PhaseStateError("phase journal cannot be decoded") from exc
        return self._validate(value)

    def append(
        self,
        *,
        event_type: EventType,
        phase: Stage08Phase | None = None,
        diff_provenance: DiffProvenance | None = None,
        verification: Iterable[VerificationFingerprint] = (),
        provider_invocation_id: str | None = None,
        interruption_reason: InterruptionReason | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self.load()
        binding = AttemptBinding(**current["binding"])
        events = [self._event_from_dict(item) for item in current["events"]]
        active_phase = self.current_phase(events)
        target = phase or active_phase
        if target is None:
            raise PhaseStateError("the first event must establish PRECHECK_COMPLETE")
        if event_type is EventType.PHASE and target not in _TRANSITIONS[active_phase]:
            raise PhaseStateError(f"illegal phase transition: {active_phase} -> {target}")
        if event_type is not EventType.PHASE and active_phase is None:
            raise PhaseStateError("pause/resume requires established phase state")
        if diff_provenance is not None:
            diff_provenance.validate(binding)
        if event_type is EventType.SAFE_PAUSE and interruption_reason is None:
            raise PhaseStateError("SAFE_PAUSE requires an interruption reason")
        if event_type is not EventType.SAFE_PAUSE and interruption_reason is not None:
            raise PhaseStateError("interruption reason is valid only for SAFE_PAUSE")
        event = PhaseEvent(
            sequence=len(events) + 1,
            event_type=event_type.value,
            phase=target.value,
            previous_digest=events[-1].event_digest if events else GENESIS_DIGEST,
            recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            diff_provenance=asdict(diff_provenance) if diff_provenance else None,
            verification=tuple(asdict(item) for item in verification),
            provider_invocation_id=provider_invocation_id,
            interruption_reason=interruption_reason.value if interruption_reason else None,
            details=dict(details or {}),
        )
        event = PhaseEvent(**(asdict(event) | {"event_digest": self._event_digest(event)}))
        events.append(event)
        return self._persist(binding, events)

    def _persist(self, binding: AttemptBinding, events: list[PhaseEvent]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._journal_payload(binding, events)
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.path.parent,
            prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
        )
        temporary = Path(handle.name)
        try:
            with handle:
                yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            return self.load()
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _event_from_dict(value: Mapping[str, Any]) -> PhaseEvent:
        fields = dict(value)
        fields["verification"] = tuple(fields.get("verification") or ())
        return PhaseEvent(**fields)

    def _validate(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise PhaseStateError("unknown or corrupt phase schema")
        try:
            binding = AttemptBinding(**value["binding"])
            raw_events = value["events"]
        except (KeyError, TypeError) as exc:
            raise PhaseStateError("phase journal is incomplete") from exc
        binding.validate()
        if binding.attempt_id != self.path.stem or not isinstance(raw_events, list):
            raise PhaseStateError("phase journal identity is inconsistent")
        events: list[PhaseEvent] = []
        active: Stage08Phase | None = None
        prior = GENESIS_DIGEST
        for index, raw in enumerate(raw_events, start=1):
            try:
                event = self._event_from_dict(raw)
                event_type = EventType(event.event_type)
                phase = Stage08Phase(event.phase)
            except (TypeError, ValueError) as exc:
                raise PhaseStateError("phase event is malformed") from exc
            if event.sequence != index or event.previous_digest != prior:
                raise PhaseStateError("phase sequence or digest chain is broken")
            if self._event_digest(event) != event.event_digest:
                raise PhaseStateError("phase event content digest is invalid")
            if event_type is EventType.PHASE:
                if phase not in _TRANSITIONS[active]:
                    raise PhaseStateError("phase transition history is illegal")
                active = phase
            elif active is None or phase is not active:
                raise PhaseStateError("resume/pause event does not bind current phase")
            if event.diff_provenance is not None:
                DiffProvenance(
                    dirty_paths=tuple(event.diff_provenance.get("dirty_paths") or ()),
                    **{k: v for k, v in event.diff_provenance.items() if k != "dirty_paths"},
                ).validate(binding)
            prior = event.event_digest
            events.append(event)
        return self._journal_payload(binding, events)

    @staticmethod
    def current_phase(events: Iterable[PhaseEvent]) -> Stage08Phase | None:
        current = None
        for event in events:
            if event.event_type == EventType.PHASE.value:
                current = Stage08Phase(event.phase)
        return current

    def content_digest(self) -> str:
        return canonical_sha256(self.load())

    def evidence_binding(self) -> dict[str, Any]:
        journal = self.load()
        events = [self._event_from_dict(item) for item in journal["events"]]
        return {
            "schema_version": SCHEMA_VERSION,
            "attempt_id": journal["binding"]["attempt_id"],
            "journal_path": self.path.relative_to(self.repo_root).as_posix(),
            "journal_sha256": canonical_sha256(journal),
            "phase_event_digests": [item.event_digest for item in events],
            "current_phase": self.current_phase(events).value if events else None,
            "resume_count": sum(item.event_type == EventType.RESUME.value for item in events),
            "interruption_reasons": [
                item.interruption_reason for item in events if item.interruption_reason
            ],
        }

    def revalidate_resume(
        self,
        context: ResumeContext,
        *,
        expected_verification: Iterable[VerificationFingerprint] = (),
    ) -> ResumeDecision:
        journal = self.load()
        stored = AttemptBinding(**journal["binding"])
        reasons: list[str] = []
        if stored != context.binding:
            reasons.append("AUTHORITY_OR_ATTEMPT_BINDING_MISMATCH")
        if not all((
            context.stage07_valid, context.envelope_valid, context.task_authority_valid,
            context.security_valid, context.environment_valid,
        )):
            reasons.append("CURRENT_AUTHORIZATION_OR_ENVIRONMENT_INVALID")
        if context.unknown_side_effects:
            reasons.append("UNKNOWN_SIDE_EFFECT")
        if context.unexpected_untracked:
            reasons.append("UNEXPECTED_UNTRACKED_PATH")
        if context.scope_overrun or not context.diff_attributable:
            reasons.append("DIRTY_DIFF_PROVENANCE_INVALID")
        events = [self._event_from_dict(item) for item in journal["events"]]
        phase = self.current_phase(events)
        latest_diff = next(
            (item.diff_provenance for item in reversed(events) if item.diff_provenance), None
        )
        if latest_diff is not None and (
            tuple(latest_diff["dirty_paths"]) != context.dirty_paths
            or latest_diff["diff_sha256"] != context.diff_sha256
        ):
            reasons.append("CURRENT_DIFF_MISMATCH")
        reusable: list[str] = []
        expected = {item.level: item for item in expected_verification}
        for event in events:
            for raw in event.verification:
                prior = VerificationFingerprint(**raw)
                current = expected.get(prior.level)
                if current is not None and prior.reusable_against(current):
                    reusable.append(prior.level)
        if reasons:
            return ResumeDecision("BLOCK", phase.value if phase else None, False, (), tuple(dict.fromkeys(reasons)))
        return ResumeDecision(
            "RESUME_ALLOWED", phase.value if phase else None,
            phase in {
                Stage08Phase.CODEX_PATCH_COMPLETE, Stage08Phase.FAST_VERIFY_COMPLETE,
                Stage08Phase.TARGET_VERIFY_COMPLETE, Stage08Phase.FINAL_VERIFY_COMPLETE,
                Stage08Phase.STAGE8_COMPLETE,
            },
            tuple(dict.fromkeys(reusable)), (),
        )


def classify_safe_pause(context: ResumeContext, reason: InterruptionReason) -> ResumeDecision:
    """Classify interruption facts without mutating or discarding dirty work."""
    failures = []
    if context.binding.attempt_id == "":
        failures.append("ATTEMPT_ID_MISSING")
    if not all((
        context.stage07_valid, context.envelope_valid, context.task_authority_valid,
        context.security_valid, context.environment_valid,
    )):
        failures.append("CURRENT_AUTHORIZATION_OR_SECURITY_INVALID")
    if context.scope_overrun:
        failures.append("UNAUTHORIZED_DIRTY_PATH")
    if context.unexpected_untracked:
        failures.append("UNEXPECTED_UNTRACKED_PATH")
    if not context.diff_attributable:
        failures.append("DIFF_PROVENANCE_UNVERIFIABLE")
    if context.unknown_side_effects:
        failures.append("UNKNOWN_SIDE_EFFECT")
    return ResumeDecision(
        "BLOCK" if failures else "SAFE_PAUSE",
        None, False, (), tuple(failures) if failures else (reason.value,),
    )
