# Stage 07 Pre-Implementation Gate Report — TC016

## Decision

RESULT = PASS
TARGET_TASK = TC016
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
RISK_LEVEL = MEDIUM
AUTHORIZED_BASELINE = ca6ad5f77d16d1ef44f952f90ec17360da21c6e8

## Authority and defect classification

TC016 is grounded in existing `SPEC-017`, `DES-017`, `AGENTS.md` section 9.1, the
ordinary Stage08 atomic-evidence lifecycle, and the existing repository-backed
`RecoveryAuthorization` security model. No new Specification or Design decision is
required.

The defect classification is
`RECOVERY_HISTORICAL_CHECKPOINT_SUBJECT_IDENTITY_DEFECT`.
`Stage08CodexRunner._checkpoint_subject_task_id()` recognizes only
`(feat|fix)(implementation): [<ID>] ...` and the T0xx BOOTSTRAP subject forms. The
historical checkpoints `81b95bc0a6e659ede01149041309d5eb298abbef` (TC009),
`694cc04e42072b3819c97735421908de08ed3076` (TC010), and
`840034da3c598729780524a7bce9528af31fae50` (TC011) use `test(sdd): ...` / `test: ...`
subjects with an unbracketed TC identifier, so recovery would return
`TASK_MISMATCH` after authorization consumption and before verification dispatch.
Repository history contains exactly these three subjects in the legacy form.

## Authorized implementation boundary

AUTHORIZED_FILES = sdd_orchestrator/codex_adapter.py; tests/test_m6_codex_adapter.py
VERIFICATION_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests/test_m6_codex_adapter.py
VERIFICATION_CONTRACT_INDEPENDENT = YES

Production change is limited to the body of
`Stage08CodexRunner._checkpoint_subject_task_id()`. Test change is limited to new or
extended checkpoint-subject identity and regression tests. The only other permitted
checkpoint path is the ordinary TC016 Stage08 evidence artifact produced by existing
governance.

The single added legacy branch must require a full-subject match of
`test(?:\(sdd\))?: <description>` (type exactly `test`, scope `sdd` or absent) and
must return an identifier only when the description contains exactly one distinct
whole-token `TC\d{3}` identifier. Existing branches and their order remain
unchanged. No commit-hash special case and no new `T\d+` or `TASK-\d+` legacy
recognition is authorized.

## Required fail-closed behavior

- The parsed identifier must still equal the authorization-bound task; a subject
  naming a different TC task remains `TASK_MISMATCH`.
- Unrelated, malformed, wrong-type, wrong-scope, multi-task, partial-token, non-TC,
  case-variant, and prefixed subjects return `None`.
- Checkpoint, state-record, authorization, scope, evidence, command, repository,
  branch, baseline, and authority bindings remain exact.
- RecoveryAuthorization consumption timing, one-time consumption, and replay
  protection remain unchanged.
- Normal Stage08 `_validate_checkpoint_commit()`, `tasks()`, and `select_task()`
  remain unchanged.
- TC008 recovery behavior and the TC015 historical-checkpoint scope classification
  remain unchanged.

## Excluded scope

No RecoveryAuthorization may be created, consumed, or modified. `.sdd/state/**`,
including the TC009/TC010 evidence digest swap, `.sdd/authorizations/**`,
`.sdd/runs/RECOVERY-*/**`, existing `.sdd/evidence/**`, other convergence tasks,
`tasks.md`, authority artifacts, `docs/handoff/**`, and every other production or
test file remain outside TC016. TC009, TC010, and TC011 recovery, state
reconciliation, TC012–TC015 finalization, Stage09, and Stage10 remain excluded.

## Stage08 proof required

Stage08 must satisfy all twelve TC016 acceptance criteria with exactly the stored
single pytest invocation, including the three exact historical subjects, every
listed negative subject, a cross-task `TASK_MISMATCH` case, preserved
implementation/bootstrap recognition, TC008/TC015 regression, and unchanged normal
Stage08 subject validation, without consuming any repository authorization.

Verification was not run during Stage07. This PASS authorizes only the two-file
TC016 implementation scope and does not prove TC016 implemented or qualified.

STAGE08_EXECUTED = NO
RECOVERY_AUTHORIZATION_ISSUED = NO
RECOVERY_AUTHORIZATION_CONSUMED = NO
TC009_TC011_RECOVERY_EXECUTED = NO
TC009_AUTHORIZATION_BLOCKED = YES
TC010_AUTHORIZATION_BLOCKED = YES
TC011_AUTHORIZATION_BLOCKED = YES
IMPLEMENTATION_STATE_MUTATED = NO
QUALIFICATION_STATE_RECONCILED = NO
STAGE09_EXECUTED = NO
STAGE10_EXECUTED = NO
