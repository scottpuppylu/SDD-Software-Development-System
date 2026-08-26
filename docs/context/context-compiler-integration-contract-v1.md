# Context Compiler Integration Contract v1

**Status:** APPROVED - BLOCKER 6 RESOLVED

**Phase:** Phase 04 - Manifested Context Optimization

**Milestone:** M4.1 - Deterministic Context Manifest and Conservative Operational Reduction

**Planning authority:** `docs/context/context-optimization-plan-v1.md`

**Manifest contract:** `docs/context/context-manifest-contract-v1.md`

**Reduction policy:** `docs/context/git-history-reduction-policy-v1.md`

## 1. Scope and authority boundary

This document freezes the approved M4.1 Blocker 6 compiler-integration and atomic-fallback contract. It defines compiler ownership, the `StageRunner.run()` integration point, executor preparation and dispatch boundaries, optimized-package validation, failure precedence, provider-call cardinality, and BASELINE compatibility.

This document resolves Blocker 6 only. It does not define or authorize the explicit activation mechanism, comparison or evidence contract, implementation of the compiler or reducer, production-code changes, test changes, persistence, or schema migration.

Normative terms `MUST`, `MUST NOT`, `REQUIRED`, and `INVALID` are binding implementation requirements. Conceptual type and method names in this document freeze responsibilities and boundaries, not exact class, file, protocol, or adapter spelling.

## 2. Compiler ownership

M4.1 has a separate ephemeral compiler boundary conceptually owned by:

```text
sdd_orchestrator.context_compiler.ContextCompiler
```

The exact class and file spelling is an implementation detail.

`ContextCompiler` owns:

- decomposition of `StageExecutionRequest` into the components frozen by the manifest contract;
- classification;
- canonicalization;
- `ContextManifest` construction;
- the approved `GIT_HISTORY` reduction;
- reconstruction of an optimized request when required; and
- validation of the compilation, packages, entries, manifest/request relationship, and optimized candidate.

`ContextCompiler` MUST NOT own:

- provider invocation;
- telemetry authority;
- lifecycle transitions;
- persistence;
- `StageExecutionResult` validation;
- output writes; or
- checkpoints.

The compiler input is one `StageExecutionRequest`. The source request is borrowed read-only and MUST NOT be mutated, including any nested value. The compiler output is an ephemeral `ContextCompilation`.

## 3. Ephemeral compilation model

The conceptual minimum semantics are:

```text
ContextCompilation
  status
  source_request
  baseline
  optimized | null
  selected | null
  fallback_reason | null

CompiledContextPackage
  mode: BASELINE | OPTIMIZED
  request: StageExecutionRequest
  manifest: ContextManifest
  immutable ordered compiled entries

CompiledContextEntry
  manifest_entry
  source_body
  result_body

PreparedExecution
  selected_mode
  selected_request
  executor-owned immutable prepared payload
  executor-owned non-authoritative dispatch metadata
```

These models are ephemeral. They MUST NOT contain persistence, telemetry-authority, lifecycle, or cache fields. They MUST NOT be persisted as authority or state.

The BASELINE package uses the original `StageExecutionRequest` object. The OPTIMIZED package uses a newly constructed request and MUST NOT retain mutable aliasing through which the source request or any nested source value could be altered.

## 4. `StageRunner.run()` integration point

Compilation integrates in `StageRunner.run()` after:

1. `build_request()` has produced the original logical request; and
2. existing `stage_request` telemetry has measured that original logical request.

Compilation occurs before the current executor execution boundary. Conceptually:

```text
request = build_request(...)
measure_stage_request(request)

compilation = compiler.compile(request, mode)
result = dispatch_coordinator.execute(executor, compilation)
```

The compiler and dispatch coordinator MUST preserve the existing surrounding lifecycle and result-handling behavior. Authority or classification logic MUST NOT be moved into providers.

`Stage08CodexRunner` and `CodexCLI` do not consume `StageExecutionRequest` and remain BASELINE-only in M4.1.

## 5. Executor preparation and dispatch boundary

