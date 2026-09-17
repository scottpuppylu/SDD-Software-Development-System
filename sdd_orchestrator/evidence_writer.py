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

from .security_policy import redact_security_value

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


@dataclass(frozen=True)
class ImplementationQualificationBinding:
    """Intrinsic, immutable evidence facts accepted by implementation state.

    Git reachability, committed-blob identity, and checkpoint/task scope are
    deliberately validated by the Git runtime before this binding is persisted.
    """

    task_id: str
    implementation_checkpoint: str
    evidence_kind: str
    evidence_record_sha256: str
    verification_outcome: str
    recorded_at: str


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


def implementation_qualification_binding(
    payload: Mapping[str, Any],
    task: AtomicTask,
    *,
    ordinary_checkpoint: str | None = None,
) -> ImplementationQualificationBinding:
    """Validate intrinsic ordinary/recovery evidence without inventing state.

    Recovery authorizations are historical by reconciliation time, so this
    validates the immutable attestation that already qualified and was committed;
    it does not re-run the authorization lifecycle or verification command.
    """

    task_id = str(payload.get("task_id", ""))
    if task_id != task.task_id:
        raise InvalidEvidence("TASK_MISMATCH: evidence belongs to another task")

    if payload.get("record_kind") == RECOVERY_RECORD_KIND:
        checks = (
            (payload.get("schema_version") == RECOVERY_SCHEMA_VERSION, "SCHEMA_INVALID"),
            (bool(str(payload.get("authorization_id", "")).strip()), "AUTHORITY_INVALID"),
            (payload.get("authorization_issuer") == "PROJECT_AUTHORITY", "AUTHORITY_INVALID"),
            (payload.get("verification_outcome") == "PASS", "VERIFICATION_FAILED"),
            (payload.get("exit_status") == 0, "VERIFICATION_FAILED"),
            (payload.get("complete") is True, "VERIFICATION_INCOMPLETE"),
            (payload.get("timed_out") is False, "VERIFICATION_INCOMPLETE"),
            (payload.get("implementation_mutated") is False, "IMPLEMENTATION_MUTATED"),
            (payload.get("pre_head") == payload.get("post_head"), "IMPLEMENTATION_MUTATED"),
        )
        for valid, reason in checks:
            if not valid:
                raise InvalidEvidence(f"{reason}: recovery evidence is non-qualifying")
        checkpoint = str(payload.get("checkpoint_commit", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", checkpoint):
            raise InvalidEvidence("CHECKPOINT_MISMATCH: full checkpoint is required")
        expected = canonical_sha256({
            key: value for key, value in payload.items() if key != "record_sha256"
        })
        if payload.get("record_sha256") != expected:
            raise InvalidEvidence("SCHEMA_INVALID: recovery record digest mismatch")
        recorded_at = str(payload.get("recorded_at", ""))
        _parse_utc(recorded_at, "recorded_at")
        return ImplementationQualificationBinding(
            task_id=task.task_id,
            implementation_checkpoint=checkpoint,
            evidence_kind=RECOVERY_RECORD_KIND,
            evidence_record_sha256=expected,
            verification_outcome="PASS",
            recorded_at=recorded_at,
        )

    verification = payload.get("verification")
    codex = payload.get("codex")
    ordinary_valid = (
        payload.get("schema_version") == "1.0"
        and payload.get("stage") == "08"
        and payload.get("status") == "PASS"
        and isinstance(verification, list)
        and bool(verification)
        and all(
            isinstance(item, Mapping)
            and item.get("returncode") == 0
            and item.get("passed") is True
            for item in verification
        )
        and isinstance(codex, Mapping)
        and codex.get("returncode") == 0
    )
    if not ordinary_valid:
        raise InvalidEvidence("VERIFICATION_FAILED: ordinary evidence is non-qualifying")
    if ordinary_checkpoint is None or not re.fullmatch(r"[0-9a-f]{40}", ordinary_checkpoint):
        raise InvalidEvidence("CHECKPOINT_MISMATCH: ordinary evidence requires its atomic checkpoint")
    recorded_at = str(payload.get("recorded_at", ""))
    _parse_utc(recorded_at, "recorded_at")
    return ImplementationQualificationBinding(
        task_id=task.task_id,
        implementation_checkpoint=ordinary_checkpoint,
        evidence_kind="ORDINARY_STAGE08",
        evidence_record_sha256=canonical_sha256(payload),
        verification_outcome="PASS",
        recorded_at=recorded_at,
    )


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
    criterion_satisfied: bool | None = None

    def __post_init__(self) -> None:
        for name in ("check_id", "criterion", "scope", "evidence_version", "current_version", "regression_risk"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidEvidence(f"{name} is required")
        if not isinstance(self.executed, bool):
            raise InvalidEvidence(f"{self.check_id} requires a boolean execution status")
        if not isinstance(self.outcome, str) or self.outcome not in EVIDENCE_OUTCOMES:
            raise InvalidEvidence(f"{self.check_id} has invalid outcome {self.outcome!r}")
        if not isinstance(self.coverage_links, (tuple, list)) or not self.coverage_links or any(
            not isinstance(link, str) or not link.strip() for link in self.coverage_links
        ):
            raise InvalidEvidence(f"{self.check_id} requires coverage links")
        object.__setattr__(self, "coverage_links", tuple(self.coverage_links))
        for name in ("relevant", "required", "security_related"):
            if not isinstance(getattr(self, name), bool):
                raise InvalidEvidence(f"{self.check_id} requires boolean {name}")
        if self.outcome == "NOT RUN":
            if (
                self.executed
                or self.evidence_reference is not None
                or not isinstance(self.evidence_gap, str)
                or not self.evidence_gap.strip()
                or self.criterion_satisfied is not None
            ):
                raise InvalidEvidence("NOT RUN requires no execution/evidence and an explicit gap")
        else:
            expected_satisfaction = self.outcome == "PASS"
            if self.criterion_satisfied is None:
                object.__setattr__(self, "criterion_satisfied", expected_satisfaction)
            if (
                not self.executed
                or not isinstance(self.evidence_reference, str)
                or not self.evidence_reference.strip()
                or self.evidence_gap is not None
                or self.criterion_satisfied is not expected_satisfaction
            ):
                raise InvalidEvidence(
                    f"{self.outcome} requires executed evidence and a matching criterion result"
                )
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
        try:
            fields = {
                key: value[key]
                for key in cls.__dataclass_fields__
                if key in value
            }
            fields["coverage_links"] = tuple(fields["coverage_links"])
            return cls(**fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidEvidence(f"malformed evidence record: {exc}") from exc


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
    if any(not isinstance(item, EvidenceRecord) for item in items):
        raise InvalidEvidence("qualification inputs must contain evidence records")
    current_by_check: dict[str, EvidenceRecord] = {}
    for item in items:
        current_by_check[item.check_id] = item
    required = tuple(item for item in current_by_check.values() if item.required)
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
        if not isinstance(record, EvidenceRecord):
            raise InvalidEvidence("registry accepts only validated evidence records")
        records = self.load()
        if any(item.check_id == record.check_id and item == record for item in records):
            raise InvalidEvidence(f"duplicate evidence record {record.check_id}")
        history = tuple(item for item in records if item.check_id == record.check_id)
        for prior in history:
            if (
                prior.criterion != record.criterion
                or prior.scope != record.scope
                or prior.coverage_links != record.coverage_links
            ):
                raise InvalidEvidence(
                    f"stable check identity {record.check_id} cannot change criterion, scope, or coverage"
                )
        if any(item.required for item in history) and not record.required:
            raise InvalidEvidence(f"required check {record.check_id} cannot be downgraded")
        if any(item.security_related for item in history) and not record.security_related:
            raise InvalidEvidence(f"security check {record.check_id} cannot be downgraded")
        payload = {"schema_version": "1.0", "records": [item.to_dict() for item in (*records, record)]}
        temporary_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
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


DEMONSTRATION_CHAIN = (
    "IDEA",
    "REQUIREMENT_CLARIFICATION",
    "APPROVED_PRODUCT_REQUIREMENTS",
    "SPECIFICATION",
    "DESIGN",
    "TASK_DECOMPOSITION",
    "HUMAN_DECISION",
    "AUTHORIZED_AI_CODING",
    "TESTING_VERIFICATION",
    "GIT_TRACEABILITY",
    "TRUTHFUL_STATUS_FAILURE_HANDLING",
    "MAINTENANCE_CHANGE",
    "REGRESSION_VERIFICATION",
)

DEMONSTRATION_GOVERNING_EFFECTS = (
    "AUTHORITY_NOT_BYPASSED",
    "AI_DID_NOT_DECIDE_PRODUCT_REQUIREMENTS",
    "HUMAN_DECISION_GOVERNED_AFFECTED_WORK",
    "BLOCKERS_STOPPED_AFFECTED_WORK",
    "UNVERIFIED_WORK_NOT_COMPLETE",
    "MAINTENANCE_REGRESSION_PROTECTED",
)

MANIFEST_REFERENCE_STATUSES = frozenset({
    "QUALIFYING", "MISSING", "STALE", "BROKEN", "AMBIGUOUS", "NON_QUALIFYING",
})


@dataclass(frozen=True)
class DemonstrationReference:
    """One minimum-disclosure pointer; never a substitute for its source proof."""

    reference_id: str
    subject: str
    owner: str
    status: str
    repository_path: str | None = None
    commit: str | None = None
    content_sha256: str | None = None
    forward_links: tuple[str, ...] = ()
    reverse_links: tuple[str, ...] = ()
    gap: str | None = None

    def __post_init__(self) -> None:
        for name in ("reference_id", "subject", "owner"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidEvidence(f"demonstration {name} is required")
        if self.status not in MANIFEST_REFERENCE_STATUSES:
            raise InvalidEvidence(f"invalid demonstration reference status: {self.status}")
        for value in (self.reference_id, self.subject, self.owner, self.repository_path,
                      self.gap, *self.forward_links, *self.reverse_links):
            _validate_safe_reference(value)
        if self.repository_path is not None:
            path = Path(self.repository_path)
            if path.is_absolute() or ".." in path.parts or path.as_posix() != self.repository_path:
                raise InvalidEvidence("demonstration reference path must be repository-relative")
        if self.commit is not None and not re.fullmatch(r"[0-9a-f]{40}", self.commit):
            raise InvalidEvidence("demonstration reference requires a full Git commit")
        if self.content_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", self.content_sha256):
            raise InvalidEvidence("demonstration reference content digest is invalid")
        if self.status == "QUALIFYING":
            if not all((self.repository_path, self.commit, self.content_sha256)):
                raise InvalidEvidence("qualifying demonstration reference requires path, commit, and digest")
            if not self.forward_links or not self.reverse_links:
                raise InvalidEvidence("qualifying demonstration reference must be bidirectionally navigable")
            if self.gap is not None:
                raise InvalidEvidence("qualifying demonstration reference cannot contain a gap")
        elif not isinstance(self.gap, str) or not self.gap.strip():
            raise InvalidEvidence("non-qualifying demonstration reference requires an explicit gap")

    @property
    def qualifies(self) -> bool:
        return self.status == "QUALIFYING"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"qualifies": self.qualifies}


@dataclass(frozen=True)
class DemonstrationManifest:
    snapshot_identity: str
    chain: tuple[DemonstrationReference, ...]
    governing_effects: tuple[DemonstrationReference, ...]
    status: str
    gaps: tuple[str, ...]
    verification_decision: None = None
    release_decision: None = None
    mvp_qualified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_identity, str) or not self.snapshot_identity.strip():
            raise InvalidEvidence("demonstration snapshot identity is required")
        if self.status not in {"REFERENCE_COMPLETE", "INCOMPLETE"}:
            raise InvalidEvidence("invalid demonstration manifest status")
        if self.verification_decision is not None or self.release_decision is not None or self.mvp_qualified:
            raise InvalidEvidence("demonstration manifest cannot create qualification or a gate decision")
        expected_complete = all(item.qualifies for item in (*self.chain, *self.governing_effects))
        if (self.status == "REFERENCE_COMPLETE") is not expected_complete:
            raise InvalidEvidence("demonstration manifest status contradicts its references")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "snapshot_identity": self.snapshot_identity,
            "status": self.status,
            "chain": [item.to_dict() for item in self.chain],
            "governing_effects": [item.to_dict() for item in self.governing_effects],
            "gaps": list(self.gaps),
            "verification_decision": None,
            "release_decision": None,
            "mvp_qualified": False,
        }


def _manifest_items(
    supplied: Iterable[DemonstrationReference],
    required_subjects: tuple[str, ...],
    category: str,
) -> tuple[DemonstrationReference, ...]:
    indexed: dict[str, DemonstrationReference] = {}
    for item in supplied:
        if not isinstance(item, DemonstrationReference):
            raise InvalidEvidence("manifest accepts only validated demonstration references")
        if item.subject in indexed:
            raise InvalidEvidence(f"ambiguous duplicate demonstration subject: {item.subject}")
        if item.subject not in required_subjects:
            raise InvalidEvidence(f"unexpected demonstration subject: {item.subject}")
        indexed[item.subject] = item
    return tuple(
        indexed.get(subject) or DemonstrationReference(
            reference_id=f"MISSING-{category}-{subject}", subject=subject,
            owner="AUTHORITATIVE_OWNER", status="MISSING",
            gap=f"{category} proof is absent for {subject}",
        )
        for subject in required_subjects
    )


def assemble_demonstration_manifest(
    *,
    snapshot_identity: str,
    chain_references: Iterable[DemonstrationReference],
    governing_effect_references: Iterable[DemonstrationReference],
) -> DemonstrationManifest:
    """Build an inspectable index without producing evidence or qualification."""

    chain = _manifest_items(chain_references, DEMONSTRATION_CHAIN, "CHAIN_LINK")
    effects = _manifest_items(
        governing_effect_references, DEMONSTRATION_GOVERNING_EFFECTS, "GOVERNING_EFFECT"
    )
    gaps = tuple(
        f"{item.subject}: {item.status}: {item.gap}"
        for item in (*chain, *effects) if not item.qualifies
    )
    return DemonstrationManifest(
        snapshot_identity=snapshot_identity,
        chain=chain,
        governing_effects=effects,
        status="INCOMPLETE" if gaps else "REFERENCE_COMPLETE",
        gaps=gaps,
    )


def inspect_demonstration_reference(
    repo_root: Path,
    *,
    reference_id: str,
    subject: str,
    owner: str,
    repository_path: str,
    commit: str,
    expected_sha256: str,
    forward_links: Iterable[str],
    reverse_links: Iterable[str],
    declared_qualifying: bool = True,
) -> DemonstrationReference:
    """Classify a repository reference against immutable Git content."""

    common = dict(
        reference_id=reference_id, subject=subject, owner=owner,
        repository_path=repository_path, commit=commit,
        content_sha256=expected_sha256,
        forward_links=tuple(forward_links), reverse_links=tuple(reverse_links),
    )
    try:
        candidate = DemonstrationReference(status="QUALIFYING", **common)
    except InvalidEvidence as exc:
        return DemonstrationReference(
            reference_id=reference_id, subject=subject, owner=owner,
            status="BROKEN", gap=f"invalid reference metadata: {exc}",
        )
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=repo_root, capture_output=True, check=False,
        )
        content = subprocess.run(
            ["git", "show", f"{commit}:{repository_path}"],
            cwd=repo_root, capture_output=True, check=False,
        )
    except OSError:
        ancestor = content = None
    if ancestor is None or content is None or ancestor.returncode != 0 or content.returncode != 0:
        return DemonstrationReference(status="BROKEN", gap="Git reference is missing or unreachable", **common)
    actual_sha256 = hashlib.sha256(content.stdout).hexdigest()
    if actual_sha256 != expected_sha256:
        return DemonstrationReference(status="STALE", gap="referenced content digest no longer matches", **common)
    if not declared_qualifying:
        return DemonstrationReference(status="NON_QUALIFYING", gap="source record does not qualify", **common)
    return candidate


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
    governance_audit: Mapping[str, Any] | None = None,
    stage08_attempt: Mapping[str, Any] | None = None,
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
    if governance_audit is not None:
        required = {"envelope_id", "approval_class", "approval_reference", "pre_dispatch", "post_dispatch"}
        if not required.issubset(governance_audit):
            raise InvalidEvidence("governance audit is missing required envelope bindings")
        payload["governance"] = redact_security_value(dict(governance_audit))
    if stage08_attempt is not None:
        required_attempt = {
            "schema_version", "attempt_id", "journal_path", "journal_sha256",
            "phase_event_digests", "current_phase", "resume_count",
            "interruption_reasons",
        }
        if (
            not required_attempt.issubset(stage08_attempt)
            or stage08_attempt.get("schema_version") != "1.0"
            or not re.fullmatch(r"[0-9a-f]{64}", str(stage08_attempt.get("attempt_id", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(stage08_attempt.get("journal_sha256", "")))
            or not isinstance(stage08_attempt.get("phase_event_digests"), list)
            or any(
                not re.fullmatch(r"[0-9a-f]{64}", str(item))
                for item in stage08_attempt.get("phase_event_digests", [])
            )
        ):
            raise InvalidEvidence("stage08 attempt binding is incomplete or invalid")
        payload["stage08_attempt"] = redact_security_value(dict(stage08_attempt))
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
