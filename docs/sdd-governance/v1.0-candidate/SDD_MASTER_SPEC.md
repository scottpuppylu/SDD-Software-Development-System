# SDD_MASTER_SPEC.md

> Version: v1.0-candidate
> Status: Release Candidate — Governance Complete / Runtime Partial
> Baseline Governance: Shared Knowledge v2.3
> Date: 2026-09-09
> Purpose: SDD normative source of truth.

## 0. Governance Rule

Authority order:

1. `SDD_MASTER_SPEC.md`
2. Accepted entries in `SDD_DECISION_LOG.md`
3. Normative contracts referenced by this Master Spec
4. `SDD_Current_Architecture.md`
5. Implementation roadmaps / test matrices
6. Chats, experiments, drafts

Chat, model output, implementation convenience, provider capability, or runtime state must not silently override normative governance.

---

## 1. System Definition

SDD is a governed Spec-Driven Development control system.

Canonical flow:

`Intent → Requirements → Technical Contract → Design → Agent Governance → Tasks → Pre-Gate → Implementation → Verification → Release Readiness → Protected External Action`

SDD owns:
- lifecycle
- domain authority
- authorization
- Gate semantics
- evidence requirements
- recovery
- human approval boundaries
- provider constraints
- security/cost control

LLM / Coding Agent owns only provider-specific reasoning and/or authorized execution.

---

## 2. Canonical Lifecycle

`INITIALIZATION_ENTRY` exists before the lifecycle but is **not a Stage**.

Canonical lifecycle remains exactly:

```text
01 Product Proposal
02 Product Requirements
03 Technical Specification
04 Software Design
05 Agent Governance
06 Implementation Tasks
07 Pre-Implementation Gate
08 Implementation Runner
09 Verification & Convergence
10 Handoff & Release Readiness
```

Stage 01–06 = Authoring / Specification
Stage 07–09 = Execution / Verification
Stage 10 = Handoff / Release Readiness

---

## 3. Domain-Specific Authority

| Domain | Authority |
|---|---|
| Product Intent | `docs/proposal.md` |
| Product Requirement / Scope / Priority / AC | `docs/PRD.md` |
| Technical Contract | `docs/spec.md` |
| Implementation Decision | `docs/Design.md` |
| Agent / Repository Governance | `AGENTS.md` |
| Execution Decomposition | `tasks.md` |
| Implementation Evidence | Code + Tests + Git |
| Stage 07 Decision | Pre-Implementation Gate Report |
| Stage 09 Decision | `docs/handoff/verification-report.md` |
| Stage 10 Decision | `docs/handoff/handoff-report.md` |

Cross-domain conflict rule:

`detect → report → block → return to authoritative owner`

No downstream Stage, Orchestrator, Agent, infrastructure privilege, Human Decision mechanism, or provider capability may rewrite another domain's authority directly.

---

## 4. Stage Contracts

### Stage 01 — Product Proposal
Output: `docs/proposal.md`
Owns WHY / WHO / PROBLEM / OUTCOME / MVP direction.

### Stage 02 — Product Requirements
Output: `docs/PRD.md`
Owns FR / NFR / EC / business rules / product constraints / priority / AC.

### Stage 03 — Technical Specification
Output: `docs/spec.md`
Owns technical state, schema, API/interface, validation, error, security/privacy, persistence, integration and technical invariants.

### Stage 04 — Software Design
Output: `docs/Design.md`
Owns architecture, module boundaries, implementation strategy, dependencies, framework/library, observability and repository mapping.

### Stage 05 — Agent Governance
Output: `AGENTS.md`
Owns permissions, prohibitions, authority-conflict behavior, testing, Git checkpoint, start/resume, protected scope and escalation.

### Stage 06 — Implementation Tasks
Output: `tasks.md`
Atomic Tasks must be independently executable, verifiable, traceable and checkpointable.

### Stage 07 — Pre-Implementation Gate
Result: `PASS | FAIL | INCOMPLETE`

Only:

`Stage 07 PASS → IMPLEMENTATION_AUTHORIZATION = YES`

### Stage 08 — Implementation Runner
Entry requires current implementation authorization.

Canonical loop:

`Read Task → Validate Authority/Scope → Baseline → Implement → Verify → Git Checkpoint → Update State`

Default invariant:

`one independently verifiable Atomic Task → one checkpoint`

### Stage 09 — Verification & Convergence
Result: `PASS | FAIL | INCOMPLETE`

Implementation gap:
`09 → convergence task → 08 → verify → 09`

Authority conflict:
`owner Stage → propagate → 07 → 08 → 09`

### Stage 10 — Handoff & Release Readiness
Entry: Stage 09 PASS

Result:
`READY | READY_WITH_KNOWN_ISSUES | BLOCKED`

`READY != unconditional production authorization`

---

## 5. Traceability

Forward:

`Goal → PRD/AC → SPEC → DES → Task → Code → Test/Evidence`

Reverse:

`Code/Test → Task → DES → SPEC → PRD/AC`

Stage 09 must support bidirectional traceability.

---

## 6. Restart / Recovery

Execution state must not depend on chat memory.

Recovery derives from:
- authoritative artifacts
- `.sdd/state/*`
- Git status / branch / HEAD / recent commits
- last verified commit
- current / next task
- recovery provenance

Pre-existing implementation recovery may exist as an exception path, but may not fabricate historical Stage 07 PASS or retrospective implementation authorization.

---

## 7. Initialization Entry

Formal contract:
`SDD_INITIALIZATION_ENTRY_CONTRACT.md`

It is a non-Authority Intake & Routing Layer.

Routes:
- New Project → Stage 01
- Resume → current lawful lifecycle position
- Change Request → affected authority owner
- Pre-existing Implementation → Recovery Eligibility
- Ambiguous / unsafe → HUMAN_DECISION

