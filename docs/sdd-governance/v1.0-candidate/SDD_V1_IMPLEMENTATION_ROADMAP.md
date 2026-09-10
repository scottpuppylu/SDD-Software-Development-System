# SDD_V1_IMPLEMENTATION_ROADMAP.md

> Version: v1.0-candidate
> Goal: turn governance-complete SDD into production-capable runtime.

## Wave 0 — Baseline Freeze

- Put v1.0 Candidate governance package into SDD repository.
- Assign exact Git commit.
- Tag candidate.
- Add compatibility/version manifest.
- Run cross-document consistency checks.

Exit:
`GOVERNANCE_BASELINE_FROZEN = YES`

## Wave 1 — Control-Plane Foundations

Implement:
- Initialization Entry classifier/router
- common Adapter types/manifests/errors
- Human Decision durable records
- Snapshot registry types
- budget policy types
- version compatibility manifest

No new provider or cloud sandbox yet.

Exit:
all common contracts represented in runtime types and tests.

## Wave 2 — Existing Codex Conformance

Wrap rather than rewrite mature paths.

Validate:
- Codex reasoning adapter
- Codex Stage 08 implementation adapter
- protected paths
- Orchestrator verification
- Git checkpoint/recovery
- normalized errors
- Human Approval boundaries

Exit:
`CODEX_COMMON_CONFORMANCE = PASS`

## Wave 3 — Snapshot / Recovery UX Runtime

Implement:
- Snapshot registry
- compare
- history-preserving restore
- lifecycle reconciliation
- verified/release-ready labels
- known-good rollback reference

Exit:
restore/recovery acceptance suite PASS.

## Wave 4 — Cost / Budget Runtime

Implement:
- usage provenance normalization
- cost ledger
- pre-dispatch budget interlock
- BUDGET_BLOCKED resume
- budget reporting

Exit:
no fake token claims; no authority truncation; hard-stop tests PASS.

## Wave 5 — Remote Sandbox Foundation

Implement:
- provider-neutral sandbox interface
- S0/S1 first
- workspace isolation
- scoped credentials
- deny-by-default network
- resource governor
- evidence export
- kill switch

Exit:
sandbox isolation/security tests PASS.

## Wave 6 — Second Provider

Implement Claude Code adapter after Codex common conformance is stable.

Run same conformance suite.

Exit:
`MULTI_PROVIDER_CONFORMANCE = PASS`

## Wave 7 — Provider Router

Implement:
- explicit provider profiles
- capability selection
- cost/reliability policy
- no weak fallback
- provider identity telemetry

Exit:
provider swaps do not alter lifecycle semantics.

## Wave 8 — Staging / Protected Actions

Implement:
- S2 staging operation
- S3 protected-action runner
- deployment pre-authorization
- production credential broker
- protected action evidence

Exit:
production credentials never enter general Stage 08 sandbox.

## Wave 9 — Upgrade / Patch Runtime

Implement:
- U0–U4 classifier
- candidate workspace automation
- migration registry
- provider evaluation harness
- canary rollout
- rollback controller
- upgrade provenance

Exit:
SDD can propose/test upgrades but cannot self-authorize governance changes.

## Wave 10 — Zero-DevEnv Product Layer

Implement Web UI:
- Start / Continue / Change Request
- project state
- progress
- Human Decision
- Snapshot / Compare / Restore
- budget
- release
- incidents/blockers

User should not need Docker/Git/Python/Node/PowerShell.

## Wave 11 — Platform v1 Production Readiness

Run:
- full acceptance matrix
- interrupted execution drill
- restore drill
- credential revocation drill
- budget exhaustion drill
- provider outage/fallback drill
- staging deployment drill
- canary upgrade drill
- real-project burn-in

Only after evidence PASS may the runtime be called production-complete.
