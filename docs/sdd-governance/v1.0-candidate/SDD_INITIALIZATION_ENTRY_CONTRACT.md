# SDD_INITIALIZATION_ENTRY_CONTRACT.md

> Contract Version: 1.0-draft
> Decision Basis: D-017
> Lifecycle Position: Before Stage 01; not a Stage
> Authority: NONE
> Owner: SDD Orchestrator / Control Plane

---

## 1. Purpose

`INITIALIZATION_ENTRY` converts a user request plus repository/runtime evidence into a lawful SDD routing decision.

It exists so the user can describe intent naturally without understanding Stage numbering.

---

## 2. Non-Authority Invariant

`INITIALIZATION_ENTRY` owns no product, requirement, technical, design, governance, task, verification, or release authority.

It may classify and route. It may not decide or rewrite authoritative content.

---

## 3. Required Inputs

As available:

- user request
- repository presence
- `.sdd/system.yaml`
- `.sdd/stages.yaml`
- `.sdd/state/project-state.yaml`
- `.sdd/state/implementation-state.*`
- `.sdd/state/authority-state.*`
- Git branch / HEAD
- Git working-tree status
- recent checkpoints / release identity
- known recovery provenance

Missing inputs must be explicitly represented as missing; they must not be invented.

---

## 4. Request Types

Canonical request types:

- `NEW_PROJECT`
- `RESUME_PROJECT`
- `CHANGE_REQUEST`
- `IMPLEMENTATION_FIX`
- `RECOVERY_CANDIDATE`
- `INSPECTION_ONLY`
- `AMBIGUOUS`

---

## 5. Routing Rules

### NEW_PROJECT
Route: `01`

### RESUME_PROJECT
Route to the current legally authorized lifecycle position derived from repository state.

### CHANGE_REQUEST
Classify affected domain:

| Change | Owner |
|---|---|
| Product intent | 01 |
| Product behavior / scope / priority / AC | 02 |
| Technical contract | 03 |
| Implementation design | 04 |
| Agent / repository governance | 05 |
| Task decomposition only | 06 |

After upstream formal artifact changes, downstream rerun rules apply.

### IMPLEMENTATION_FIX
Only route directly toward implementation/convergence when current authority contracts are unchanged and existing lifecycle authorization permits it.

### RECOVERY_CANDIDATE
Route to Recovery Eligibility Check. Never direct to Stage 09 merely because code exists.

### AMBIGUOUS
Route: `HUMAN_DECISION`

---

## 6. Fail-Closed Rules

The Entry must stop and request resolution if:

- repository identity is uncertain
- lifecycle state conflicts with Git evidence
- authority ownership is ambiguous
- requested change crosses multiple domains without safe routing
- implementation authorization is stale or missing
- working tree contains unexplained changes
- recovery provenance is insufficient
- request would require retroactive authorization
- protected authority artifacts appear modified outside owner-stage flow

---

## 7. Output Schema

Example logical schema:

```yaml
entry_result:
  request_type: NEW_PROJECT | RESUME_PROJECT | CHANGE_REQUEST | IMPLEMENTATION_FIX | RECOVERY_CANDIDATE | INSPECTION_ONLY | AMBIGUOUS
  repository_state: NEW | EXISTING_CLEAN | EXISTING_DIRTY | UNKNOWN
  lifecycle_state: null | "01" | "02" | "03" | "04" | "05" | "06" | "07" | "08" | "09" | "10"
  affected_authority_domains: []
  implementation_authorized: false
  release_authorized: false
  recovery_required: false
  human_decision_required: false
  recommended_route: "01"
  required_preconditions: []
  evidence_refs: []
```

This output is routing evidence, not lifecycle authority.

---

## 8. UX Rule

The end user should not need to know `INITIALIZATION_ENTRY` exists.

Typical UX:

> User: 「我要做一個股票研究系統。」

System internally:
`INITIALIZATION_ENTRY → NEW_PROJECT → Stage 01`

Or:

> User: 「把目前登入流程改成支援 passkey。」

System internally:
`INITIALIZATION_ENTRY → CHANGE_REQUEST → classify domain → owner stage`

---

## 9. Compatibility

This contract must remain provider-agnostic.

It cannot depend on:
- Codex-specific reasoning
- Claude-specific reasoning
- OpenAI API availability
- chat-session memory

A provider may assist classification, but deterministic evidence and authority rules remain enforced by the Orchestrator.

---

## 10. Acceptance Criteria for Runtime Implementation

The implementation is not complete until tests prove at least:

1. New empty repo routes to Stage 01.
2. Existing valid state resumes without replaying Stage 01.
3. Product behavior change routes to Stage 02.
4. Technical contract change routes to Stage 03.
5. Design-only change routes to Stage 04.
6. Agent permission change routes to Stage 05.
7. Task-only decomposition change routes to Stage 06.
8. Existing code with missing provenance does not jump directly to Stage 09.
9. Missing/stale implementation authorization prevents Stage 08 routing.
10. Conflicting repository/state evidence routes to HUMAN_DECISION.
11. Chat memory alone cannot determine lifecycle position.
12. Initialization Entry cannot grant implementation or release authorization.
