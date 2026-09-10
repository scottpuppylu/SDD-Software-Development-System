# SDD_Current_Architecture.md

> Version: v1.0-candidate
> Snapshot Date: 2026-09-09
> Status: Governance-complete architecture / Runtime partial

## 1. System View

```text
User / Web UI
      ↓
INITIALIZATION_ENTRY
      ↓
SDD Control Plane / Orchestrator
      ├─ Lifecycle + Authority
      ├─ Human Approval Interlock
      ├─ Cost/Budget Interlock
      ├─ Provider Router
      ├─ Sandbox Policy
      ├─ Git/Snapshot
      └─ Evidence / Recovery
      ↓
01–06 Authoring
      ↓
07 Pre-Implementation Gate
      ↓
08 Implementation Adapter
      ↓
09 Verification
      ↓
10 Release Readiness
      ↓
Protected Action Runner / Deployment
```

## 2. Persistent Truth

Persistent execution/recovery truth:
- repository
- exact Git identities
- authoritative artifacts
- `.sdd/state/*`
- evidence
- decisions
- snapshots/releases

Chat/provider session is not execution authority.

## 3. Provider Layer

Defined:
- Reasoning Adapter
- Implementation Adapter
- capability manifest
- normalized results/errors
- Orchestrator-owned verification

Implemented/validated:
- Codex CLI core paths
- OpenAI reasoning path

Pending:
- Claude Code adapter runtime
- common provider router
- ≥2-provider conformance in production runtime

## 4. Git / Snapshot Layer

Defined:
- checkpoint
- snapshot
- verified version
- release-ready version
- release
- compare
- restore classes

Existing strong implementation evidence:
- Git checkpoint
- explicit paths
- dirty worktree checks
- last_verified_commit
- recovery snapshot

Pending:
- user-facing Snapshot registry
- compare/restore service
- lifecycle reconciliation engine
- release snapshot automation

## 5. Human Approval

Defined:
`GOVERNED_AUTONOMY`

A0/A1/A2/A3 policy is normative.

Pending:
- durable approval-policy engine integration across all runtime paths
- pre-authorization evaluator
- protected-action UX

## 6. Zero-DevEnv / Sandbox

Defined security model:
- S0–S3
- ephemeral default
- least capability
- deny-by-default network
- short-lived scoped credentials
- project/tenant isolation
- kill switch

Pending:
- concrete cloud sandbox provider selection/implementation
- credential broker
- network policy engine
- production protected-action runner
- tenant-scale isolation validation

## 7. Cost / Token

Defined:
- truthful usage classes
- budget scopes/states
- pre-dispatch hard stop
- no governance truncation

Pending:
- cost ledger
- budget policy engine
- usage normalization wiring
- provider cost router
- UI/dashboard

## 8. Upgrade / Patch

Defined:
- U0–U4
- isolated candidate
- governed promotion
- staged rollout
- rollback/provenance

Pending:
- version compatibility manifest runtime
- migration registry
- provider evaluation harness
- canary rollout controller

## 9. Current Maturity Summary

| Area | Governance | Runtime |
|---|---|---|
| Stage 01–10 | Complete | Strong existing core |
| Initialization Entry | Complete | Pending |
| Agent Adapter | Complete | Partial |
| Human Approval | Complete | Partial |
| Git/Checkpoint | Complete | Strong |
| Snapshot UX | Complete | Pending |
| Remote Sandbox Security | Complete | Pending |
| Cost/Token | Complete | Partial telemetry foundation |
| Upgrade/Patch | Complete | Pending |
| Zero-DevEnv Web UX | Direction complete | Pending |
