# Context Activation Contract v1

**Status:** APPROVED - BLOCKER 7 RESOLVED

**Phase:** Phase 04 - Manifested Context Optimization

**Milestone:** M4.1 - Deterministic Context Manifest and Conservative Operational Reduction

**Planning authority:** `docs/context/context-optimization-plan-v1.md`

**Manifest contract:** `docs/context/context-manifest-contract-v1.md`

**Reduction policy:** `docs/context/git-history-reduction-policy-v1.md`

**Compiler integration contract:** `docs/context/context-compiler-integration-contract-v1.md`

## 1. Scope and authority boundary

This document freezes the approved M4.1 Blocker 7 explicit activation mechanism. It defines activation ownership, the sole public configuration source, its exact grammar and default, resolution scope, typed propagation, invalid-configuration behavior, interaction with optimized dispatch, and compatibility requirements.

This document resolves Blocker 7 only. It does not define or authorize the comparison and evidence contract, implementation of activation, the compiler or reducer, production-code changes, test changes, persistence, telemetry changes, schema migration, provider or model routing, or lifecycle changes.

Activation is operational configuration only. It is not PRD, Spec, Design, Tasks, gate, lifecycle, or `.sdd` authority. Normative terms `MUST`, `MUST NOT`, `REQUIRED`, and `INVALID` are binding implementation requirements. Conceptual type and composition names freeze responsibilities and boundaries, not exact class, file, protocol, or adapter spelling.

## 2. Activation ownership

Activation belongs only to the application composition/runtime configuration layer.

CLI or application startup MUST:

1. read the public activation configuration once;
2. validate it once;
3. resolve one typed `CompilationMode`; and
4. inject that mode into controller and `StageRunner` composition.

`StageRunner.run()` receives and uses the already resolved mode and MUST NOT reread the environment. `ContextCompiler` receives the resolved mode and MUST NOT own activation. Providers and executors MUST NOT own activation or reread activation configuration. Lifecycle and `.sdd` MUST NOT own activation.

## 3. Sole public activation surface

The only public activation source for M4.1 is exactly:

```text
SDD_CONTEXT_COMPILATION_MODE
```

M4.1 MUST NOT add a CLI activation flag, `.sdd` activation setting, provider-local activation, model-local activation, persisted run activation, or any second public configuration source. Internal typed propagation parameters are not additional configuration sources.

## 4. Exact grammar and mode vocabulary

The complete public grammar is:

| Environment state or exact value | Resolved mode |
| --- | --- |
| unset | `CompilationMode.BASELINE` |
| `BASELINE` | `CompilationMode.BASELINE` |
| `OPTIMIZED` | `CompilationMode.OPTIMIZED` |

Parsing is case-sensitive and performs no trimming. An empty string, lowercase or mixed-case value, leading or trailing whitespace, Unicode lookalike, or value with extra characters is INVALID.

There are no aliases. In particular, `1`, `0`, `true`, `false`, `yes`, `no`, `on`, `off`, `enabled`, `evaluation`, and `auto` are INVALID. Heuristic activation is forbidden.

The existing `CompilationMode` vocabulary MUST be reused and remains exactly:

- `BASELINE`
- `OPTIMIZED`

`OPTIMIZED_EVALUATION` or any other activation enum MUST NOT be introduced. Evaluation describes authorized M4.1 use; it is not a third mode.

## 5. Default and resolution scope

The default is always `CompilationMode.BASELINE`. Optimization requires explicit, exact `OPTIMIZED` opt-in. Automatic, heuristic, token-threshold, authority-risk, provider/model, and stage-result activation are forbidden.

The environment value is resolved once per application/controller execution. The resulting mode applies to every eligible `StageRunner` reasoning-stage execution performed by that command/controller execution. Changing the process environment after composition MUST NOT change the already resolved execution mode.

A directly or programmatically constructed `StageRunner` defaults to `CompilationMode.BASELINE` unless an already resolved typed `CompilationMode` is explicitly supplied.

Regardless of the resolved mode:

- `Stage08CodexRunner` and `CodexCLI` remain BASELINE-only; and
- a custom `StageExecutor` without atomic optimized preparation capability remains BASELINE-only.

## 6. Typed propagation contract

The conceptual propagation path is:

```text
SDD_CONTEXT_COMPILATION_MODE
-> application-startup parser/validator
-> one typed CompilationMode
-> direct StageRunner / PipelineController / FullSystemController composition
-> StageRunner
-> StageRunner.run()
-> ContextCompiler.compile(original_request, resolved_mode)
-> Blocker 6 dispatch coordinator
```

There is one resolved activation decision per logical stage execution. Controllers only propagate the typed mode. Providers, executors, the compiler, and `StageRunner.run()` MUST NOT inspect the environment. A per-run `StageRunner.run()` override is not authorized in M4.1. No competing source or precedence hierarchy is permitted.

## 7. Invalid public configuration

Any invalid `SDD_CONTEXT_COMPILATION_MODE` value MUST fail application startup/configuration validation before:

- `StageExecutionRequest` construction;
- lifecycle mutation;
- compiler execution; and
- provider or subprocess dispatch.

Invalid explicit configuration MUST NOT silently fall back to `CompilationMode.BASELINE`.

The diagnostic MAY identify the variable name, a safely represented invalid value, and the accepted values `BASELINE` and `OPTIMIZED`. It MUST NOT dump the process environment.

