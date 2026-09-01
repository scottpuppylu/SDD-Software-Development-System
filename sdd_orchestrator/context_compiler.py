from __future__ import annotations

from dataclasses import dataclass
import copy
from enum import Enum
import hashlib
import json
from typing import Any

from .executor import StageExecutionRequest


CANONICALIZATION_ID = "sdd.canonical.utf8-sorted-compact-v1"
GIT_HISTORY_REDUCTION_POLICY_ID = "sdd.git-history.newest8-oldest2-v1"
IDENTITY_NAMESPACE = "sdd.context.component"
IDENTITY_VERSION = "m4.2-v1"
TASK_COORDINATE = "task-absent"


class CompilationMode(str, Enum):
    BASELINE = "BASELINE"
    OPTIMIZED = "OPTIMIZED"


class OptimizationCompilationError(ValueError):
    """An optimized candidate failed construction-time integrity checks."""


class ManifestClassification(str, Enum):
    KNOWN_AUTHORITY = "KNOWN_AUTHORITY"
    KNOWN_GOVERNANCE = "KNOWN_GOVERNANCE"
    APPROVED_REDUCIBLE_OPERATIONAL_HISTORY = (
        "APPROVED_REDUCIBLE_OPERATIONAL_HISTORY"
    )
    UNKNOWN = "UNKNOWN"
    MIXED_AUTHORITY = "MIXED_AUTHORITY"


class AuthorityTreatment(str, Enum):
    EXACT_REQUIRED = "EXACT_REQUIRED"
    APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE = (
        "APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE"
    )


class InclusionDisposition(str, Enum):
    EXACT = "EXACT"
    REDUCED = "REDUCED"
    OMITTED = "OMITTED"


