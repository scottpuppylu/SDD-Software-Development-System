# Stage 07 Pre-Implementation Gate Report — TASK-028

## 1. Decision

```text
STAGE_ID = 07
STAGE_NAME = PRE_IMPLEMENTATION_GATE
RESULT = PASS
CLASSIFICATION = null
IMPLEMENTATION_AUTHORIZATION = GRANTED
AUTHORIZED_TASK = TASK-028
UNAUTHORIZED_TASKS = TASK-023,TASK-024,TASK-025
AUTHORIZED_NEXT_OPERATION = SEALED_STAGE08_TASK_028_IMPLEMENTATION
NEXT_STAGE = 08
```

This is a fresh constitution-aware Stage07 decision evaluated against entry baseline `98c012606eb0e76edf08e6d6a85d493675f2da17` on branch `telemetry-measurement-v2`. It authorizes only TASK-028. It does not implement TASK-028, execute TASK-023/TASK-024/TASK-025, create implementation evidence/checkpoints, or execute Stage08, Stage09, or Stage10.

## 2. Owner, runtime, repository, and authority readiness

- `.sdd/stages.yaml` and `.sdd/instructions/stage-07.md` identify Stage07 as the sole owner of `PRE_IMPLEMENTATION_GATE_DECISION`.
- Entry HEAD exactly matched `98c012606eb0e76edf08e6d6a85d493675f2da17`; worktree was clean; branch was `telemetry-measurement-v2`.
- Repository runtime is Python `3.14.7`; pytest is `9.1.1`.
- `tests/test_v117_machine_task_contract.py` passed 10 tests. This is gate/tooling evidence, not TASK-028 implementation verification.
- Stage05/06 authority is current; `authority-state.yaml` contains no unresolved conflict or blocking TBD.
- `tasks.md` supplies a complete bounded TASK-028 contract; `SPEC-019` and `DES-020` supply current technical/design authority.

## 3. TASK-028 eligibility and dependencies

The authoritative contract is `tasks.md`, section `TASK-028 - Observational Stage08 phase-consumption telemetry`. TASK-028 is `TODO` and DAG-eligible after `TASK-026 -> TASK-027 -> TASK-028`.

| Dependency | Implementation checkpoint | Qualifying evidence |
| --- | --- | --- |
| `T021` | `6588ef148d44070ee71c03158fa9f5fe6dae85ae` | `.sdd/evidence/20260916T000708.940197Z-T021.json` |
| `T022` | `48c4fc796886190bb282d61fc479f76361242749` | `.sdd/evidence/20260916T060527.168269Z-T022.json` |
| `T027` | `974909349039c2dac5d9a1e6462895d792e815fe` | `.sdd/evidence/20260917T072607.785719Z-T027.json` |

All are repository-qualified, evidence-backed, and checkpoint-bound. TASK-027 state-finalization commit `98c012606eb0e76edf08e6d6a85d493675f2da17` is the entry baseline. Its durable phase state, attempt identity, SAFE_PAUSE, precise resume, no-duplicate invocation/verification, diff provenance, and phase-history evidence binding remain authoritative. TASK-028 may observe these facts but cannot change their governance semantics.

## 4. Objective and observational-only scope

```text
AUTHORIZED_OBJECTIVE = OBSERVATIONAL_STAGE08_PHASE_CONSUMPTION_TELEMETRY_ONLY
```

The authorized additive telemetry must make these values derivable: `codex_invocation_count`, `codex_active_duration`, `local_verification_duration`, `fast_verify_duration`, `target_verify_duration`, `full_verify_duration`, `remediation_count`, `resume_count`, total Stage08 duration, and `CODEX_ACTIVE_TIME / TOTAL_STAGE8_TIME`.

Telemetry cannot authorize/deny execution, qualify implementation, enforce/reserve budget or resources, apply hard/soft limits, stop at thresholds, alter retry/phase behavior, change runtime/process/deployment limits, implement exhaustion routing, create authority, checkpoint work, or affect Stage09/10. Forbidden scope is budget policy/state, reservation, enforcement counters, hard/soft limits, resource/runtime/deployment constraints, exhaustion stop/route, provider promotion/change/fallback, parallel stores, independent persistence/shadow pipelines, upstream authority changes, and TASK-023/024/025 execution.

## 5. TASK-023 ownership

TASK-023 exclusively owns resource/budget/token/cost/provider/tool/retry accounting used for enforcement, reservation, limits, runtime/resource/deployment constraints, approved increases, and exhaustion routing. TASK-028 may record attributable counts/durations only. Shared telemetry primitives do not transfer semantic authority. Any metric-driven allow/deny/pause/route/reserve/enforcement behavior is out of scope and must route to TASK-023 or Stage06.

## 6. Existing telemetry framework and truth classes

