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

## 16. M4.2 planning authority: Stage/Task-Aware Context Selection and Baseline+Delta Reuse

### 16.1 Status and problem

**M4.2 planning authority is APPROVED.** This section approves planning authority only. It does not approve implementation contracts, authorize production coding, or alter the authority established in Sections 1-15.

M4.1 reduced an already-selected operational component safely. M4.2 addresses the upstream selection of context and the repeated inclusion of unchanged context.

### 16.2 Scope

M4.2 planning scope is limited to:

- deterministic stage-aware context selection;
- task-aware selection only where explicit task identity already exists;
- stable content-addressed identity for unchanged context;
- ephemeral baseline plus delta assembly;
- measurement of redundant unchanged bytes; and
- provider-input token usage only when reliable actual schema-1.0.4 usage exists.

### 16.3 Non-goals

M4.2 does not authorize:

- a persistent cache;
- automatic authority truncation;
- authority summarization;
- semantic retrieval or ranking;
- provider or model routing;
- new lifecycle authority;
- new task identity;
- an arbitrary percentage reduction target; or
- inferred token-savings claims.

### 16.4 Context treatment model

The M4.2 context treatment model consists of:

- **always required**;
- **stage-required**;
- **task-required**;
- **reusable unchanged**;
- **delta-only candidate**; and
- **fail-closed exact**.

### 16.5 Authority preservation

M4.2 preserves the following authority rules:

- Product Requirement authority is the PRD.
- Technical Contract authority is the Spec.
- Implementation Decision authority is the Design.
- Tasks cannot override authoritative artifacts.
- Cross-domain conflicts block the affected implementation.
- Authority coverage must equal 100%.
- Authority byte mismatch must equal 0 wherever exact inclusion is required.
- `UNKNOWN` and `MIXED_AUTHORITY` fail closed.
- Summaries cannot replace authority for efficiency.

### 16.6 Stable identity

Stable identity must be deterministic. Later approved contracts must freeze the canonical boundary, namespace and version, digest algorithm and encoding, collision behavior, ordering, duplicate treatment, empty-versus-absent semantics, and stage/task coordinates needed to avoid aliasing.

Identity establishes reuse eligibility only. It creates no persistence or lifecycle authority.

### 16.7 Baseline plus delta

A validated baseline plus delta must reconstruct exactly the same effective ordered provider input as fresh exact assembly.

Any uncertainty, mismatch, stale identity, unsupported provider behavior, or reconstruction failure must fall back to fresh exact assembly.

Local byte reduction must not be described as provider-input savings unless the provider boundary actually avoids retransmitting those unchanged bytes.

### 16.8 Measurement

At minimum, M4.2 evaluation must measure or evaluate:

- total source-context UTF-8 bytes;
- selected-context bytes;
- authority bytes and coverage;
- unchanged repeated bytes;
- delta bytes;
- reuse-eligible and reuse-ineligible bytes, with reasons;
- bytes actually avoided at the provider boundary, if demonstrable;
- authority mismatch;
- semantic regression;
- lifecycle regression;
- gate regression; and
- actual provider input tokens only from reliable schema-1.0.4 usage.

Codex CLI `tokens used`, byte counts, estimates, and tokenizer estimates are not provider-token evidence.

### 16.9 Activation and default

The existing exact BASELINE remains the default. Any future M4.2 evaluation must be explicit opt-in. No migration or state repair may be required merely to disable optimization. Stage08 remains outside scope unless separately authorized.

### 16.10 Failure and fallback

No partial optimized context may be dispatched. Optimization failure cannot introduce retries, lifecycle failures, or altered provider-call cardinality. Existing authority conflicts continue to block the affected implementation.

### 16.11 Telemetry

No telemetry schema change is authorized. The schema remains 1.0.4. M4.2 evaluation metadata remains ephemeral, in-memory, or test-local unless separate authority later approves persistence.

### 16.12 Deterministic evaluation

Controlled repeated executions must cover:

- stage changes;
- task identity present and missing;
- changed and unchanged components;
- duplicates;
- empty and absent inputs;
- `UNKNOWN` and `MIXED_AUTHORITY`;
- authority conflicts;
- identity mismatch and collision simulation;
- stale or missing baseline; and
- unsupported provider reuse.

The required invariants are:

- effective reconstructed provider input equals fresh exact assembly;
- authority coverage equals 100%;
- authority mismatch equals 0;
- semantic regression equals 0;
- lifecycle regression equals 0; and
- gate regression equals 0.

### 16.13 Implementation blockers

Exactly 10 planning blockers remain unresolved before implementation:

1. **Component mapping:** complete the component inventory and always/stage/task mapping.
2. **Stage and task semantics:** identify the authoritative stage-mapping source and existing task-identity semantics.
3. **Authority equivalence:** define exact authority-coverage and byte-equivalence boundaries.
4. **Identity contract:** define namespace, canonicalization, digest, collision, version, order, duplicate, empty, and absent rules.
5. **Baseline and delta contract:** define baseline coordinates, lifetime, trust, invalidation, and atomic delta reconstruction and equivalence.
6. **Provider-boundary proof:** prove any provider boundary where unchanged bytes can actually avoid retransmission without changing effective input.
7. **Activation and fallback contract:** define activation, fallback, call cardinality, and default compatibility.
8. **Evaluation contract:** define measurement boundaries, reuse reasons, controlled corpus, evidence location, and semantic-comparison rubric.
9. **Provider-usage validity:** establish reliable schema-1.0.4 actual-usage availability and its validity test.
10. **Persistence decision:** decide to keep evaluation metadata non-persistent, or obtain separate authority for any persistence or telemetry-schema change.

### 16.14 Non-authoritative suggested implementation slices

Until the blockers in Section 16.13 are resolved, the following suggested slices are **NON-AUTHORITATIVE**:

- component inventory plus stage/task selection;
- stable identity plus unchanged eligibility;
- ephemeral baseline/delta reconstruction;
- provider-boundary reuse evaluation, if supported;
- measurement and evaluation; and
- opt-in integration and regression closure.

**M4.2 IMPLEMENTATION STATUS: BLOCKED**

Coding must not begin until all Section 16 planning blockers required for the affected implementation slice are resolved through separately approved contracts/planning authority.
