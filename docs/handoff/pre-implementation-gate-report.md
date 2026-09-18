# Stage 07 Pre-Implementation Gate Report — TASK-023

## 1. Decision

```text
STAGE_ID = 07
STAGE_NAME = PRE_IMPLEMENTATION_GATE
RESULT = PASS
CLASSIFICATION = null
IMPLEMENTATION_AUTHORIZATION = GRANTED
AUTHORIZED_TASK = TASK-023
UNAUTHORIZED_TASKS = TASK-024,TASK-025
AUTHORIZED_NEXT_OPERATION = SEALED_STAGE08_TASK_023_IMPLEMENTATION
NEXT_STAGE = 08
```

This is a fresh constitution-aware Stage07 decision evaluated against entry baseline `86c45e0675383347aac79c3fbda02d9f6ff09af2` on branch `telemetry-measurement-v2`. The failed decision at `bfa8c170fc11146f807b16a93f66eb9b81f4b919` is historical audit evidence only; no prior TASK-023 authorization or envelope is reused. This decision authorizes only TASK-023 and does not implement it, execute TASK-024/TASK-025, create implementation evidence/checkpoints, or execute Stage08, Stage09, or Stage10.

## 2. Owner, runtime, repository, and authority readiness

- `.sdd/stages.yaml` and `.sdd/instructions/stage-07.md` identify Stage07 as the sole owner of `PRE_IMPLEMENTATION_GATE_DECISION`.
- Entry HEAD exactly matched `86c45e0675383347aac79c3fbda02d9f6ff09af2`; the worktree was clean; branch was `telemetry-measurement-v2`.
- Repository runtime is Python `3.14.7`; pytest is `9.1.1`.
- `tests/test_v117_machine_task_contract.py` passed 10 tests. This is gate/tooling evidence, not TASK-023 implementation verification.
- `.sdd/state/authority-state.yaml` contains no unresolved authority conflict or blocking TBD.
- Product, Spec, Design, Stage05, and repaired Stage06 authority are current and were not modified by this gate.

## 3. Stage06 repair validation

Stage06 repair checkpoint `86c45e0675383347aac79c3fbda02d9f6ff09af2` and run `.sdd/runs/20260918T040422.880990Z-stage-06.json` are valid. The run records `TASK-023_MACHINE_VERIFICATION_READINESS_REPAIR`, a completed transition to Stage07, and false values for substantive-authority, dependency, allowed-file, and acceptance-intent changes.

Comparison with the pre-repair TASK-023 contract proves that title/objective, dependencies, allowed files, allowed implementation scope, required behavior, preservation obligations, failure behavior, safety obligations, checkpoint eligibility, and out-of-scope authority remain unchanged. Only the invalid verification filenames and verification-proof clarification changed. The prior invalid command is not authoritative and must not be reused.

## 4. Eligibility and dependencies

The authoritative contract is `tasks.md`, `TASK-023 - Cost, token, call, runtime, resource, and deployment-limit enforcement`. TASK-023 remains prospective `TODO`, has no implementation qualification, and is DAG-eligible.

| Dependency | Status | Implementation checkpoint | Qualifying evidence |
| --- | --- | --- | --- |
| `T021` | `IMPLEMENTATION_QUALIFIED` | `6588ef148d44070ee71c03158fa9f5fe6dae85ae` | `.sdd/evidence/20260916T000708.940197Z-T021.json` |
| `T022` | `IMPLEMENTATION_QUALIFIED` | `48c4fc796886190bb282d61fc479f76361242749` | `.sdd/evidence/20260916T060527.168269Z-T022.json` |

The whole task graph resolves every dependency and is acyclic. TASK-024 and TASK-025 have no qualification record and remain pending/unexecuted.

## 5. Authorized objective, scope, and forbidden scope

TASK-023 authorizes a cohesive resource-policy/enforcement boundary for provider/model/runtime identity; applicable resource-budget lookup and state; actual/estimated/context-size/unavailable measurement truth; provider-call, tool-call, and retry accounting; token, cost, duration, process/resource, filesystem, network, Git, deployment, and secret-access hard/soft bounds already named by authority; pre-dispatch reservation/check; post-dispatch accounting; deterministic exhaustion stop/route; and approval binding for material budget/deployment changes.

The task must preserve required authority/context/evidence rather than truncate it to fit a limit. It may integrate enforcement decisions into existing governed dispatch boundaries, but Codex remains a bounded worker and telemetry remains observation rather than lifecycle authority.

Forbidden scope is billing-provider integration, cloud or deployment execution, changing budgets as authority, provider-default selection/promotion, provider registry redesign, TASK-024 provider-conformance authority, TASK-025 DecisionGateway fixture repair, a second telemetry recorder/store or shadow metrics pipeline, upstream authority changes, and Stage09/Stage10 semantic changes.

