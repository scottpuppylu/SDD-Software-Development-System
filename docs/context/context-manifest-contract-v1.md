# Context Manifest Implementation Contract v1

**Status:** APPROVED FOR BLOCKERS 1-4 ONLY

**Phase:** Phase 04 - Manifested Context Optimization

**Milestone:** M4.1 - Deterministic Context Manifest and Conservative Operational Reduction

**Planning authority:** `docs/context/context-optimization-plan-v1.md`

## 1. Scope and authority boundary

This document freezes the M4.1 implementation contract for blockers 1-4 only:

1. component inventory and classification mapping;
2. manifest representation;
3. stable identity and deterministic ordering; and
4. canonicalization and digest behavior.

It does not authorize implementation. In particular, it does not define the `GIT_HISTORY` reduction algorithm, compiler integration or atomic dispatch/fallback, activation, or comparison/evidence behavior. Those remain blockers 5-8.

The `ContextManifest` and its compiler are separate ephemeral compiler models. They do not add fields to `StageExecutionRequest` or `StageExecutionResult`. They have no lifecycle-authority, persistence, telemetry, or cache fields. Source and result bodies remain outside the manifest in ephemeral compilation objects.

This contract introduces no linear `PRD > Spec > Design` precedence. Authority remains domain-specific. Telemetry component classification is observational and MUST NOT be used as authority for manifest classification.

Normative terms `MUST`, `MUST NOT`, `REQUIRED`, and `INVALID` are binding implementation requirements.

## 2. Closed vocabularies

### 2.1 `CompilationMode`

- `BASELINE`
- `OPTIMIZED`

### 2.2 `ManifestClassification`

- `KNOWN_AUTHORITY`
- `KNOWN_GOVERNANCE`
- `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY`
- `UNKNOWN`
- `MIXED_AUTHORITY`

### 2.3 `AuthorityTreatment`

- `EXACT_REQUIRED`
- `APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE`

### 2.4 `InclusionDisposition`

- `EXACT`
- `REDUCED`
- `OMITTED`

`OMITTED` exists in the vocabulary but is INVALID for every M4.1 compiled output.

### 2.5 `ContentKind`

- `TEXT`
- `JSON`
- `ABSENT`
- `EMPTY_MAPPING`
- `EMPTY_LIST`

## 3. Manifest representation

`ContextManifest` has exactly these required minimum semantics:

- `mode: CompilationMode`
- `canonicalization_id: str`
- `entries`: an ordered immutable sequence of `ContextManifestEntry`

For M4.1, `ContextManifest.canonicalization_id` is REQUIRED, non-null, and exactly:

```text
sdd.canonical.utf8-sorted-compact-v1
```

`ContextManifestEntry` has exactly these required minimum semantics:

- `component_id: str`
- `source_role: str`
- `classification: ManifestClassification`
- `authority_treatment: AuthorityTreatment`
- `disposition: InclusionDisposition`
- `content_kind: ContentKind`
- `source_metadata: ContentMetadata`
- `result_metadata: ContentMetadata`
- `reduction_policy_id: str | null`

`ContentMetadata` is:

- `chars: int`
- `utf8_bytes: int`
- `sha256: str`
- `canonicalization_id: str`

Every `ContentMetadata.canonicalization_id` is REQUIRED, non-null, and, for M4.1, exactly `sdd.canonical.utf8-sorted-compact-v1`. Source and result metadata each carry the field independently.

The manifest is metadata only. Each ephemeral compiled entry separately retains the source body and result body needed to render and directly validate canonical-byte identity. Bodies MUST NOT be embedded in the manifest merely to satisfy this validation requirement.

For `EXACT` disposition:

- `source_metadata.chars == result_metadata.chars`;
- `source_metadata.utf8_bytes == result_metadata.utf8_bytes`;
- `source_metadata.sha256 == result_metadata.sha256`;
- `source_metadata.canonicalization_id == result_metadata.canonicalization_id`; and
- source and result canonical bytes are directly identical, or an equivalent invariant is proven by tests that directly compare those bytes.

Digest equality alone is insufficient to establish exact inclusion.

`reduction_policy_id` MUST be null for `EXACT`. It MUST be a non-empty approved identifier for `REDUCED`. M4.1 does not permit `OMITTED`.

## 4. Component inventory and source roles

One logical `StageExecutionRequest` is decomposed only at these boundaries:

