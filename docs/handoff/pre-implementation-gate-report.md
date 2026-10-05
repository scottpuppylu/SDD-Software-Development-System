# Stage 07 Pre-Implementation Gate Report — TC015

## Decision

RESULT = PASS
TARGET_TASK = TC015
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
AUTHORIZED_BASELINE = 2a27d6d1647cf9305cdeb11b24007c68f76285f8

## Authority and defect classification

TC015 is grounded in existing `SPEC-017`, `DES-017`, the ordinary Stage08
atomic-evidence lifecycle, and the existing repository-backed
`RecoveryAuthorization` security model. No new Specification or Design decision is
required.

The defect classification is
`RECOVERY_HISTORICAL_CHECKPOINT_SCOPE_CLASSIFICATION_DEFECT`. The current recovery
adapter applies ordinary task `allowed_paths` to every changed path in a historical
checkpoint. The governing contract instead distinguishes task implementation/test
paths from the exact ordinary Stage08 evidence artifact created atomically for that
same task and checkpoint.

## Authorized implementation boundary

AUTHORIZED_FILES = sdd_orchestrator/codex_adapter.py; tests/test_m6_codex_adapter.py
VERIFICATION_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests/test_m6_codex_adapter.py
VERIFICATION_CONTRACT_INDEPENDENT = YES

The repair is limited to historical recovery checkpoint changed-path
classification. A path is admissible only when it is within the task's exact
`allowed_paths`, or when it is the single original ordinary Stage08 evidence
artifact whose path, content digest, task, historical checkpoint, Stage08 execution
identity, recovery operation, and authority context all match the sealed recovery
bindings.

No generic `.sdd/evidence/**` or path-prefix exception is authorized.

## Required fail-closed behavior

- Evidence for another task, a wrong path or digest, an arbitrary evidence file, or
  an unrelated governance artifact remains `SCOPE_MISMATCH` or another applicable
  fail-closed result.
- Extra production or test paths outside the task contract remain rejected.
- Historical checkpoints and evidence remain immutable.
- Recovery operation, authorization, task, checkpoint, evidence, command,
  repository, branch, baseline, and authority bindings remain exact.
- RecoveryAuthorization consumption and replay protection remain unchanged.
- Normal Stage08 file boundaries, `tasks()`, and `select_task()` remain unchanged.

## Consumed TC008 authorization preservation

`RECOVERY-AUTH-TC008-20261005T002258330057Z` remains permanently `CONSUMED`.
It cannot be reactivated, reused, amended into `ACTIVE`, or treated as a live test
authorization. Its consumption checkpoint
`cde7a4cdba5025d84b04f273cbbddd7f5695086a` and nonqualifying attempt audit
checkpoint `d2a6624fbdcbb27387d3af98a623a450ea23df7c` remain immutable operational
evidence.

## Stage08 proof required

Stage08 must satisfy all fourteen TC015 acceptance criteria with exactly the stored
single pytest invocation. Coverage must include the exact TC008 checkpoint
`6cbb7df678a671493520fa0f6abaddcc9bf61557`, its bound original evidence, every
negative path/digest/task/governance case, consumed-authorization preservation,
normal Stage08 regression, and TC009–TC011 compatibility without executing any
recovery operation.

Verification was not run during Stage07. This PASS authorizes only the two-file
TC015 implementation scope and does not prove TC015 implemented or qualified.

STAGE08_EXECUTED = NO
TC008_NEW_AUTHORIZATION_ISSUED = NO
TC008_RECOVERY_EXECUTED = NO
IMPLEMENTATION_STATE_MUTATED = NO
QUALIFICATION_STATE_RECONCILED = NO
STAGE09_EXECUTED = NO
STAGE10_EXECUTED = NO