It cannot create Stage/Gate authority.

---

## 8. Agent Adapter

Formal contract:
`SDD_AGENT_ADAPTER_CONTRACT.md`

Roles:
- Reasoning Adapter
- Implementation Adapter

Invariant:

`Agent edits → Orchestrator verifies → Git records → Stage 09 decides → Stage 10 decides release readiness`

Provider narrative is not runtime truth.

Current mapping:
- Codex CLI: validated principal reasoning + implementation provider
- OpenAI Responses-style API: reasoning path
- Claude Code: approved compatibility target; runtime implementation pending
- Future providers: require common conformance tests

---

## 9. Human Approval

Formal contract:
`SDD_HUMAN_APPROVAL_BOUNDARY_MATRIX.md`

Default mode:
`GOVERNED_AUTONOMY`

Classes:
- A0 AUTO
- A1 NOTIFY / AUDIT
- A2 HUMAN DECISION REQUIRED
- A3 EXPLICIT HIGH-RISK APPROVAL

Routine authorized work proceeds automatically.

Material product choice, substantive authority conflict, permission/security expansion, protected production action, destructive/irreversible operation, and governance baseline change require human intervention as defined by the contract.

Human Decision is durable authoritative input; owning Stage applies it.

---

## 10. Git / Snapshot / Restore

Formal contract:
`SDD_SNAPSHOT_GIT_CONTRACT.md`

- Git commit = immutable version identity
- Checkpoint = governed execution commit
- Snapshot = exact commit + SDD metadata
- Verified Version = Stage 09 PASS at exact commit
- Release-Ready Version = eligible Stage 10 result at exact commit
- Release = exact commit + version/release identity/tag

Branch is context, not identity.

Restore is split into:
- workspace restore
- history-preserving revert
- pointer reset
- production rollback

Snapshot itself creates no lifecycle authority.

---

## 11. Zero-DevEnv / Remote Sandbox Security

Formal contract:
`SDD_REMOTE_SANDBOX_SECURITY_CONTRACT.md`

Security posture:
`FAIL-CLOSED + LEAST CAPABILITY + EPHEMERAL BY DEFAULT`

Sandbox classes:
- S0 READ_ONLY_REASONING
- S1 WORKSPACE_WRITE
- S2 STAGING_OPERATION
- S3 PROTECTED_PRODUCTION_ACTION

Key rules:
- project/tenant isolation
- deny-by-default network
- short-lived scoped credentials
- no production-write credential in general Stage 08
- resource limits
- audit/evidence export
- Control Plane kill switch
- narrow protected-action runner preferred for production actions

Remote Sandbox is infrastructure, not Authority.

---

## 12. Cost / Token Governance

Formal contract:
`SDD_COST_TOKEN_GOVERNANCE_CONTRACT.md`

Measurement truth classes:
- ACTUAL
- ESTIMATED
- CONTEXT_SIZE
- UNAVAILABLE

Unavailable is not zero.

Bytes/chars are not token truth.

Hard budget exhaustion:
`stop new metered dispatch → preserve state/evidence → BUDGET_BLOCKED`

Budget must never trigger silent truncation of required authority/governance/evidence.

Cost-aware provider routing may use only SDD-conformant adapters.

---

## 13. Upgrade / Patch Governance

Formal contract:
`SDD_UPGRADE_PATCH_PROTOCOL.md`

Version identities are separated:
- Governance Version
- Runtime Version
- Provider Profile Version
- Shared Knowledge / Stage Instruction versions as applicable

Change classes:
- U0 Non-normative patch
- U1 Runtime patch
- U2 Provider/model compatibility upgrade
- U3 Governance change
- U4 Breaking governance/state migration

Running SDD may propose/test candidate changes, but may not self-authorize U3/U4.

Candidate changes must be isolated, validated, release-identified, staged and rollback-capable.

---

## 14. Model / Provider Upgrade Policy

New models/providers are evaluated, never auto-promoted simply because they are newer or stronger.

Evaluate:
- reasoning
- coding
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

Possible outcomes:
- APPROVE_DEFAULT
- APPROVE_OPTIONAL
- APPROVE_LIMITED_STAGE
- HOLD_FOR_MORE_EVIDENCE
- REJECT

---

## 15. Completion Definition

A project is not complete merely because code exists.

Minimum governed completion:

- Stage 07 PASS
- required Stage 08 tasks DONE
- Stage 09 PASS
- Stage 10 READY or READY_WITH_KNOWN_ISSUES
- deployment/smoke verification when included in project scope
- protected external actions separately authorized when required

---

## 16. SDD v1.0 Candidate Maturity

### Governance Complete
The following normative governance areas are now defined:
- lifecycle and authority
- Initialization Entry
- Agent Adapter
- Human Approval
- Snapshot/Git
- Remote Sandbox security
- Cost/Token governance
- Upgrade/Patch governance

### Runtime Partial / Pending Implementation
Not yet production-complete:
- Claude Code adapter implementation
- multi-provider router implementation
- production Remote Sandbox provider/runtime
- Zero-DevEnv production deployment
- Snapshot registry/restore engine
- budget interlock/cost ledger
- upgrade migration/staged rollout controller
- full Web UI
- full v1.0 conformance/acceptance suite

These are implementation gaps, not missing governance principles.

---

## 17. v1.0 Candidate Release Rule

This document may become `v1.0` only after:

1. cross-contract terminology check PASS
2. Decision Log conflict check PASS
3. acceptance matrix defined
4. consolidated implementation roadmap defined
5. runtime-gap inventory defined
6. final historical audit PASS
7. governance package has an exact release identity/tag when moved into the SDD repository
