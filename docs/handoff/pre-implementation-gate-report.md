# Stage 07 Pre-Implementation Gate Report — TASK-023

## 1. Decision

```text
STAGE_ID = 07
STAGE_NAME = PRE_IMPLEMENTATION_GATE
RESULT = FAIL
CLASSIFICATION = null
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
TARGET_TASK = TASK-023
AUTHORIZED_NEXT_OPERATION = NONE
NEXT_ROUTE = STAGE06_EXECUTION_DECOMPOSITION_REMEDIATION
```

This is a fresh constitution-aware Stage07 decision evaluated against entry baseline `20ca16a25901c5581139300386b12334ee02d052` on branch `telemetry-measurement-v2`. The review preserves the accepted read-only upgrade-gate conclusion `A_NO_UPSTREAM_UPGRADE_REQUIRED` and the substantive TASK-023 ownership boundary. It does not implement TASK-023, authorize or execute TASK-024/TASK-025, create implementation evidence/checkpoints, or execute Stage08, Stage09, or Stage10.

Stage07 cannot grant implementation authorization because the exact authoritative TASK-023 verification command names two repository paths that do not exist at the evaluated baseline and are not authorized TASK-023 write paths. Stage07 is prohibited from substituting similarly named tests or editing Stage06 authority to force `PASS`.

## 2. Owner, runtime, repository, and authority readiness

- `.sdd/stages.yaml` and `.sdd/instructions/stage-07.md` identify Stage07 as the sole owner of `PRE_IMPLEMENTATION_GATE_DECISION`.
- Entry HEAD exactly matched `20ca16a25901c5581139300386b12334ee02d052`; the worktree was clean; branch was `telemetry-measurement-v2`.
- Repository runtime is Python `3.14.7`; pytest is `9.1.1`.
- `tests/test_v117_machine_task_contract.py` passed 10 tests. This is gate/tooling evidence, not TASK-023 implementation verification.
- `.sdd/state/authority-state.yaml` contains no unresolved authority conflict or blocking TBD.
- The protected Product, Spec, Design, Stage05, and Stage06 authorities were inspected read-only and not modified.

## 3. TASK-023 contract, eligibility, and dependencies

The authoritative contract is `tasks.md`, section `TASK-023 - Cost, token, call, runtime, resource, and deployment-limit enforcement`. Its objective is to enforce explicit pre-dispatch and cumulative resource limits without weakening governance, truncating required authority/evidence, or misrepresenting measurement truth.

TASK-023 depends on TASK-021 and TASK-022 only:

| Dependency | Status | Implementation checkpoint | Qualifying evidence |
| --- | --- | --- | --- |
| `T021` | `IMPLEMENTATION_QUALIFIED` | `6588ef148d44070ee71c03158fa9f5fe6dae85ae` | `.sdd/evidence/20260916T000708.940197Z-T021.json` |
| `T022` | `IMPLEMENTATION_QUALIFIED` | `48c4fc796886190bb282d61fc479f76361242749` | `.sdd/evidence/20260916T060527.168269Z-T022.json` |

The dependency graph is satisfied and TASK-023 has no implementation-state qualification record. TASK-024 and TASK-025 likewise remain unexecuted. DAG eligibility alone cannot overcome an invalid machine-executable verification contract.

## 4. Upgrade-gate and ownership preservation

The accepted upgrade-gate result `A_NO_UPSTREAM_UPGRADE_REQUIRED` and `TASK023_REEVALUATION = STILL_REQUIRED_UNCHANGED` remain valid as architectural conclusions. No contradiction was found in TASK-023's substantive ownership:

- TASK-028 owns observational Stage08 phase measurement.
- TASK-023 exclusively owns resource, cost, token, call, retry, runtime, process/resource, reservation, limit, accounting, and exhaustion enforcement.
- TASK-024 owns provider change/fallback/default-promotion conformance.
- TASK-025 owns DecisionGateway fixture isolation only.

