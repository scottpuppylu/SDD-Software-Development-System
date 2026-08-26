# Token / Context Architecture v2 — Phase 04 Planning Authority

**Status:** APPROVE WITH AMENDMENTS

**Phase:** Phase 04 — Manifested Context Optimization

**First milestone:** M4.1 — Deterministic Context Manifest and Conservative Operational Reduction

## 1. Purpose

This document establishes new planning authority for Phase 04 and its first milestone, M4.1. It defines the conservative boundary for compiling a deterministic context manifest, preserving the current context package as a baseline, and evaluating an optimized package in which only approved operational Git history may be reduced.

This document is not recovered historical authority. It does not implement the compiler, reduction, caching, or activation mechanism, and it does not amend the telemetry measurement contract or measurement schema 1.0.4.

## 2. Authority boundary

### 2.1 Established architectural constraints

The following constraints predate and govern the Phase 04 planning decisions in this document:

- PRD, Spec, Design, Tasks, governance, and every other authority-bearing input must not be lossy-compressed.
- Domain-specific authority must be preserved. No linear `PRD > Spec > Design` precedence may be introduced.
- A prompt or execution package is compiled context, not authority.
- Telemetry is observational. It cannot decide whether a context component is included, reduced, or omitted.
- Future caching is intended to be content-addressed, but caching is outside M4.1.

This plan does not modify lifecycle authority, `.sdd` authority, the telemetry measurement contract, or schema 1.0.4.

### 2.2 Newly approved Phase 04 and M4.1 decisions

Phase 04 is named **Manifested Context Optimization**. Its first milestone is **M4.1 — Deterministic Context Manifest and Conservative Operational Reduction**. M4.1 introduces planning authority for:

- an ephemeral deterministic `ContextManifest`;
- deterministic BASELINE and OPTIMIZED compilation of the same logical `StageExecutionRequest`;
- exact inclusion of authority, governance, unknown, and mixed-authority inputs;
- explicitly opted-in reduction of `runtime_inputs["GIT_HISTORY"]` only;
- evaluation that treats the existing baseline path as the canonical fallback.

The milestone identifier M3.1 must not be used for this work.

### 2.3 Remaining implementation-contract TBDs

This planning authority intentionally does not select implementation details that require a separate coding contract. The blocking TBDs are enumerated in Section 15.

### 2.4 Deferred future capabilities

Capabilities explicitly outside M4.1 are listed in Section 14. Their mention does not authorize design or implementation.

## 3. Phase 04 scope

Phase 04 begins with manifesting the components that form compiled context and evaluating a narrowly constrained optimization without changing lifecycle or authority behavior. M4.1 is limited to deterministic compilation, conservative classification and inclusion, one approved reducible operational source, explicit evaluation activation, and evidence sufficient to compare baseline and optimized packages.

M4.1 does not establish a general-purpose context budgeter, authority summarizer, retrieval system, router, or cache.

## 4. M4.1 contract

For one logical `StageExecutionRequest`, M4.1 must be able to construct:

- **BASELINE:** the current behavior with unchanged logical/context content; and
- **OPTIMIZED:** the same logical request, with authority and governance included exactly and reduction permitted only for the approved `GIT_HISTORY` target under an explicitly named policy.

The existing baseline path remains the canonical fallback. Default behavior remains BASELINE. OPTIMIZED is initially available only through explicit opt-in/evaluation mode.

No global automatic activation, global token-budget dropping, or lifecycle behavior change is authorized.

## 5. ContextManifest lifecycle and semantics

### 5.1 Lifecycle

For M4.1, `ContextManifest` is an ephemeral execution/compiler object. It is not lifecycle authority and must not be persisted into:

- `.sdd/state`;
- `.sdd/evidence`;
- `.sdd/runs`;
- the artifact registry;
- checkpoint state; or
- telemetry `events.jsonl`.

M4.1 must not require a telemetry schema change. The measurement schema remains 1.0.4. Comparison and evaluation tooling may inspect manifest metadata in memory or in test-local evidence, subject to existing secret-handling and data-minimization rules.

### 5.2 Minimum manifest semantics

A manifest must represent deterministic ordered entries. Each entry must expose at least:

