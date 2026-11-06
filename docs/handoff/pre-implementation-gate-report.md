# Stage 07 Pre-Implementation Gate Report — TC020 and TC021

## Decision

RESULT = PASS
TARGET_TASKS = TC020; TC021
IMPLEMENTATION_AUTHORIZATION = GRANTED
GOVERNANCE_PROFILE = SDD_STRICT
RISK_LEVEL = HIGH
AUTHORIZED_BASELINE = ca9d352e670d62244f57342dc1c4a3070a3df438
DECISIONS_INDEPENDENT = YES

The fresh Stage07 reviews for TC020 and TC021 independently passed. Each task
has its own sealed Stage08 authorization envelope. This report authorizes only
the bounded implementation described by the applicable envelope; it does not
mark either task implemented or complete, does not evaluate Stage09, and does
not authorize Stage10.

## TC020 decision and sealed Stage08 envelope

ENVELOPE_ID = STAGE07-TC020-ca9d352-e18ca38f
TASK_ID = TC020
REVIEW_RESULT = PASS
SCOPE_SEALED = YES
IMPLEMENTATION_AUTHORIZATION = GRANTED
TASK_CONTRACT_SHA256 = e18ca38f868eb7fdc596c2f612996fe84086845df518021627f83a160488df5b
ALLOWED_FILES = tests/test_m10_convergence_auto.py

TC020 remains classified as `TEST_FIXTURE_DEFECT`. Implementation may repair
only the fixture-local no-op commit assumption in the allowed file. It must
preserve all three existing behavioral assertions, authority-conflict rejection,
implementation-gap persistence and Stage08 routing, generated convergence-task
execution behavior, and fail-closed visibility of unexpected Git failures.

Forbidden scope includes `tests/test_m6_codex_adapter.py`, `sdd_orchestrator/**`,
all other production and test files, PRD, Spec, Design, AGENTS, tasks authority,
`.sdd/state/**`, `.sdd/evidence/**`, `.sdd/authorizations/**`, `docs/handoff/**`,
Stage09 or Stage10 authority mutation, arbitrary Git-error suppression, and
allow-empty or fabricated commits.

TARGETED_VERIFICATION = python -m pytest -q tests/test_m10_convergence_auto.py::M10Tests::test_authority_conflict_cannot_emit_tc tests/test_m10_convergence_auto.py::M10Tests::test_stage09_gap_persists_tc_task_and_routes_08 tests/test_m10_convergence_auto.py::M10Tests::test_tc_task_can_be_executed_by_stage08

Checkpoint eligibility requires the exact targeted command to pass, the diff
to remain limited to the allowed file plus separately governed ordinary Stage08
evidence, all existing assertions to remain intact, and every configured atomic
checkpoint condition to pass.

## TC021 decision and sealed Stage08 envelope

ENVELOPE_ID = STAGE07-TC021-ca9d352-8ebc9e6f
TASK_ID = TC021
REVIEW_RESULT = PASS
SCOPE_SEALED = YES
IMPLEMENTATION_AUTHORIZATION = GRANTED
TASK_CONTRACT_SHA256 = 8ebc9e6fe474b597730906c07fea8d8edeb0686df8fe31e1dec3942ba2801784
ALLOWED_FILES = tests/test_m6_codex_adapter.py

TC021 remains classified as `TEST_EXPECTATION_DEFECT`. Implementation may only
construct the named test authorization with the controlled fixture's exact
repository, branch, baseline, and integrity-valid identity. Exact production
repository and branch binding, baseline ancestry, authorization integrity,
historical evidence-scope enforcement, fail-closed `AUTHORITY_INVALID` behavior,
and production code byte identity must be preserved.

Forbidden scope includes `tests/test_m10_convergence_auto.py`,
`sdd_orchestrator/**`, all other production and test files, recovery authorization
or historical evidence mutation, repository/branch/baseline/digest/scope
relaxation, production path normalization or portability substitution, PRD,
Spec, Design, AGENTS, tasks authority, `.sdd/state/**`, `.sdd/evidence/**`,
`.sdd/authorizations/**`, `docs/handoff/**`, and Stage09 or Stage10 authority
mutation.

TARGETED_VERIFICATION = python -m pytest -q tests/test_m6_codex_adapter.py::M6CodexAdapterTests::test_historical_checkpoint_scope_accepts_only_exact_bound_stage08_evidence tests/test_m6_codex_adapter.py::V1116GeneratedVerificationArtifactTests::test_historical_checkpoint_scope_accepts_only_exact_bound_stage08_evidence

Checkpoint eligibility requires the exact targeted command to pass, the diff
to remain limited to the allowed file plus separately governed ordinary Stage08
evidence, exact fail-closed binding and negative coverage to remain intact, and
every configured atomic checkpoint condition to pass.

## Joint regression and independence

TC020 and TC021 have no implementation dependency and may be executed and
checkpointed independently. After both targeted verifications pass and before a
fresh Stage09 execution, the following joint regression is mandatory:

```text
python -m pytest -q tests
git diff --check
git diff --cached --check
git status --porcelain=v1
```

The complete suite and both diff checks must pass, Git status must be empty, and
no known failure may be skipped or normalized. This joint regression obligation
does not combine the two implementation scopes.

## Authority bindings

- `AGENTS.md` SHA-256: `4631d00d71e8d1e0636c6a555cc43a58ba3cd78cd85766915eea9f37b6353d48`
- `.sdd/stages.yaml` SHA-256: `6f82d21bb6a8be32062025eeb89f6561a4ad5baee89e1ff0627f9c12afbe1af5`
- `docs/PRD.md` SHA-256: `3ce7acae7acfa966990eebc89fe1a18ac8426c67f6db618f0b7e27f560fd89cb`
- `docs/spec.md` SHA-256: `b3d4f3c5d657fee1f2e1984f3c820c283d33f67120de81b38dee55dd7effc9aa`
- `docs/Design.md` SHA-256: `5bf1f9beab6f91943672d9afd55af575e583377f31c4545143ca1b387c8f0d79`
- `tasks.md` SHA-256: `528650343aa31cddad8475511f5f6b5cb29a70e039c423797fb73be5b2db1814`
- `.sdd/convergence/TC020.yaml` pre-decision SHA-256: `e18ca38f868eb7fdc596c2f612996fe84086845df518021627f83a160488df5b`
- `.sdd/convergence/TC021.yaml` pre-decision SHA-256: `8ebc9e6fe474b597730906c07fea8d8edeb0686df8fe31e1dec3942ba2801784`

STAGE08_EXECUTED = NO
TC020_IMPLEMENTED = NO
TC021_IMPLEMENTED = NO
IMPLEMENTATION_STATE_MUTATED = NO
STAGE09_DECISION = NOT_EVALUATED
STAGE10_AUTHORIZED = NO