class ContentKind(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"
    ABSENT = "ABSENT"
    EMPTY_MAPPING = "EMPTY_MAPPING"
    EMPTY_LIST = "EMPTY_LIST"


class ComponentTreatment(str, Enum):
    ALWAYS_REQUIRED = "ALWAYS_REQUIRED"
    FAIL_CLOSED_EXACT = "FAIL_CLOSED_EXACT"
    DELTA_ONLY_CANDIDATE = "DELTA_ONLY_CANDIDATE"
    STAGE_REQUIRED_CANDIDATE = "STAGE_REQUIRED_CANDIDATE"


class ComponentDeltaKind(str, Enum):
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    REORDERED = "REORDERED"


@dataclass(frozen=True)
class ComponentIdentity:
    namespace: str
    version: str
    stage_coordinate: str
    task_coordinate: str
    component_coordinate: str

    def __post_init__(self) -> None:
        if self.namespace != IDENTITY_NAMESPACE:
            raise ValueError("unrecognized component identity namespace")
        if self.version != IDENTITY_VERSION:
            raise ValueError("unrecognized component identity version")
        _validate_stage_coordinate(self.stage_coordinate)
        if self.task_coordinate != TASK_COORDINATE:
            raise ValueError("task coordinate must remain task-absent")
        _validate_component_coordinate(self.component_coordinate)

    @property
    def text(self) -> str:
        return "/".join((
            self.namespace,
            self.version,
            self.stage_coordinate,
            self.task_coordinate,
            self.component_coordinate,
        ))


@dataclass(frozen=True)
class ComponentSelection:
    identity: ComponentIdentity
    treatment: ComponentTreatment
    candidate_treatment: ComponentTreatment | None
    stage_required: bool
    task_required: bool
    preserve_exact: bool
    authority_protected: bool
    canonical_bytes: bytes
    content_digest: str


@dataclass(frozen=True)
class ExactContextComponent:
    identity: ComponentIdentity
    canonical_bytes: bytes
    content_digest: str
    authority_protected: bool


@dataclass(frozen=True)
class EphemeralContextBaseline:
    namespace: str
    version: str
    stage_coordinate: str
    task_coordinate: str
    canonicalization_id: str
    components: tuple[ExactContextComponent, ...]
    scope: object

    @property
    def identity_sequence(self) -> tuple[ComponentIdentity, ...]:
        return tuple(component.identity for component in self.components)


@dataclass(frozen=True)
class ComponentDelta:
    kind: ComponentDeltaKind
    identity: ComponentIdentity
    baseline_position: int | None
    current_position: int | None
    current_component: ExactContextComponent | None


@dataclass(frozen=True)
class ContextDelta:
    changes: tuple[ComponentDelta, ...]
    baseline_components: tuple[ExactContextComponent, ...]
    current_components: tuple[ExactContextComponent, ...]
    direct_reuse_eligible: bool
    exact_reconstruction_eligible: bool
    invalid_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ReconstructionResult:
    components: tuple[ExactContextComponent, ...]
    reconstructed: bool
    used_fresh_exact: bool
    fresh_exact_required: bool
    exact_match: bool
    authority_coverage_percent: int
    authority_byte_mismatch: int
    invalid_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ContentMetadata:
    chars: int
    utf8_bytes: int
    sha256: str
    canonicalization_id: str


@dataclass(frozen=True)
class ContextManifestEntry:
    component_id: str
    source_role: str
    classification: ManifestClassification
    authority_treatment: AuthorityTreatment
    disposition: InclusionDisposition
    content_kind: ContentKind
    source_metadata: ContentMetadata
    result_metadata: ContentMetadata
    reduction_policy_id: str | None


@dataclass(frozen=True)
class ContextManifest:
    mode: CompilationMode
    canonicalization_id: str
    entries: tuple[ContextManifestEntry, ...]


@dataclass(frozen=True)
class CompiledContextEntry:
    manifest_entry: ContextManifestEntry
    source_body: Any
    result_body: Any


@dataclass(frozen=True)
class CompiledContextPackage:
    mode: CompilationMode
    request: StageExecutionRequest
    manifest: ContextManifest
    entries: tuple[CompiledContextEntry, ...]


@dataclass(frozen=True)
class GitHistoryReduction:
    source_body: Any
    result_body: Any
    disposition: InclusionDisposition
    reduction_policy_id: str | None


def reduce_git_history(value: Any) -> GitHistoryReduction:
    exact = GitHistoryReduction(value, value, InclusionDisposition.EXACT, None)
    if not isinstance(value, str):
        return exact
    if value == "":
        return exact
    if "\r" in value or value.startswith("\n") or value.endswith("\n"):
        return exact
    lines = value.split("\n")
    if len(lines) > 20:
        return exact
    for line in lines:
        if line.count("\t") != 1:
            return exact
        commit_hash, subject = line.split("\t")
        if (len(commit_hash) != 40
                or any(character not in "0123456789abcdef" for character in commit_hash)
                or "\t" in subject or "\n" in subject or "\r" in subject):
            return exact
    if len(lines) <= 10:
        return exact
    omitted = len(lines) - 10
    result = "\n".join(
        lines[:8] + [f"[[GIT_HISTORY_OMITTED_ENTRIES:{omitted}]]"] + lines[-2:]
    )
    return GitHistoryReduction(
        value, result, InclusionDisposition.REDUCED, GIT_HISTORY_REDUCTION_POLICY_ID
    )


_ARTIFACT_ROLES = {
    "docs/proposal.md": ("PRODUCT_INTENT_AUTHORITY", ManifestClassification.KNOWN_AUTHORITY),
    "docs/PRD.md": ("PRODUCT_REQUIREMENT_AUTHORITY", ManifestClassification.KNOWN_AUTHORITY),
    "docs/spec.md": ("TECHNICAL_CONTRACT_AUTHORITY", ManifestClassification.KNOWN_AUTHORITY),
    "docs/Design.md": ("IMPLEMENTATION_DECISION_AUTHORITY", ManifestClassification.KNOWN_AUTHORITY),
    "AGENTS.md": ("AGENT_REPOSITORY_GOVERNANCE", ManifestClassification.KNOWN_GOVERNANCE),
    "tasks.md": ("EXECUTION_DECOMPOSITION_AUTHORITY", ManifestClassification.KNOWN_AUTHORITY),
    "docs/handoff/pre-implementation-gate-report.md": (
        "PRE_IMPLEMENTATION_GATE_DECISION_AUTHORITY",
        ManifestClassification.KNOWN_AUTHORITY,
    ),
    "docs/handoff/verification-report.md": (
        "VERIFICATION_DECISION_AUTHORITY",
        ManifestClassification.KNOWN_AUTHORITY,
    ),
    "docs/handoff/handoff-report.md": (
        "RELEASE_DECISION_AUTHORITY",
        ManifestClassification.KNOWN_AUTHORITY,
    ),
}


def canonical_text_bytes(value: str) -> bytes:
    if not isinstance(value, str):
        raise TypeError("canonical text requires str")
    return value.encode("utf-8")


def _validated_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise TypeError("floating-point JSON numbers are not supported")
    if isinstance(value, list):
        return [_validated_json(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return {
            key: _validated_json(value[key])
            for key in sorted(value, key=lambda item: item.encode("utf-8"))
        }
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    validated = _validated_json(value)
    text = json.dumps(
        validated,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def content_kind_and_bytes(value: Any, *, absent: bool = False) -> tuple[ContentKind, bytes]:
    if absent:
        return ContentKind.ABSENT, b'{"state":"absent"}'
    if isinstance(value, str):
        return ContentKind.TEXT, canonical_text_bytes(value)
    if isinstance(value, dict) and not value:
        return ContentKind.EMPTY_MAPPING, b"{}"
    if isinstance(value, list) and not value:
        return ContentKind.EMPTY_LIST, b"[]"
    return ContentKind.JSON, canonical_json_bytes(value)


def metadata_for_canonical_bytes(canonical: bytes) -> ContentMetadata:
    text = canonical.decode("utf-8")
    return ContentMetadata(
        chars=len(text),
        utf8_bytes=len(canonical),
        sha256=hashlib.sha256(canonical).hexdigest(),
        canonicalization_id=CANONICALIZATION_ID,
    )


def content_metadata(value: Any, *, absent: bool = False) -> ContentMetadata:
    return metadata_for_canonical_bytes(content_kind_and_bytes(value, absent=absent)[1])


def encode_component_key(key: str) -> str:
    if not isinstance(key, str):
        raise TypeError("component dictionary keys must be strings")
    return key.encode("utf-8").hex()


_FIXED_COMPONENT_COORDINATES = frozenset((
    "request/stage-contract",
    "request/stage-instructions",
    "request/metadata/stage-id",
    "request/metadata/stage-name",
    "request/metadata/stage-type",
    "request/metadata/core-question",
))
_KEYED_COMPONENT_PREFIXES = (
    "request/artifacts/",
    "request/semantic-inputs/",
    "request/runtime-inputs/",
)


def _validate_encoded_utf8(value: str, *, label: str, allow_empty: bool) -> None:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise ValueError(f"invalid {label} encoding")
    if value != value.lower() or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"invalid {label} encoding")
    if len(value) % 2:
        raise ValueError(f"invalid {label} encoding")
    try:
        decoded = bytes.fromhex(value).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid {label} UTF-8") from exc
    if decoded.encode("utf-8").hex() != value:
        raise ValueError(f"non-canonical {label} encoding")


def _validate_stage_coordinate(value: str) -> None:
    if value == "stage-absent":
        return
    if not isinstance(value, str) or not value.startswith("stage-id/"):
        raise ValueError("invalid stage coordinate")
    _validate_encoded_utf8(value[len("stage-id/"):], label="stage", allow_empty=True)


def _validate_component_coordinate(value: str) -> None:
    if value in _FIXED_COMPONENT_COORDINATES:
        return
    for prefix in _KEYED_COMPONENT_PREFIXES:
        if isinstance(value, str) and value.startswith(prefix):
            _validate_encoded_utf8(value[len(prefix):], label="component key", allow_empty=True)
            return
    raise ValueError("invalid component coordinate")


def build_component_identity(
    component_coordinate: str, stage_id: str | None
) -> ComponentIdentity:
    if stage_id is not None and not isinstance(stage_id, str):
        raise TypeError("stage identity must be a string or absent")
    stage_coordinate = (
        "stage-absent" if stage_id is None
        else f"stage-id/{stage_id.encode('utf-8').hex()}"
    )
    return ComponentIdentity(
        IDENTITY_NAMESPACE,
        IDENTITY_VERSION,
        stage_coordinate,
        TASK_COORDINATE,
        component_coordinate,
    )


def parse_component_identity(text: str) -> ComponentIdentity:
    if not isinstance(text, str):
        raise TypeError("component identity text must be a string")
    parts = text.split("/")
    if len(parts) < 6 or parts[0] != IDENTITY_NAMESPACE or parts[1] != IDENTITY_VERSION:
        raise ValueError("malformed component identity")
    if parts[2] == "stage-absent":
        stage_coordinate = parts[2]
        task_index = 3
    elif parts[2] == "stage-id" and len(parts) >= 7:
        stage_coordinate = "/".join(parts[2:4])
        task_index = 4
    else:
        raise ValueError("malformed stage coordinate")
    identity = ComponentIdentity(
        parts[0], parts[1], stage_coordinate, parts[task_index],
        "/".join(parts[task_index + 1:]),
    )
    if identity.text != text:
        raise ValueError("non-canonical component identity")
    return identity


def content_digest(canonical: bytes) -> str:
    if not isinstance(canonical, bytes):
        raise TypeError("content digest requires canonical bytes")
    return hashlib.sha256(canonical).hexdigest()


def _recursive_artifact_role(key: str) -> tuple[str, ManifestClassification] | None:
    for prefix in ("src/", "tests/"):
        if key.startswith(prefix):
            remainder = key[len(prefix):]
            segments = remainder.split("/")
            if "\\" not in remainder and remainder and all(
                segment not in ("", ".", "..") for segment in segments
            ):
                return "IMPLEMENTATION_EVIDENCE_AUTHORITY", ManifestClassification.KNOWN_AUTHORITY
    return None


def classify_artifact(key: str) -> tuple[str, ManifestClassification, AuthorityTreatment]:
    if not isinstance(key, str):
        raise TypeError("artifact keys must be strings")
    role_and_classification = _ARTIFACT_ROLES.get(key) or _recursive_artifact_role(key)
    if role_and_classification is None:
        return "ARTIFACT", ManifestClassification.MIXED_AUTHORITY, AuthorityTreatment.EXACT_REQUIRED
    role, classification = role_and_classification
    return role, classification, AuthorityTreatment.EXACT_REQUIRED


def _compiled_entry(
    component_id: str,
    source_role: str,
    classification: ManifestClassification,
    treatment: AuthorityTreatment,
    body: Any,
    *,
    absent: bool = False,
) -> CompiledContextEntry:
    kind, canonical = content_kind_and_bytes(body, absent=absent)
    metadata = metadata_for_canonical_bytes(canonical)
    manifest_entry = ContextManifestEntry(
        component_id=component_id,
        source_role=source_role,
        classification=classification,
        authority_treatment=treatment,
        disposition=InclusionDisposition.EXACT,
        content_kind=kind,
        source_metadata=metadata,
        result_metadata=metadata,
        reduction_policy_id=None,
    )
    return CompiledContextEntry(manifest_entry, body, body)


def _sorted_items(values: dict[str, Any]) -> list[tuple[str, Any]]:
    if not isinstance(values, dict):
        raise TypeError("request component groups must be dictionaries")
    if any(not isinstance(key, str) for key in values):
        raise TypeError("request component dictionary keys must be strings")
    return sorted(values.items(), key=lambda item: item[0].encode("utf-8"))


def build_baseline_package(request: StageExecutionRequest) -> CompiledContextPackage:
    entries: list[CompiledContextEntry] = []
    entries.append(_compiled_entry(
        "request/stage-contract", "STAGE_CONTRACT",
        ManifestClassification.KNOWN_GOVERNANCE, AuthorityTreatment.EXACT_REQUIRED,
        request.contract,
    ))
    entries.append(_compiled_entry(
        "request/stage-instructions", "STAGE_INSTRUCTIONS",
        ManifestClassification.KNOWN_GOVERNANCE, AuthorityTreatment.EXACT_REQUIRED,
        request.stage_instructions, absent=request.stage_instructions is None,
    ))
    for key, body in _sorted_items(request.artifacts):
        role, classification, treatment = classify_artifact(key)
        entries.append(_compiled_entry(
            f"request/artifacts/{encode_component_key(key)}", role,
            classification, treatment, body,
        ))
    for key, body in _sorted_items(request.semantic_inputs):
        entries.append(_compiled_entry(
            f"request/semantic-inputs/{encode_component_key(key)}", "SEMANTIC_INPUT",
            ManifestClassification.UNKNOWN, AuthorityTreatment.EXACT_REQUIRED, body,
        ))
    for key, body in _sorted_items(request.runtime_inputs):
        eligible = key == "GIT_HISTORY"
        entries.append(_compiled_entry(
            f"request/runtime-inputs/{encode_component_key(key)}", "RUNTIME_INPUT",
            (ManifestClassification.APPROVED_REDUCIBLE_OPERATIONAL_HISTORY
             if eligible else ManifestClassification.UNKNOWN),
            (AuthorityTreatment.APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE
             if eligible else AuthorityTreatment.EXACT_REQUIRED),
            body,
        ))
    metadata_slots = (
        ("stage-id", "METADATA_STAGE_ID", request.stage_id),
        ("stage-name", "METADATA_STAGE_NAME", request.stage_name),
        ("stage-type", "METADATA_STAGE_TYPE", request.stage_type),
        ("core-question", "METADATA_CORE_QUESTION", request.core_question),
    )
    for identity, role, body in metadata_slots:
        entries.append(_compiled_entry(
            f"request/metadata/{identity}", role,
            ManifestClassification.KNOWN_GOVERNANCE, AuthorityTreatment.EXACT_REQUIRED,
            body, absent=body is None,
        ))
    immutable_entries = tuple(entries)
    manifest = ContextManifest(
        CompilationMode.BASELINE,
        CANONICALIZATION_ID,
        tuple(entry.manifest_entry for entry in immutable_entries),
    )
    package = CompiledContextPackage(
        CompilationMode.BASELINE, request, manifest, immutable_entries
    )
    validate_compiled_package(package)
    return package


def build_optimized_package(request: StageExecutionRequest) -> CompiledContextPackage:
    source_snapshot = copy.deepcopy(request)
    baseline = build_baseline_package(request)
    optimized_request = copy.deepcopy(request)
    reduction = reduce_git_history(request.runtime_inputs.get("GIT_HISTORY")) \
        if "GIT_HISTORY" in request.runtime_inputs else None
    if reduction is None or reduction.disposition is InclusionDisposition.EXACT:
        optimized_entries = baseline.entries
    else:
        optimized_request.runtime_inputs["GIT_HISTORY"] = reduction.result_body
        git_id = f"request/runtime-inputs/{encode_component_key('GIT_HISTORY')}"
        changed: list[CompiledContextEntry] = []
        for compiled in baseline.entries:
            if compiled.manifest_entry.component_id != git_id:
                changed.append(compiled)
                continue
            result_bytes = canonical_text_bytes(reduction.result_body)
            entry = compiled.manifest_entry
            changed.append(CompiledContextEntry(
                ContextManifestEntry(
                    component_id=entry.component_id,
                    source_role=entry.source_role,
                    classification=entry.classification,
                    authority_treatment=entry.authority_treatment,
                    disposition=InclusionDisposition.REDUCED,
                    content_kind=entry.content_kind,
                    source_metadata=entry.source_metadata,
                    result_metadata=metadata_for_canonical_bytes(result_bytes),
                    reduction_policy_id=GIT_HISTORY_REDUCTION_POLICY_ID,
                ),
                reduction.source_body,
                reduction.result_body,
            ))
        optimized_entries = tuple(changed)
    manifest = ContextManifest(
        CompilationMode.OPTIMIZED,
        CANONICALIZATION_ID,
        tuple(entry.manifest_entry for entry in optimized_entries),
    )
    package = CompiledContextPackage(
        CompilationMode.OPTIMIZED, optimized_request, manifest, optimized_entries
    )
    try:
        validate_compiled_package(package)
    except ValueError as exc:
        raise OptimizationCompilationError(
            "optimized candidate package validation failed"
        ) from exc
    if request != source_snapshot:
        raise OptimizationCompilationError(
            "source request was mutated during optimized compilation"
        )
    return package


class ContextCompiler:
    def compile_baseline(self, request: StageExecutionRequest) -> CompiledContextPackage:
        return build_baseline_package(request)

    def compile_optimized(self, request: StageExecutionRequest) -> CompiledContextPackage:
        return build_optimized_package(request)


def _body_bytes(entry: CompiledContextEntry, *, result: bool) -> bytes:
    body = entry.result_body if result else entry.source_body
    absent = entry.manifest_entry.content_kind is ContentKind.ABSENT
    return content_kind_and_bytes(body, absent=absent)[1]


def validate_compiled_package(package: CompiledContextPackage) -> None:
    if not isinstance(package.mode, CompilationMode):
        raise ValueError("invalid compilation mode")
    if package.manifest.mode is not package.mode:
        raise ValueError("package and manifest modes differ")
    if package.manifest.canonicalization_id != CANONICALIZATION_ID:
        raise ValueError("invalid manifest canonicalization ID")
    if len(package.entries) != len(package.manifest.entries):
        raise ValueError("compiled and manifest entry counts differ")
    identities = [entry.manifest_entry.component_id for entry in package.entries]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate component identity")
    expected = build_expected_component_order(package.request)
    if identities != expected:
        raise ValueError("invalid component ordering")
    git_id = f"request/runtime-inputs/{encode_component_key('GIT_HISTORY')}"
    for compiled, manifest_entry in zip(package.entries, package.manifest.entries):
        entry = compiled.manifest_entry
        if entry != manifest_entry:
            raise ValueError("compiled entry does not match manifest")
        if not all((isinstance(entry.classification, ManifestClassification),
                    isinstance(entry.authority_treatment, AuthorityTreatment),
                    isinstance(entry.disposition, InclusionDisposition),
                    isinstance(entry.content_kind, ContentKind))):
            raise ValueError("invalid enum value")
        if entry.disposition is InclusionDisposition.OMITTED:
            raise ValueError("M4.1 entries must never be OMITTED")
        if package.mode is CompilationMode.BASELINE and entry.disposition is not InclusionDisposition.EXACT:
            raise ValueError("BASELINE entries must be EXACT")
        if entry.disposition is InclusionDisposition.EXACT and entry.reduction_policy_id is not None:
            raise ValueError("EXACT entries require null reduction policy")
        if entry.classification in (ManifestClassification.UNKNOWN, ManifestClassification.MIXED_AUTHORITY):
            if entry.authority_treatment is not AuthorityTreatment.EXACT_REQUIRED:
                raise ValueError("unknown and mixed entries require exact treatment")
        if entry.classification in (ManifestClassification.KNOWN_AUTHORITY, ManifestClassification.KNOWN_GOVERNANCE):
            if entry.authority_treatment is not AuthorityTreatment.EXACT_REQUIRED:
                raise ValueError("authority and governance entries require exact treatment")
        if entry.classification is ManifestClassification.APPROVED_REDUCIBLE_OPERATIONAL_HISTORY:
            if entry.component_id != git_id or entry.authority_treatment is not AuthorityTreatment.APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE:
                raise ValueError("reducible classification outside top-level GIT_HISTORY")
        elif entry.authority_treatment is not AuthorityTreatment.EXACT_REQUIRED:
            raise ValueError("reduction eligibility requires reducible classification")
        source_bytes = _body_bytes(compiled, result=False)
        result_bytes = _body_bytes(compiled, result=True)
        actual_kind = content_kind_and_bytes(
            compiled.source_body,
            absent=entry.content_kind is ContentKind.ABSENT,
        )[0]
        if actual_kind is not entry.content_kind:
            raise ValueError("content kind does not match source body")
        if entry.disposition is InclusionDisposition.REDUCED:
            if (package.mode is not CompilationMode.OPTIMIZED
                    or entry.component_id != git_id
                    or entry.classification is not ManifestClassification.APPROVED_REDUCIBLE_OPERATIONAL_HISTORY
                    or entry.authority_treatment is not AuthorityTreatment.APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE
                    or entry.reduction_policy_id != GIT_HISTORY_REDUCTION_POLICY_ID):
                raise ValueError("invalid reduced GIT_HISTORY entry")
            if source_bytes == result_bytes:
                raise ValueError("REDUCED source and result must differ")
            reduction = reduce_git_history(compiled.source_body)
            if (reduction.disposition is not InclusionDisposition.REDUCED
                    or reduction.result_body != compiled.result_body):
                raise ValueError("REDUCED result does not match approved policy")
        else:
            if source_bytes != result_bytes:
                raise ValueError("EXACT source and result canonical bytes differ")
            if entry.source_metadata != entry.result_metadata:
                raise ValueError("EXACT source and result metadata differ")
        if entry.source_metadata != metadata_for_canonical_bytes(source_bytes):
            raise ValueError("source metadata does not match body")
        if entry.result_metadata != metadata_for_canonical_bytes(result_bytes):
            raise ValueError("result metadata does not match body")
        if entry.source_metadata.canonicalization_id != CANONICALIZATION_ID:
            raise ValueError("invalid metadata canonicalization ID")
        if entry.result_metadata.canonicalization_id != CANONICALIZATION_ID:
            raise ValueError("invalid result metadata canonicalization ID")
    if package.mode is CompilationMode.OPTIMIZED:
        redecomposed = build_baseline_package(package.request)
        if len(redecomposed.entries) != len(package.entries):
            raise ValueError("optimized request decomposition count differs")
        for candidate, expected_entry in zip(redecomposed.entries, package.entries):
            if candidate.manifest_entry.component_id != expected_entry.manifest_entry.component_id:
                raise ValueError("optimized request decomposition identity differs")
            if _body_bytes(candidate, result=True) != _body_bytes(expected_entry, result=True):
                raise ValueError("optimized request does not match manifest result")


def build_expected_component_order(request: StageExecutionRequest) -> list[str]:
    identities = ["request/stage-contract", "request/stage-instructions"]
    identities.extend(f"request/artifacts/{encode_component_key(key)}" for key, _ in _sorted_items(request.artifacts))
    identities.extend(f"request/semantic-inputs/{encode_component_key(key)}" for key, _ in _sorted_items(request.semantic_inputs))
    identities.extend(f"request/runtime-inputs/{encode_component_key(key)}" for key, _ in _sorted_items(request.runtime_inputs))
    identities.extend((
        "request/metadata/stage-id", "request/metadata/stage-name",
        "request/metadata/stage-type", "request/metadata/core-question",
    ))
    return identities


def _declared_required_coordinates(
    stage_id: str | None, stages: dict[str, Any]
) -> frozenset[str]:
    if not isinstance(stages, dict):
        raise TypeError("authoritative stage mapping must be a dictionary")
    if stage_id is None or stage_id not in stages:
        return frozenset()
    declaration = stages[stage_id]
    if not isinstance(declaration, dict):
        raise ValueError("stage declaration must be a dictionary")
    required = declaration.get("required_inputs", {})
    if not isinstance(required, dict):
        raise ValueError("required_inputs must be a dictionary")
    coordinates: set[str] = set()
    groups = (
        ("files", "request/artifacts/"),
        ("semantic", "request/semantic-inputs/"),
        ("runtime", "request/runtime-inputs/"),
    )
    for group, prefix in groups:
        keys = required.get(group, [])
        if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
            raise ValueError(f"required_inputs.{group} must be a list of strings")
        coordinates.update(prefix + encode_component_key(key) for key in keys)
    return frozenset(coordinates)


def validate_component_selections(
    selections: tuple[ComponentSelection, ...] | list[ComponentSelection],
) -> None:
    identities: dict[ComponentIdentity, bytes] = {}
    digest_bodies: dict[str, bytes] = {}
    for selection in selections:
        if not isinstance(selection, ComponentSelection):
            raise TypeError("invalid component selection")
        if selection.identity in identities:
            raise ValueError("duplicate complete component identity")
        if content_digest(selection.canonical_bytes) != selection.content_digest:
            raise ValueError("content digest does not match canonical bytes")
        previous = digest_bodies.get(selection.content_digest)
        if previous is not None and previous != selection.canonical_bytes:
            raise ValueError("digest collision or canonical-content ambiguity")
        if (not selection.preserve_exact or selection.task_required
                or (selection.authority_protected and not selection.preserve_exact)):
            raise ValueError("Slice 1 selection must preserve exact content")
        if selection.candidate_treatment is not None and (
            selection.candidate_treatment is not ComponentTreatment.STAGE_REQUIRED_CANDIDATE
            or not selection.stage_required
        ):
            raise ValueError("invalid stage-required candidate treatment")
        identities[selection.identity] = selection.canonical_bytes
        digest_bodies[selection.content_digest] = selection.canonical_bytes


def select_stage_candidates(
    request: StageExecutionRequest, stages: dict[str, Any]
) -> tuple[ComponentSelection, ...]:
    """Plan conservative Slice 1 treatments without omitting or transforming input.

    ``stages`` must be the mapping under ``stages`` from the authoritative
    ``.sdd/stages.yaml`` document. This pure helper never loads or persists it.
    """
    required = _declared_required_coordinates(request.stage_id, stages)
    baseline = build_baseline_package(request)
    selected: list[ComponentSelection] = []
    git_coordinate = f"request/runtime-inputs/{encode_component_key('GIT_HISTORY')}"
    for compiled in baseline.entries:
        coordinate = compiled.manifest_entry.component_id
        stage_required = coordinate in required
        if coordinate in _FIXED_COMPONENT_COORDINATES:
            treatment = ComponentTreatment.ALWAYS_REQUIRED
        elif coordinate == git_coordinate:
            treatment = ComponentTreatment.DELTA_ONLY_CANDIDATE
        else:
            treatment = ComponentTreatment.FAIL_CLOSED_EXACT
        canonical = _body_bytes(compiled, result=False)
        authority_protected = (
            compiled.manifest_entry.authority_treatment
            is AuthorityTreatment.EXACT_REQUIRED
        )
        selected.append(ComponentSelection(
            identity=build_component_identity(coordinate, request.stage_id),
            treatment=treatment,
            candidate_treatment=(
                ComponentTreatment.STAGE_REQUIRED_CANDIDATE
                if stage_required else None
            ),
            stage_required=stage_required,
            task_required=False,
            preserve_exact=True,
            authority_protected=authority_protected,
            canonical_bytes=canonical,
            content_digest=content_digest(canonical),
        ))
    result = tuple(selected)
    validate_component_selections(result)
    return result


def _exact_components(
    components: tuple[ComponentSelection | ExactContextComponent, ...]
    | list[ComponentSelection | ExactContextComponent],
) -> tuple[ExactContextComponent, ...]:
    exact: list[ExactContextComponent] = []
    for component in components:
        if isinstance(component, ComponentSelection):
            exact.append(ExactContextComponent(
                component.identity,
                component.canonical_bytes,
                component.content_digest,
                component.authority_protected,
            ))
        elif isinstance(component, ExactContextComponent):
            exact.append(component)
        else:
            raise TypeError("invalid exact context component")
    return tuple(exact)


def _component_validation_reasons(
    components: tuple[ExactContextComponent, ...],
    *,
    expected_stage_coordinate: str | None = None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    identities: set[ComponentIdentity] = set()
    digest_bodies: dict[str, bytes] = {}
    for component in components:
        if not isinstance(component.identity, ComponentIdentity):
            reasons.append("malformed_identity")
            continue
        identity = component.identity
        if (identity.namespace != IDENTITY_NAMESPACE
                or identity.version != IDENTITY_VERSION):
            reasons.append("identity_namespace_or_version_mismatch")
        if identity.task_coordinate != TASK_COORDINATE:
            reasons.append("task_coordinate_not_absent")
        if (expected_stage_coordinate is not None
                and identity.stage_coordinate != expected_stage_coordinate):
            reasons.append("stage_coordinate_mismatch")
        if identity in identities:
            reasons.append("duplicate_identity")
        identities.add(identity)
        if not isinstance(component.canonical_bytes, bytes):
            reasons.append("canonical_bytes_unavailable")
            continue
        actual_digest = content_digest(component.canonical_bytes)
        if component.content_digest != actual_digest:
            reasons.append("content_digest_mismatch")
        previous = digest_bodies.get(component.content_digest)
        if previous is not None and previous != component.canonical_bytes:
            reasons.append("digest_canonical_ambiguity")
        digest_bodies[component.content_digest] = component.canonical_bytes
    return tuple(dict.fromkeys(reasons))


def build_ephemeral_baseline(
    fresh_exact_components: tuple[ComponentSelection | ExactContextComponent, ...]
    | list[ComponentSelection | ExactContextComponent],
    *,
    scope: object,
) -> EphemeralContextBaseline:
    """Capture an in-memory baseline from one already fresh exact assembly."""
    if scope is None:
        raise ValueError("an ephemeral scope object is required")
    components = _exact_components(fresh_exact_components)
    if not components:
        raise ValueError("fresh exact assembly must establish its coordinate envelope")
    stage_coordinate = components[0].identity.stage_coordinate
    reasons = _component_validation_reasons(
        components, expected_stage_coordinate=stage_coordinate
    )
    if reasons:
        raise ValueError("invalid fresh exact assembly: " + ", ".join(reasons))
    return EphemeralContextBaseline(
        IDENTITY_NAMESPACE,
        IDENTITY_VERSION,
        stage_coordinate,
        TASK_COORDINATE,
        CANONICALIZATION_ID,
        components,
        scope,
    )


def compare_baseline_to_current(
    baseline: EphemeralContextBaseline,
    current_fresh_exact: tuple[ComponentSelection | ExactContextComponent, ...]
    | list[ComponentSelection | ExactContextComponent] | None,
    *,
    scope: object,
) -> ContextDelta:
    """Classify exact component changes without granting omission authority."""
    reasons: list[str] = []
    if not isinstance(baseline, EphemeralContextBaseline):
        raise TypeError("invalid ephemeral baseline")
    if baseline.scope is not scope:
        reasons.append("scope_mismatch")
    if (baseline.namespace != IDENTITY_NAMESPACE
            or baseline.version != IDENTITY_VERSION):
        reasons.append("identity_namespace_or_version_mismatch")
    if baseline.task_coordinate != TASK_COORDINATE:
        reasons.append("task_coordinate_not_absent")
    if baseline.canonicalization_id != CANONICALIZATION_ID:
        reasons.append("canonicalization_mismatch")
    reasons.extend(_component_validation_reasons(
        baseline.components, expected_stage_coordinate=baseline.stage_coordinate
    ))
    if current_fresh_exact is None:
        reasons.append("current_fresh_exact_unavailable")
        return ContextDelta(
            (), baseline.components, (), False, False,
            tuple(dict.fromkeys(reasons)),
        )

    current = _exact_components(current_fresh_exact)
    reasons.extend(_component_validation_reasons(
        current, expected_stage_coordinate=baseline.stage_coordinate
    ))
    baseline_by_id = {item.identity: (position, item)
                      for position, item in enumerate(baseline.components)}
    current_by_id = {item.identity: (position, item)
                     for position, item in enumerate(current)}
    changes: list[ComponentDelta] = []
    for position, component in enumerate(baseline.components):
        current_match = current_by_id.get(component.identity)
        if current_match is None:
            changes.append(ComponentDelta(
                ComponentDeltaKind.REMOVED, component.identity, position, None, None
            ))
            if component.authority_protected:
                reasons.append("authority_protected_component_removed")
            continue
        current_position, current_component = current_match
        if (component.content_digest == current_component.content_digest
                and component.canonical_bytes != current_component.canonical_bytes):
            reasons.append("digest_canonical_ambiguity")
        kind = (ComponentDeltaKind.UNCHANGED
                if (component.content_digest == current_component.content_digest
                    and component.canonical_bytes == current_component.canonical_bytes)
                else ComponentDeltaKind.CHANGED)
        changes.append(ComponentDelta(
            kind, component.identity, position, current_position, current_component
        ))
        if current_position != position:
            changes.append(ComponentDelta(
                ComponentDeltaKind.REORDERED, component.identity, position,
                current_position, current_component,
            ))
    for position, component in enumerate(current):
        if component.identity not in baseline_by_id:
            changes.append(ComponentDelta(
                ComponentDeltaKind.ADDED, component.identity, None, position, component
            ))
    invalid_reasons = tuple(dict.fromkeys(reasons))
    direct = not invalid_reasons and all(
        change.kind is ComponentDeltaKind.UNCHANGED for change in changes
    ) and len(changes) == len(current)
    return ContextDelta(
        tuple(changes), baseline.components, current, direct,
        not invalid_reasons, invalid_reasons,
    )


def reconstruct_exact_context(
    baseline: EphemeralContextBaseline,
    delta: ContextDelta,
    *,
    scope: object,
) -> ReconstructionResult:
    """Atomically reconstruct and prove equality to the fresh exact target."""
    reasons = list(delta.invalid_reasons)
    if baseline.scope is not scope:
        reasons.append("scope_mismatch")
    if baseline.components != delta.baseline_components:
        reasons.append("delta_baseline_mismatch")
    if not delta.exact_reconstruction_eligible:
        return _fresh_exact_fallback(delta.current_components, reasons)

    baseline_by_id = {component.identity: component
                      for component in baseline.components}
    change_by_id = {
        change.identity: change.current_component
        for change in delta.changes
        if change.kind in (ComponentDeltaKind.CHANGED, ComponentDeltaKind.ADDED)
    }
    candidate: list[ExactContextComponent] = []
    for target in delta.current_components:
        component = change_by_id.get(target.identity, baseline_by_id.get(target.identity))
        if component is None:
            reasons.append("missing_reconstructed_component")
            break
        candidate.append(component)
    candidate_tuple = tuple(candidate)
    reasons.extend(validate_reconstruction(candidate_tuple, delta.current_components))
    if reasons:
        return _fresh_exact_fallback(delta.current_components, reasons)
    return ReconstructionResult(
        candidate_tuple, True, False, False, True, 100, 0, ()
    )


def validate_reconstruction(
    reconstructed: tuple[ExactContextComponent, ...],
    current_fresh_exact: tuple[ExactContextComponent, ...],
) -> tuple[str, ...]:
    reasons = list(_component_validation_reasons(current_fresh_exact))
    reasons.extend(_component_validation_reasons(reconstructed))
    if len(reconstructed) != len(current_fresh_exact):
        reasons.append("component_count_mismatch")
    if tuple(item.identity for item in reconstructed) != tuple(
        item.identity for item in current_fresh_exact
    ):
        reasons.append("identity_sequence_mismatch")
    for candidate, target in zip(reconstructed, current_fresh_exact):
        if candidate.canonical_bytes != target.canonical_bytes:
            reasons.append("canonical_byte_mismatch")
        if candidate.content_digest != target.content_digest:
            reasons.append("content_digest_mismatch")
        if candidate.authority_protected != target.authority_protected:
            reasons.append("authority_mapping_mismatch")
    return tuple(dict.fromkeys(reasons))


def _fresh_exact_fallback(
    current: tuple[ExactContextComponent, ...], reasons: list[str]
) -> ReconstructionResult:
    available = bool(current) and not _component_validation_reasons(current)
    fallback = current if available else ()
    return ReconstructionResult(
        fallback, False, available, True, available, 100 if available else 0, 0,
        tuple(dict.fromkeys(reasons)),
    )
