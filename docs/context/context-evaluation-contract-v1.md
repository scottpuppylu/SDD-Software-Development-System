# Context Evaluation Contract v1

**Status:** APPROVED - BLOCKER 8 RESOLVED

**Phase:** Phase 04 - Manifested Context Optimization

**Milestone:** M4.1 - Deterministic Context Manifest and Conservative Operational Reduction

**Planning authority:** `docs/context/context-optimization-plan-v1.md`

**Related contracts:** `docs/context/context-manifest-contract-v1.md`, `docs/context/git-history-reduction-policy-v1.md`, `docs/context/context-compiler-integration-contract-v1.md`, `docs/context/context-activation-contract-v1.md`, and `docs/telemetry/measurement-contract-v1.md`

## 1. Scope and authority boundary

This document freezes the approved M4.1 Blocker 8 comparison and evidence contract. It defines the exact comparison unit, mandatory controlled cases, semantic and deterministic comparison requirements, byte/context measurement, actual-token evidence eligibility, optional live-provider evaluation, evidence representation, the required bounded evaluation report, data minimization, regression requirements, and evaluation status.

This document resolves Blocker 8 only. It does not implement or independently authorize the compiler, reducer, activation mechanism, evaluation tooling, production-code changes, test changes, telemetry changes, schema migration, persistence, or lifecycle changes. It does not redefine any existing authority, gate, lifecycle, artifact-registry, or `.sdd` contract.

Normative terms `MUST`, `MUST NOT`, and `REQUIRED` are binding implementation and evaluation requirements.

## 2. Evaluation purpose

M4.1 evaluation MUST prove all of the following:

- deterministic `ContextManifest` construction;
- deterministic BASELINE and OPTIMIZED compilation;
- canonical-byte identity of every authority and governance component;
- exact inclusion of `UNKNOWN` and `MIXED_AUTHORITY` components;
- `runtime_inputs["GIT_HISTORY"]` is the only reducible component;
- at least one controlled case demonstrates both fewer optimized logical-request UTF-8 bytes and fewer optimized rendered-provider-payload UTF-8 bytes than BASELINE;
- no semantic regression;
- no lifecycle regression;
- no Stage07, Stage09, or Stage10 gate regression;
- no blocker or next-action regression;
- no fallback regression;
- no provider-call-cardinality regression;
- default BASELINE compatibility; and
- the complete existing regression suite passes.

No arbitrary minimum percentage reduction is authorized. Character or byte reduction MUST NOT be described as token savings.

## 3. Exact comparison unit

One comparison pair is two compilations, BASELINE and OPTIMIZED, of the same logical `StageExecutionRequest`.

Both sides MUST use identical source inputs and configuration, including:

- stage ID;
- stage name;
- stage type;
- core question;
- stage contract;
- stage instructions;
- authority artifacts and their original keys;
- semantic inputs;
- runtime inputs before reduction;
- code revision;
- canonicalization contract;
- reduction policy;
- provider, model, and provider configuration when provider execution is compared;
- executor configuration; and
- deterministic fixtures.

The source request MUST remain unchanged. BASELINE and OPTIMIZED may differ only in:

1. the result body of the exact top-level `runtime_inputs["GIT_HISTORY"]` component when reduction is approved; and
2. deterministic downstream reconstruction, rendering, serialization, and measurement caused solely by that approved change.

Observational IDs, timestamps, and provider stochastic output are excluded from logical comparison identity.

## 4. Mandatory controlled cases

Local deterministic unit and integration tests are mandatory. The controlled evaluation corpus MUST include at least:

1. BASELINE compatibility;
2. no eligible `GIT_HISTORY`;
3. valid 0-entry history;
4. valid 10-entry history;
5. valid 11-entry reducible history;
6. valid 20-entry reducible history;
7. malformed history fail-closed;
8. authority and governance byte equality;
9. representative `UNKNOWN` exact inclusion;
10. representative `MIXED_AUTHORITY` exact inclusion;
11. optimization-specific pre-dispatch fallback;
12. shared-prerequisite non-fallback where safely injectable;
13. BASELINE-only custom executor;
14. Stage08 BASELINE-only behavior;
15. repeated deterministic compilation;
16. provider-call cardinality; and
17. activation unset versus explicit BASELINE equivalence.

Reducer-specific tests MUST separately cover the complete malformed-input table frozen by `docs/context/git-history-reduction-policy-v1.md`.

Live provider calls are not required for compiler or contract correctness.

## 5. Semantic comparison rubric

Deterministic local comparison MUST compare the validated `StageExecutionResult` and resulting lifecycle behavior. BASELINE and OPTIMIZED MUST preserve equivalent lifecycle-significant semantics, including, as applicable:

- status;
- result;
- classification;
- ordered remediation reasons;
- normalized convergence tasks;
- task identities;
- allowed paths;
- verification commands;
- lifecycle-consumed metadata;
- required artifact path set;
- deterministic artifact content;
- result validation outcome;
- allowed-output-path validation outcome;
- blocking state and reasons;
- TBD conclusions;
- authority-conflict conclusions;
- lifecycle transition;
- next action;
- output-write behavior;
- convergence persistence;
- run recording;
- artifact-registry behavior;
- checkpoint behavior; and
- controller routing.