TASK-028 must reuse `telemetry/models.py`, `telemetry/measurement.py`, and `telemetry/recorder.py`, including existing sinks. It must not create another store, recorder architecture, persistence layer, or metrics pipeline. Recorder/sink failure must remain best-effort and cannot change governed execution truth.

Current schema `sdd.measurement.stage_execution/1.0.4` distinguishes `AVAILABLE/ACTUAL` from `UNAVAILABLE/UNAVAILABLE`. Codex CLI usage uses `CODEX_CLI_UNAVAILABLE` with all token fields `null`. Unavailable is never zero, estimated actual, derived from duration, or fabricated. Unknown/non-attributable values remain unavailable/unknown as applicable and cannot be represented as measured actual.

## 7. Schema and storage compatibility

Stage06/DES-020 authorize an additive versioned `STAGE08_PHASE` event or equivalent backward-compatible existing-framework extension. Frozen `STAGE08_TASK` event readers/metadata, provider-call provenance, canonical JSONL storage, null-recorder behavior, historical readability, and the existing storage contract remain unchanged. No incompatible in-place schema mutation or historical rewrite is authorized.

New observations contain only minimum-disclosure identifiers, categories, bounded counts, durations, hashes, and normalized outcomes; bind to TASK-027 attempt/phase identities; reject unsupported versions/invalid values; and remain readable beside historical events.

## 8. Derivation and de-duplication

All counts/durations bind stable attempt, event, invocation, and verification identities, using non-negative monotonic intervals. Replay/resume must not count a completed interval twice.

- one `resume_count` per unique governed resume event, not per reload;
- one invocation count per unique provider invocation identity, including distinct bounded remediation calls;
- one remediation count per unique remediation episode/transition;
- reused verification adds no new duration; only actual local execution intervals count;
- FAST/TARGET/FULL durations remain disjoint and level-bound;
- local verification excludes SAFE_PAUSE and provider-active intervals;
- SAFE_PAUSE is not provider-active or verification time;
- total Stage08 time has an explicit consistent pause rule and no resume-overlap duplication;
- the activity ratio is derived only with a valid positive denominator and never becomes a threshold.

Missing correlation, overlap, duplicate events, negative/non-monotonic duration, or unsupported schema remains explicit and cannot be repaired into measured truth.

## 9. Security and governance preservation

TASK-021 identity/auth/authz, exact capability/tool/action/target validation, default deny, least privilege, Human Approval, and audit remain non-bypassable. Telemetry is never an authorization input.

TASK-022 classification, redaction, prompt-injection containment, sandbox/filesystem/network/process/credential/secret boundaries, retention, and minimum disclosure apply before recording. Telemetry must not contain prompts, source/package/diff content, secrets, credentials, raw tracebacks, sensitive failure payloads, or raw remediation context.

TASK-026 remains preserved: Codex is a bounded worker, local runtime owns verification, and FAST/TARGET/FULL plus legacy behavior remain unchanged. TASK-027 remains preserved: telemetry observes but cannot mutate phase, SAFE_PAUSE, resume, provenance, evidence, or checkpoint semantics.

## 10. Exact allowed files

- `sdd_orchestrator/telemetry/models.py` — additive versioned phase-event model/validation.
- `sdd_orchestrator/telemetry/measurement.py` — safe phase observation construction/derivation.
- `sdd_orchestrator/telemetry/recorder.py` — existing recorder/sink integration only.
- `sdd_orchestrator/codex_adapter.py` — thin hooks at authoritative Stage08 boundaries.
- `sdd_orchestrator/codex_cli.py` — provider-active timing/provenance at the existing adapter boundary.
- `tests/test_telemetry_stage08_phase.py` — phase metric/de-duplication/non-authority proof.
- `tests/test_telemetry_models.py` — model/schema/truth-class compatibility.
- `tests/test_telemetry_measurement.py` — measurement and unavailable-value correctness.
- `tests/test_telemetry_stage08_task.py` — frozen legacy Stage08 behavior.
- `tests/test_telemetry_application_wiring.py` — shared-recorder wiring.
- `tests/test_telemetry_storage_contract.py` — persistence compatibility.

No budget/resource enforcement, authority, state, Stage09/10, or unrelated file is authorized.

