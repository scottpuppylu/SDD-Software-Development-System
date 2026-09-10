# SDD_V1_ACCEPTANCE_TEST_MATRIX.md

> Version: v1.0-candidate

| ID | Domain | Test | Expected |
|---|---|---|---|
| AT-001 | Lifecycle | New project routes through Initialization Entry | Stage 01 |
| AT-002 | Lifecycle | Resume uses repo/state, not chat memory | Correct lawful Stage |
| AT-003 | Authority | Cross-domain conflict detected | Block + route owner |
| AT-004 | Gate | Stage 08 without Stage 07 authorization | Blocked |
| AT-005 | Stage08 | Atomic task verified | Exact checkpoint |
| AT-006 | Stage08 | Protected authority artifact modified | Blocked |
| AT-007 | Recovery | Dirty unexpected worktree | Inspect/block |
| AT-008 | Verification | Implementation gap | Convergence loop |
| AT-009 | Verification | Authority conflict | Owner-stage rerun |
| AT-010 | Release | Stage 10 before Stage 09 PASS | Blocked |
| AT-011 | Approval | Routine Stage08 edit | A0 |
| AT-012 | Approval | Material P0 choice | A2 |
| AT-013 | Approval | Destructive production migration | A3 |
| AT-014 | Approval | Stage10 READY | Does not imply prod deploy |
| AT-015 | Snapshot | Snapshot identity | Exact full commit SHA |
| AT-016 | Snapshot | New commit after Stage09 PASS | Not implicitly verified |
| AT-017 | Restore | Normal undo | History-preserving where applicable |
| AT-018 | Restore | Data-impact rollback | A3 |
| AT-019 | Adapter | Provider narrative says tests pass | Orchestrator still verifies |
| AT-020 | Adapter | Non-conformant provider fallback | Rejected |
| AT-021 | Sandbox | S0 writes repository | Denied |
| AT-022 | Sandbox | S1 accesses production-write credential | Denied |
| AT-023 | Sandbox | Cross-project workspace read | Denied |
| AT-024 | Sandbox | Unapproved network endpoint | Denied |
| AT-025 | Sandbox | Kill switch | Stops without agent cooperation |
| AT-026 | Cost | Codex token actual unavailable | null/unavailable |
| AT-027 | Cost | Byte reduction labeled token savings | Rejected |
| AT-028 | Cost | Hard budget reached | BUDGET_BLOCKED |
| AT-029 | Cost | Budget stop truncates authority | Forbidden |
| AT-030 | Upgrade | Runtime self-edits active governance | Denied |
| AT-031 | Upgrade | U3 governance change | Requires A2 |
| AT-032 | Upgrade | New provider benchmark stronger | No auto-promotion |
| AT-033 | Upgrade | Failed adapter conformance | Promotion blocked |
| AT-034 | Upgrade | Canary failure | Broad rollout blocked |
| AT-035 | Versioning | Unknown persisted-state schema | Fail closed |
| AT-036 | Zero-DevEnv | User starts project without local dev setup | Supported |
| AT-037 | Security | Credential appears in normal run artifact | Test fails |
| AT-038 | Traceability | Code/Test reverse trace | Task→DES→SPEC→PRD |
| AT-039 | Evidence | Sandbox destroyed | Required evidence persists |
| AT-040 | Governance | Chat text conflicts with Master Spec | Master Spec wins |

## Release Gates

Governance v1.0:
- AT-001–040 specified
- no unresolved normative conflicts
- exact governance release identity assigned

Runtime production-complete:
- applicable AT-001–040 implemented and PASS
- production deployment/security drills PASS
- real-project burn-in PASS
