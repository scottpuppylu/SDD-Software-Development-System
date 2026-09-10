# SDD_SNAPSHOT_GIT_CONTRACT.md

> Contract Version: 1.0-draft
> SDD Baseline: v0.6-snapshot-git-rc
> Status: Accepted Architecture / Governance Contract
> Owner: SDD Orchestrator + Git Runtime

## 1. Core Principle

`Git = immutable technical version identity`

`Snapshot = governed user-facing reference to an exact Git commit + SDD metadata`

Snapshot does not replace Git and does not create lifecycle authority.

## 2. Distinct Concepts

- **Checkpoint**: governed Git commit created during execution.
- **Snapshot**: durable alias to exact commit + lifecycle/evidence metadata.
- **Verified Version**: exact commit reviewed by Stage 09 with PASS.
- **Release-Ready Version**: exact commit with eligible Stage 10 result.
- **Release**: exact commit + version/release identity, normally with annotated tag.

## 3. Snapshot Identity

A Snapshot MUST bind to a full Git commit SHA.

Branch is metadata only because branches are mutable.

Minimum logical record:

```yaml
snapshot:
  snapshot_id: SNP-...
  snapshot_type: TASK | MANUAL | VERIFIED | RELEASE_READY | RELEASE
  git:
    commit: "<full sha>"
    branch_at_creation: "..."
    tag: null
  lifecycle:
    current_stage: "08"
    last_completed_task: "T010"
  verification:
    stage09_result: null
    stage10_result: null
  evidence_refs: []
  created_at: "..."
```

## 4. Automatic Task Snapshot

After a successful Stage 08 Atomic Task checkpoint, SDD may expose a TASK Snapshot when:

- verification PASS
- checkpoint commit exists
- task scope is exact
- no unexpected staged/unrelated changes exist
- implementation state is updated

This is A0/A1 under the Human Approval contract.

## 5. Manual Snapshot

A user may request "save a snapshot here".

Default rule:
- clean worktree required

If the worktree is dirty:
- classify dirty paths
- do not silently stage everything
- either create explicit governed checkpoints or stop for resolution

Automatic `git add -A` behavior is forbidden by default.

## 6. Verified / Release-Ready Snapshot

### Verified
Only when Stage 09 PASS reviewed the exact commit.

A later commit is not implicitly verified.

### Release-Ready
Only when:
- Stage 09 PASS
- Stage 10 READY or READY_WITH_KNOWN_ISSUES
- Stage 10 release identity references the exact commit

## 7. Branch and Tag Semantics

- Snapshot identity = commit SHA, not branch.
- Snapshot remains historically valid if branch moves or is deleted.
- Task checkpoints normally do not need tags.
- Formal releases should use an annotated tag where practical.

Tag creation alone does not create Stage 10 readiness.

## 8. Compare

Compare Snapshot A and B using exact commit identities.

Minimum comparison:
- commit A / commit B
- changed paths
- Git diff
- lifecycle/evidence differences
- highlight changes to authority artifacts separately

AI summary is presentation only; Git diff remains evidence.

## 9. Restore Types

"Restore" MUST NOT be one generic destructive operation.

### WORKSPACE_RESTORE
Restore selected workspace content or create a new branch from the Snapshot.

### HISTORY_REVERT
Undo changes while preserving history; preferred for governed/shared history.

### POINTER_RESET
Move branch/ref backward. High-risk because it may rewrite visible history.

### PRODUCTION_ROLLBACK
Operational rollback of a deployed system; separate from Git-only restore.

## 10. Restore Safety

Before restore/revert/reset:

1. capture current Git identity
2. inspect dirty worktree
3. create pre-restore safety Snapshot where possible
4. identify affected paths/commits
5. identify authority/lifecycle impact
6. apply Human Approval class
7. execute
8. verify
9. record resulting identity

Never destroy the only known recoverable state.

## 11. Dirty Worktree

Dirty worktree is not a valid governed Snapshot.

Existing execution rule remains:
- explicit checkpoint paths
- no indiscriminate staging
- unrelated dirty paths may block checkpoint/recovery

## 12. Lifecycle Reconciliation After Restore

Restoring code does not automatically restore valid governance state.

If authoritative artifacts or implementation commits move backward/forward:
- apply downstream invalidation/rerun rules
- recompute current repository identity
- invalidate stale Stage status/authorization as required

Do not blindly restore old `.sdd/state` as truth without reconciliation.

## 13. User UX Mapping

| User sees | Underlying meaning |
|---|---|
| Save Version | governed checkpoint/snapshot |
| Snapshot | exact commit + SDD metadata |
| Compare | Git diff + evidence delta |
| Restore | governed restore/revert workflow |
| Verified | Stage 09 PASS at exact commit |
| Ready to Release | Stage 10 eligible at exact commit |
| Release | exact commit + release identity/tag |
| Undo | usually history-preserving revert |

## 14. Release Identity

A formal release should contain at minimum:

```yaml
release:
  version: "v1.2.0"
  commit: "<full sha>"
  tag: "v1.2.0"
  stage09: "PASS"
  stage10: "READY"
  target_environment: "production"
  rollback_reference: "<known-good snapshot/release>"
```

## 15. Known-Good Rollback

Stage 10 should identify a previous known-good Snapshot/Release where rollback is in scope.

Missing critical rollback remains a Stage 10 blocker.

## 16. Authority Boundary

Creating a Snapshot does NOT:
- approve Product Requirement
- create Stage 07 PASS
- create implementation authorization
- create Stage 09 PASS
- create Stage 10 READY
- authorize production deployment

Snapshot records state; it does not create authority.

## 17. Multi-Agent / Concurrency

Each workspace/agent must use an explicit baseline commit.

Stale baseline, unrelated changes, or merge conflicts must fail closed or route through governed reconciliation.

No agent may silently merge unrelated work.

## 18. Acceptance Tests

1. Atomic Task checkpoint maps to exact commit.
2. Snapshot stores full commit SHA.
3. Branch movement does not alter old Snapshot identity.
4. Dirty unrelated worktree blocks automatic Snapshot.
5. Checkpoint does not stage unrelated files.
6. Stage 09 PASS applies only to reviewed commit.
7. New commit after Stage 09 is not implicitly verified.
8. Stage 10 readiness binds to exact release commit.
9. Snapshot creation grants no lifecycle authority.
10. Compare uses exact commit pair.
11. Default undo preserves history where applicable.
12. Shared-history reset requires high-risk approval.
13. Restore creates/records pre-restore safety identity when possible.
14. Restore invalidates affected lifecycle state.
15. Production rollback with data impact requires A3.
16. Metadata/Git conflict fails closed.
