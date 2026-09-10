# SDD_HUMAN_APPROVAL_BOUNDARY_MATRIX.md

> Contract Version: 1.0-draft
> SDD Baseline: v0.5-human-approval-rc
> Status: Accepted Governance Contract
> Owner: SDD Governance / Orchestrator
> Default Operating Mode: GOVERNED_AUTONOMY

---

# 1. Purpose

This contract defines when SDD may continue autonomously and when it must stop for a Human Decision.

The design goal is not:

`Every Stage → ask human`

and not:

`AI → decide everything`

The governing model is:

```text
Routine, reversible, already-authorized work
        → AUTO

Material authority choice, irreversible/high-risk action,
external commitment, or unresolved conflict
        → HUMAN APPROVAL
```

Human approval is triggered by the nature of the decision or action, not merely by Stage number.

---

# 2. Default Operating Mode — GOVERNED_AUTONOMY

The default SDD mode is:

`GOVERNED_AUTONOMY`

Meaning:

- AI / Orchestrator should continue automatically when the current authority is clear and execution stays inside approved scope.
- SDD must stop when a required human boundary is crossed.
- The system must not ask for human confirmation for routine mechanical work merely because a new Stage begins.
- The system must not treat lack of response as approval.
- Mandatory approval points fail closed.

This is the default for SDD v1 planning.

---

# 3. Human Decision Is Input, Not Artifact Rewriting Authority

A Human Decision may resolve a substantive choice.

But the Human Decision mechanism MUST NOT directly rewrite:

- `docs/proposal.md`
- `docs/PRD.md`
- `docs/spec.md`
- `docs/Design.md`
- `AGENTS.md`
- `tasks.md`

Canonical process:

```text
Human Decision
→ record decision + provenance
→ route to owning Stage
→ owning Stage updates authoritative artifact
→ invalidate affected downstream state
→ rerun applicable Gate
```

This preserves domain-specific authority.

---

# 4. Approval Classes

SDD uses four approval classes.

## A0 — AUTO

No human approval required.

Allowed only when all of the following are true:

- authority is already established
- no material product choice is being invented
- no cross-domain conflict exists
- scope remains inside current authorization
- operation is reversible or operationally low-risk
- no production/external destructive side effect occurs
- no protected security/credential boundary is expanded

---

## A1 — NOTIFY / AUDIT

No blocking approval required, but the action/result should be surfaced or recorded.

Examples:

- successful automated test/build
- Git checkpoint
- non-blocking warning
- routine Stage progression
- automated retry within a defined policy
- provider fallback that preserves the exact required capability/security contract

A1 is informational, not an approval Gate.

---

## A2 — HUMAN DECISION REQUIRED

Execution must stop until an authorized human resolves the decision.

Examples:

- material product behavior or scope is ambiguous
- new P0 behavior must be selected
- conflict between authoritative domains
- requested behavior changes approved business meaning
- recovery/adoption requires a substantive provenance decision
- permission boundary expansion
- security exception
- destructive data action
- production deployment without an existing valid pre-authorization policy

---

## A3 — EXPLICIT HIGH-RISK APPROVAL

A stronger approval is required immediately before the protected action.

Examples:

- destructive production migration
- irreversible production data deletion
- secret/credential rotation with production impact
- disabling a security control
- irreversible external publication/commitment
- production rollback that may discard or rewrite data
- privileged infrastructure/IAM change

A3 approval must identify the exact action and scope. General approval such as "do whatever is needed" is insufficient.

---

# 5. Canonical Human Approval Matrix