| Request source | `source_role` | Component cardinality | Default classification | Treatment |
| --- | --- | --- | --- | --- |
| `contract` | `STAGE_CONTRACT` | one | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |
| `stage_instructions` | `STAGE_INSTRUCTIONS` | one, including absent | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |
| each `artifacts` item | `ARTIFACT` | one per top-level key | closed mapping in Section 5 | `EXACT_REQUIRED` |
| each `semantic_inputs` item | `SEMANTIC_INPUT` | one per top-level key | `UNKNOWN` | `EXACT_REQUIRED` |
| each `runtime_inputs` item | `RUNTIME_INPUT` | one per top-level key | Section 6 | Section 6 |
| `stage_id` | `METADATA_STAGE_ID` | one, including absent if representable | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |
| `stage_name` | `METADATA_STAGE_NAME` | one, including absent if representable | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |
| `stage_type` | `METADATA_STAGE_TYPE` | one, including absent if representable | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |
| `core_question` | `METADATA_CORE_QUESTION` | one, including absent | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |

The governance classifications above are closed structural-role mappings: the stage contract, stage instructions, and stage metadata are governance supplied by the stage registry/instruction assembly boundary. They do not make compiled context into authority.

Nested arbitrary values under one semantic-input or runtime-input key remain one canonical JSON component. They MUST NOT be recursively decomposed into manifest entries unless a later closed, source-specific contract explicitly authorizes that decomposition. Lists therefore remain within their containing logical component; where a future authorized decomposition creates list components, logical indices MUST order ascending.

Absent and present-empty values are distinct. Fixed slots are represented even when absent. Arbitrary map entries exist only for keys actually present; implementations MUST NOT invent a universe of absent arbitrary keys.

## 5. Closed artifact authority mapping

Only the following explicitly enumerated, closed artifact-role mapping may produce `KNOWN_AUTHORITY` or `KNOWN_GOVERNANCE`. An implementation MUST NOT infer either classification from a concept such as “recognized authority,” a filename's appearance, content appearance, telemetry labels, or implementation intuition.

Matching is against the original repository-relative artifact key supplied in `StageExecutionRequest.artifacts`. Matching uses exact Unicode code-point identity, `/` as the repository-relative separator for the listed roles, no Unicode normalization, and no case folding. Absolute or machine-local paths do not match. Except for the two explicitly closed recursive patterns below, no basename or suffix matching is permitted.