- a stable component identity;
- source role;
- authority treatment;
- inclusion disposition;
- canonical content digest;
- canonical character size;
- canonical UTF-8 byte size;
- an exact, reduced, or omitted state; and
- a reduction policy identifier when reduction applies.

The digest and size fields describe the canonical content represented by the relevant manifest entry/disposition. The coding contract must remove any ambiguity about canonicalization, digest algorithm, identity construction, ordering, and whether pre- and post-reduction representations require separate fields. This plan does not define cache keys.

An omitted state is part of the general manifest vocabulary; M4.1 does not thereby authorize omission of any current context input. Under the approved M4.1 policy, non-target inputs are exact-included, and the approved target may be exact-included or reduced only as its named policy permits.

## 6. Classification and inclusion policy

M4.1 freezes this fail-closed policy:

| Classification | Required treatment |
| --- | --- |
| `KNOWN_AUTHORITY` | Exact include |
| `KNOWN_GOVERNANCE` | Exact include |
| `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY` | Reduction permitted only by an explicitly named policy |
| `UNKNOWN` | Exact include |
| `MIXED_AUTHORITY` | Exact include |

Unknown or mixed classification must always fail closed to exact inclusion, never omission or reduction. Classification must not create a precedence ordering among authority domains. Telemetry must not participate in classification or inclusion decisions.

All existing context inputs other than the specifically approved target in Section 7 remain exact-inclusion unless a later planning amendment explicitly authorizes another source.

## 7. GIT_HISTORY reduction boundary

The only reducible source authorized for the first implementation and evaluation is:

```text
runtime_inputs["GIT_HISTORY"]
```

Reduction is permitted only when this source is classified as `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY` and an explicitly named reduction policy applies. The coding contract must define that policy and its conservative failure behavior before implementation begins.

No authority-bearing content embedded in, combined with, or inseparable from a candidate component may be reduced. Ambiguity or mixed content requires `MIXED_AUTHORITY` treatment and exact inclusion.

Stage09 evidence is not a first-target reduction source. Every other existing context input remains exact-included.

## 8. Baseline and optimized relationship

BASELINE and OPTIMIZED are two compilations of the same logical request under the same M4.1 policy configuration:

- BASELINE preserves current behavior and unchanged logical/context content.
- OPTIMIZED preserves exact authority and governance content and may reduce only the approved `GIT_HISTORY` component.
- Authority-bearing content in BASELINE and OPTIMIZED must be byte-identical.
- The baseline path is canonical fallback and must remain behaviorally unchanged.
- Disabling optimization must require no migration or state repair.

An optimized package is compiled context only. It does not supersede or mutate its source authority.

## 9. Determinism

Identical logical `StageExecutionRequest` inputs under the same M4.1 policy configuration must produce:

- identical ordered manifest semantics;
- identical component dispositions;
- identical component digests;
- identical compiled BASELINE packages; and
- identical compiled OPTIMIZED packages.

Compiler determinism includes classification, ordering, canonicalization, disposition, reduction, rendering, and package assembly to the extent those operations affect the required outputs. Provider stochastic output is outside compiler determinism.

The implementation contract must define the normalized input and policy-configuration boundaries needed to test this requirement without weakening it.

## 10. Activation

Optimization must initially be explicit opt-in/evaluation mode. Default behavior remains BASELINE. M4.1 does not authorize automatic global activation or automatic dropping to meet a global token budget.

The exact public configuration mechanism remains an implementation-contract TBD because this planning authority does not select a mechanism that may belong to another authority domain.

## 11. Failure and fallback

If optimized manifest construction, compilation, or reduction fails, M4.1 must:

1. discard the incomplete optimized package;
2. never dispatch a partial optimized package;
3. retain the unchanged baseline package and path; and
4. leave lifecycle and authority behavior unchanged.

Optimization failure must not become a new lifecycle failure mode. Diagnostic observation remains non-authoritative and must conform to existing secret-handling and data-minimization rules.

The coding contract must define failure boundaries and the atomic handoff that prevents partial optimized dispatch while preserving the requirements above.

## 12. Measurement and evidence