Any lifecycle-significant difference is a semantic regression unless an existing authority explicitly permits that difference.

Provider free-form narrative is not required to be text-identical unless it is itself an authoritative or deterministic required artifact.

### 5.1 Gate semantics and `INCOMPLETE`

This rubric preserves, and does not redefine, existing gate authority. The gate-result domains are:

- Stage07: `PASS | FAIL | INCOMPLETE`;
- Stage09: `PASS | FAIL | INCOMPLETE`, plus existing classification semantics where applicable; and
- Stage10: existing release-decision semantics.

Stage09 classification MUST NOT replace or remove the `PASS | FAIL | INCOMPLETE` gate-result domain.

BASELINE versus OPTIMIZED comparison MUST detect any change in the meaning, availability, or interpretation of Stage07 or Stage09 `INCOMPLETE` as a semantic and gate regression.

### 5.2 Stochastic provider results

For stochastic live providers:

- narrative equality is not asserted;
- artifact byte equality is not asserted merely because the provider is stochastic;
- each result independently MUST satisfy existing result, output, gate, and lifecycle contracts;
- formal decisions, blocking conclusions, and authority conclusions may be compared;
- narrative wording alone MUST NOT determine PASS or FAIL; and
- live results MUST NOT replace deterministic semantic tests.

## 6. Determinism contract

Two identical compilations are the minimum comparison count for every determinism fixture. Repeated identical inputs and configuration MUST compare equal for:

- manifest mode;
- canonicalization ID;
- entry count and order;
- component IDs;
- source roles;
- content kinds;
- classifications;
- authority treatments;
- dispositions;
- source metadata;
- result metadata;
- `reduction_policy_id`;
- compiled-request logical values and types;
- deterministic rendered payload;
- omission-marker text, placement, and count;
- selected compilation state;
- fallback classification; and
- prepared payload where safely representable without secrets.

Timestamps, UUIDs, event IDs, provider request IDs, absolute machine paths, locale, process-local state, and accidental insertion ordering MUST NOT affect deterministic comparison.

## 7. Byte and context measurement

All measurements in this section MUST use canonicalization ID:

```text
sdd.canonical.utf8-sorted-compact-v1
```

Evaluation MUST measure the following for both BASELINE and OPTIMIZED:

- logical request characters, UTF-8 bytes, and SHA-256;
- rendered provider payload characters, UTF-8 bytes, and SHA-256; and
- each manifest source and result component's characters, UTF-8 bytes, SHA-256, and canonicalization ID.

Evaluation MUST also record:

- source history entry count;
- result retained commit-entry count;
- omission count;
- disposition; and
- reduction policy ID.

Exact inclusion requires direct canonical-byte equality. Digest equality alone is insufficient.

A component reduction requires all of:

- changed canonical bytes;
- fewer UTF-8 bytes;
- `REDUCED` disposition; and
- the exact approved reduction policy ID.

At least one controlled case MUST prove both:

```text
optimized_request_utf8_bytes < baseline_request_utf8_bytes
optimized_rendered_utf8_bytes < baseline_rendered_utf8_bytes
```

For multi-part provider rendering, evaluation MUST compare each real rendered part and the total bytes of the ordered real parts. It MUST NOT invent synthetic separators. Wire measurement may be reported separately, but it does not replace rendered measurement.

## 8. Actual token evidence

Actual input-token comparison may be reported only from existing schema-1.0.4 `provider_call` usage when both comparison sides independently satisfy all of:

- `availability == available`;
- `quality == actual`;
- `usage_source == openai_responses_usage`; and
- `input_tokens` is a valid provider-reported non-negative integer.

If either side does not satisfy every condition, the evaluation MUST report:

```text
token_usage = unavailable
```

For Codex CLI, usage remains unavailable. Evaluation MUST NOT estimate usage, parse stdout, parse stderr, or parse token-looking text. Unavailable MUST NOT be interpreted as zero.

When actual usage is unavailable, evaluation MUST report only bytes, characters, and digests. It MUST NOT estimate tokens or claim token savings. Actual token unavailability alone does not make M4.1 `INCOMPLETE`.

This contract does not change telemetry schema `1.0.4`.

## 9. Live-provider evaluation

Live provider calls are optional and may be used only for actual provider-token evidence or non-blocking operational corroboration. They are not required to prove compiler or integration correctness.

When used, a paired comparison MUST preserve the same provider, model, logical request, code revision, and non-secret configuration. Only the authorized `GIT_HISTORY` reduction may differ. Provider stochasticity MUST be acknowledged. Semantic PASS or FAIL MUST NOT be determined solely from narrative wording. Duplicate live calls MUST NOT be issued merely to manufacture token evidence.

## 10. Evidence representation and persistence

Approved evidence forms are:

- automated test assertions;
- in-memory comparison projections;
- test-local temporary files where necessary;
- aggregate non-sensitive counts, digests, enums, and statuses; and
- the required bounded Markdown evaluation report in Section 11.

