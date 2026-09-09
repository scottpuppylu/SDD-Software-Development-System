"""Repository-backed governed state and rebuildable traceability projections.

The caller owns the location of the canonical record.  This module deliberately
does not prescribe a repository layout or persist the derived link index.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Any, Iterable, Mapping


ALLOWED_RESULTS = {"PASS", "FAIL", "NOT RUN"}
ALLOWED_LINK_KINDS = {"G", "FR", "NFR", "EC", "AC", "SPEC", "DES", "TASK", "CODE", "TEST_EVIDENCE"}


class InvalidGovernedRecord(ValueError):
    """Canonical state is missing, contradictory, ambiguous, or stale."""


class PublicationError(OSError):
    """Atomic publication failed without advancing the visible record."""

    def __init__(self, path: Path, affected_scope: str, cause: BaseException):
        super().__init__(f"failed write {path}: {cause}; affected scope: {affected_scope}")
        self.path = path
        self.affected_scope = affected_scope
        self.cause = cause


@dataclass(frozen=True)
class GitIdentity:
    version: str
    change: str
    checkpoint: str | None = None


@dataclass(frozen=True)
class AuthorityReference:
    identity: str
    artifact: str
    owner: str
    status: str


@dataclass(frozen=True)
class VerificationReference:
    identity: str
    result: str
    evidence: str | None = None
    gap: str | None = None


@dataclass(frozen=True)
class ObservationReference:
    """Non-authoritative implementation evidence, kept separate from authority."""

    identity: str
    reference: str
    affected_scope: str


@dataclass(frozen=True)
class ImpactAmbiguity:
    identity: str
    gap: str
    affected_scope: str
    owner_route: str
    material: bool = True


@dataclass(frozen=True)
class ImpactRisk:
    identity: str
    risk: str
    affected_scope: str
    owner_route: str
    high_risk: bool = False


@dataclass(frozen=True)
class ImpactAssessment:
    dependent_completion_allowed: bool
    status: str
    gaps: tuple[str, ...]
    risks: tuple[str, ...]
    owner_routes: tuple[str, ...]


@dataclass(frozen=True)
class TraceLink:
    source: str
    source_kind: str
    target: str
    target_kind: str
    affected_scope: str
    governing_decision: str
    version: str

    def validate(self, current_version: str) -> None:
        if not all((self.source, self.target, self.affected_scope, self.governing_decision)):
            raise InvalidGovernedRecord(f"broken link {self.source!r} -> {self.target!r}")
        if self.source_kind not in ALLOWED_LINK_KINDS or self.target_kind not in ALLOWED_LINK_KINDS:
            raise InvalidGovernedRecord(f"unknown link kind in {self.source} -> {self.target}")
        if self.version != current_version:
            raise InvalidGovernedRecord(
                f"stale link {self.source} -> {self.target}: {self.version} != {current_version}"
            )


@dataclass(frozen=True)
class ModificationImpactLedger:
    """Bounded impact analysis for one requested modification (TASK-013)."""

    modification_id: str
    request_reference: str
    requested_change: tuple[str, ...]
    authorized_change_scope: tuple[str, ...]
    affected_behavior_data: tuple[str, ...]
    preservation_expectations: tuple[str, ...]
    authority_basis: tuple[AuthorityReference, ...]
    observed_evidence: tuple[ObservationReference, ...]
    ambiguities: tuple[ImpactAmbiguity, ...]
    risks: tuple[ImpactRisk, ...]
    governing_requirements: tuple[str, ...]
    governing_contracts: tuple[str, ...]
    governing_designs: tuple[str, ...]
    governing_tasks: tuple[str, ...]
    links: tuple[TraceLink, ...]
    input_version: str
    current_version: str

    def validate(self) -> None:
        required = (
            self.modification_id,
            self.request_reference,
            self.input_version,
            self.current_version,
        )
        if not all(required) or not self.requested_change:
            raise InvalidGovernedRecord("modification identity, request, version, and requested change are required")
        collections = {
            "requested change": self.requested_change,
            "authorized change scope": self.authorized_change_scope,
            "affected behavior/data": self.affected_behavior_data,
            "preservation expectations": self.preservation_expectations,
            "governing requirements": self.governing_requirements,
            "governing contracts": self.governing_contracts,
            "governing designs": self.governing_designs,
            "governing tasks": self.governing_tasks,
        }
        for label, values in collections.items():
            if any(not value for value in values) or len(values) != len(set(values)):
                raise InvalidGovernedRecord(f"blank or duplicate {label} classification")
        conflict = set(self.requested_change) & set(self.preservation_expectations)
        if conflict:
            raise InvalidGovernedRecord(f"conflicting requested/preserved classifications: {sorted(conflict)}")

        authority_ids: set[str] = set()
        for item in self.authority_basis:
            if not all((item.identity, item.artifact, item.owner, item.status)):
                raise InvalidGovernedRecord("authority basis requires identity, artifact, owner, and status")
            if item.identity in authority_ids:
                raise InvalidGovernedRecord(f"ambiguous duplicate authority identity: {item.identity}")
            authority_ids.add(item.identity)

        observation_ids: set[str] = set()
        for item in self.observed_evidence:
            if not all((item.identity, item.reference, item.affected_scope)):
                raise InvalidGovernedRecord("observed evidence requires identity, reference, and affected scope")
            if item.identity in observation_ids:
                raise InvalidGovernedRecord(f"ambiguous duplicate observation identity: {item.identity}")
            observation_ids.add(item.identity)

        for item in (*self.ambiguities, *self.risks):
            if not all((item.identity, item.affected_scope, item.owner_route)):
                raise InvalidGovernedRecord("ambiguity/risk requires identity, affected scope, and owner route")
        if any(not item.gap for item in self.ambiguities):
            raise InvalidGovernedRecord("ambiguity requires an exact gap")
        if any(not item.risk for item in self.risks):
            raise InvalidGovernedRecord("risk requires an exact description")

        seen_links: set[tuple[str, str, str]] = set()
        for link in self.links:
            link.validate(self.current_version)
            identity = (link.source, link.target, link.affected_scope)
            if identity in seen_links:
                raise InvalidGovernedRecord(f"ambiguous duplicate link: {identity}")
            seen_links.add(identity)

    def assess(self) -> ImpactAssessment:
        self.validate()
        gaps: list[str] = []
        risks = [f"{item.identity}: {item.risk} (scope: {item.affected_scope})" for item in self.risks]
        routes: list[str] = []

        if not self.authority_basis:
            gaps.append("missing authority basis")
            routes.append("authoritative owner")
        if not self.affected_behavior_data:
            gaps.append("affected behavior/data scope is materially unknown")
            routes.append("impact-ledger owner")
        if not self.preservation_expectations:
            gaps.append("preservation scope is materially unknown")
            routes.append("impact-ledger owner")
        unauthorized = sorted(set(self.requested_change) - set(self.authorized_change_scope))
        if unauthorized:
            gaps.append(f"requested scope exceeds authorized change scope: {unauthorized}")
            routes.append("Stage07 implementation-authorization owner")
        if self.input_version != self.current_version:
            gaps.append(f"stale impact input: {self.input_version} != {self.current_version}")
            routes.append("impact-ledger owner")
        for item in self.ambiguities:
            if item.material:
                gaps.append(f"{item.identity}: {item.gap} (scope: {item.affected_scope})")
                routes.append(item.owner_route)
        for item in self.risks:
            routes.append("TASK-011 safety interlock" if item.high_risk else item.owner_route)

        governing_groups = (
            ("requirements", self.governing_requirements, "Stage02 product-requirement owner"),
            ("contracts", self.governing_contracts, "Stage03 technical-contract owner"),
            ("designs", self.governing_designs, "Stage04 implementation-design owner"),
            ("tasks", self.governing_tasks, "Stage06 task owner"),
        )
        for label, identities, owner in governing_groups:
            if not identities:
                gaps.append(f"missing governing {label}")
                routes.append(owner)

        required_trace = set(
            self.governing_requirements
            + self.governing_contracts
            + self.governing_designs
            + self.governing_tasks
        )
        linked = {link.source for link in self.links} | {link.target for link in self.links}
        missing_trace = sorted(required_trace - linked)
        if missing_trace:
            gaps.append(f"missing governing trace links: {missing_trace}")
            routes.append("traceability owner")
        adjacency: dict[str, set[str]] = {}
        for link in self.links:
            adjacency.setdefault(link.source, set()).add(link.target)
        disconnected: list[str] = []
        for identity in self.governing_requirements + self.governing_contracts + self.governing_designs:
            pending = [identity]
            visited: set[str] = set()
            while pending:
                candidate = pending.pop()
                if candidate in visited:
                    continue
                visited.add(candidate)
                pending.extend(adjacency.get(candidate, ()))
            if not set(self.governing_tasks) & visited:
                disconnected.append(identity)
        if disconnected:
            gaps.append(f"governing trace does not reach a task: {sorted(disconnected)}")
            routes.append("traceability owner")

        routes = list(dict.fromkeys(routes))
        return ImpactAssessment(
            dependent_completion_allowed=not gaps and not self.risks,
            status="READY" if not gaps and not self.risks else "BLOCKED",
            gaps=tuple(gaps),
            risks=tuple(risks),
            owner_routes=tuple(routes),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModificationImpactLedger":
        try:
            ledger = cls(
                modification_id=value["modification_id"],
                request_reference=value["request_reference"],
                requested_change=tuple(value.get("requested_change", ())),
                authorized_change_scope=tuple(value.get("authorized_change_scope", ())),
                affected_behavior_data=tuple(value.get("affected_behavior_data", ())),
                preservation_expectations=tuple(value.get("preservation_expectations", ())),
                authority_basis=tuple(AuthorityReference(**item) for item in value.get("authority_basis", ())),
                observed_evidence=tuple(ObservationReference(**item) for item in value.get("observed_evidence", ())),
                ambiguities=tuple(ImpactAmbiguity(**item) for item in value.get("ambiguities", ())),
                risks=tuple(ImpactRisk(**item) for item in value.get("risks", ())),
                governing_requirements=tuple(value.get("governing_requirements", ())),
                governing_contracts=tuple(value.get("governing_contracts", ())),
                governing_designs=tuple(value.get("governing_designs", ())),
                governing_tasks=tuple(value.get("governing_tasks", ())),
                links=tuple(TraceLink(**item) for item in value.get("links", ())),
                input_version=value["input_version"],
                current_version=value["current_version"],
            )
        except (KeyError, TypeError) as exc:
            raise InvalidGovernedRecord(f"malformed impact ledger: {exc}") from exc
        ledger.validate()
        return ledger


@dataclass(frozen=True)
class GovernedRecord:
    lifecycle_position: str
    current_work: str | None
    next_work: str | None
    completed_work: tuple[str, ...]
    authorities: tuple[AuthorityReference, ...]
    human_decisions: tuple[str, ...]
    affected_scope: tuple[str, ...]
    task_execution_state: Mapping[str, str]
    verification: tuple[VerificationReference, ...]
    failures: tuple[str, ...]
    invalidations: tuple[str, ...]
    recovery_gate_provenance: tuple[str, ...]
    git: GitIdentity
    governing_decisions: tuple[str, ...]
    links: tuple[TraceLink, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_execution_state", MappingProxyType(dict(self.task_execution_state)))
        self.validate()

    def validate(self) -> None:
        if not self.lifecycle_position or not self.git.version or not self.git.change:
            raise InvalidGovernedRecord("lifecycle position and Git version/change are required")
        if not self.affected_scope:
            raise InvalidGovernedRecord("affected scope is required")
        authority_ids = [item.identity for item in self.authorities]
        if len(authority_ids) != len(set(authority_ids)):
            raise InvalidGovernedRecord("ambiguous duplicate authority identity")
        for item in self.authorities:
            if not all((item.identity, item.artifact, item.owner, item.status)):
                raise InvalidGovernedRecord("authority references require identity, artifact, owner, and status")
        verification_ids: set[str] = set()
        for item in self.verification:
            if not item.identity:
                raise InvalidGovernedRecord("verification identity is required")
            if item.identity in verification_ids:
                raise InvalidGovernedRecord(f"ambiguous duplicate verification identity: {item.identity}")
            verification_ids.add(item.identity)
            if item.result not in ALLOWED_RESULTS:
                raise InvalidGovernedRecord(f"invalid verification result: {item.result}")
            if item.result == "NOT RUN" and not item.gap:
                raise InvalidGovernedRecord(f"NOT RUN verification {item.identity} requires a gap")
        seen: set[tuple[str, str, str]] = set()
        for link in self.links:
            link.validate(self.git.version)
            identity = (link.source, link.target, link.affected_scope)
            if identity in seen:
                raise InvalidGovernedRecord(f"ambiguous duplicate link: {identity}")
            seen.add(identity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lifecycle_position": self.lifecycle_position,
            "current_work": self.current_work,
            "next_work": self.next_work,
            "completed_work": list(self.completed_work),
            "authorities": [asdict(item) for item in self.authorities],
            "human_decisions": list(self.human_decisions),
            "affected_scope": list(self.affected_scope),
            "task_execution_state": dict(self.task_execution_state),
            "verification": [asdict(item) for item in self.verification],
            "failures": list(self.failures),
            "invalidations": list(self.invalidations),
            "recovery_gate_provenance": list(self.recovery_gate_provenance),
            "git": asdict(self.git),
            "governing_decisions": list(self.governing_decisions),
            "links": [asdict(item) for item in self.links],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernedRecord":
        try:
            return cls(
                lifecycle_position=value["lifecycle_position"],
                current_work=value.get("current_work"),
                next_work=value.get("next_work"),
                completed_work=tuple(value.get("completed_work", ())),
                authorities=tuple(AuthorityReference(**item) for item in value.get("authorities", ())),
                human_decisions=tuple(value.get("human_decisions", ())),
                affected_scope=tuple(value["affected_scope"]),
                task_execution_state=value.get("task_execution_state", {}),
                verification=tuple(VerificationReference(**item) for item in value.get("verification", ())),
                failures=tuple(value.get("failures", ())),
                invalidations=tuple(value.get("invalidations", ())),
                recovery_gate_provenance=tuple(value.get("recovery_gate_provenance", ())),
                git=GitIdentity(**value["git"]),
                governing_decisions=tuple(value.get("governing_decisions", ())),
                links=tuple(TraceLink(**item) for item in value.get("links", ())),
            )
        except (KeyError, TypeError) as exc:
            raise InvalidGovernedRecord(f"malformed governed record: {exc}") from exc


class RepositoryStateStore:
    """Publish one caller-located canonical record using same-directory replace."""

    def __init__(self, record_path: str | Path):
        self.record_path = Path(record_path)

    def load(self) -> GovernedRecord:
        try:
            value = json.loads(self.record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidGovernedRecord(f"cannot reconstruct {self.record_path}: {exc}") from exc
        if not isinstance(value, dict):
            raise InvalidGovernedRecord("canonical record must be an object")
        return GovernedRecord.from_dict(value)

    def publish(self, record: GovernedRecord, *, affected_scope: str) -> None:
        record.validate()
        self.record_path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{self.record_path.name}.", suffix=".tmp", dir=self.record_path.parent
            )
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(record.to_dict(), stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.record_path)
            temporary = None
        except Exception as exc:
            raise PublicationError(self.record_path, affected_scope, exc) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass


class ImpactLedgerStore:
    """Atomically persist a caller-located modification impact ledger."""

    def __init__(self, ledger_path: str | Path):
        self.ledger_path = Path(ledger_path)

    def load(self) -> ModificationImpactLedger:
        try:
            value = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidGovernedRecord(f"cannot reconstruct {self.ledger_path}: {exc}") from exc
        if not isinstance(value, dict):
            raise InvalidGovernedRecord("impact ledger must be an object")
        return ModificationImpactLedger.from_dict(value)

    def publish(self, ledger: ModificationImpactLedger) -> None:
        ledger.validate()
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{self.ledger_path.name}.", suffix=".tmp", dir=self.ledger_path.parent
            )
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(ledger.to_dict(), stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.ledger_path)
            temporary = None
        except Exception as exc:
            assessment = ledger.assess()
            scope = ", ".join(ledger.affected_behavior_data) or ", ".join(ledger.requested_change)
            if assessment.gaps:
                scope = f"{scope}; gaps: {'; '.join(assessment.gaps)}"
            raise PublicationError(self.ledger_path, scope, exc) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass


class TraceabilityIndex:
    """Disposable forward/backward projection rebuilt only from canonical links."""

    def __init__(self, links: Iterable[TraceLink], current_version: str):
        forward: dict[str, list[TraceLink]] = {}
        backward: dict[str, list[TraceLink]] = {}
        seen: set[tuple[str, str, str]] = set()
        for link in links:
            link.validate(current_version)
            key = (link.source, link.target, link.affected_scope)
            if key in seen:
                raise InvalidGovernedRecord(f"ambiguous duplicate link: {key}")
            seen.add(key)
            forward.setdefault(link.source, []).append(link)
            backward.setdefault(link.target, []).append(link)
        self._forward = {key: tuple(value) for key, value in forward.items()}
        self._backward = {key: tuple(value) for key, value in backward.items()}

    @classmethod
    def rebuild(cls, record: GovernedRecord) -> "TraceabilityIndex":
        return cls(record.links, record.git.version)

    def forward(self, identity: str, *, affected_scope: str | None = None) -> tuple[TraceLink, ...]:
        links = self._forward.get(identity, ())
        return tuple(link for link in links if affected_scope is None or link.affected_scope == affected_scope)

    def backward(self, identity: str, *, affected_scope: str | None = None) -> tuple[TraceLink, ...]:
        links = self._backward.get(identity, ())
        return tuple(link for link in links if affected_scope is None or link.affected_scope == affected_scope)

    def require_path(self, identities: Iterable[str], *, affected_scope: str) -> str:
        path = tuple(identities)
        if len(path) < 2:
            raise ValueError("a trace path needs at least two identities")
        for source, target in zip(path, path[1:]):
            matches = [link for link in self.forward(source, affected_scope=affected_scope) if link.target == target]
            if len(matches) != 1:
                return "INCOMPLETE"
        return "PASS"
