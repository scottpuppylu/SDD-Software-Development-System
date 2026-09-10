# SDD_DECISION_LOG.md

> Version: v1.0-candidate
> Date: 2026-09-09

## Accepted Decision Index

- D-001 — Canonical Stage 01–10 Spec-Driven Lifecycle
- D-002 — Domain-Specific Authority
- D-003 — Canonical lifecycle status vocabularies
- D-004 — Stage 07 PASS required for normal Stage 08 authorization
- D-005 — Atomic Task + Verify + Git Checkpoint
- D-006 — Chat Memory is not Execution Authority
- D-007 — Stage 09 Bidirectional Traceability
- D-008 — Implementation Gap vs Authority Conflict routing
- D-009 — Stage 10 is Release Readiness Authority
- D-010 — SDD decoupled from a single Coding Agent
- D-011 — Codex CLI is current primary validated provider
- D-012 — API is optional integration, not intrinsic SDD requirement
- D-013 — Claude Code is compatibility target
- D-014 — Git is persistent execution state
- D-015 — Snapshot is user-facing Git abstraction
- D-016 — Zero-DevEnv is accepted product direction
- D-017 — Initialization Entry is non-Stage routing layer
- D-018 — Recovery must not fabricate historical Stage 07
- D-019 — Shared Knowledge v2.3 baseline
- D-020 — SDD Suite itself is version-governed
- D-021 — Orchestrator is Control Plane, not Domain Authority
- D-022 — Optimization cannot precede governance correctness
- D-023 — Three-document governance structure
- D-024 — Dual-role Agent Adapter abstraction
- D-025 — Governed Autonomy Human Approval Boundary
- D-026 — Snapshot bound to exact Git identity
- D-027 — Remote Sandbox: ephemeral + least capability + fail-closed
- D-028 — Truthful Cost/Token measurement + pre-dispatch budget interlock
- D-029 — Upgrade/Patch: candidate isolation + governed promotion
- D-030 — v1.0 governance-complete / runtime-partial classification

---

# D-030 — Governance Complete Does Not Mean Runtime Complete
**Status:** Accepted

For SDD v1.0 Candidate:

The normative governance model is considered complete enough for v1.0 candidate consolidation.

The following do not block governance v1.0 because they are runtime implementation items:
- Claude Code adapter implementation
- provider router implementation
- production Remote Sandbox implementation
- Zero-DevEnv production deployment
- Snapshot registry/restore runtime
- cost budget runtime
- upgrade rollout/migration runtime
- Web UI

They remain mandatory roadmap/conformance items before claiming the platform itself is production-complete.

---

## Open Implementation Work — Not Governance Decisions

- I-001 Claude Code Adapter implementation
- I-002 Multi-provider Router implementation
- I-003 Remote Sandbox provider/runtime
- I-004 Zero-DevEnv production deployment
- I-005 Snapshot registry/restore engine
- I-006 Budget/Cost interlock runtime
- I-007 Upgrade/Migration/Canary runtime
- I-008 Production Web UI
- I-009 Full conformance/acceptance suite

No unresolved normative decision currently blocks the v1.0 Candidate governance package.