Executors that support OPTIMIZED execution require an internal atomic capability equivalent to:

```text
prepare(selected_request) -> PreparedExecution
dispatch(prepared_execution) -> StageExecutionResult
```

This capability MAY be implemented through a private protocol or adapter. It MUST NOT change the public compatibility surface:

```text
StageExecutor.execute(StageExecutionRequest)
```

Custom executors remain BASELINE-only unless they explicitly support the atomic preparation capability. The system MUST NOT call `execute()` speculatively to discover optimization support.

Preparation MUST complete all selected-request rendering, serialization, payload construction, and selected-package invariant checks that can fail before provider or subprocess invocation. Preparation MUST NOT initiate a network, provider, or subprocess call.

Dispatch accepts only a complete immutable `PreparedExecution`. No incomplete or partially built optimized candidate is dispatchable.

## 6. Shared prerequisite precedence

Before interpreting any preparation error as optimization fallback, the executor/dispatch boundary MUST structurally distinguish:

```text
SHARED_EXECUTOR_PREREQUISITE_FAILURE
```

from:

```text
OPTIMIZATION_SPECIFIC_PREPARATION_FAILURE
```

This distinction MUST arise from the operation boundary or typed/structured outcome. An implementation MUST NOT classify a failure merely by matching exception text.

### 6.1 Shared executor prerequisite failure

A `SHARED_EXECUTOR_PREREQUISITE_FAILURE` is independent of the selected request and would prevent both unchanged BASELINE and OPTIMIZED execution. It includes, at minimum:

- required executable unavailable;
- required provider configuration unavailable;
- required API credential absent or unusable when detectable before dispatch;
- executor initialization or configuration failure independent of the selected request; and
- command or provider capability unavailable independent of the selected request.

A shared executor prerequisite failure:

- is a genuine existing executor failure;
- MUST NOT become `OPTIMIZATION_FALLBACK`;
- MUST NOT trigger a BASELINE retry;
- MUST NOT perform a second provider or subprocess attempt; and
- preserves existing executor failure semantics.

Shared prerequisites SHOULD be checked once per logical execution before optimization-specific payload preparation when feasible. A common preflight result MAY be reused by selected-payload preparation, but it remains ephemeral, non-authoritative, and MUST NOT be persisted as authority or state.

### 6.2 Optimization-specific preparation failure

An `OPTIMIZATION_SPECIFIC_PREPARATION_FAILURE` is attributable only to preparation of the selected optimized package while unchanged BASELINE remains independently valid and preparable. Examples include:

- optimized request reconstruction or rendering failure;
- optimized-only payload serialization failure;
- optimized package invariant failure; and
- selected optimized content that cannot be prepared.

Only an optimization-specific failure occurring before dispatch may trigger BASELINE fallback.

## 7. Explicit-optimization compilation flow

When the separately governed activation mechanism explicitly requests optimization, the logical execution MUST proceed in this order:

1. Build the original logical `StageExecutionRequest`.
2. Emit existing `stage_request` telemetry for the original logical request.
3. Retain that original request unchanged as BASELINE.
4. Construct the BASELINE manifest and package.
5. Construct an independent OPTIMIZED candidate.
6. Apply only `sdd.git-history.newest8-oldest2-v1` and only to the exact top-level `runtime_inputs["GIT_HISTORY"]` slot.
7. Reconstruct a new candidate `StageExecutionRequest` only when needed.
8. Validate the complete candidate and its manifest/request relationship.
9. Complete shared executor prerequisite or preflight handling under Section 6.
10. Prepare the complete optimized payload without dispatch.
11. Mark `OPTIMIZED_READY` only after all applicable validation and preparation succeeds.
12. Dispatch the selected prepared payload exactly once.

If an optimization-specific construction, validation, reconstruction, or preparation failure occurs before dispatch, the coordinator MUST discard the optimized candidate, retain unchanged BASELINE, prepare BASELINE, and dispatch BASELINE exactly once.

If a shared executor prerequisite fails, the coordinator MUST preserve the genuine executor failure and MUST NOT fallback.

