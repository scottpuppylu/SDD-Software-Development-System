# Stage 07 Pre-Implementation Gate Report — TC017

## Decision

RESULT = PASS
TARGET_TASK = TC017
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
RISK_LEVEL = HIGH
AUTHORIZED_BASELINE = 118c7abb0670e695e791db08abb056f7b9cde7be

## Authority and defect classification

TC017 is grounded in existing `SPEC-017`, `DES-017`, `AGENTS.md` section 9.1,
`tasks.md` section 11.6, the ordinary Stage08 atomic-evidence lifecycle, and the
existing repository-backed `RecoveryAuthorization` security model. No new
Specification or Design decision is required.

The defect classification is `RECOVERY_STATE_EVIDENCE_SCOPE_CLASSIFICATION_DEFECT`.
`RecoveryManager._resolve_evidence()` rejects every recovery-evidence checkpoint
path outside task `allowed_paths`. Historical checkpoint
`6cbb7df678a671493520fa0f6abaddcc9bf61557` also contains TC008's original Stage08
evidence `.sdd/evidence/20260924T103204.2963462Z-TC008.json`, so qualifying TC008
recovery evidence is rejected and `QUALIFICATION-STATE-RECONCILIATION-001` is
blocked. TC015 applied the exact bound-evidence rule only to the recovery executor.

## Prior Stage07 block and resolution

The Stage07 review at `8ed43d37abd72b0640c3104a106a501b2a0d8d2f` was BLOCKED
because the plan used `RecoveryAuthorization.validate(require_active=False)`, which
enforces current-time validity and would have made historical qualification
time-dependent. The Stage06 amendment at
`118c7abb0670e695e791db08abb056f7b9cde7be` replaces that step with local historical
integrity validation that never consults the current wall clock. The blocker is
resolved.

## Authorized implementation boundary

AUTHORIZED_FILES = sdd_orchestrator/git_runtime.py; tests/test_m5_git_recovery.py
VERIFICATION_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests/test_m5_git_recovery.py
VERIFICATION_CONTRACT_INDEPENDENT = YES

Production change is limited to recovery-evidence changed-path classification in
`RecoveryManager._resolve_evidence()` plus exactly two private helpers in
`sdd_orchestrator/git_runtime.py`: `_bound_original_evidence_valid` and
`_historical_consumed_authorization`. Test change is limited to new or extended
state-side classification and historical-integrity tests. The only other permitted
checkpoint path is the ordinary TC017 Stage08 evidence artifact.

At most one checkpoint path may exceed task `allowed_paths`, and only when it is
exactly the `target_original_evidence` of the repository-backed, historically
intact `CONSUMED` authorization bound to the recovery evidence and it passes the
mirrored TC015 structural, identity, and content checks.

## Required historical authorization integrity

- Exact authorization path from the attestation `authorization_id`; committed,
  ancestor of HEAD, working blob equal to committed blob.
- Schema, record kind, Project Authority issuer and role, recovery purpose,
  `one_time`, and status `CONSUMED`.
- Exactly two events: `ACTIVE`/`PROJECT_AUTHORITY`/`ISSUED` then
  `CONSUMED`/`RECOVERY_EXECUTOR`/`FRESH_VERIFICATION_DISPATCH`; sequence,
  `previous_event_digest` chain, every `event_digest`, and status projection.
- `grant_digest` and `record_digest`.
- Non-clock structural validity carried from `validate()`.
- Recorded-time window only: `expires_at > issued_at`, ACTIVE event at `issued_at`,
  and `issued_at <= consumed_at < expires_at`.
- Exact bindings: `authorization_id`, `attempt_id`, `target_task_id`,
  `target_checkpoint`, `task_contract_digest`, `verification_command`, and
  `target_original_evidence`.

The current wall clock is never compared with `issued_at`, `expires_at`, or any
event `occurred_at`. Only `CONSUMED` passes; `ACTIVE` (expired or not), `EXPIRED`,
`REVOKED`, and malformed records fail closed. `RecoveryAuthorization.validate()`
and `RecoveryAuthorizationStore.load()` are not called on this path and remain
unchanged.

## Required fail-closed behavior

- Any other `.sdd/evidence/**` path, unrelated `.sdd` governance file, extra
  production or test path, or multiple extra paths remain rejected.
- Ordinary evidence resolution and recovery tree-identity and diff-identity checks
  remain unchanged.
- No generic `.sdd/evidence/**` exception, no expired-ACTIVE bypass, and no task or
  commit-hash special case.

## Excluded scope

`.sdd/state/**`, `.sdd/authorizations/**`, `.sdd/runs/RECOVERY-*/**`, existing
`.sdd/evidence/**`, other convergence tasks, `tasks.md`, authority artifacts,
`docs/handoff/**`, `sdd_orchestrator/codex_adapter.py`,
`sdd_orchestrator/evidence_writer.py`, and every other production or test file
remain outside TC017. Authorization creation or consumption, recovery execution,
`QUALIFICATION-STATE-RECONCILIATION-001`, TC012–TC016 finalization, Stage09,
Stage10, and push remain excluded.

## Stage08 proof required

Stage08 must satisfy all thirteen TC017 acceptance criteria with exactly the stored
single pytest invocation, including TC008 resolution at `6cbb7df` (also with the
clock patched past `expires_at`), unchanged TC009–TC011 recovery digests, unchanged
TC007 ordinary resolution, continued rejection of original TC008–TC011 ordinary
evidence, every historical-integrity and binding negative, and proof of no
repository-state side effects.

Verification was not run during Stage07. All five live `CONSUMED` authorization
records were checked read-only against the amended integrity rules and satisfy
them. This PASS authorizes only the two-file TC017 implementation scope and does
not prove TC017 implemented or qualified.

STAGE08_EXECUTED = NO
RECOVERY_AUTHORIZATION_ISSUED = NO
RECOVERY_AUTHORIZATION_CONSUMED = NO
IMPLEMENTATION_STATE_MUTATED = NO
QUALIFICATION_STATE_RECONCILED = NO
RECONCILIATION_BLOCKED = YES
STAGE09_EXECUTED = NO
STAGE10_EXECUTED = NO
