from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable, Mapping, Protocol
from uuid import uuid4

from .core import SDDOrchestratorError


class CodexAdapterError(SDDOrchestratorError):
    pass


class NoExecutableTaskError(CodexAdapterError):
    pass


FAILURE_CLASSES = {
    "LIFECYCLE", "TOOL", "AI_PROVIDER", "COMMAND", "GIT", "TEST_VERIFICATION",
    "AUTHORITY", "SECURITY", "EXECUTION",
}
RECOVERY_ROUTES = {
    "RETRY", "ALTERNATE", "REMEDIATION", "REVISION", "ESCALATION", "HUMAN_DECISION",
}


class FailureEnvelopeError(SDDOrchestratorError):
    """The durable failure record is missing, malformed, or could not be persisted."""


@dataclass(frozen=True)
class PartialOutput:
    reference: str
    classification: str  # VALID, UNVERIFIED, or INVALID

    def validate(self) -> None:
        if not self.reference or self.classification not in {"VALID", "UNVERIFIED", "INVALID"}:
            raise FailureEnvelopeError("partial output requires a safe reference and valid classification")


@dataclass(frozen=True)
class RecoveryRoute:
    kind: str
    owner: str
    preconditions: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.kind not in RECOVERY_ROUTES or not self.owner:
            raise FailureEnvelopeError(f"invalid recovery route: {self.kind!r}")


@dataclass(frozen=True)
class FailureAttempt:
    attempt_id: str
    failure_id: str
    attempted_route: str
    status: str
    occurred_at: str
    safe_reference: str | None = None

    def validate(self) -> None:
        if not self.attempt_id or not self.failure_id or self.attempted_route not in RECOVERY_ROUTES:
            raise FailureEnvelopeError("attempt identity, original failure, and route are required")
        if self.status not in {"INCOMPLETE", "BLOCKED", "FAILED", "SUCCEEDED"}:
            raise FailureEnvelopeError(f"invalid attempt status: {self.status}")


@dataclass(frozen=True)
class FailureEnvelope:
    failure_id: str
    operation: str
    step: str
    cause_class: str
    affected_scope: tuple[str, ...]
    pre_operation_identity: str
    truthful_status: str
    unsafe_to_continue: bool
    owner: str
    safe_reference: str
    valid_completed_work: tuple[str, ...] = ()
    partial_outputs: tuple[PartialOutput, ...] = ()
    candidate_routes: tuple[RecoveryRoute, ...] = ()
    attempts: tuple[FailureAttempt, ...] = ()
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        required = (self.failure_id, self.operation, self.step, self.pre_operation_identity,
                    self.owner, self.safe_reference)
        if not all(required) or not self.affected_scope:
            raise FailureEnvelopeError("failure identity, point, scope, owner, and safe reference are required")
        if self.cause_class not in FAILURE_CLASSES:
            raise FailureEnvelopeError(f"invalid cause class: {self.cause_class}")
        if self.truthful_status not in {"INCOMPLETE", "BLOCKED"}:
            raise FailureEnvelopeError("a failure must remain INCOMPLETE or BLOCKED")
        if self.cause_class in {"AUTHORITY", "SECURITY"} and (
            self.truthful_status != "BLOCKED" or not self.unsafe_to_continue
        ):
            raise FailureEnvelopeError("authority and security failures must block continuation")
        for output in self.partial_outputs:
            output.validate()
        for route in self.candidate_routes:
            route.validate()
        for attempt in self.attempts:
            attempt.validate()
            if attempt.failure_id != self.failure_id:
                raise FailureEnvelopeError("every attempt must link to the original failure")

    def eligible_routes(self, facts: Iterable[str]) -> tuple[RecoveryRoute, ...]:
        known = set(facts)
        return tuple(route for route in self.candidate_routes if set(route.preconditions) <= known)

    def linked_attempt(
        self, route: str, *, facts: Iterable[str] = (), status: str = "INCOMPLETE",
        safe_reference: str | None = None,
    ) -> "FailureEnvelope":
        if route not in {item.kind for item in self.eligible_routes(facts)}:
            raise FailureEnvelopeError("route is not eligible under current preconditions")
        attempt = FailureAttempt(
            attempt_id=f"attempt-{uuid4().hex}", failure_id=self.failure_id,
            attempted_route=route, status=status,
            occurred_at=datetime.now(timezone.utc).isoformat(), safe_reference=safe_reference,
        )
        value = FailureEnvelope(**{**asdict(self), "partial_outputs": self.partial_outputs,
            "candidate_routes": self.candidate_routes, "attempts": self.attempts + (attempt,)})
        value.validate()
        return value

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "FailureEnvelope":
        try:
            envelope = cls(
                **{**value,
                   "affected_scope": tuple(value["affected_scope"]),
                   "valid_completed_work": tuple(value.get("valid_completed_work", ())),
                   "partial_outputs": tuple(PartialOutput(**item) for item in value.get("partial_outputs", ())),
                   "candidate_routes": tuple(RecoveryRoute(**{**item, "preconditions": tuple(item.get("preconditions", ()))}) for item in value.get("candidate_routes", ())),
                   "attempts": tuple(FailureAttempt(**item) for item in value.get("attempts", ()))},
            )
        except (KeyError, TypeError) as exc:
            raise FailureEnvelopeError(f"malformed failure envelope: {exc}") from exc
        envelope.validate()
        return envelope


