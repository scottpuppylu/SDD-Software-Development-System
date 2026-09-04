from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

from .codex_results import VerificationResult
from .result_serialization import serialize_verification_result
from .task_parser import AtomicTask


EVIDENCE_OUTCOMES = frozenset({"PASS", "FAIL", "NOT RUN"})
RECOVERY_CAPABILITY = "POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY"
RECOVERY_RECORD_KIND = "POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY"
RECOVERY_SCHEMA_VERSION = "2.0"


class InvalidEvidence(ValueError):
    """An evidence candidate is incomplete, contradictory, or ambiguous."""


class EvidencePersistenceError(OSError):
    """The registry could not be published; its prior visible state is intact."""


@dataclass(frozen=True)
class RecoveryAuthorization:
    authorization_id: str
    issuer: str
    capability: str
    task_id: str
    checkpoint_commit: str
    repository: str
    branch: str
    baseline_commit: str
    authority_versions: tuple[tuple[str, str], ...]
    task_contract_sha256: str
    verification_command: str
    allowed_evidence_prefix: str
    attempt_id: str
    issued_at: str
    expires_at: str | None = None
    status: str = "ACTIVE"
    single_use: bool = True
    allow_persistence_resume: bool = False

    def validate(self) -> None:
        required = (
            "authorization_id", "issuer", "capability", "task_id",
            "checkpoint_commit", "repository", "branch", "baseline_commit",
            "task_contract_sha256", "verification_command",
            "allowed_evidence_prefix", "attempt_id", "issued_at",
        )
        if any(not str(getattr(self, name)).strip() for name in required):
            raise InvalidEvidence("AUTHORITY_INVALID: incomplete recovery authorization")
        if self.issuer != "PROJECT_AUTHORITY" or self.capability != RECOVERY_CAPABILITY:
            raise InvalidEvidence("AUTHORITY_INVALID: recovery requires Project Authority")
        if self.status != "ACTIVE" or not self.single_use:
            raise InvalidEvidence("AUTHORITY_INVALID: authorization is inactive or not single-use")
        if not re.fullmatch(r"[0-9a-f]{40}", self.checkpoint_commit):
            raise InvalidEvidence("CHECKPOINT_MISMATCH: full checkpoint commit is required")
        if not re.fullmatch(r"[0-9a-f]{40}", self.baseline_commit):
            raise InvalidEvidence("AUTHORITY_INVALID: full baseline commit is required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.task_contract_sha256):
            raise InvalidEvidence("TASK_MISMATCH: task contract digest is invalid")
        if not self.authority_versions or any(
            not path.strip() or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for path, digest in self.authority_versions
        ):
            raise InvalidEvidence("AUTHORITY_INVALID: authority versions are incomplete")
        if self.allowed_evidence_prefix != ".sdd/evidence/":
            raise InvalidEvidence("AUTHORITY_INVALID: recovery evidence scope is overbroad")
        issued = _parse_utc(self.issued_at, "issued_at")
        if issued > datetime.now(timezone.utc):
            raise InvalidEvidence("AUTHORITY_INVALID: recovery authorization is not yet valid")
        if self.expires_at is not None:
            expires = _parse_utc(self.expires_at, "expires_at")
            if expires <= issued or datetime.now(timezone.utc) >= expires:
                raise InvalidEvidence("AUTHORITY_INVALID: recovery authorization expired")


@dataclass(frozen=True)
class RecoveryQualification:
    qualifies: bool
    reason: str
    evidence_file: str | None = None
    evidence_checkpoint: str | None = None
    reconciliation_eligible: bool = False


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def task_contract_sha256(task: AtomicTask) -> str:
    return hashlib.sha256(task.raw_markdown.encode("utf-8")).hexdigest()


def _parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvidence(f"AUTHORITY_INVALID: invalid {label}") from exc
    if parsed.tzinfo is None:
        raise InvalidEvidence(f"AUTHORITY_INVALID: {label} must include timezone")
    return parsed.astimezone(timezone.utc)


def recovery_evidence_filename(task_id: str, attempt_id: str, recorded_at: str) -> str:
    safe_attempt = re.sub(r"[^A-Za-z0-9_.-]", "-", attempt_id)
    if not safe_attempt or safe_attempt != attempt_id:
        raise InvalidEvidence("AUTHORITY_INVALID: unsafe recovery attempt identity")
    stamp = _parse_utc(recorded_at, "recorded_at").strftime("%Y%m%dT%H%M%S.%fZ")
    return f".sdd/evidence/{stamp}-{task_id}-recovery-{safe_attempt}.json"


def write_recovery_attestation(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> tuple[str, bool]:
    data = dict(payload)
    if data.get("record_kind") != RECOVERY_RECORD_KIND:
        raise InvalidEvidence("SCHEMA_INVALID: wrong recovery record discriminator")
    if data.get("schema_version") != RECOVERY_SCHEMA_VERSION:
        raise InvalidEvidence("SCHEMA_INVALID: unsupported recovery schema")
    expected_digest = canonical_sha256({
        key: value for key, value in data.items() if key != "record_sha256"
    })
    if data.get("record_sha256") != expected_digest:
        raise InvalidEvidence("SCHEMA_INVALID: recovery record digest mismatch")
    rel = recovery_evidence_filename(
        str(data.get("task_id", "")), str(data.get("attempt_id", "")),
        str(data.get("recorded_at", "")),
    )
    evidence_dir = repo_root / ".sdd" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    target = repo_root / rel
    encoded = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") == encoded:
            return rel, False
        raise InvalidEvidence("EVIDENCE_CONFLICT: attempt identity already has different content")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=evidence_dir, prefix=".tmp-recovery-", suffix=".json",
            delete=False, encoding="utf-8",
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            raise InvalidEvidence("EVIDENCE_CONFLICT: recovery target appeared during publication")
        os.replace(temporary_path, target)
        temporary_path = None
    except InvalidEvidence:
        raise
    except OSError as exc:
        raise EvidencePersistenceError(f"PERSISTENCE_FAILED: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return rel, True


def find_recovery_attempts(
    repo_root: Path, authorization: RecoveryAuthorization
) -> tuple[tuple[str, dict[str, Any]], ...]:
    root = repo_root / ".sdd" / "evidence"
    found: list[tuple[str, dict[str, Any]]] = []
    if not root.exists():
        return ()
    for path in sorted(root.glob(f"*-{authorization.task_id}-recovery-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if (
            payload.get("authorization_id") == authorization.authorization_id
            or payload.get("attempt_id") == authorization.attempt_id
        ):
            found.append((path.relative_to(repo_root).as_posix(), payload))
    return tuple(found)


def qualify_recovery_attestation(
    payload: Mapping[str, Any],
    authorization: RecoveryAuthorization,
    task: AtomicTask,
) -> RecoveryQualification:
    try:
        authorization.validate()
    except InvalidEvidence as exc:
        return RecoveryQualification(False, str(exc).split(":", 1)[0])
    checks = (
        (payload.get("record_kind") == RECOVERY_RECORD_KIND, "SCHEMA_INVALID"),
        (payload.get("schema_version") == RECOVERY_SCHEMA_VERSION, "SCHEMA_INVALID"),
        (payload.get("authorization_id") == authorization.authorization_id, "AUTHORITY_INVALID"),
        (payload.get("attempt_id") == authorization.attempt_id, "AUTHORITY_INVALID"),
        (payload.get("task_id") == task.task_id == authorization.task_id, "TASK_MISMATCH"),
        (payload.get("checkpoint_commit") == authorization.checkpoint_commit, "CHECKPOINT_MISMATCH"),
        (payload.get("task_contract_sha256") == authorization.task_contract_sha256 == task_contract_sha256(task), "TASK_MISMATCH"),
        (payload.get("verification_command") == authorization.verification_command, "COMMAND_MISMATCH"),
        (payload.get("verification_outcome") == "PASS", "VERIFICATION_FAILED"),
        (payload.get("exit_status") == 0, "VERIFICATION_FAILED"),
        (payload.get("complete") is True and payload.get("timed_out") is False, "VERIFICATION_INCOMPLETE"),
        (payload.get("implementation_mutated") is False, "IMPLEMENTATION_MUTATED"),
        (payload.get("pre_head") == payload.get("post_head") == authorization.baseline_commit, "IMPLEMENTATION_MUTATED"),
    )
    for valid, reason in checks:
        if not valid:
            return RecoveryQualification(False, reason)
    expected = canonical_sha256({key: value for key, value in payload.items() if key != "record_sha256"})
    if payload.get("record_sha256") != expected:
        return RecoveryQualification(False, "SCHEMA_INVALID")
    return RecoveryQualification(True, "QUALIFYING", reconciliation_eligible=True)


@dataclass(frozen=True)
class EvidenceRecord:
    check_id: str
    criterion: str
    scope: str
    executed: bool
    outcome: str
    evidence_reference: str | None
    evidence_gap: str | None
    coverage_links: tuple[str, ...]
    evidence_version: str
    current_version: str
    relevant: bool
    regression_risk: str
    required: bool = True
    security_related: bool = False

    def __post_init__(self) -> None:
        for name in ("check_id", "criterion", "scope", "evidence_version", "current_version", "regression_risk"):
            if not getattr(self, name).strip():
                raise InvalidEvidence(f"{name} is required")
        if self.outcome not in EVIDENCE_OUTCOMES:
            raise InvalidEvidence(f"{self.check_id} has invalid outcome {self.outcome!r}")
        if not self.coverage_links or any(not link.strip() for link in self.coverage_links):
            raise InvalidEvidence(f"{self.check_id} requires coverage links")
        if self.outcome == "NOT RUN":
            if self.executed or self.evidence_reference or not self.evidence_gap:
                raise InvalidEvidence("NOT RUN requires no execution/evidence and an explicit gap")
        elif not self.executed or not self.evidence_reference or self.evidence_gap:
            raise InvalidEvidence(f"{self.outcome} requires execution/evidence and no evidence gap")
        _validate_safe_reference(self.evidence_reference)

    @property
    def fresh(self) -> bool:
        return self.evidence_version == self.current_version

    @property
    def qualifies(self) -> bool:
        return self.outcome == "PASS" and self.executed and self.fresh and self.relevant

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"fresh": self.fresh, "qualifies": self.qualifies}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRecord":
        fields = {key: value[key] for key in cls.__dataclass_fields__}
        fields["coverage_links"] = tuple(fields["coverage_links"])
        return cls(**fields)


@dataclass(frozen=True)
class QualificationInputs:
    evidence_complete: bool
    all_required_checks_pass: bool
    coverage_complete: bool
    current_and_relevant: bool
    security_evidence_complete: bool
    gaps: tuple[str, ...]
    regression_risks: tuple[str, ...]
    verification_decision: None = None
    release_decision: None = None


def qualification_inputs(records: Iterable[EvidenceRecord]) -> QualificationInputs:
    """Project raw facts only; Stage09/Stage10 must make their own decisions."""
    items = tuple(records)
    required = tuple(item for item in items if item.required)
    gaps: list[str] = []
    for item in required:
        if item.outcome == "NOT RUN":
            gaps.append(f"{item.check_id}: {item.evidence_gap}")
        elif item.outcome == "FAIL":
            gaps.append(f"{item.check_id}: executed check failed")
        elif not item.fresh:
            gaps.append(f"{item.check_id}: stale evidence for {item.current_version}")
        elif not item.relevant:
            gaps.append(f"{item.check_id}: evidence is irrelevant to current scope")
    all_pass = bool(required) and all(item.outcome == "PASS" for item in required)
    current = bool(required) and all(item.fresh and item.relevant for item in required)
    security = all(item.qualifies for item in required if item.security_related)
    complete = bool(required) and all(item.qualifies for item in required)
    return QualificationInputs(
        evidence_complete=complete,
        all_required_checks_pass=all_pass,
        coverage_complete=complete,
        current_and_relevant=current,
        security_evidence_complete=security,
        gaps=tuple(gaps),
        regression_risks=tuple(item.regression_risk for item in items),
    )


class EvidenceRegistry:
    """Append-only JSON registry with atomic publication and retained history."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> tuple[EvidenceRecord, ...]:
        if not self.path.exists():
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return tuple(EvidenceRecord.from_dict(item) for item in raw["records"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError, InvalidEvidence) as exc:
            raise InvalidEvidence(f"cannot load evidence registry {self.path}: {exc}") from exc

    def append(self, record: EvidenceRecord) -> None:
        records = self.load()
        if any(item.check_id == record.check_id and item == record for item in records):
            raise InvalidEvidence(f"duplicate evidence record {record.check_id}")
        payload = {"schema_version": "1.0", "records": [item.to_dict() for item in (*records, record)]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=self.path.parent, prefix=".tmp-evidence-", delete=False, encoding="utf-8") as handle:
                temporary_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(self.path)
        except OSError as exc:
            raise EvidencePersistenceError(f"failed to publish evidence registry {self.path}: {exc}") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


_SENSITIVE = re.compile(r"(?i)(token|password|secret|api[_-]?key)\s*[:=]\s*\S+")


def _redact(value: str) -> str:
    return _SENSITIVE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def redact_evidence_output(value: str) -> str:
    return _redact(value)


def _validate_safe_reference(value: str | None) -> None:
    if value is not None and ("\n" in value or "\r" in value or _SENSITIVE.search(value)):
        raise InvalidEvidence("evidence reference contains sensitive or unnecessary output")


def write_stage08_evidence(
    repo_root: Path,
    task: AtomicTask,
    proc: subprocess.CompletedProcess[str],
    changed: list[str],
    verification: list[VerificationResult],
    *,
    status: str,
) -> str:
    evidence_dir = repo_root / ".sdd" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    rel = f".sdd/evidence/{stamp}-{task.task_id}.json"
    payload = {
        "schema_version": "1.0",
        "stage": "08",
        "task_id": task.task_id,
        "title": task.title,
        "status": status,
        "changed_paths": changed,
        "verification": [
            serialize_verification_result(v)
            for v in verification
        ],
        "codex": {
            "returncode": proc.returncode,
            "final_stdout": _redact(proc.stdout),
            "stderr": _redact(proc.stderr),
        },
        "recorded_at": stamp,
    }
    evidence_path = repo_root / rel
    temporary_file = tempfile.NamedTemporaryFile(
        dir=evidence_dir,
        prefix=".tmp-",
        suffix=f"-{task.task_id}.json",
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()
    try:
        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary_path.replace(evidence_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return rel