## 8. Validation before optimized dispatch

The following validation and readiness checks are REQUIRED in deterministic order:

1. manifest structure and canonicalization identifiers are valid;
2. component identities are valid and unique;
3. entry ordering is deterministic and valid;
4. classifications and treatments are valid;
5. every `EXACT` component has canonical-byte-identical source and result bodies;
6. every `EXACT` component's metadata exactly matches its content;
7. only the exact top-level `runtime_inputs["GIT_HISTORY"]` component may be `REDUCED`;
8. a reduced entry's classification is exactly `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY`;
9. a reduced entry's policy identifier is exactly `sdd.git-history.newest8-oldest2-v1`;
10. reduced-result metadata exactly matches the reduced result body;
11. no entry is `OMITTED`;
12. the optimized `StageExecutionRequest` is structurally valid;
13. re-decomposing the optimized candidate yields components matching the manifest result bodies;
14. every request field other than the eligible `GIT_HISTORY` value equals BASELINE;
15. unchanged BASELINE remains intact and available;
16. shared prerequisite handling passes; and
17. complete optimized payload preparation succeeds.

If the approved reducer produces canonical bytes unchanged from source, the entry remains `EXACT` with a null `reduction_policy_id`; optimization is not applicable.

## 9. BASELINE compatibility freeze

BASELINE means current behavior. The following are frozen:

- `request.to_dict()` has the same value, key order, nested values, nested types, and insertion behavior;
- `_provider_system_instructions()` has exact string equality;
- `_provider_user_input()` has exact string equality, including formatting;
- the Codex reasoning combined prompt has exact string and UTF-8-byte identity;
- OpenAI instructions and input have exact string and UTF-8-byte identity;
- OpenAI request rendering and serialization remain unchanged;
- `ExternalCommandExecutor` stdin has the exact current JSON-string behavior;
- `StaticExecutor` BASELINE receives the original request object; and
- the public `StageExecutor.execute(StageExecutionRequest)` compatibility surface remains unchanged.

M4.1 MUST NOT redesign provider rendering. In OPTIMIZED mode, only the approved `GIT_HISTORY` value may cause a rendered difference from BASELINE.

## 10. Atomic fallback and failure outcomes

Only either of these packages may be dispatched:

- fully validated and fully prepared OPTIMIZED; or
- unchanged and fully prepared BASELINE.

The required outcomes are:

| Condition | Required outcome |
| --- | --- |
| Optimization-specific failure before dispatch | `OPTIMIZATION_FALLBACK`; prepare and dispatch BASELINE once |
| Shared prerequisite failure | Genuine executor failure; no fallback |
| BASELINE preparation failure | Genuine executor failure; no further fallback |
| Provider failure after dispatch begins | Preserve current failure; no BASELINE second call |
| Response or result parsing failure after dispatch | Preserve current failure; no BASELINE second call |

No partially built optimized candidate is dispatchable. Fallback is atomic selection of a complete independent BASELINE payload, not continuation from partial optimized state.

## 11. Dispatch boundaries

Dispatch begins at these exact conceptual boundaries:

| Executor | Dispatch begins |
| --- | --- |
| `OpenAIResponsesExecutor` | on entry into `urllib.request.urlopen(...)` |
| `CodexExecReasoningExecutor` | on entry into `subprocess.run(...)` |
| `ExternalCommandExecutor` | on entry into `subprocess.run(...)` |
| `StaticExecutor` | on invocation of its selected one-shot execution operation |
| Stage08 `CodexCLI` | on entry into `subprocess.run(...)`; BASELINE-only in M4.1 |

Before dispatch, only an optimization-specific preparation failure may cause fallback. After dispatch begins there is no fallback, no automatic optimization retry, and no duplicate provider or subprocess call.

## 12. Provider-call cardinality

For one logical execution, provider or subprocess cardinality is frozen as follows:

| Outcome | Provider/subprocess calls |
| --- | --- |
| OPTIMIZED success | one optimized call |
| BASELINE | one BASELINE call |
| Optimization-specific fallback before dispatch | one BASELINE call total |
| Shared prerequisite failure detected before dispatch | zero calls |
| Optimized dispatch failure | one failed optimized call and zero BASELINE retries |