class FailureJournal(Protocol):
    def persist(self, envelope: FailureEnvelope) -> None: ...
    def get(self, failure_id: str) -> FailureEnvelope: ...


class JsonFailureJournal:
    """Optional repository-native adapter; the envelope contract is storage-neutral."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {"failures": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or not isinstance(value.get("failures"), dict):
                raise ValueError("journal must contain a failures object")
            return value
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise FailureEnvelopeError(f"cannot reconstruct failure journal: {exc}") from exc

    def get(self, failure_id: str) -> FailureEnvelope:
        try:
            return FailureEnvelope.from_dict(self._load()["failures"][failure_id])
        except KeyError as exc:
            raise FailureEnvelopeError(f"missing failure envelope: {failure_id}") from exc

    def persist(self, envelope: FailureEnvelope) -> None:
        envelope.validate()
        state = self._load()
        failures = dict(state["failures"])
        prior = failures.get(envelope.failure_id)
        if prior is not None:
            original = FailureEnvelope.from_dict(prior)
            immutable = ("operation", "step", "cause_class", "affected_scope",
                         "pre_operation_identity", "owner", "safe_reference", "occurred_at")
            if any(getattr(original, name) != getattr(envelope, name) for name in immutable):
                raise FailureEnvelopeError("original failure facts are immutable")
            if envelope.attempts[:len(original.attempts)] != original.attempts:
                raise FailureEnvelopeError("attempt history cannot be erased or rewritten")
        failures[envelope.failure_id] = envelope.to_dict()
        state["failures"] = failures
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            fd, name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
            temporary = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(state, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except Exception as exc:
            raise FailureEnvelopeError(f"failure envelope was not persisted: {exc}") from exc
        finally:
            if temporary is not None:
                try: temporary.unlink()
                except FileNotFoundError: pass


def new_failure(
    *, operation: str, step: str, cause_class: str, affected_scope: Iterable[str],
    pre_operation_identity: str, owner: str, safe_reference: str,
    unsafe_to_continue: bool = True, valid_completed_work: Iterable[str] = (),
    partial_outputs: Iterable[PartialOutput] = (), candidate_routes: Iterable[RecoveryRoute] = (),
) -> FailureEnvelope:
    envelope = FailureEnvelope(
        failure_id=f"failure-{uuid4().hex}", operation=operation, step=step,
        cause_class=cause_class, affected_scope=tuple(affected_scope),
        pre_operation_identity=pre_operation_identity,
        truthful_status="BLOCKED" if unsafe_to_continue else "INCOMPLETE",
        unsafe_to_continue=unsafe_to_continue, owner=owner, safe_reference=safe_reference,
        valid_completed_work=tuple(valid_completed_work), partial_outputs=tuple(partial_outputs),
        candidate_routes=tuple(candidate_routes),
    )
    envelope.validate()
    return envelope