The blocker is a Stage06 machine-execution-readiness defect in the exact verification command, not a reason to reopen SPEC-019, DES-020, or alter the TASK-023 objective.

## 5. Authorized TASK-023 scope if Stage06 repairs verification readiness

The current task contract bounds prospective implementation to:

- provider/model/runtime identity;
- applicable budget lookup and governed budget state;
- actual, estimated, unavailable, and context-size measurement truth;
- provider-call, tool-call, and retry accounting;
- token, cost, duration, process/resource, filesystem, network, Git, deployment, and secret-access hard/soft bounds already named by authority;
- pre-dispatch reservation/check and post-dispatch accounting;
- deterministic exhaustion stop/route;
- approval binding for material budget or deployment changes;
- reuse of existing timeout and telemetry primitives without granting telemetry lifecycle authority.

Forbidden scope remains billing-provider integration, cloud/deployment execution, changing budgets as authority, provider-default selection or promotion, provider registry redesign, DecisionGateway fixture repair, authority document mutation during implementation, and Stage09/10 semantic changes.

## 6. TASK-028 observation/enforcement boundary

TASK-028 telemetry must be reused where it provides attributable Stage08 observations, including invocation count, active/local verification durations, verification-level durations, remediation/resume counts, total Stage08 duration, and activity ratio. TASK-023 must not create a second Stage08 phase collector, duration measurement system, recorder, store, or shadow pipeline.

Telemetry remains non-authoritative observation. A TASK-023 policy decision must separately bind policy, limit, reservation/accounting state, observation provenance, identity, authority, and audit outcome. No measurement event may directly mutate lifecycle state or authorize/deny execution without policy evaluation.

Deterministic attempt, phase-event, provider-invocation, remediation, resume, and verification identities must prevent charging completed work twice after SAFE_PAUSE, resume, persistence retry, reused verification, or a reconstructed phase journal. A new actual provider/tool/process execution may consume budget; re-observing or replaying an already-accounted completed unit may not.

## 7. Cost/token truth and SAFE_PAUSE interaction

- Unavailable remains unavailable and is never coerced to zero.
- Unknown remains unknown where the applicable contract distinguishes it.
- Codex CLI token usage remains unavailable unless attributable structured provider evidence exists.
- Estimated values never populate measured-actual fields.
- Required hard-limit input that is unknown or unavailable fails closed before new metered dispatch when authority requires that limit.
- Mandatory authority, context, evidence, or audit content must not be truncated to fit a budget.

TASK-027 provider interruption reasons (`CODEX_QUOTA_EXHAUSTED`, `CODEX_INTERRUPTED`, `CODEX_TIMEOUT`) remain distinct from TASK-023 policy exhaustion. TASK-023 may determine a governed resource stop/block/route, but cannot weaken TASK-027 provenance, authorization revalidation, dirty-state preservation, no-duplicate invocation, or reusable-verification rules. Any permitted retry/resume must revalidate both the attempt and remaining/accounted resource state; a required block must be deterministic and auditable.

## 8. Preservation obligations

- TASK-021 pre-dispatch identity/auth/authz, capability default deny, exact call validation, audit, and Human Approval bindings remain mandatory.
- TASK-022 minimum disclosure, prompt-injection containment, sandbox/filesystem/network/process/credential/secret policy remains mandatory.
- TASK-026 bounded worker, provider-neutral Work Package, controller-owned local verification, and FAST/TARGET/FULL semantics remain unchanged.
- TASK-027 phase state, SAFE_PAUSE, precise resume, provenance revalidation, and no-duplicate behavior remain unchanged.
- TASK-028 existing telemetry framework, versioned phase event, deterministic event identity, truth classes, and non-authority behavior remain unchanged.
- TASK-024 and TASK-025 remain pending, unexecuted, and outside TASK-023.

TASK-001 through TASK-022 and TASK-026 through TASK-028 qualification/evidence remain intact. Historical evidence is not modified.

## 9. Exact allowed files