If a shared prerequisite cannot be detected before the existing dispatch boundary, existing boundary semantics are preserved, but no second attempt may be added. Preparation itself MUST NOT initiate a provider, network, or subprocess call. Optimization MUST NOT increase provider-call cardinality.

## 13. Telemetry non-interference

Existing `stage_request` telemetry continues to observe only the original logical `StageExecutionRequest`. The compiled, optimized, selected, or fallback request MUST NOT generate a second `stage_request` event.

Provider-call telemetry remains attached to the actual dispatched provider call. Abandoned preparation produces no provider-call telemetry.

This contract authorizes no manifest body, Git-history copy, fallback metadata field, or new telemetry field. The telemetry measurement contract remains unchanged and telemetry schema remains 1.0.4. Telemetry remains observational and MUST NOT become compiler, classification, fallback, or dispatch authority.

## 14. Lifecycle non-interference

M4.1 compiler integration MUST NOT alter:

- `StageExecutionResult` schema or validation;
- output writes;
- convergence persistence;
- lifecycle transitions;
- run recording;
- artifact registry behavior;
- Stage07, Stage09, or Stage10 gate meaning;
- checkpoint semantics; or
- controller routing.

Run and lifecycle recording continue using the original logical request wherever existing behavior does so. A compiler or optimization-specific pre-dispatch failure is not a lifecycle failure when unchanged BASELINE can validly dispatch. Genuine shared prerequisite and provider failures retain existing semantics.

## 15. Executor compatibility matrix

| Executor | M4.1 capability |
| --- | --- |
| OpenAI Responses | BASELINE and OPTIMIZED |
| `CodexExecReasoningExecutor` | BASELINE and OPTIMIZED |
| `ExternalCommandExecutor` | BASELINE and OPTIMIZED |
| `StaticExecutor` | BASELINE and OPTIMIZED for tests; BASELINE receives original request object |
| Custom `StageExecutor` | BASELINE by default; OPTIMIZED only with explicit atomic preparation support |
| `Stage08CodexRunner` / `CodexCLI` | BASELINE-only |

No executor may be invoked speculatively to determine whether it supports optimization.

## 16. Internal optimization taxonomy

The closed ephemeral internal status concepts are:

```text
OPTIMIZATION_NOT_APPLICABLE
OPTIMIZATION_FALLBACK
OPTIMIZED_READY
```

`OPTIMIZATION_NOT_APPLICABLE` includes:

- optimization default-off;
- a BASELINE-only executor;
- no eligible component; and
- the approved policy producing unchanged canonical bytes.

`OPTIMIZATION_FALLBACK` includes only optimization-specific construction, validation, reconstruction, or preparation failures occurring before dispatch.

`OPTIMIZED_READY` means the candidate is valid, preparation is complete, and the selected immutable payload is dispatchable.

Shared prerequisite failures and provider execution failures are outside this taxonomy. These concepts are ephemeral and internal; they MUST NOT become lifecycle, result, persistence, or telemetry fields.

## 17. Compatibility and non-authorization

This contract authorizes no change to:

- `StageExecutionRequest` schema;
- `StageExecutionResult` schema;
- telemetry schema 1.0.4;
- the telemetry measurement contract;
- `.sdd` authority;
- lifecycle, run, or evidence schemas;
- default BASELINE behavior;
- provider rendering beyond the single approved optimized `GIT_HISTORY` difference; or
- provider-call cardinality.

It authorizes no persistence or schema migration and does not implement compiler, reducer, activation, or evidence behavior.

## 18. Resolution and remaining blockers

6. **RESOLVED:** Compiler integration and atomic fallback.
7. **BLOCKED:** Explicit activation mechanism.
8. **BLOCKED:** Comparison and evidence contract.

This document resolves Blocker 6 only. M4.1 implementation readiness remains **BLOCKED** until Blockers 7 and 8 are separately resolved by their appropriate authority.
