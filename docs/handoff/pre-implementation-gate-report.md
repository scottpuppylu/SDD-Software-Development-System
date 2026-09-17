# Stage 07 Pre-Implementation Gate Report — TASK-027

## 1. Decision

```text
STAGE_ID = 07
STAGE_NAME = PRE_IMPLEMENTATION_GATE
RESULT = PASS
CLASSIFICATION = null
IMPLEMENTATION_AUTHORIZATION = GRANTED
AUTHORIZED_TASK = TASK-027
UNAUTHORIZED_TASKS = TASK-023,TASK-024,TASK-025,TASK-028
AUTHORIZED_NEXT_OPERATION = SEALED_STAGE08_TASK_027_IMPLEMENTATION
NEXT_STAGE = 08
```

This is a fresh constitution-aware Stage07 decision evaluated against entry baseline `42c0374aca48e13995ff2981f00182cf68441cc0` on branch `telemetry-measurement-v2`. It authorizes only the repository-stored TASK-027 contract. It does not implement TASK-027, authorize or execute TASK-028, release the Project Authority hold on TASK-023/TASK-024/TASK-025, execute any of those tasks, create implementation evidence or an implementation checkpoint, or execute Stage08, Stage09, or Stage10.

## 2. Owner, runtime, repository, and authority readiness

- Repository authority identifies Stage07 `PRE_IMPLEMENTATION_GATE` as the sole owner of `PRE_IMPLEMENTATION_GATE_DECISION`; its contract sources are `.sdd/stages.yaml` and `.sdd/instructions/stage-07.md`.
- Entry HEAD exactly matched `42c0374aca48e13995ff2981f00182cf68441cc0`; the entry worktree was clean and the branch was `telemetry-measurement-v2`.
- Repository-local `.\.venv\Scripts\python.exe` reported Python `3.14.7`; `python -m pytest --version` reported pytest `9.1.1`.
- The Stage07 machine-contract check `tests/test_v117_machine_task_contract.py` passed: 10 tests passed. This was a gate/tooling check, not TASK-027 implementation verification.
- `VerificationCommandPolicy` accepts the exact command parsed from TASK-027 without transcription, normalization, substitution, or execution.
- Stage05 run `.sdd/runs/20260916T235338.068450Z-stage-05.json` is `COMPLETED`, and its embedded `AGENTS.md` exactly matches current authority.
- Stage06 run `.sdd/runs/20260917T000714.589386Z-stage-06.json` is `COMPLETED`, and its embedded `tasks.md` exactly matches current authority. Stage06 checkpoint `c4f8280f22b9b54cfbe340ec4ac0207284ba5a26` remains reachable.
- `docs/spec.md` contains approved current `SPEC-019`; `docs/Design.md` contains approved current `DES-020`; authority state contains no unresolved conflict or blocking TBD.
- Prior TASK-026 Stage07 authorization is historical and task-bounded. It does not authorize TASK-027; this report is the fresh TASK-027 decision.

## 3. TASK-027 authority, eligibility, and dependencies

The authoritative task contract is `tasks.md`, section `TASK-027 - Durable Stage08 phase state, SAFE_PAUSE, and precise resume`, created by the current Stage06 re-decomposition. TASK-027 remains `TODO`; TASK-026 is qualified and state-finalized; TASK-027 is now the DAG-eligible successor in `TASK-026 -> TASK-027 -> TASK-028`.

The repository qualification validator successfully revalidated the complete schema `2.0` implementation state. Every declared TASK-027 dependency is `IMPLEMENTATION_QUALIFIED`, has repository-backed `PASS` evidence, and has a reachable implementation checkpoint:

