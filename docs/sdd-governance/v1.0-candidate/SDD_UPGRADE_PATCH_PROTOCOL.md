# SDD_UPGRADE_PATCH_PROTOCOL.md

> Contract Version: 1.0-draft
> SDD Baseline: v0.9-upgrade-patch-rc
> Status: Accepted Governance / Release Contract
> Owner: SDD Governance + Release Control
> Principle: SDD MAY IMPROVE ITSELF, BUT MAY NOT SELF-AUTHORIZE GOVERNANCE CHANGE

---

## 1. Purpose

This protocol governs changes to SDD itself, including:
- Orchestrator code
- Stage runtime behavior
- Shared Knowledge
- Stage Instructions
- Agent Adapters
- Sandbox runtime
- Snapshot/Git behavior
- Human Approval rules
- Cost/Token governance
- provider/model configuration
- schemas/contracts
- Web UI/control plane

Core invariant:

`The running SDD instance must not silently rewrite the governance baseline that authorizes it.`

---

## 2. Separate Version Identities

SDD maintains at least:

### Governance Version
Normative contracts/specification.

Examples:
- MASTER_SPEC
- Decision Log
- Shared Knowledge
- Stage contracts
- Human Approval
- Agent Adapter
- Sandbox security

### Runtime Version
Executable implementation:
- orchestrator
- adapters
- CLI/backend
- sandbox integration
- UI

### Provider Profile Version
Configured/approved provider/model capabilities.

These versions may move independently but compatibility must be explicit.

---

## 3. Change Classes

### U0 — NON-NORMATIVE PATCH
Examples:
- typo/docs formatting
- logging fix
- internal refactor with proven equivalent behavior
- test-only hardening

May be automated within already-approved task scope.

### U1 — RUNTIME PATCH
Changes implementation behavior but not normative governance.

Examples:
- bug fix
- performance improvement
- adapter implementation
- sandbox provider integration

Requires normal SDD lifecycle validation and release.

### U2 — COMPATIBILITY / PROVIDER UPGRADE
Examples:
- new Codex version
- Claude Code adapter
- new model/provider
- provider API version migration

Requires Adapter Contract conformance and compatibility validation.

### U3 — GOVERNANCE CHANGE
Changes:
- Stage semantics
- authority
- Gate rules
- Human Approval
- protected scopes
- security baseline
- lifecycle
- evidence requirements

Requires Human Approval A2 and explicit Decision Log / Master Spec update.

### U4 — BREAKING GOVERNANCE / MIGRATION
Changes compatibility of persisted state, project contracts, lifecycle, schema, or rollback assumptions.

Requires explicit migration plan, backward/forward compatibility analysis, A2 approval, staged rollout and rollback.

---

## 4. No In-Place Self-Authorization

A production/running SDD may:
- detect a possible improvement
- draft a proposal
- create a candidate branch
- run tests/evaluation

It MUST NOT:
- directly modify the currently active normative baseline
- approve its own governance change
- activate its own U3/U4 change
- rewrite Decision Log history
- retroactively claim compatibility
- bypass Human Approval A2

Candidate changes are evaluated by the current trusted baseline.

---

## 5. Canonical Upgrade Flow

```text
Detect / Request Change
      ↓
Classify U0–U4
      ↓
Identify affected authority/contracts
      ↓
Create isolated candidate branch/workspace
      ↓
Patch candidate only
      ↓
Static / Contract / E2E tests
      ↓
Installation Smoke Test
      ↓
Compatibility / Migration Test
      ↓
Real-project validation
      ↓
Security / Cost regression
      ↓
Release Candidate Snapshot
      ↓
Human Approval if required
      ↓
Tag / Publish
      ↓
Staged Activation
      ↓
Post-activation Smoke
      ↓
Promote or Roll Back
```

---

## 6. Candidate Isolation

Upgrade work MUST occur away from the active production baseline.

Allowed:
- separate Git branch
- separate worktree
- separate repository clone
- isolated Remote Sandbox

Forbidden by default:
- modifying active production files in place
- overwriting active governance artifacts before validation
- testing U3/U4 changes against only the live control plane

---

## 7. Required Impact Analysis

Before implementation, identify affected:
- Master Spec sections
- Decision Log entries
- Shared Knowledge
- Stage Instructions
- Stage entry/exit rules
- state schemas
- persisted project data
- Agent Adapter contract
- sandbox/security
- snapshot/recovery
- approval classes
- cost/token policies
- provider compatibility
- UI/API contracts

Unknown impact on governance/security must fail closed.

---

## 8. Shared Knowledge / Instructions Versioning

Shared Knowledge and Stage Instructions may version independently.

Every runtime release must declare compatible versions.

Example:

```yaml
sdd_release:
  runtime: 1.2.0
  governance: 1.0.0
  shared_knowledge: 2.4
  stage_instruction_set: 1.3
```

A runtime must refuse activation if required governance assets are missing/incompatible.

---

## 9. Provider / Model Upgrade

A new model/provider is a candidate, not an automatic replacement.

Evaluate:
- reasoning quality
- coding quality
- structured output
- tool use
- sandbox compatibility
- context handling
- reliability
- latency
- cost/token observability
- reproducibility
- security
- SDD Gate/evidence compatibility