## 11. Verification and acceptance

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_telemetry_stage08_phase.py tests/test_telemetry_models.py tests/test_telemetry_measurement.py tests/test_telemetry_stage08_task.py tests/test_telemetry_application_wiring.py tests/test_telemetry_storage_contract.py
```

This set covers phase-event/derivation correctness, truth classes, frozen task events, recorder/application wiring, storage compatibility, de-duplication, unavailable-not-zero, minimum disclosure, and non-authority behavior. Stage07 does not run TASK-028 implementation verification; its result is `NOT RUN`.

Acceptance criteria: `EXISTING_TELEMETRY_FRAMEWORK_REUSED`; `TELEMETRY_TRUTH_CLASSES_PRESERVED`; `TASK023_RESOURCE_ENFORCEMENT_NOT_DUPLICATED`; `TASK021_AND_TASK022_GOVERNANCE_PRESERVED`; `LEGACY_STAGE08_TASKS_REMAIN_COMPATIBLE`; `ALL_REQUIRED_PHASE_METRICS_DERIVABLE_WITHOUT_DOUBLE_COUNTING_OR_FABRICATION`.

## 12. Architecture Constitution

These results establish contract authorizability, not implementation proof.

| Criterion | Result | Basis |
| --- | --- | --- |
| `ARCH-AC-01` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | SDD remains controller; telemetry is read-only Edge/Spoke observation. |
| `ARCH-AC-02` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Thin hooks emit facts; telemetry modules own cohesive observation behavior, not control logic. |
| `ARCH-AC-03` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Attempt/phase/duration/count/outcome semantics are provider-neutral. |
| `ARCH-AC-06` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Data/runtime/persistence stay bounded and non-controlling; TASK-023 enforcement is excluded. |
| `ARCH-AC-07` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Lifecycle stages and decision ownership remain unchanged. |
| `ARCH-AC-08` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | TASK-021/TASK-022 security, audit, Human Approval, and disclosure controls remain binding. |
| `ARCH-AC-04` | `PRESERVED_NOT_DIRECTLY_IMPLEMENTED` | Pre-dispatch/resume revalidation remains controller behavior. |
| `ARCH-AC-05` | `PRESERVED_NOT_DIRECTLY_IMPLEMENTED` | Default deny, exact paths, and least capability remain unchanged. |
| `ARCH-AC-09` | `PRESERVED_NOT_DIRECTLY_IMPLEMENTED` | Provider promotion/change conformance is unchanged. |

No applicable requirement is missing, failed, contradictory, or unverifiable at this gate boundary.

## 13. Preservation and seal

TASK-001 through TASK-022, TASK-026, and TASK-027 qualification/evidence remain intact. TASK-027 remains finalized at checkpoint `974909349039c2dac5d9a1e6462895d792e815fe` and commit `98c012606eb0e76edf08e6d6a85d493675f2da17`. TASK-023/024/025 authority remains unchanged and none is executed. Historical evidence/telemetry is unchanged. No implementation evidence/checkpoint is created.

After the Stage07 checkpoint, a new deterministic TASK-028 sealed envelope must be assembled and revalidated against the complete execution-bound HEAD. It binds TASK-028, entry baseline, authority/report/task digests, Stage06 contract, T021/T022/T027 state, exact allowed files, forbidden/observational scope, verification command, acceptance/truth-class rules, SPEC-019, DES-020, Architecture Constitution results, runtime, Stage05/TASK-021/TASK-022 security/Human Approval, and checkpoint conditions. Any mismatch blocks Stage08.

## 14. Final state

```text
PRE_IMPLEMENTATION_GATE_DECISION = PASS
EVALUATED_BASELINE = 98c012606eb0e76edf08e6d6a85d493675f2da17
TARGET_TASK = TASK-028
TASK_DEPENDENCIES = T021,T022,T027
TASK_DEPENDENCY_STATUS = ALL_REPOSITORY_QUALIFIED_AND_STATE_FINALIZED
TASK_CONTRACT_STATUS = VALID_COMPLETE_BOUNDED_OBSERVATIONAL_ONLY
VERIFICATION_POLICY_VALID = YES
TASK028_IMPLEMENTATION_VERIFICATION = NOT_RUN
APPLICABLE_ARCHITECTURE_CONSTITUTION = ARCH-AC-01,ARCH-AC-02,ARCH-AC-03,ARCH-AC-06,ARCH-AC-07,ARCH-AC-08
ARCH_AC_04 = PRESERVED
ARCH_AC_05 = PRESERVED
ARCH_AC_09 = PRESERVED
ARCHITECTURE_CONSTITUTION_GATE_RESULT = PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF
NORMAL_STAGE08_AUTHORIZED = YES_TASK_028_ONLY
STAGE08_AUTHORIZATION_BOUND_TASK = TASK-028
TASK-023_THROUGH_TASK-025_AUTHORIZED = NO
TASK-001_THROUGH_TASK-022_QUALIFICATION = PRESERVED
TASK-026_QUALIFICATION = PRESERVED
TASK-027_QUALIFICATION = PRESERVED
TASK028_EXECUTED = NO
TASK023_EXECUTED = NO
TASK024_EXECUTED = NO
TASK025_EXECUTED = NO
IMPLEMENTATION_EVIDENCE_CREATED = NO
IMPLEMENTATION_CHECKPOINT_CREATED = NO
STAGE09_DECISION = NOT_EVALUATED
STAGE10_DECISION = NOT_EVALUATED
NEXT_STEP = CREATE_AND_VALIDATE_POST_CHECKPOINT_SEALED_ENVELOPE_THEN_STOP_BEFORE_STAGE08
BLOCKER = NONE
```