| Dependency | Implementation checkpoint | Qualifying evidence |
| --- | --- | --- |
| `T001` | `cac76dfdd7e2d4298be450d1ab06d0bec8a0408c` | `.sdd/evidence/20260908T015718.824423Z-T001.json` |
| `T002` | `602d5e183fa3daebb483b140c401bd7523853765` | `.sdd/evidence/20260908T023935.201179Z-T002.json` |
| `T010` | `d5bca6588033ecf89e1caa685fd5a0846c660696` | `.sdd/evidence/20260909T054649.203279Z-T010.json` |
| `T011` | `000afb265a811cf4a8aee8030d08fe189a44592c` | `.sdd/evidence/20260909T071007.112397Z-T011.json` |
| `T012` | `ccffccef435481d82d748e2235df1c53d20f7127` | `.sdd/evidence/20260907T023726.044768Z-T012-recovery-T012-EVIDENCE-RECOVERY-001.json` |
| `T017` | `b58e79883b41904e710801191997c9729f26e8bf` | `.sdd/evidence/20260910T051318.814896Z-T017.json` |
| `T021` | `6588ef148d44070ee71c03158fa9f5fe6dae85ae` | `.sdd/evidence/20260916T000708.940197Z-T021.json` |
| `T022` | `48c4fc796886190bb282d61fc479f76361242749` | `.sdd/evidence/20260916T060527.168269Z-T022.json` |
| `T026` | `fea7db462333f4ad85b1ba7732d7487429f305a2` | `.sdd/evidence/20260917T054409.914726Z-T026.json` |

TASK-026 state-finalization commit `42c0374aca48e13995ff2981f00182cf68441cc0` is the entry baseline. TASK-027 has no qualification record and has not been executed. TASK-023, TASK-024, TASK-025, and TASK-028 have no implementation-qualification records and are not made eligible by this decision.

## 4. Authorized objective and bounded gap scope

The authorized objective is:

```text
DURABLE_ATOMIC_STAGE08_PHASE_STATE_SAFE_PAUSE_AND_PRECISE_RESUME
```

Authorized behavior is strictly limited to:

1. durable, versioned, atomic, and reconstructable Stage08 phase-bound attempt state;
2. attempt identity and authorization/envelope/branch/entry-HEAD/baseline/task-authority/allowed-files binding;
3. allowed-files digest, dirty-path/diff digest and attributable diff provenance;
4. verification command/result fingerprint and completion provenance;
5. truthful normalization of `CODEX_QUOTA_EXHAUSTED`, `CODEX_INTERRUPTED`, and `CODEX_TIMEOUT`;
6. fail-closed `SAFE_PAUSE` classification and governed resume validation;
7. skipping an already-completed initial Codex invocation when its proof remains valid;
8. skipping already-successful verification only while its complete proof remains valid;
9. bounded remediation resume under the same unchanged task and sealed authority; and
10. backward-compatible Stage08 evidence/checkpoint binding to complete phase history.

Forbidden scope is exact: phase-consumption telemetry; resource, budget, token, cost, or exhaustion-limit enforcement; provider promotion/change/fallback; TASK-023 enforcement; TASK-024 authority; TASK-025 fixture repair; TASK-028 telemetry; destructive Git recovery; upstream authority changes; implementation-state qualification shortcuts; Stage09/10 changes; automatic execution of another task; and any expansion of allowed files or behavior.

## 5. TASK-026 dependency preservation

TASK-027 builds on TASK-026 and must preserve all of its qualified guarantees:

- the provider-neutral immutable Codex Work Package and structured result contract;
- the bounded worker-only role for Codex, with no Stage08 controller, authorization, verification, evidence, checkpoint, or lifecycle responsibility;
- controller-owned local deterministic verification independent of an active provider session;
- FAST/TARGET/FULL semantics, with legacy commands mapped to TARGET;
- no implicit FULL regression and unchanged Stage09 full/system verification ownership;
- minimum-disclosure remediation packages without a default full-context rebuild; and
- all TASK-021/TASK-022, allowed-file, sealed-envelope, evidence, and compatibility guarantees.

Resume orchestration remains local-controller responsibility. TASK-027 cannot re-expand Codex into Stage08 control-plane responsibility or transfer deterministic verification to a provider.

## 6. Phase-state contract

The authoritative ordered phase model is:

1. `PRECHECK_COMPLETE`
2. `CONTEXT_READY`
3. `CODEX_PATCH_COMPLETE`
4. `FAST_VERIFY_COMPLETE`
5. `TARGET_VERIFY_COMPLETE`
6. `REMEDIATION_REQUIRED`
7. `FINAL_VERIFY_COMPLETE`
8. `STAGE8_COMPLETE`