## 8. Programmatic misuse and source conflicts

Internal APIs accept only typed `CompilationMode`. Supplying an invalid or non-`CompilationMode` internal value is programmer misuse and MUST deterministically fail before request construction or dispatch. Internal propagation is not a second activation source.

If an implementation accidentally exposes both a resolved mode and another override source, it MUST reject the conflict and MUST NOT choose by implicit precedence.

## 9. Activation versus optimized dispatch

`CompilationMode.OPTIMIZED` means only that optimized compilation and preparation are attempted when the stage and executor are eligible. It does not guarantee optimized dispatch.

The required outcomes are:

| Condition | Required outcome |
| --- | --- |
| Eligible `GIT_HISTORY`, valid reduction, and valid preparation | Dispatch OPTIMIZED once |
| No eligible `GIT_HISTORY` | BASELINE; `OPTIMIZATION_NOT_APPLICABLE` |
| Reduction yields unchanged canonical bytes | BASELINE; `OPTIMIZATION_NOT_APPLICABLE` |
| BASELINE-only executor | BASELINE; `OPTIMIZATION_NOT_APPLICABLE` |
| Stage08 | Existing BASELINE-only path |
| Optimization-specific pre-dispatch failure | Blocker 6 atomic fallback; dispatch BASELINE once |
| Shared executor prerequisite failure | Existing genuine failure; no fallback |
| Provider failure after dispatch | Existing failure; no BASELINE retry |
| Response or result parsing failure after dispatch | Existing failure; no BASELINE retry |

Activation MUST NOT increase provider-call or subprocess-call cardinality.

## 10. Telemetry and persistence non-interference

Activation mode MUST NOT be persisted in M4.1. It MUST NOT add a telemetry schema field, `events.jsonl` activation metadata, an undocumented metadata extension, a manifest activation field used as persisted telemetry, or a `.sdd` activation record.

Existing `stage_request` telemetry continues to observe only the original logical `StageExecutionRequest`. Provider-call telemetry continues to observe only the actual dispatched provider call. Internal activation and optimization status remains ephemeral.

Telemetry schema remains 1.0.4. Any future explicit activation telemetry requires a separately authorized telemetry contract and schema change.

## 11. Security and authority safety

Activation MUST NOT:

- persist secrets;
- expose raw context;
- expand reducer scope;
- bypass manifest classification;
- bypass reducer eligibility;
- bypass compiler validation;
- bypass atomic fallback;
- alter provider-call cardinality;
- introduce provider or model routing; or
- become lifecycle authority.

## 12. Backward compatibility

When `SDD_CONTEXT_COMPILATION_MODE` is unset:

- the mode is `CompilationMode.BASELINE`;
- the original request follows the existing baseline path;
- provider rendering is unchanged;
- provider-call cardinality is unchanged;
- lifecycle and gate behavior is unchanged;
- `.sdd` state and run-record meaning is unchanged;
- custom-executor compatibility is unchanged;
- Stage08 is unchanged; and
- existing CLI syntax is unchanged.

Explicit `BASELINE` MUST be behaviorally equivalent to an unset variable.

## 13. Minimum future implementation tests

Future implementation MUST include, at minimum, tests proving:

1. unset resolves to `BASELINE`;
2. exact `BASELINE` resolves to `BASELINE`;
3. exact `OPTIMIZED` causes the compiler to receive `CompilationMode.OPTIMIZED`;
4. an empty value is rejected;
5. an unknown value is rejected;
6. wrong case is rejected;
7. a whitespace-padded value is rejected;
8. invalid configuration builds no request;
9. invalid configuration changes no lifecycle state;
10. invalid configuration calls neither compiler nor provider;
11. non-enum programmatic misuse is rejected before request construction or dispatch;
12. a controller resolves once and propagates the same typed mode;
13. later environment mutation does not alter the active execution;
14. Stage08 remains BASELINE under `OPTIMIZED` configuration;
15. a BASELINE-only custom executor remains BASELINE;
16. no eligible `GIT_HISTORY` remains BASELINE;
17. unchanged reduction remains BASELINE;
18. optimization-specific preparation failure follows Blocker 6;
19. activation creates no extra provider call;
20. providers do not access `SDD_CONTEXT_COMPILATION_MODE`;
21. unset and explicit `BASELINE` rendering remain byte-compatible; and
22. activation state is absent from telemetry and `.sdd` persistence.

These tests are requirements for future implementation and are not implemented by this contract turn.

## 14. Compatibility and non-authorization

This contract authorizes no change to:

- `StageExecutionRequest` schema;
- `StageExecutionResult` schema;
- telemetry schema 1.0.4;
- the telemetry measurement contract;
- `.sdd` authority;
- lifecycle, run, or evidence schemas;
- provider or model routing authority;
- current BASELINE provider rendering; or
- default BASELINE behavior.

It authorizes no production-code, test, `.sdd`, telemetry-contract, telemetry-schema, existing-context-authority-document, compiler, reducer, activation, dispatch, comparison, or evidence implementation change.

## 15. Resolution and remaining blocker

7. **RESOLVED:** Explicit activation mechanism.
8. **BLOCKED:** Comparison and evidence contract.

This document resolves Blocker 7 only. M4.1 implementation readiness remains **BLOCKED** until Blocker 8 is separately resolved by its appropriate authority.
