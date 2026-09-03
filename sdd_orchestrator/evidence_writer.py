from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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


class InvalidEvidence(ValueError):
    """An evidence candidate is incomplete, contradictory, or ambiguous."""


class EvidencePersistenceError(OSError):
    """The registry could not be published; its prior visible state is intact."""


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
