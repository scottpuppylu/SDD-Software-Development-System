# Stage 07 Pre-Implementation Gate Report — TC018

## Decision

RESULT = PASS
TARGET_TASK = TC018
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
RISK_LEVEL = HIGH
AUTHORIZED_BASELINE = 7998c5091b373bf02de3e660ed4ba79e196d3d88

## Authority and defect classification

TC018 is grounded in existing `SPEC-017`, `DES-017`, `AGENTS.md` section 9.1, and the
existing repository-backed `RecoveryAuthorization` security model. No new
Specification or Design decision is required.

The defect classification is
`RECOVERY_AUTHORIZATION_STORE_HISTORICAL_ENUMERATION_DEFECT`.
`RecoveryAuthorizationStore._active_records()` calls
`record.validate(require_active=False)` on every stored record before filtering to
`ACTIVE`. `validate()` always applies two current-time checks regardless of
`require_active`, so structurally intact historical records fail enumeration after
their `expires_at`. The defect is confined to enumeration; `load()`, `consume()`,
and `issue()` validate the grant in use through separate calls that keep their time
checks.

## Authorized implementation boundary

AUTHORIZED_FILES = sdd_orchestrator/git_runtime.py; tests/test_m5_git_recovery.py
VERIFICATION_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests/test_m5_git_recovery.py
VERIFICATION_CONTRACT_INDEPENDENT = YES

Production change is limited to `RecoveryAuthorizationStore._active_records()` plus
exactly one new private helper,
`RecoveryAuthorizationStore._validate_record_integrity(record)`, in
`sdd_orchestrator/git_runtime.py`. In `_active_records()`, only the
`record.validate(require_active=False)` call is replaced by
`self._validate_record_integrity(record)`; `_read(path)`, the sorted `*.yaml` scan,
and the `status == "ACTIVE"` filter stay unchanged. Test change is limited to new
or extended authorization-store tests. The only other permitted checkpoint path is
the ordinary TC018 Stage08 evidence artifact. Importing existing `evidence_writer`
constants (including `RECOVERY_AUTHORIZATION_STATUSES`) without modifying
`evidence_writer.py` is permitted.

## Binding implementation clarification

The helper mirrors exactly the non-clock rules of `RecoveryAuthorization.validate()`.
`expires_at` is optional in the record schema (`str | None`) and `validate()` checks
it only when present; therefore, when `expires_at` is present it must parse as UTC
and be strictly later than `issued_at`, and its absence is not an integrity failure.
`issued_at` must always parse as UTC. The helper must not be stricter or weaker than
the non-clock subset of `validate()`.

## Semantic rules (R1–R7)

- R1: every stored record receives non-clock integrity validation before filtering.
- R2: any integrity failure raises from enumeration (fail closed).
- R3: current wall-clock time is not used during enumeration.
- R4: only `ACTIVE` records are returned; `CONSUMED`, `REVOKED`, and `EXPIRED`
  records are integrity-checked but not returned.
- R5: expired or not-yet-valid `ACTIVE` grants remain unusable through unchanged
  `load()` and `consume()`.
- R6: a record whose status is still `ACTIVE` after `expires_at` remains returned
  for conflict detection and continues to block overlapping issuance.
- R7: no authorization file is rewritten, transitioned, normalized, or deleted; no
  expiry bypass.

## R6 stale-ACTIVE policy confirmation

R6 is CONFIRMED by this gate. A record whose status is still `ACTIVE` is a nominally
open single-use capability until a governed status transition closes it. Under
`AGENTS.md` section 9.1, overlapping active authorizations for the same task or
checkpoint are ambiguity that must be detected, reported, and blocked. Ignoring
expired `ACTIVE` grants during overlap detection would permit a second grant while
the first remains nominally open, so that alternative is rejected. R6 cannot weaken
execution: the stale grant stays unusable through `load()` and `consume()`. TC018
adds no status transition or cleanup behavior; closing a stale `ACTIVE` grant
requires separate authority. No live record is currently `ACTIVE`.

## Duplicated validation

The helper duplicates only stable, non-clock integrity rules; lifecycle and
current-time validity remain solely in `validate()`. No shared refactor is
authorized in TC018. Future consolidation with `validate()` and the TC017 helpers
may be proposed as a separate task.

## Excluded scope

`sdd_orchestrator/evidence_writer.py` (including `RecoveryAuthorization.validate()`),
`sdd_orchestrator/codex_adapter.py`, `RecoveryAuthorizationStore.load()`,
`consume()`, `_persist()`, `_read()`, `relative_path()`,
`_approval_reference_valid()`, `ProjectAuthorityRecoveryAuthorizationIssuer.issue()`,
all `RecoveryManager` behavior including the TC017 helpers, `_resolve_evidence`,
`_validate_v2`, `_write_state`, and `reconcile_qualification`, `.sdd/state/**`,
`.sdd/authorizations/**`, `.sdd/runs/**`, existing `.sdd/evidence/**`, other
convergence tasks, `tasks.md`, authority artifacts, `docs/handoff/**`, and every
other production or test file remain outside TC018. Finalization, reconciliation,
Stage09, Stage10, and push remain excluded.

## Stage08 proof required

Stage08 must satisfy all twelve TC018 acceptance criteria with exactly the stored
single pytest invocation, using the existing frozen-clock helper for time-dependent
cases, including the three currently failing real-date tests returning to PASS, the
TC017 tests passing unchanged, every integrity-negative case, R5 and R6 behavior,
and proof of no live repository side effects.

Verification was not run during Stage07. This PASS authorizes only the two-file
TC018 implementation scope and does not prove TC018 implemented or qualified.

STAGE08_EXECUTED = NO
RECOVERY_AUTHORIZATION_ISSUED = NO
RECOVERY_AUTHORIZATION_CONSUMED = NO
IMPLEMENTATION_STATE_MUTATED = NO
TC012_TC017_FINALIZATION_BLOCKED = YES
STAGE09_EXECUTED = NO
STAGE10_EXECUTED = NO