`SPEC-019` and `DES-020` require a durable versioned attempt journal, immutable attempt/task/authorization/envelope/baseline/content bindings, same-directory atomic persistence, reload plus schema/digest validation, and a reconstructable ordered hash chain. Corrupt or unknown schema, missing/duplicate/reordered events, illegal transitions, digest-chain breakage, or binding mismatch must fail closed.

Phase state is attempt progress only. It is not implementation qualification, implementation evidence by itself, or a Git implementation checkpoint. Qualification remains impossible until ordinary Stage08 completion, qualifying evidence, required verification, scope checks, and checkpoint conditions all pass.

## 7. SAFE_PAUSE and precise-resume contract

TASK-027 may classify `CODEX_QUOTA_EXHAUSTED`, `CODEX_INTERRUPTED`, or `CODEX_TIMEOUT` as `SAFE_PAUSE` only when all required facts remain provable: every dirty/untracked path is authorized; the diff is attributable to the same attempt; no unexpected untracked path or unknown side effect exists; current Stage07 authorization, sealed envelope, branch, entry HEAD, authorized baseline, task authority, allowed-files digest, TASK-021/TASK-022 security handling, and minimum-disclosure constraints all revalidate. Unknown or unverifiable state must `BLOCK -> REPORT -> ROUTE`, never `SAFE_PAUSE`.

Resume must reload and revalidate:

- attempt ID and task ID;
- current TASK-027-specific Stage07 authorization and sealed envelope;
- branch, entry HEAD, and authorized baseline;
- task, authority, Work Package, result, and allowed-files digests;
- dirty paths, current diff digest, and diff provenance;
- completed verification commands, ordering, results, runtime/input/diff fingerprints, and prior `PASS` evidence;
- environment/input validity, security policy, approval/audit bindings, and absence of unknown side effects.

A still-valid `CODEX_PATCH_COMPLETE` prevents duplicate initial Codex invocation. A still-valid successful verification fingerprint prevents duplicate execution of that deterministic level unless current authority explicitly requires revalidation. Any relevant change invalidates the reusable proof and dependent later phases. Resume must not rebuild full context by default, reuse stale authorization, expand scope, or treat provider/session availability as authority. Remediation is a separate bounded invocation identity under the same unchanged task and envelope.

## 8. Git, recovery, evidence, and compatibility safety

- `GitRuntime` remains the source of branch, HEAD, dirty-path, diff, provenance, and checkpoint facts.
- `RecoveryManager` remains the owner of implementation qualification and `pending_evidence_write`; TASK-027 references and preserves those facts rather than replacing them.
- `path_scope_policy` remains fail-closed. Authorized dirty work may be preserved only when provenance is complete; unauthorized or unexplained diff blocks.
- TASK-027 cannot silently reset, revert, clean, discard, or destructively recover work. No cleanup may conceal provenance, and resume never broadens allowed files.
- Ordinary Stage08 evidence gains only a backward-compatible optional/versioned attempt section for new-feature executions. Existing readers and historical evidence remain compatible and immutable.
- Attempt and ordered phase history, invocation identities, final journal digest, diff/verification identities, and checkpoint identity remain auditable and content-bound.
- Final evidence/checkpoint may qualify implementation only after ordinary Stage08 completion conditions pass; phase history never upgrades qualification by itself.

## 9. TASK-021, TASK-022, and approval preservation

TASK-021 remains non-bypassable on initial dispatch, remediation, resume, local tool execution, evidence, and Git-write boundaries: identity/authentication-reference/authorization bindings, exact capability/tool/action/argument/target matching, default deny, least capability, Human Approval class/reference, and attributable audit obligations must revalidate.

TASK-022 remains non-bypassable: data sensitivity, redaction, retention/encryption references, minimum disclosure, prompt-injection and confused-deputy containment, filesystem/network/process/credential/secret boundaries, sandbox/environment compatibility, and stop-before-side-effect behavior remain mandatory. Journals and status projections must contain no secret value or unsafe raw error output. Resume cannot use stale approval, credential possession, provider session, historical chat, or prior success to weaken either task.

## 10. Exact allowed files and necessity review

Only these files are authorized:

- `sdd_orchestrator/stage08_phase_state.py` — cohesive versioned journal, transition, digest, persistence, reconstruction, and resume-validation domain module.
- `sdd_orchestrator/codex_adapter.py` — thin sequencing integration for phase transitions, reuse decisions, remediation, evidence, and checkpoint boundaries.
- `sdd_orchestrator/codex_cli.py` — bounded provider-process interruption, timeout, and quota result capture.
- `sdd_orchestrator/codex_results.py` — provider-result normalization for the three authorized interruption classes.
- `sdd_orchestrator/git_runtime.py` — authoritative branch/HEAD/diff/provenance and existing recovery interaction.
- `sdd_orchestrator/path_scope_policy.py` — exact dirty/untracked path and fail-closed resume safety decisions.
- `sdd_orchestrator/evidence_writer.py` — additive, backward-compatible phase-history binding and final-journal validation.
- `sdd_orchestrator/result_serialization.py` — compatible safe-pause/resume status projection without qualification inference.
- `sdd_orchestrator/system_controller.py` — governed task-attempt resume routing without automatic next-task execution.
- `tests/test_stage08_phase_resume.py` — focused positive, negative, corruption, interruption, resume, reuse, and evidence-binding proof.
- `tests/test_m5_git_recovery.py` — Git/provenance, pending-evidence, and non-destructive recovery regression.
- `tests/test_m6_codex_adapter.py` — thin adapter, sealed-envelope, worker boundary, and sequencing regression.
- `tests/test_v1118_safe_pause_and_evidence.py` — legacy SAFE_PAUSE, scope, evidence, and checkpoint compatibility regression.

Every allowed path maps directly to a DES-020 responsibility or required regression surface. No telemetry, resource-budget, provider-promotion, fixture, authority, Stage09/10, or unrelated file is authorized.

## 11. Verification and acceptance contract