`ContextManifest`, source and result bodies, and prepared payload bodies remain ephemeral. Tests MUST clean temporary evidence.

Evaluation MUST NOT persist:

- manifest bodies;
- source or result bodies;
- raw `GIT_HISTORY`;
- reduced `GIT_HISTORY`;
- raw prompts;
- provider payload bodies;
- raw provider responses;
- optimization state in `.sdd`; or
- new telemetry events or fields.

No new machine-readable repository evidence schema is authorized.

## 11. Required M4.1 evaluation report

M4.1 implementation closure MUST create:

```text
docs/context/m4.1-evaluation-report.md
```

This bounded report is REQUIRED M4.1 implementation-closure evidence. Passing automated tests plus this bounded report constitute the required M4.1 evaluation evidence under this contract.

The report is non-authoritative implementation-evaluation evidence. It is not planning authority, Product Requirement authority, Technical Contract authority, Implementation Decision authority, lifecycle authority, Stage07/09/10 gate authority, `.sdd` evidence, telemetry, or artifact-registry authority.

### 11.1 Required safe aggregate content

The report MUST contain only safe aggregate evidence and MUST include:

- tested revision;
- canonicalization ID;
- reduction policy ID;
- controlled case names;
- `PASS`, `FAIL`, or `INCOMPLETE` per case;
- request and rendered byte and character counts;
- omission counts;
- authority exact-match count;
- authority mismatch count;
- `UNKNOWN` exact-match count;
- `MIXED_AUTHORITY` exact-match count;
- deterministic-comparison outcome;
- semantic-comparison outcome;
- actual token usage with provenance, or `unavailable`;
- fallback results;
- provider-call-cardinality results;
- focused test result;
- telemetry test result;
- full regression result; and
- overall M4.1 evaluation status.

### 11.2 Prohibited report content

The report MUST NOT contain:

- raw authority bodies;
- raw prompts;
- raw or reduced `GIT_HISTORY`;
- commit subjects;
- provider transcripts;
- raw provider responses;
- secrets;
- environment dumps;
- arbitrary exception text; or
- unsanitized absolute filesystem paths.

## 12. Secret and data minimization

Evaluation MUST never retain or display:

- raw environment values;
- API keys, credentials, authorization values, or cookies;
- secret lengths or secret hashes;
- complete prompts or complete provider payloads;
- raw provider responses;
- stdout or stderr;
- raw or reduced Git history;
- real commit subjects when not required;
- source artifact bodies;
- arbitrary exception text;
- unsanitized absolute paths; or
- sensitive transport headers or envelopes.

Permitted evidence SHOULD prefer SHA-256 only for permitted non-secret content; character, UTF-8-byte, entry, and omission counts; component and policy IDs; closed enums and statuses; sanitized repository-relative paths; and typed failure categories.

Secrets are excluded, not hashed or measured.

## 13. Regression requirements

M4.1 implementation closure requires all of:

- focused optimization tests PASS;
- telemetry tests PASS;
- the complete existing test suite PASS;
- `git diff --check` PASS;
- default or unset BASELINE compatibility PASS;
- explicit BASELINE and unset equivalence PASS;
- Stage08 BASELINE-only behavior PASS;
- telemetry schema remains exactly `1.0.4`;
- two identical compilations per determinism fixture compare equal;
- the positive request and rendered byte-reduction controlled case PASS; and
- no optimization evaluation evidence is written to `.sdd` or telemetry.

## 14. Evaluation status

The only evaluation statuses are:

- `PASS`
- `FAIL`
- `INCOMPLETE`

### 14.1 PASS

`PASS` means all mandatory deterministic cases, semantic checks, regressions, reduction proof, fallback checks, and cardinality checks pass. Actual token usage may be unavailable.

### 14.2 FAIL

`FAIL` means an executed mandatory criterion has a negative result, including any:

- authority or governance mismatch;
- non-exact `UNKNOWN` or `MIXED_AUTHORITY` treatment;
- unauthorized reduction;
- semantic regression;
- lifecycle, gate, blocker, or next-action regression;
- fallback regression;
- provider-call-cardinality regression;
- nondeterministic compilation;
- failure to demonstrate the required positive byte reduction;
- BASELINE incompatibility;
- implementation-attributable regression failure;
- prohibited evidence persistence; or
- secret exposure.

### 14.3 INCOMPLETE

`INCOMPLETE` means a mandatory case was not executed, required non-token evidence could not be collected, or required regression attribution remains unresolved, without an observed negative result.

If both missing evidence and a demonstrated mandatory failure exist, `FAIL` wins. Actual provider-token unavailability alone does not cause `INCOMPLETE`.

## 15. Resolution and implementation readiness

8. **RESOLVED:** Comparison and evidence contract.

With this document approved, Blockers 1-8 are **CONTRACT-RESOLVED**.

M4.1 implementation is not complete. Coding is not automatically authorized by this document alone. The next step is **M4.1 implementation-entry review / implementation planning**. This contract introduces no new planning blocker.
