# Stage 07 Pre-Implementation Gate Report — TC014

## Decision

RESULT = PASS
TARGET_TASK = TC014
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
AUTHORIZED_BASELINE = 216a7f216e02935321b3016ff75b18bb7f210973

## Authority and task readiness

TC014 is grounded in `SPEC-017`, `DES-017`, `AGENTS.md` section 9.1, and the
approved Stage03/Stage04/Stage05 recovery-authorization decision. The corrected
Stage06 artifact is `TODO`, has no Stage08 execution evidence, and exposes the
complete bounded write scope through the repository-authoritative `allowed_paths`
field. No upstream contradiction or unresolved TC014 contract ambiguity was found.

TC014 extends the existing `RecoveryAuthorization` primitive. It does not replace
`SafetyAuthorization`, reinterpret normal Stage07 implementation authorization, or
permit a parallel authorization framework.

## Authorized implementation boundary

AUTHORIZED_FILES = sdd_orchestrator/evidence_writer.py; sdd_orchestrator/git_runtime.py; sdd_orchestrator/codex_adapter.py; tests/test_v1118_safe_pause_and_evidence.py; tests/test_m5_git_recovery.py; tests/test_m6_codex_adapter.py
VERIFICATION_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests/test_v1118_safe_pause_and_evidence.py tests/test_m5_git_recovery.py tests/test_m6_codex_adapter.py
VERIFICATION_CONTRACT_INDEPENDENT = YES

The authorized behavior is limited to one repository-backed
`RECOVERY_AUTHORIZATION_V1` family at
`.sdd/authorizations/recovery/<authorization_id>.yaml`. It must extend the existing
primitive with the Stage06-defined schema, Project-Authority-only issuance,
repository-owned load by authorization ID or unique approved recovery-operation
lookup, complete fail-closed binding validation, atomic one-time consumption before
fresh verification, and append-only hash-chained status/audit events.

The sealed Stage08 envelope binds all six machine-readable paths and the exact single
verification command directly. Its TC014 task-contract digest additionally binds the
complete acceptance criteria, forbidden scope, artifact schema, issuance/load/
validation/consumption/audit contracts, dependencies, and governance profile. Current
authority artifact digests bind the applicable specification, design, and policy
versions.

## Required security and lifecycle invariants

- Only `PROJECT_AUTHORITY` may issue; the executor cannot self-authorize.
- Missing, invalid, ambiguous, expired, revoked, consumed, overlapping, substituted,
  path-escaping, or otherwise mismatched authorization data fails closed.
- Task, task-contract digest, checkpoint, original evidence, exact command,
  repository, branch, baseline, runtime tree/evidence, authority versions, scope, and
  worktree requirements remain exact bindings.
- Statuses are exactly `ACTIVE`, `CONSUMED`, `EXPIRED`, and `REVOKED`; execution
  failure remains an attempt outcome.
- Consumption is persisted and checkpointed after successful preflight and before a
  fresh verification child starts. A consumed authorization cannot replay.
- Persistence-only resume is permitted only by the explicit same-attempt durable
  success contract and cannot launch new verification.
- Normal `tasks()` and `select_task()` behavior remains unchanged, and recovery
  authority cannot derive normal Stage08 implementation authorization.

## Forbidden scope and preservation

TC014 does not authorize normal Stage08 selector redesign, TC008–TC011 status or
recovery-package changes, historical evidence rewrite, implementation-state
reconciliation, TC012/TC013 reimplementation or finalization, validator weakening,
`SafetyAuthorization` replacement, Stage09, or Stage10.

TC008–TC011 recovery packages and TC012/TC013 Stage08 results remain preserved. This
gate issued no SPEC-017 recovery authorization and executed no recovery operation.

## Stage08 proof required

Stage08 must satisfy all TC014 acceptance criteria using exactly the stored single
pytest invocation. Required coverage includes valid Project Authority issuance and
repository persistence/load; every positive and negative binding case; expiry,
revocation, replay, overlap, self-authorization and audit-chain enforcement; issuance
and consumption runtime-tree preservation; persistence-only resume; normal selector
preservation; and TC008 recovery-entry capability.

Verification was not run by Stage07. Passing this gate authorizes implementation but
does not prove TC014 implemented or qualified.

STAGE08_EXECUTED = NO
RECOVERY_AUTHORIZATION_ISSUED = NO
RECOVERY_EXECUTED = NO
TC013_STATE_FINALIZATION_EXECUTED = NO
TC012_STATE_FINALIZATION_EXECUTED = NO
STAGE09_EXECUTED = NO
STAGE10_EXECUTED = NO