M4.1 evaluation must compare BASELINE and OPTIMIZED for the same logical request and policy configuration. Evidence must be sufficient to establish determinism, inclusion/disposition correctness, digest equality for authority-bearing components, byte reduction in a controlled case, semantic comparison, and absence of lifecycle, gate, blocker, and regression-test regressions.

At least one controlled case must demonstrate positive request/rendered-byte reduction. Character and byte measurements are context-size measurements, not token measurements.

When reliable actual provider input-token usage is available, evaluation must report actual BASELINE versus OPTIMIZED input tokens. When actual provider usage is unavailable, evaluation must not claim token savings from character or byte measurements and must report only measured context/byte reduction.

M4.1 does not freeze an arbitrary minimum percentage reduction. Manifest metadata used by comparison/evaluation tooling remains in-memory or test-local and is subject to existing secret-handling and data-minimization rules; it must not be added to telemetry `events.jsonl` or require a change to schema 1.0.4.

The approved semantic comparison rubric, controlled corpus/cases, and evidence representation remain implementation-contract TBDs.

## 13. M4.1 acceptance criteria

M4.1 passes only when all of the following are demonstrated:

- the manifest is deterministic;
- compilation is deterministic;
- authority-bearing BASELINE and OPTIMIZED content is byte-identical;
- no authority-bearing component is reduced or omitted;
- unknown and mixed context is exact-included;
- `GIT_HISTORY` is the only authorized reducible target;
- at least one controlled case demonstrates positive request/rendered-byte reduction;
- no authority digest mismatch occurs;
- no semantic regression occurs under the approved comparison rubric;
- no lifecycle, gate, or blocker regression occurs;
- baseline-path behavior remains unchanged;
- optimization can be disabled without migration or state repair; and
- all existing regression tests pass.

Actual input-token comparisons are required when reliable provider usage is available. Otherwise, results must be limited to measured context/byte reduction and must not be described as token savings.

## 14. Deferred work

The following capabilities are explicitly deferred beyond M4.1:

- content-addressed cache implementation;
- cache storage or retrieval;
- cache key contract;
- authority-risk routing;
- provider or model routing;
- general token/context budget enforcement;
- automatic dropping to satisfy budgets;
- authority summarization;
- semantic retrieval or ranking;
- Stage08 coding-agent prompt optimization; and
- additional reducible sources.

Deferral means these capabilities are neither required nor authorized by this milestone.

## 15. Implementation entry gate

**M4.1 implementation is BLOCKED.** Coding must not begin until the implementation-contract TBDs necessary for coding are explicitly resolved by the appropriate authority. At minimum, the following remain blocking:

1. **Component inventory and classification mapping:** the complete mapping of current `StageExecutionRequest` context inputs to source roles and conservative classifications, including mixed/unknown handling at actual assembly boundaries.
2. **Manifest representation:** the concrete entry model and the precise relationship between source, baseline, and optimized entry metadata, including how exact/reduced/omitted disposition is represented.
3. **Stable identity and deterministic ordering:** component identity construction, collision handling, ordering rules, and treatment of absent, empty, repeated, or structurally equivalent inputs.
4. **Canonicalization and digest contract:** canonical content boundaries, character-count semantics, UTF-8 encoding rules, digest algorithm and encoding, newline/Unicode handling, and pre-/post-reduction digest and size fields.
5. **Named `GIT_HISTORY` reduction policy:** the policy identifier, deterministic reduction algorithm, preservation rules, limits, behavior for malformed/mixed/unknown content, and proof that no other source can enter the reduction path.
6. **Compiler integration and atomic fallback:** the exact compilation boundary, BASELINE compatibility contract, optimized-package validation, failure boundaries, and dispatch handoff that makes partial optimized dispatch impossible.
7. **Explicit activation mechanism:** the public/configuration surface for opt-in evaluation, its default-off semantics, and the authority responsible for that surface.
8. **Comparison and evidence contract:** the approved semantic comparison rubric, controlled evaluation cases, reliable actual-token availability test, evidence format/location, secret/data-minimization controls, and regression checks.

These TBDs must be resolved without changing the established constraints or expanding the M4.1 reduction boundary. This document deliberately does not invent those details merely to mark the gate ready.

Until the required contracts are approved, planning status is **APPROVE WITH AMENDMENTS**, and implementation readiness is **BLOCKED**.