The exact repository-authoritative TASK-027 verification command is:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_stage08_phase_resume.py tests/test_m5_git_recovery.py tests/test_m6_codex_adapter.py tests/test_v1118_safe_pause_and_evidence.py
```

The command is sufficient at the task-contract gate boundary because it combines the focused new phase/resume suite with Git recovery, adapter/governance, and legacy safe-pause/evidence regressions. It was not executed by this Stage07 gate; TASK-027 implementation verification remains `NOT RUN`.

Resolved acceptance criteria:

- `PHASE_STATE_ATOMIC_AND_RECONSTRUCTABLE`
- `QUOTA_INTERRUPTION_TIMEOUT_SAFE_PAUSE_WHEN_PROVEN_SAFE`
- `RESUME_REVALIDATES_AUTHORIZATION_BASELINE_ENVELOPE_AND_ALLOWED_FILES`
- `COMPLETED_CODEX_INVOCATION_NOT_REPEATED`
- `SUCCESSFUL_VERIFICATION_NOT_REPEATED_WHEN_STILL_VALID`
- `UNAUTHORIZED_DIFF_FAILS_CLOSED`
- `EVIDENCE_AND_CHECKPOINT_BIND_PHASE_HISTORY`
- `TASK021_AND_TASK022_GOVERNANCE_PRESERVED`
- `LEGACY_STAGE08_TASKS_REMAIN_COMPATIBLE`

## 12. Architecture Constitution evaluation

These results establish task-contract conformance and authorizability only; they are not implementation proof.

| Criterion | Gate result | Basis |
| --- | --- | --- |
| `ARCH-AC-01` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | SDD/local runtime remains controller and governor; durable phase state is an Edge/Spoke module and does not move lifecycle authority into Codex. |
| `ARCH-AC-02` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | `Stage08CodexRunner` remains a thin sequencing harness while the cohesive phase-state module owns persistence, transition, reconstruction, and validation behavior. |
| `ARCH-AC-03` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Phase and result contracts remain provider-neutral; provider-specific transport stays within adapters and cannot enter phase, evidence, or Git policy. |
| `ARCH-AC-04` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Initial execution and every resume/remediation revalidate governance, Stage07, envelope, approval, baseline, scope, provenance, and environment before dispatch. |
| `ARCH-AC-05` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Exact allowed files and least capabilities remain default-deny; stale/unknown authorization, dirty scope, side effects, or requested expansion blocks. |
| `ARCH-AC-06` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Runtime, Git, filesystem, network, process, security, timeout, and provider bounds remain enforced; pause never removes a limit and TASK-023 resource/budget enforcement is excluded. |
| `ARCH-AC-07` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | Current SPEC/DES/TASK authority, this fresh Stage07 gate, sealed Stage08 entry, evidence/checkpoint ordering, and unchanged Stage09/10 ownership preserve the lifecycle. |
| `ARCH-AC-08` | `PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF` | TASK-021 identity/authorization/tool/audit/Human Approval and TASK-022 data/injection/sandbox/network/credential controls are explicitly revalidated and non-bypassable. |
| `ARCH-AC-09` | `PRESERVED_NOT_DIRECTLY_IMPLEMENTED` | Provider-neutral contracts and unchanged TASK-024 promotion/conformance authority prevent resume or fallback from promoting or weakening provider governance. |

No applicable Architecture Constitution requirement is missing, failed, contradictory, or unverifiable at the task-contract gate boundary.

## 13. Preservation, seal, and stop boundary

- TASK-001 through TASK-022 qualification and evidence remain unchanged.
- TASK-026 qualification, implementation checkpoint `fea7db462333f4ad85b1ba7732d7487429f305a2`, evidence, and state-finalization commit `42c0374aca48e13995ff2981f00182cf68441cc0` remain unchanged.
- TASK-023, TASK-024, and TASK-025 authority and Project Authority hold remain unchanged; none is executed.
- TASK-028 remains unauthorized and unexecuted.
- Historical evidence is unchanged; no implementation evidence or implementation checkpoint is created by this gate.

After this Stage07 authorization checkpoint, a brand-new deterministic TASK-027 sealed execution envelope must be assembled and validated against the complete execution-bound HEAD. It must bind TASK-027, current authority hashes, this report, branch, execution-bound HEAD, Stage06 task contract and raw task digest, exact allowed paths, forbidden/behavior scope, exact verification command, acceptance criteria through the task digest, SPEC-019, DES-020, Architecture Constitution findings, runtime, TASK-021/TASK-022 security and Human Approval authority, and checkpoint conditions. Any later mismatch makes the envelope stale and blocks Stage08.

## 14. Final state

```text
PRE_IMPLEMENTATION_GATE_DECISION = PASS
EVALUATED_BASELINE = 42c0374aca48e13995ff2981f00182cf68441cc0
TARGET_TASK = TASK-027
TASK_DEPENDENCIES = T001,T002,T010,T011,T012,T017,T021,T022,T026
TASK_DEPENDENCY_STATUS = ALL_REPOSITORY_QUALIFIED_AND_STATE_FINALIZED
TASK_CONTRACT_STATUS = VALID_COMPLETE_BOUNDED
VERIFICATION_POLICY_VALID = YES
TASK027_IMPLEMENTATION_VERIFICATION = NOT_RUN
APPLICABLE_ARCHITECTURE_CONSTITUTION = ARCH-AC-01_THROUGH_ARCH-AC-08
ARCH_AC_09 = PRESERVED
ARCHITECTURE_CONSTITUTION_GATE_RESULT = PASS_TASK_CONTRACT_CONFORMANCE_ONLY_NOT_IMPLEMENTATION_PROOF
NORMAL_STAGE08_AUTHORIZED = YES_TASK_027_ONLY
STAGE08_AUTHORIZATION_BOUND_TASK = TASK-027
TASK-023_THROUGH_TASK-025_AUTHORIZED = NO
TASK-028_AUTHORIZED = NO
TASK-001_THROUGH_TASK-022_QUALIFICATION = PRESERVED
TASK-026_QUALIFICATION = PRESERVED
TASK027_EXECUTED = NO
TASK028_EXECUTED = NO
TASK023_EXECUTED = NO
TASK024_EXECUTED = NO
TASK025_EXECUTED = NO
IMPLEMENTATION_EVIDENCE_CREATED = NO
IMPLEMENTATION_CHECKPOINT_CREATED = NO
STAGE09_DECISION = NOT_EVALUATED
STAGE10_DECISION = NOT_EVALUATED
RELEASE_AUTHORIZED = NO
NEXT_STEP = CREATE_AND_VALIDATE_POST_CHECKPOINT_SEALED_ENVELOPE_THEN_STOP_BEFORE_STAGE08
BLOCKER = NONE
```