| Activity / Decision | Default | Notes |
|---|---|---|
| Clarify user intent conversationally | A0 | May ask questions when material ambiguity remains |
| Draft `proposal.md` from explicit user intent | A0 | Must not invent material goals |
| Choose material product goal / target user / MVP boundary not already supplied | A2 | Human owns substantive product choice |
| Draft PRD from approved intent | A0 | Drafting is automatic |
| Establish or materially change product behavior / P0 scope / AC meaning | A2 | AI may propose options, not silently decide |
| Technical specification within approved product requirements | A0 | Unless it introduces material external/security/data choice |
| Select routine implementation technique within approved constraints | A0 | Stage 04 authority |
| High-impact architecture choice with major irreversible cost/lock-in/security implication | A2 | Human choice recorded, Stage 04 reruns |
| Generate/update AGENTS rules within already-approved governance baseline | A0 | Scope expansion requires A2 |
| Expand agent write/tool/network/credential permission | A2 | A3 if privileged production access |
| Decompose approved work into Atomic Tasks | A0 | Does not itself authorize implementation |
| Stage 07 evaluation | A0 | Formal Gate may be automatic |
| Grant implementation authorization from valid Stage 07 PASS | A0 | Mechanical consequence of formal Gate |
| Stage 08 task execution inside authorized scope | A0 | Includes ordinary code edits |
| Task-scoped test/build/lint/typecheck | A0 | Runtime evidence controlled by Orchestrator |
| Git task checkpoint | A0 / A1 | Automatic, auditable |
| Modify protected authority artifact from Stage 08 | FORBIDDEN | Must route to owning Stage |
| Implementation discovers additional product/contract scope | A2 if substantive choice needed | Otherwise route owner Stage automatically |
| Stage 09 verification | A0 | Verification decision can be automated |
| Implementation-gap convergence task | A0 | If authority unchanged |
| Authority conflict resolution | A2 | Human resolves substantive choice; owner Stage applies it |
| Stage 10 release-readiness evaluation | A0 | READY is not itself production execution |
| Create release tag / immutable release artifact | A0 / A1 | If covered by release policy and reversible enough |
| Deploy to local/dev/test sandbox | A0 | No material external impact |
| Deploy to staging | A0 / A1 | Under approved staging policy |
| Deploy to production | A2 by default | May be pre-authorized by explicit deployment policy |
| Routine production deploy under valid pre-authorization policy | A0 / A1 | Only within exact scope/guardrails |
| Destructive production DB migration | A3 | Cannot be covered by broad routine pre-approval |
| Non-destructive backward-compatible migration | A2 by default | May become A0 under explicit migration policy |
| Production data deletion / irreversible mutation | A3 | Exact target required |
| Rollback application binary/config only | A2 by default | Can be pre-authorized under rollback policy |
| Rollback affecting production data | A3 | Exact data/recovery impact required |
| Read secret reference without exposing value | A0 | If already authorized |
| Introduce/rotate/revoke production credentials | A3 | Privileged external effect |
| Change auth/IAM/security boundary | A2 or A3 | A3 when production privilege is affected |
| Publish externally / send customer-facing communication | A2 by default | May be policy-pre-authorized for routine notifications |
| Spend money / create paid resource | A2 | Must be explicit |
| Increase recurring cost beyond approved budget | A2 | Cost policy may define threshold |
| Delete cloud resource / repository / release | A3 | Protected destructive action |
| Recovery eligibility evaluation | A0 | Evaluation only |
| Approve pre-existing implementation recovery/adoption | A2 | Cannot fabricate historical authority |
| Provider/model selection within approved policy | A0 | Must satisfy Adapter Contract |
| Weaken sandbox/evidence/security because preferred provider unavailable | FORBIDDEN | No silent downgrade |
| Change SDD Master Spec / governance baseline | A2 | SDD itself is governed |
| Patch SDD implementation without changing normative governance | A0 | Subject to normal SDD lifecycle |
| Release a new SDD governance baseline | A2 | Human approval of governance change |

---

# 6. Stage-by-Stage Human Boundary

## Initialization Entry

AUTO:
- inspect repository/state
- classify request
- recommend route

HUMAN:
- ambiguous material intent
- conflicting repository identity/provenance that cannot be safely resolved
- request requires a substantive authority choice

---

## Stage 01 — Product Proposal

