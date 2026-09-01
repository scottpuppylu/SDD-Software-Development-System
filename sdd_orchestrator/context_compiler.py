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