## 6. TASK-028 observation and TASK-023 enforcement boundary

TASK-028 owns observational measurement. TASK-023 owns resource, budget, accounting, limit, and exhaustion policy evaluation and enforcement. TASK-023 must consume attributable TASK-028 observations where relevant without reimplementing phase/duration measurement, creating a second recorder/store, or converting an observation event directly into lifecycle authority.

Policy outcomes must separately bind current identity, policy, limits, reservation/accounting state, observation provenance, authorization, Human Approval where applicable, and an auditable deterministic result. Re-observing or replaying an already-accounted completed unit cannot consume the same budget twice.

## 7. Truth classes and SAFE_PAUSE/resume

- `ACTUAL`, `ESTIMATED`, `UNAVAILABLE`, and `UNKNOWN` remain distinguishable where applicable.
- Unavailable provider/Codex CLI token usage remains unavailable and is never coerced to zero.
- Estimated values never populate measured-actual fields.
- Missing trustworthy data follows the task-defined fail-closed/fallback policy; required unknown or unavailable hard-limit inputs stop new metered dispatch.
- Mandatory authority, evidence, security, or audit content is never truncated to satisfy a budget.

TASK-027 worker interruption (`CODEX_QUOTA_EXHAUSTED`, `CODEX_INTERRUPTED`, or `CODEX_TIMEOUT`) remains distinct from an SDD resource-policy exhaustion outcome. Any permitted SAFE_PAUSE/resume/remediation must preserve authorization, phase/diff provenance, remaining budget, and accounting identity. Completed worker invocations and still-valid reused verification are not charged again merely because execution resumes. A policy stop/block is deterministic and auditable and cannot weaken TASK-027 dirty-state preservation or precise-resume rules.

## 8. Exact allowed files

- `sdd_orchestrator/resource_policy.py`
- `sdd_orchestrator/governance_envelope.py`
- `sdd_orchestrator/providers.py`
- `sdd_orchestrator/codex_adapter.py`
- `sdd_orchestrator/codex_cli.py`
- `sdd_orchestrator/context_evaluation.py`
- `sdd_orchestrator/telemetry/measurement.py`
- `sdd_orchestrator/telemetry/models.py`
- `tests/test_resource_policy.py`

`tests/test_resource_policy.py` is absent and explicitly authorized for creation during TASK-023 Stage08. No other production, telemetry, authority, state, or test file is authorized.

## 9. Authoritative verification and machine readiness

