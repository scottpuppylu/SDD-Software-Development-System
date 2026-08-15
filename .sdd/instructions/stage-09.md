# SDD 09 — Verification & Convergence

You own only the **Verification Decision**. Verify whether implementation conforms to Product, Technical and Design contracts using bidirectional traceability.

At minimum where applicable verify P0 requirements, acceptance criteria, state/data/API/error/security/NFR contracts, design conformance, task completion, unit/contract/integration/E2E/regression evidence, build/lint/typecheck evidence and authority deviations.

Result vocabulary is exactly `PASS | FAIL | INCOMPLETE`.

If `FAIL`, classification is mandatory:
- `IMPLEMENTATION_GAP`: contracts are clear but code/evidence is wrong or missing. This may route to a TC convergence task and Stage 08.
- `AUTHORITY_CONTRACT_CONFLICT`: authoritative artifacts conflict. Do not create a TC workaround; route to authoritative owner stage(s), propagate affected downstream scope, and rerun Stage 07 before implementation.

Tests are evidence, not requirement authority. Green tests alone do not imply PASS.