The authoritative TASK-023 list is:

- `sdd_orchestrator/resource_policy.py` — new cohesive resource-policy and accounting boundary.
- `sdd_orchestrator/governance_envelope.py` — bind current limits/policy references to governed dispatch.
- `sdd_orchestrator/providers.py` — provider/model identity and metered reasoning dispatch integration.
- `sdd_orchestrator/codex_adapter.py` — Stage08 policy checks/accounting integration while preserving controller ownership.
- `sdd_orchestrator/codex_cli.py` — attributable Codex process/call outcomes without fabricating usage.
- `sdd_orchestrator/context_evaluation.py` — actual/estimated/context-size/unavailable truth handling.
- `sdd_orchestrator/telemetry/measurement.py` — reuse existing measurement primitives only; no duplicate phase measurement.
- `sdd_orchestrator/telemetry/models.py` — reuse/preserve truth models and bounded compatibility only.
- `tests/test_resource_policy.py` — TASK-023 enforcement and integration proof.

No other production, telemetry, state, authority, or test file is authorized by the current task contract.

## 10. Authoritative verification command and blocker

The exact `tasks.md` command is:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_resource_policy.py tests/test_m42_context_evaluation.py tests/test_m42_measurement.py tests/test_m6_codex_adapter.py
```

Repository inspection at baseline established:

```text
tests/test_resource_policy.py = ABSENT_BUT_AUTHORIZED_FOR_CREATION
tests/test_m42_context_evaluation.py = ABSENT_AND_NOT_AN_AUTHORIZED_TASK023_WRITE_PATH
tests/test_m42_measurement.py = ABSENT_AND_NOT_AN_AUTHORIZED_TASK023_WRITE_PATH
tests/test_m6_codex_adapter.py = PRESENT
```

Related present files such as `tests/test_m42_evaluation_metrics.py` and `tests/test_telemetry_measurement.py` cannot be substituted by name inference. Doing so would change the authoritative command. Adding the missing paths during TASK-023 implementation would exceed the allowed-file list. Consequently the required Stage08 verification command cannot be executed exactly after an in-scope implementation, violating the Stage07 Stage06→Stage08 machine contract readiness rule.

The current command also does not explicitly name `tests/test_stage08_phase_resume.py` or `tests/test_telemetry_stage08_phase.py`. Stage06 must decide—without Stage07 inventing scope—whether coverage belongs inside `tests/test_resource_policy.py`, requires additional preserved regression commands/files, or is already proven by an exact existing command. The repaired contract must make TASK-028 reuse, no-double-accounting, truth-class preservation, and TASK-027 SAFE_PAUSE/resume compatibility executable and unambiguous.

TASK-023 implementation verification was not run. Its result is `NOT RUN`.

## 11. Acceptance criteria resolved from current authority

If Stage06 repairs the execution contract without changing substantive ownership, the implementation must prove at minimum:

- fail-closed pre-dispatch resource-policy evaluation;
- deterministic reservation and cumulative accounting;
- hard-limit denial with no new dispatch and soft-limit non-authoritative warning behavior;
- provider/tool/retry/token/cost/runtime/process/resource exhaustion handling;
- actual/estimated/context-size/unavailable truth-class separation;
- Codex unavailable tokens remain null/unavailable;
- no mid-context or required-evidence truncation;
- reuse of TASK-028 telemetry primitives without duplicate phase measurement/store;
- no double accounting across SAFE_PAUSE, resume, remediation, replay, reused verification, and persistence retry;
- approval-bound material budget/deployment changes;
- telemetry remains non-authoritative;
- TASK-021/022/026/027/028 and Stage09/10 boundaries remain preserved.

These are contract-readiness expectations, not implementation evidence.

## 12. Architecture Constitution evaluation

These results evaluate the TASK-023 contract boundary, not implementation conformance.

| Criterion | Result | Basis |
| --- | --- | --- |
| `ARCH-AC-01` | `PASS_SCOPE_CONFORMANCE_ONLY` | SDD remains controller/governor; policy does not move into Codex. |
| `ARCH-AC-02` | `PASS_SCOPE_CONFORMANCE_ONLY` | `resource_policy.py` is the cohesive spoke; adapters only integrate policy decisions. |
| `ARCH-AC-03` | `PASS_SCOPE_CONFORMANCE_ONLY` | Provider/model identity is input to a provider-neutral policy contract. |
| `ARCH-AC-04` | `PASS_SCOPE_CONFORMANCE_ONLY` | Required limits and reservations are evaluated before metered dispatch. |
| `ARCH-AC-05` | `PASS_SCOPE_CONFORMANCE_ONLY` | Missing required policy/limit/grant fails closed under least capability. |
| `ARCH-AC-06` | `FAIL_MACHINE_VERIFICATION_READINESS` | The task is intended to implement runtime/resource limits, but its exact proof command is not executable at this baseline. |
| `ARCH-AC-07` | `PASS_SCOPE_CONFORMANCE_ONLY` | Stage07 correctly withholds Stage08 authorization and routes Stage06 remediation. |
| `ARCH-AC-08` | `PASS_SCOPE_CONFORMANCE_ONLY` | Evidence, audit, minimum disclosure, and Human Approval remain required. |
| `ARCH-AC-09` | `PRESERVED_NOT_IMPLEMENTED_BY_TASK023` | Provider promotion/fallback remains TASK-024 authority. |

Because an applicable criterion is unverifiable through the exact task command, the aggregate Architecture Constitution gate result is `FAIL_MACHINE_EXECUTION_READINESS`.

## 13. Seal and authorization result

No TASK-023 sealed execution envelope is created. No Stage07 implementation authorization/checkpoint is created. The existing TASK-028 authorization is not reusable for TASK-023 and the mutable implementation-authorization projection is revoked by this fresh FAIL decision.

Stage06 must repair the TASK-023 exact verification command and/or allowed test-file scope through its owning-authority workflow. Stage07 must then be rerun from the resulting clean baseline. Stage07 does not prescribe which test filename is authoritative.

## 14. Final state

```text
PRE_IMPLEMENTATION_GATE_DECISION = FAIL
EVALUATED_BASELINE = 20ca16a25901c5581139300386b12334ee02d052
TARGET_TASK = TASK-023
TASK_DEPENDENCIES = T021,T022
TASK_DEPENDENCY_STATUS = ALL_REPOSITORY_QUALIFIED_AND_STATE_FINALIZED
UPGRADE_GATE_DECISION = A_NO_UPSTREAM_UPGRADE_REQUIRED_PRESERVED
TASK023_REEVALUATION = STILL_REQUIRED_UNCHANGED_PRESERVED
TASK_CONTRACT_STATUS = SUBSTANTIVELY_BOUNDED_BUT_MACHINE_VERIFICATION_NOT_EXECUTABLE
TASK023_IMPLEMENTATION_VERIFICATION = NOT_RUN
ARCHITECTURE_CONSTITUTION_GATE_RESULT = FAIL_MACHINE_EXECUTION_READINESS
NORMAL_STAGE08_AUTHORIZED = NO
SEALED_EXECUTION_ENVELOPE_CREATED = NO
TASK023_EXECUTED = NO
TASK024_EXECUTED = NO
TASK025_EXECUTED = NO
IMPLEMENTATION_EVIDENCE_CREATED = NO
IMPLEMENTATION_CHECKPOINT_CREATED = NO
STAGE09_DECISION = NOT_EVALUATED
STAGE10_DECISION = NOT_EVALUATED
NEXT_STEP = STAGE06_REPAIR_TASK023_MACHINE_VERIFICATION_CONTRACT_THEN_FRESH_STAGE07
BLOCKER = AUTHORITATIVE_VERIFICATION_COMMAND_REFERENCES_NONEXISTENT_UNAUTHORIZED_TEST_PATHS
```