Examples include Codex, Claude Code, OpenAI models, and future models such as Astra-class candidates.

New provider/model must pass relevant common conformance tests.

---

## 10. Model Evaluation Outcome

Possible outcome:
- APPROVE_DEFAULT
- APPROVE_OPTIONAL
- APPROVE_LIMITED_STAGE
- HOLD_FOR_MORE_EVIDENCE
- REJECT

A stronger benchmark score alone does not authorize default replacement.

---

## 11. Adapter Upgrade Compatibility

For provider/adapter updates:
- run common Agent Adapter conformance suite
- confirm result schema
- confirm protected path behavior
- confirm sandbox behavior
- confirm error normalization
- confirm auth/session boundary
- confirm verification remains Orchestrator-owned

If any mandatory capability regresses, do not promote.

---

## 12. Migration Policy

U4 changes require:
- source version range
- target version
- migration steps
- preconditions
- backup/snapshot
- dry-run where practical
- migration verification
- rollback or forward-recovery plan
- incompatible project handling

Do not assume all existing projects can be migrated automatically.

---

## 13. State Compatibility

Persisted SDD/project state must carry schema/version identity.

Runtime must classify:
- COMPATIBLE
- MIGRATION_REQUIRED
- UNSUPPORTED
- UNKNOWN

UNKNOWN fails closed.

---

## 14. Staged Rollout

Preferred activation:
1. offline/local test
2. isolated sandbox test
3. staging control plane
4. limited/canary project
5. broader production
6. full promotion

U3/U4 changes should not jump directly from development to all projects.

---

## 15. Real-Project Validation

At least one representative project must validate:
- new project flow
- resume/recovery
- Stage 07→08 authorization
- Stage 08 execution
- Stage 09 verification
- Stage 10 release
- Snapshot/restore
- Human Decision
- budget blocking
- sandbox failure path

For high-impact upgrades, multiple project shapes are preferred.

---

## 16. Upgrade Gate

A release candidate may promote only if:
- required tests PASS
- E2E consistency PASS
- no unresolved governance conflict
- security regression = 0
- required authority/evidence coverage intact
- migration/rollback readiness satisfied
- provider adapter conformance PASS where affected
- required Human Approval obtained

---

## 17. Release Identity

Each SDD release must bind:
- version
- exact Git commit
- governance version
- included contract versions
- compatible state/schema versions
- provider/adapter compatibility matrix
- migration notes
- rollback reference
- release evidence

Annotated tag recommended.

---

## 18. Automatic Patch Boundary

SDD may automatically apply U0/U1 patches only when a policy explicitly authorizes:
- affected files
- test requirements
- no governance semantic change
- rollback path
- deployment scope

Even then, production activation may require existing deployment pre-authorization.

U2/U3/U4 are not silently auto-promoted.

---

## 19. Emergency Security Patch

Emergency path may accelerate testing but does not erase evidence.

Minimum:
- isolate patch
- identify security issue
- targeted tests
- security verification
- exact release identity
- rollback
- incident linkage
- Human Approval according to protected-action policy

Emergency does not mean ungoverned.

---

## 20. Rollback

Before activation:
- preserve current known-good Release/Snapshot
- preserve current governance version
- verify rollback compatibility

Rollback modes:
- runtime rollback
- provider configuration rollback
- governance rollback
- state forward-recovery

Governance rollback must account for projects already created/migrated under the newer version.

---

## 21. No Silent Governance Downgrade

Rollback/provider fallback must not silently weaken:
- security
- approval
- evidence
- lifecycle
- protected paths
- authority semantics

If the old runtime cannot safely understand current state, block rather than force downgrade.

---

## 22. Patch Provenance

Each upgrade must record:
- change request
- change class U0–U4
- author/proposer
- affected contracts
- candidate commit
- tests/evidence
- approval refs
- release commit/tag
- activation time
- rollback reference
- outcome

---

## 23. Self-Improvement Loop

Allowed autonomous loop:

```text
Observe problem/opportunity
→ propose hypothesis
→ create candidate
→ test/evaluate
→ produce evidence
→ request approval if boundary requires
→ promote through release protocol
```

Forbidden loop:

```text
Observe
→ rewrite own rules
→ self-approve
→ deploy
```

---

## 24. Acceptance Tests

1. Running production SDD cannot directly mutate active governance baseline.
2. U0 change can be automated without governance version change.
3. U1 patch requires normal validation/release.
4. U2 provider change runs adapter conformance.
5. U3 governance change requires A2.
6. U4 breaking change requires migration plan.
7. Candidate runs in isolated branch/workspace.
8. Release declares governance/runtime compatibility.
9. Unknown persisted-state version fails closed.
10. Provider benchmark superiority cannot auto-promote default.
11. Failed conformance blocks provider promotion.
12. Staging/canary failure prevents broad rollout.
13. Rollback reference exists before production activation.
14. Rollback does not silently downgrade governance/security.
15. Decision Log history is not rewritten.
16. Real-project validation covers normal and recovery paths.
17. Emergency patch still records evidence/provenance.
18. Self-improvement may propose but cannot self-authorize U3/U4.