AUTO:
- structure user-supplied intent
- record goals, constraints, assumptions

HUMAN:
- choose a material goal, target user, core outcome, or MVP boundary not actually supplied/approved

AI may recommend. It may not silently promote recommendation to approved Product Intent.

---

## Stage 02 — Product Requirements

AUTO:
- translate approved intent into candidate FR/NFR/EC/AC
- normalize wording
- improve testability

HUMAN:
- material product behavior choice
- new/changed P0 scope
- product tradeoff with meaningful user/business impact
- acceptance meaning where multiple materially different outcomes are valid

Human approval establishes the choice as authoritative input; Stage 02 then updates PRD.

---

## Stage 03 — Technical Specification

AUTO by default.

HUMAN only when the technical contract requires a material policy choice such as:

- material data retention/privacy boundary
- security exception
- external provider commitment with meaningful lock-in/cost/risk
- destructive semantics
- material regulatory/business-policy choice not already owned upstream

Routine API/schema/error/state decisions remain technical authority and should not cause approval fatigue.

---

## Stage 04 — Software Design

AUTO by default.

HUMAN when:

- architecture creates material irreversible lock-in
- substantial new recurring cost
- privileged/security boundary
- destructive operational model
- material availability/recovery tradeoff requiring owner acceptance

Normal framework/module/pattern choices should remain automated.

---

## Stage 05 — Agent Governance

AUTO for policy application.

HUMAN for permission expansion:

- broader writable scope
- network access not already allowed
- privileged credentials
- production access
- reduced sandbox
- bypass of protected artifact rules

---

## Stage 06 — Tasks

AUTO.

Task approval does not replace Stage 07 and does not create implementation authorization.

If task decomposition exposes unresolved product/technical/design choices, route to owner Stage; require human only if that owner-stage choice itself is A2/A3.

---

## Stage 07 — Pre-Implementation Gate

AUTO.

A valid deterministic/formal Stage 07 PASS may automatically set:

`IMPLEMENTATION_AUTHORIZATION = YES`

No redundant human "yes" is required after a valid PASS.

If Stage 07 finds a human-boundary issue, result is FAIL/INCOMPLETE with routing to Human Decision / authority owner as applicable.

---

## Stage 08 — Implementation

AUTO inside the authorized Atomic Task envelope.

HUMAN approval is not required for every edit.

Must stop when:

- scope expands
- protected authority must change
- destructive/high-risk external action is required
- permission must expand
- current authorization becomes stale
- unexpected repository state prevents safe continuation

---

## Stage 09 — Verification & Convergence

AUTO.

- implementation gap → automatic convergence loop allowed
- authority conflict → route to owner; A2 if substantive resolution is required

Stage 09 PASS itself does not require a human click.

---

## Stage 10 — Release Readiness

AUTO evaluation.

The Gate may produce:

- READY
- READY_WITH_KNOWN_ISSUES
- BLOCKED

without human approval if evidence supports it.

But:

`READY != production action authorization`

Actual production deployment follows the protected-action rules below.

---

# 7. Production and External Side-Effect Boundary

SDD distinguishes:

```text
Release Readiness
from
External Action Authorization
```

Stage 10 READY means:

`the artifact is eligible to be released`

It does NOT automatically mean:

`perform every external action now`

Default protected external actions include:

- production deployment
- destructive migration
- production data mutation/deletion
- privileged IAM/security changes
- credential rotation/revocation
- paid resource creation
- external publication or customer communication when not policy-pre-authorized

These use A2/A3.

---

# 8. Pre-Authorization Policies

To support long-running autonomous SDD, humans may create a bounded pre-authorization policy.

Example:

```yaml
pre_authorization:
  id: "PA-PROD-DEPLOY-001"
  action: "PRODUCTION_DEPLOY"
  environment: "production"
  service: "app-a"
  allowed_release_class: "non-destructive"
  required_stage10: "READY"
  required_ci: "PASS"
  rollback_required: true
  data_migration: "none"
  expires_at: "..."
  approved_by: "..."
```