The repaired authoritative command is:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_resource_policy.py tests/test_m42_evaluation_metrics.py tests/test_telemetry_measurement.py tests/test_telemetry_models.py tests/test_telemetry_stage08_phase.py tests/test_stage08_phase_resume.py tests/test_m6_codex_adapter.py
```

Machine-path resolution:

```text
tests/test_resource_policy.py = ABSENT_BUT_AUTHORIZED_FOR_CREATION
tests/test_m42_evaluation_metrics.py = PRESENT
tests/test_telemetry_measurement.py = PRESENT
tests/test_telemetry_models.py = PRESENT
tests/test_telemetry_stage08_phase.py = PRESENT
tests/test_stage08_phase_resume.py = PRESENT
tests/test_m6_codex_adapter.py = PRESENT
ALL_VERIFICATION_PATHS_MACHINE_READY = YES
MACHINE_EXECUTION_READY = YES
ARCH_AC_06_MACHINE_READINESS = PASS_CONTRACT_LEVEL
```

The command is accepted without substitution by the repository verification-command policy. The repaired set preserves the original resource-policy, context truth-class, telemetry measurement, and Codex adapter obligations while adding explicit existing regressions for telemetry truth classes, TASK-028 de-duplication, and TASK-027 resume/provenance behavior. No proof obligation was silently removed. TASK-023 implementation verification is `NOT RUN` at Stage07.

## 10. Acceptance criteria resolved from authority

Implementation must prove: explicit fail-closed pre-dispatch resource governance; deterministic reservation and cumulative accounting; provider/tool/retry accounting; actual/estimated/unavailable truth preservation; token/cost/runtime/process/resource hard and soft limits; deterministic exhaustion stop/route; no mid-context or required-evidence truncation; approval-bound budget/deployment changes; TASK-028 telemetry reuse without duplicate measurement/store; no double accounting across SAFE_PAUSE, resume, remediation, reconstructed history, reused verification, or persistence retry; TASK-027 provenance/resume compatibility; telemetry non-authority; and preservation of TASK-021/022/026/027/028 plus Stage09/10 boundaries.

These are authorization-time contract criteria, not implementation evidence or Stage09 qualification.

## 11. Governance preservation

- TASK-021 identity/authentication/authorization bindings, default deny, exact capability/tool/action/target validation, audit, and Human Approval remain non-bypassable.
- TASK-022 sensitive-data handling, minimum disclosure, prompt-injection containment, sandbox/filesystem/network/process/credential/secret boundaries, and redaction remain mandatory.
- TASK-026 bounded worker, provider-neutral Work Package, controller-owned local verification, and FAST/TARGET/FULL semantics remain unchanged.
- TASK-027 durable phase state, SAFE_PAUSE, precise resume, provenance revalidation, and no-duplicate behavior remain unchanged.
- TASK-028 existing telemetry framework, deterministic event identity, truth classes, de-duplication, and observational-only authority remain unchanged.
- TASK-024 provider promotion/fallback conformance and TASK-025 fixture-repair authority remain separate, pending, and unexecuted.

TASK-001 through TASK-022 and TASK-026 through TASK-028 qualification/evidence remain intact. Historical evidence is unchanged.

## 12. Architecture Constitution evaluation

These results establish task-contract authorizability only, not implementation conformance.

| Criterion | Result | Basis |
| --- | --- | --- |
| `ARCH-AC-01` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | SDD remains controller/governor; resource policy does not move into Codex. |
| `ARCH-AC-02` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Cohesive policy/accounting belongs in `resource_policy.py`; adapter changes are bounded integration points. |
| `ARCH-AC-03` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Provider/model identity is input to provider-neutral policy and accounting semantics. |
| `ARCH-AC-04` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Required policy, limit, reservation, authorization, and approval checks precede metered dispatch. |
| `ARCH-AC-05` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Missing required grants/policy/limits deny dispatch; exact allowed files remain bounded. |
| `ARCH-AC-06` | `PASS_CONTRACT_LEVEL_MACHINE_READINESS_RESTORED_NOT_IMPLEMENTATION_PROOF` | Exact machine verification is now executable after authorized test creation and proves bounded runtime/resource/exhaustion behavior. |
| `ARCH-AC-07` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Stage06 repair and fresh Stage07 precede any Stage08 work; Stage09/10 remain separate. |
| `ARCH-AC-08` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Security, audit, evidence, minimum disclosure, and Human Approval bindings remain mandatory. |
| `ARCH-AC-09` | `PRESERVED_NOT_IMPLEMENTED_BY_TASK023` | Provider promotion/change/fallback conformance remains TASK-024 authority. |

No applicable Architecture Constitution requirement is missing, failed, contradictory, or unverifiable at the Stage07 contract boundary.

## 13. Fresh seal and authorization boundary

After this Stage07 report, state, and run artifact are checkpointed, a brand-new deterministic TASK-023 sealed execution envelope must be assembled and revalidated against the complete execution-bound HEAD. It binds TASK-023, the entry baseline, repaired task-contract digest, current authority/report digests, branch and execution-bound HEAD, exact allowed files, behavior/forbidden scope, repaired command, checkpoint conditions, dependency state, TASK-027 resume/accounting rules, TASK-028 observation/enforcement boundary, runtime, Architecture Constitution evaluation, and Stage05/TASK-021/TASK-022 security/Human Approval governance. Any mismatch blocks Stage08.

## 14. Final state

```text
PRE_IMPLEMENTATION_GATE_DECISION = PASS
EVALUATED_BASELINE = 86c45e0675383347aac79c3fbda02d9f6ff09af2
TARGET_TASK = TASK-023
TASK_DEPENDENCIES = T021,T022
TASK_DEPENDENCY_STATUS = ALL_REPOSITORY_QUALIFIED_AND_STATE_FINALIZED
STAGE06_REPAIR = VALIDATED
TASK_CONTRACT_STATUS = VALID_COMPLETE_BOUNDED_MACHINE_READY
VERIFICATION_POLICY_VALID = YES
ALL_VERIFICATION_PATHS_MACHINE_READY = YES
MACHINE_EXECUTION_READY = YES
TASK023_IMPLEMENTATION_VERIFICATION = NOT_RUN
APPLICABLE_ARCHITECTURE_CONSTITUTION = ARCH-AC-01,ARCH-AC-02,ARCH-AC-03,ARCH-AC-04,ARCH-AC-05,ARCH-AC-06,ARCH-AC-07,ARCH-AC-08
ARCH_AC_09 = PRESERVED
ARCHITECTURE_CONSTITUTION_GATE_RESULT = PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF
NORMAL_STAGE08_AUTHORIZED = YES_TASK_023_ONLY
STAGE08_AUTHORIZATION_BOUND_TASK = TASK-023
TASK024_AUTHORIZED = NO
TASK025_AUTHORIZED = NO
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