| Closed artifact key or pattern | Artifact role | Classification | Treatment |
| --- | --- | --- | --- |
| `docs/proposal.md` | `PRODUCT_INTENT_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `docs/PRD.md` | `PRODUCT_REQUIREMENT_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `docs/spec.md` | `TECHNICAL_CONTRACT_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `docs/Design.md` | `IMPLEMENTATION_DECISION_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `AGENTS.md` | `AGENT_REPOSITORY_GOVERNANCE` | `KNOWN_GOVERNANCE` | `EXACT_REQUIRED` |
| `tasks.md` | `EXECUTION_DECOMPOSITION_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `src/**` | `IMPLEMENTATION_EVIDENCE_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `tests/**` | `IMPLEMENTATION_EVIDENCE_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `docs/handoff/pre-implementation-gate-report.md` | `PRE_IMPLEMENTATION_GATE_DECISION_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `docs/handoff/verification-report.md` | `VERIFICATION_DECISION_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |
| `docs/handoff/handoff-report.md` | `RELEASE_DECISION_AUTHORITY` | `KNOWN_AUTHORITY` | `EXACT_REQUIRED` |

For `src/**` and `tests/**`, `**` means one or more path segments beneath the exact `src/` or `tests/` prefix. It does not match the bare directory name, sibling prefixes, backslash variants, traversal segments, or absolute paths.

`AGENTS.md` treatment is exact: only the root-relative key exactly equal to `AGENTS.md` maps to `AGENT_REPOSITORY_GOVERNANCE`, `KNOWN_GOVERNANCE`, and `EXACT_REQUIRED`. A nested, differently cased, renamed, or similarly named file does not.

For any artifact not covered by this closed mapping:

- classify it `MIXED_AUTHORITY` when authority may be embedded in or inseparable from the component; otherwise
- classify it `UNKNOWN`.

Both classifications require `EXACT_REQUIRED` and `EXACT`. Uncertainty MUST NEVER authorize reduction. When the implementation cannot prove from closed structural provenance that an unmapped artifact contains no embedded or inseparable authority, it MUST use `MIXED_AUTHORITY` rather than speculate.

This mapping is a set of domain roles, not a precedence list. It introduces no ordering of authority among PRD, Spec, Design, governance, or any other domain.

## 6. Runtime classification boundary

Only the exact top-level slot:

```text
runtime_inputs["GIT_HISTORY"]
```

may be classified `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY` and assigned `APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE`.

Eligibility is determined by both the structural `runtime_inputs` container and original top-level key exactly equal to `GIT_HISTORY`. A nested `GIT_HISTORY`, differently cased key, semantic input, artifact, or similarly named value is not eligible. No value/content inspection may grant eligibility.

The eligible entry is `EXACT` in BASELINE. In OPTIMIZED it may be `EXACT` or `REDUCED` only under the named policy required by blocker 5. This contract does not name or define that algorithm. Until blocker 5 is resolved, no `REDUCED` M4.1 package can be validly produced.

All other runtime inputs are `UNKNOWN`, `EXACT_REQUIRED`, and `EXACT`. If an otherwise eligible `GIT_HISTORY` value may contain embedded or inseparable authority under the blocker-5 policy's eventual conservative checks, it MUST fail closed to `MIXED_AUTHORITY`, `EXACT_REQUIRED`, and `EXACT`.

## 7. Stable structural identity

Component identity is the structural request slot, never its content or machine environment:

```text
request/stage-contract
request/stage-instructions
request/artifacts/<encoded-key>
request/semantic-inputs/<encoded-key>
request/runtime-inputs/<encoded-key>
request/metadata/stage-id
request/metadata/stage-name
request/metadata/stage-type
request/metadata/core-question
```

For a dictionary key segment, encode the original key's UTF-8 bytes as lowercase hexadecimal, two hex digits per byte with no prefix or separator. The original key MUST be a string. Encoding performs no Unicode normalization or case folding. Because the full original UTF-8 byte sequence is encoded, distinct valid keys cannot share an encoded segment; any duplicate resulting identity is nevertheless INVALID.

Identity MUST NOT incorporate:

- absolute or machine-local paths;
- timestamps;
- UUIDs;
- process state;
- content digests;
- locale-sensitive transformations;
- Unicode normalization; or
- case folding.

Absent, empty string, empty mapping, and empty list retain the same structural slot identity but distinct content kinds/canonical bytes. Identity does not change when content changes.

## 8. Deterministic ordering

Manifest entries MUST be ordered by these groups:

1. stage contract;
2. stage instructions;
3. artifacts;
4. semantic inputs;
5. runtime inputs; and
6. metadata, in this exact order: `stage_id`, `stage_name`, `stage_type`, `core_question`.

Within each dictionary group, sort by the original key's UTF-8 byte sequence ascending, comparing bytes unsigned and lexicographically. Do not sort by encoded text, locale collation, normalized text, folded case, insertion order, or platform behavior.

Lists remain atomic inside arbitrary semantic/runtime JSON components. Wherever an explicitly authorized component boundary contains ordered list members, their order is logical index ascending.

Ordering MUST be locale-independent and platform-independent. Manifest ordering is descriptive compiler behavior and MUST NOT itself change existing BASELINE provider rendering or map traversal/rendering behavior.

## 9. Content kind and canonicalization

The sole M4.1 canonicalization identifier is:

```text
sdd.canonical.utf8-sorted-compact-v1
```

Logical string components use canonical text. Non-string JSON-domain values use canonical JSON. A missing fixed slot uses `ABSENT`; present empty mapping and list values use `EMPTY_MAPPING` and `EMPTY_LIST`, respectively. `ContentKind` describes the logical value before encoding:

| Logical value | `ContentKind` | Canonical representation |
| --- | --- | --- |
| string, including `""` | `TEXT` | canonical text bytes |
| non-string JSON-domain value except empty mapping/list | `JSON` | canonical JSON bytes |
| absent fixed slot | `ABSENT` | `{"state":"absent"}` |
| present empty mapping | `EMPTY_MAPPING` | `{}` |
| present empty list | `EMPTY_LIST` | `[]` |

JSON `null` is a present `JSON` value and is distinct from `ABSENT`. An empty string is `TEXT` and is distinct from all three explicit empty/absent structural kinds.

### 9.1 Canonical text

Canonical text:

- preserves the original Unicode code-point sequence;
- performs no Unicode normalization;
- performs no newline rewriting;
- performs no trimming, whitespace collapsing, or case folding;
- encodes as UTF-8 with no BOM and no appended trailing newline; and
- uses those exact bytes for metadata and direct equality validation.

### 9.2 Canonical JSON

Canonical JSON:

- accepts only JSON-domain values: objects with string keys, arrays, strings, numbers, booleans, and null;
- rejects non-JSON-domain values, non-string object keys, NaN, and positive or negative infinity;
- recursively sorts every object by each original key's UTF-8 byte sequence ascending;
- uses compact separators equivalent to `,` and `:` with no optional whitespace;
- emits string data without ASCII escaping (`ensure_ascii=false` semantics), while applying only JSON-required escaping;
- preserves JSON string code points with no Unicode normalization;
- preserves JSON number, boolean, and null types rather than converting them to strings;
- encodes the serialized result as UTF-8 with no BOM and no trailing newline; and
- is locale-independent and platform-independent.

Implementations MUST define/restrict their accepted numeric representation so the same accepted logical JSON number has one platform-independent serialized form. A value for which that invariant cannot be established is a canonicalization failure; implementations MUST NOT silently coerce it.

### 9.3 Metadata calculation

For both source and result independently:

- `chars` is the number of Unicode code points in the canonical representation before UTF-8 encoding, not grapheme clusters, UTF-16 code units, display width, or source-object size;
- `utf8_bytes` is the length in bytes of the canonical UTF-8 representation;
- `sha256` is SHA-256 over those exact canonical bytes, encoded as exactly 64 lowercase hexadecimal characters; and
- `canonicalization_id` is exactly `sdd.canonical.utf8-sorted-compact-v1`.

No digest defined here is a cache key. Caching is outside M4.1.

## 10. Disposition invariants by mode

For `BASELINE`, every entry is `EXACT`. Baseline logical/context content and existing provider rendering remain unchanged.

For `OPTIMIZED`:

- every entry is `EXACT` except that the single eligible top-level `runtime_inputs["GIT_HISTORY"]` entry may be `REDUCED` under a later approved blocker-5 policy;
- `UNKNOWN` and `MIXED_AUTHORITY` entries are always `EXACT_REQUIRED` and `EXACT`;
- `KNOWN_AUTHORITY` and `KNOWN_GOVERNANCE` entries are always `EXACT_REQUIRED` and `EXACT`; and
- `OMITTED` is always INVALID.

BASELINE and OPTIMIZED manifests describe separate compilations of the same logical request. Each manifest entry records that compilation's source and result metadata. The manifest does not mutate or supersede source authority.

## 11. Validation and fail-closed behavior

The manifest/compiler validator MUST enforce all of the following:

- `UNKNOWN` means exact inclusion;
- `MIXED_AUTHORITY` means exact inclusion;
- an unknown artifact mapping means `UNKNOWN` or conservative `MIXED_AUTHORITY`, both exact inclusion;
- identity construction failure makes the optimized package invalid and retains BASELINE;
- canonicalization failure makes the optimized package invalid and retains BASELINE;
- any invalid enum or value makes the optimized package invalid and retains BASELINE;
- duplicate component identity makes the optimized package invalid;
- reducible classification outside the exact top-level `runtime_inputs["GIT_HISTORY"]` slot is invalid;
- `REDUCED` without a non-empty approved reduction policy identifier is invalid;
- `REDUCED` on any classification other than `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY` is invalid;
- `OMITTED` in M4.1 is invalid;
- an `EXACT` entry with any source/result metadata mismatch is invalid;
- an `EXACT` entry with source/result canonical-byte mismatch is invalid even if its digests match;
- a metadata canonicalization identifier other than the manifest identifier is invalid; and
- classification uncertainty never authorizes reduction.

“Retains BASELINE” in this section freezes the validation outcome, not dispatch integration. This contract does not resolve the atomic compilation/dispatch/fallback boundary; that remains blocker 6. No partial optimized package is authorized for dispatch.

## 12. Compatibility freeze

M4.1 work governed by this contract MUST preserve all of the following unchanged:

- `StageExecutionRequest`;
- `StageExecutionResult`;
- telemetry schema 1.0.4;
- the telemetry measurement contract;
- `.sdd` authority;
- lifecycle, run, and evidence schemas;
- the existing BASELINE provider-rendering behavior; and
- default BASELINE behavior until the separate activation contract is approved.

The manifest has no lifecycle authority fields, persistence fields, telemetry fields, or cache fields. It MUST NOT be persisted to `.sdd/state`, `.sdd/evidence`, `.sdd/runs`, the artifact registry, checkpoint state, or telemetry `events.jsonl`.

## 13. Resolution and remaining blockers

This contract resolves the implementation-contract definitions for blockers 1-4:

1. **RESOLVED:** Component inventory and classification mapping.
2. **RESOLVED:** Manifest representation.
3. **RESOLVED:** Stable identity and deterministic ordering.
4. **RESOLVED:** Canonicalization and digest contract.

The following remain **BLOCKED** and are not resolved or defined here:

5. **BLOCKED:** Named `GIT_HISTORY` reduction policy.
6. **BLOCKED:** Compiler integration and atomic fallback.
7. **BLOCKED:** Explicit activation mechanism.
8. **BLOCKED:** Comparison and evidence contract.

Therefore M4.1 implementation readiness remains **BLOCKED**. No M4.1 implementation may begin solely on the authority of this blockers 1-4 contract.