If every condition is satisfied, the protected action may become A0/A1.

Pre-authorization MUST be:

- explicit
- scoped
- attributable
- revocable
- time/version/environment bounded where applicable
- machine-checkable

---

# 9. Non-Delegable / No-Broad-Preapproval Actions

The following cannot be authorized by a vague blanket statement:

- destructive production data deletion
- destructive schema migration
- disabling a critical security control
- privileged IAM elevation
- irreversible credential/recovery action
- rewriting governance history
- retroactive Stage authorization
- knowingly bypassing a failed required Gate

These require exact-action approval (A3), or are outright forbidden where governance says so.

---

# 10. Human Decision Record

Every blocking Human Decision must produce a durable record.

Minimum logical schema:

```yaml
human_decision:
  decision_id: "HD-..."
  status: "APPROVED | REJECTED | CHOICE_SELECTED"
  decision_class: "A2 | A3"
  authority_domain: "PRODUCT_REQUIREMENT"
  prompt_summary: "..."
  options_considered: []
  selected_resolution: "..."
  affected_artifacts: []
  affected_scope: []
  approved_action: null
  constraints: []
  provenance:
    actor: "human"
    timestamp: "..."
  invalidates_downstream: true
```

The record itself is authoritative input, not a direct replacement for owner artifacts.

---

# 11. Stale Approval Rules

Approval becomes invalid when material assumptions change.

Examples:

- artifact hash/version changed
- deployment target changed
- migration changed
- allowed files changed
- security scope expanded
- provider capability/sandbox changed materially
- release commit changed
- requested action changed
- approval expired/revoked

Stale approval MUST NOT be silently reused.

---

# 12. No Approval Laundering

Forbidden patterns:

- Agent writes the approval it wishes it had.
- Human approves one domain and system treats it as all-domain approval.
- PRD approval is treated as Stage 07 PASS.
- Stage 07 PASS is treated as Stage 09 PASS.
- Stage 10 READY is treated as unconditional production authorization.
- A broad project statement is treated as approval of an unrelated destructive action.
- Historical chat text is treated as current approval without applicable durable authority.

---

# 13. Approval UX

Human-facing approval should be compact and decision-oriented.

For A2, show:

- what decision is needed
- why SDD cannot decide it autonomously
- 2–4 materially distinct options when appropriate
- consequences
- recommended option may be shown, but not pre-selected as approved

For A3, show:

- exact protected action
- exact target/environment
- irreversible/destructive impact
- rollback/recovery situation
- evidence snapshot / release identity
- exact approval scope

Avoid repeatedly asking the human to approve facts that are already governed by formal Gate results.

---

# 14. Fail-Closed Invariant

When unsure whether A0 or A2/A3 applies:

- if uncertainty could materially change authority, security, irreversible state, external commitment, or production impact → require Human Decision
- otherwise route to the authoritative Stage for classification

No provider may downgrade A2/A3 to A0.

---

# 15. Acceptance Tests

Minimum governance tests:

1. Routine Stage 03 decision proceeds without human approval.
2. New material P0 behavior blocks for A2.
3. Stage 07 PASS automatically grants implementation authorization without redundant human confirmation.
4. Stage 08 routine edit proceeds automatically.
5. Stage 08 authority expansion stops and routes.
6. Stage 09 implementation gap loops automatically.
7. Stage 09 authority conflict requiring substantive choice stops for A2.
8. Stage 10 READY does not by itself trigger unapproved production deployment.
9. Production deployment without pre-authorization requires A2.
10. Valid bounded production pre-authorization allows eligible routine deploy.
11. Destructive production migration still requires A3.
12. Human decision cannot directly patch PRD/Spec/Design.
13. Changed release commit invalidates action-specific approval.
14. General "approve project" cannot authorize destructive production deletion.
15. Provider/model cannot self-approve permission expansion.
16. SDD governance baseline change requires A2.
