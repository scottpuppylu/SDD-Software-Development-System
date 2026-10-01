# Stage 07 Pre-Implementation Gate Report — TC013

## Decision

RESULT = PASS
TARGET_TASK = TC013
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
AUTHORIZED_BASELINE = 4a686ae2094dd147bfb6bea669bbe6b9dd154ee6

## Authorized implementation boundary

AUTHORIZED_FILES = sdd_orchestrator/codex_adapter.py; tests/test_m6_codex_adapter.py
VERIFICATION_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests/test_m6_codex_adapter.py
VERIFICATION_CONTRACT_INDEPENDENT = YES

TC013 may add only a recovery-specific exact historical convergence-task resolver for
the SPEC-017 path. It may resolve a DONE TC008 through TC011 contract only after a
valid active, single-use Project Authority
`POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY` authorization is supplied. It must
bind task ID, task-contract digest, checkpoint, original evidence, exact command,
repository, branch, and baseline, and fail closed on every mismatch.

## Preserved normal and recovery invariants

- `Stage08CodexRunner.tasks()` and `Stage08CodexRunner.select_task()` remain unchanged.
- DONE convergence tasks remain excluded from normal Stage08 execution and cannot be
  resurrected, have their status changed, or gain normal implementation authorization.
- The resolver must not substitute authorization, task, checkpoint, evidence, command,
  repository, branch, or baseline.
- TC008–TC011 recovery packages, their historical evidence/checkpoints, and TC012
  Stage08 result/evidence remain unchanged.

## Required Stage08 proof

The targeted test must prove normal selector exclusion of DONE TC008, rejection of
normal `select_task("TC008")`, authorized exact recovery resolution for TC008 through
TC011, all listed mismatch failures, and absence of status mutation. No Stage07 test,
Stage08 implementation, recovery authorization, recovery verification, Stage09, or
Stage10 was executed by this gate.

STAGE08_EXECUTED = NO
RECOVERY_AUTHORIZATION_ISSUED = NO
RECOVERY_EXECUTED = NO
STAGE09_EXECUTED = NO
STAGE10_EXECUTED = NO
