# SDD Software Development System - Current PRD

## 1. Authority and scope

This document is the approved CURRENT prospective `PRODUCT_REQUIREMENT` authority for the SDD Software Development System. It translates the approved CURRENT `PRODUCT_INTENT` in `docs/proposal.md` and the approved product-requirement decisions in `docs/project/current-prd-decision-brief.md` into formal, traceable product requirements. Project authority has explicitly approved this substantive PRD baseline.

This approved current baseline answers: **What must the SDD product do, and what observable behavior counts as complete?** It is not recovered or reconstructed historical Phase02 authority and does not derive product behavior from source, tests, implementation evidence, runtime state, or historical completion claims.

Approval owns only `PRODUCT_REQUIREMENT`. It creates no `TECHNICAL_CONTRACT` authority, `IMPLEMENTATION_DECISION` authority, task authority, Stage07 result, implementation authorization, Recovery Gate result, Stage09 result, or Stage10, release, or deploy authorization. All downstream artifacts require independent authority approval.

## 2. Product requirement baseline

The current MVP is a governed, user-visible development journey for a project owner or non-programmer. It accepts an incomplete idea, clarifies product requirements, preserves Human Decision authority, and progresses through specification, design, task decomposition, authorized AI-assisted coding, testing and verification, Git traceability, and maintenance with regression protection.

The MVP may use a local CLI or another suitable interface. LINE, remote operation, and cloud deployment are future-capability concerns and are not required to demonstrate the current MVP core.

Requirement keywords are normative: **must** is required behavior; **may** is permitted behavior. Each `FR-*`, `NFR-*`, and `EC-*` has one priority, at least one approved `G-*` goal, and an `AC-*` acceptance criterion.

## 3. Priority model

- **P0** — required for current MVP completion.
- **P1** — important, but not required to prove the current MVP core.
- **P2** — future or optional product expansion.

Priority counts in this approved current baseline are: **P0 = 34**, **P1 = 2**, and **P2 = 1**.

## 4. Functional Requirements

| ID | Priority | Requirement | Goals | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| FR-01 | P0 | The product must accept a highly incomplete initial idea, including a vague one-sentence idea, and must accept plain-language input, documents, images or UI references, website or system references, and requests to modify an existing program or app. | G-01, G-02 | AC-01 |
| FR-02 | P0 | The product must treat requirement clarification as part of its responsibility: identify missing product information, explain why it matters in plain language, and ask focused questions needed to remove material ambiguity. | G-01, G-02 | AC-02 |
| FR-03 | P0 | The product must not advance a requirement baseline as ready until the problem, target users, MVP scope, and important behaviors or flows are clear; critical exception or risk blockers are resolved; no material scope-changing TBD remains; and project authority has approved the baseline. Non-critical technical or design details need not be resolved at PRD level. | G-01, G-02, G-04 | AC-03 |
| FR-04 | P0 | AI may infer possibilities, identify likely omissions, propose options, recommend a preferred option, and explain its reasoning, but every such output must remain a proposal rather than authority until the appropriate Human Decision approves it. | G-02, G-05 | AC-04 |
| FR-05 | P0 | The product must route material product choices and material ambiguities affecting functionality, scope, or user behavior to the appropriate Human Decision and must not convert inference, recommendation, or user silence into approval. | G-02, G-05 | AC-05 |
| FR-06 | P0 | The product must present the current stage, completed work, current work, next step, `BLOCKED` or `INCOMPLETE` state, pending Human Decision, approved and unapproved authority, and whether execution may continue. | G-01, G-02, G-05 | AC-06 |
| FR-07 | P0 | The product must provide user actions equivalent to `PAUSE`, `RESUME`, `REQUEST_REVISION`, `REJECT_PROPOSAL`, and `APPROVE_DECISION`, with each action visibly affecting the governed flow. | G-01, G-02, G-05 | AC-07 |
| FR-08 | P0 | The product must require explicit Human Decision for a material product-requirement change, MVP-scope change, formal authority-artifact approval, upstream authority conflict requiring a choice, high-risk or destructive operation, new implementation authorization, release or deployment, and every lifecycle-required decision. | G-01, G-02, G-04, G-05 | AC-08 |
| FR-09 | P0 | While a required Human Decision is pending, the product must pause affected work, display what decision is needed and its effect, and forbid completion of that work followed by retrospective approval. | G-01, G-02, G-05 | AC-09 |
| FR-10 | P0 | The product must allow an approved current decision to be revised or withdrawn and must identify affected downstream artifacts and work, mark their authority or completion state appropriately, and require affected review or rerun before continuation. | G-01, G-02, G-05 | AC-10 |
| FR-11 | P0 | The product must expose a governed journey spanning idea intake, clarification, approved product requirements, specification, design, task decomposition, Human Decision, authorized AI-assisted coding, testing and verification, Git traceability, and maintenance or modification. | G-01, G-03, G-04, G-05 | AC-11 |
| FR-12 | P0 | AI-assisted coding must occur only within approved scope and authorization and must give the user a visible change summary, preserve Git traceability, perform applicable verification, and refrain from claiming unverified work complete. | G-01, G-03, G-04, G-05 | AC-12 |
| FR-13 | P0 | If coding fails or would exceed authority, the product must stop affected work, preserve valid completed progress, identify the failure or authority boundary, report the state truthfully, and offer applicable retry, revision, remediation, escalation, or Human Decision routes. | G-01, G-03, G-04, G-05 | AC-13 |
| FR-14 | P0 | The product must provide a user-visible verification summary stating what ran, `PASS`, `FAIL`, or `NOT RUN`, which requirements or behaviors have evidence, which lack evidence, known regression risk, and whether the current state qualifies as complete, verified, or ready. | G-03, G-04, G-05 | AC-14 |
| FR-15 | P0 | The product must prevent claims that incomplete tests are verified, partial PASS is complete, absence of evidence is safe, or a non-PASS Stage09 state is release-ready. | G-03, G-04, G-05 | AC-15 |
| FR-16 | P0 | When a stage, tool, AI service, command, test, Git operation, or security-related operation fails, the product must preserve valid completed work, identify the failure point, stop unsafe continuation, explain the issue understandably, and offer applicable retry, alternate, revision, or Human Decision routes. | G-01, G-03, G-04 | AC-16 |
| FR-17 | P0 | The product must block affected execution for high-risk, destructive, security, or authority-conflict conditions until the required authoritative or human resolution permits continuation. | G-02, G-04, G-05 | AC-17 |
| FR-18 | P0 | For a requested modification, the product must identify affected existing behavior and must preserve behavior and data not requested to change where applicable. Existing behavior alone must not be treated as product authority. | G-01, G-03, G-04 | AC-18 |
| FR-19 | P0 | For a requested modification, the product must perform applicable regression verification, disclose any behavior lacking regression evidence, and warn when non-regression cannot be established; success of the new behavior alone must not establish overall completion. | G-03, G-04, G-05 | AC-19 |
| FR-20 | P0 | The MVP must provide a suitable interface through which a user can submit a request, continue or resume it, inspect status, receive a Human Decision request, and approve, reject, or request revision. The interface may be local and need not use LINE or cloud deployment. | G-01, G-02, G-05 | AC-20 |
| FR-21 | P0 | The product must support an observable end-to-end MVP demonstration covering the complete chain defined in section 9 and proving that authority, Human Decision, blockers, verification truthfulness, Git traceability, and maintenance regression protection have governing effect. | G-01, G-02, G-03, G-04, G-05 | AC-21 |
| FR-22 | P2 | A future remote or LINE experience may support new ideas and change requests, stage/status inspection, pause/continue, Human Decision, approve/reject/revise actions, errors and blockers, and test/verification summaries without changing the governed product behavior. | G-02, G-05 | AC-22 |

## 5. Non-Functional Requirements

| ID | Priority | Requirement | Goals | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| NFR-01 | P0 | All user-visible lifecycle, authority, completion, failure, and verification reporting must be truthful; unresolved states must be shown as `TBD`, `INCOMPLETE`, or `BLOCKED` as applicable rather than represented as complete. | G-04, G-05 | AC-23 |
| NFR-02 | P0 | Status, questions, decisions, failures, evidence gaps, and next actions must be understandable to a user without programming knowledge. | G-02, G-05 | AC-24 |
| NFR-03 | P0 | Repository and Git information must provide persistent, user-visible traceability for the current version, material changes, checkpoints, decision history, and the canonical `G-* -> FR/NFR/EC -> AC` chain; chat memory alone must not be treated as execution authority. | G-01, G-04, G-05 | AC-25 |
| NFR-04 | P0 | Product behavior must preserve domain-specific authority, required lifecycle gates, and the conflict sequence `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`; no domain may silently override another. | G-02, G-04, G-05 | AC-26 |
| NFR-05 | P0 | The product must support maintainable modification by making affected behavior, preservation expectations, regression evidence, and unresolved regression risk observable before overall completion is claimed. | G-03, G-04 | AC-27 |
| NFR-06 | P1 | Telemetry, when present, must remain observational and must not determine authority, lifecycle progression, approval, completion, or release readiness. | G-04, G-05 | AC-28 |

## 6. Edge-Case Requirements

| ID | Priority | Requirement | Goals | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| EC-01 | P0 | When input is materially ambiguous, the product must identify the ambiguity, ask a focused question, and block only the affected progression rather than silently guessing. | G-01, G-02, G-04 | AC-29 |
| EC-02 | P0 | When a Human Decision is pending, unaffected work may continue only if its independence is clear; affected work must remain paused and visibly pending. | G-01, G-02, G-05 | AC-30 |
| EC-03 | P0 | When approval is revised or withdrawn after downstream work exists, the product must identify every known affected downstream item and return it to the applicable review or rerun path before it can regain a complete or approved state. | G-01, G-03, G-05 | AC-31 |
| EC-04 | P0 | When coding reaches or crosses its authority boundary, the product must stop the affected action, retain valid in-scope progress, report the attempted overrun, and request authority or Human Decision without treating the overrun as approved. | G-02, G-04, G-05 | AC-32 |
| EC-05 | P0 | When required test evidence is missing, the product must mark the affected verification `NOT RUN` or incomplete, identify the evidence gap, and withhold verified, complete, safe, or ready claims that depend on it. | G-03, G-04, G-05 | AC-33 |
| EC-06 | P0 | When a required tool or provider fails, the product must preserve valid progress, name the affected step, avoid unsafe continuation, and present an applicable retry, alternate path, revision, escalation, or Human Decision route. | G-01, G-04 | AC-34 |
| EC-07 | P0 | When a security concern, destructive action, or authority conflict is detected, the product must show a `BLOCKED` state and require the applicable authoritative or Human Decision resolution before affected execution resumes. | G-02, G-04, G-05 | AC-35 |
| EC-08 | P0 | When regression protection cannot be established for a modification, the product must identify the unverified existing behavior or data risk, warn the user, and withhold overall completion. | G-03, G-04, G-05 | AC-36 |
| EC-09 | P1 | When LINE, a remote channel, or cloud deployment is unavailable, the current MVP must remain demonstrable through a viable local or other suitable interface that provides the essential journey in FR-20. | G-01, G-02, G-05 | AC-37 |

## 7. Acceptance Criteria

| ID | Requirement | Testable observable criterion |
| --- | --- | --- |
| AC-01 | FR-01 | Given one example of each approved intake form, including a vague one-sentence idea, the product accepts it and begins clarification without requiring the user to supply implementation details first. |
| AC-02 | FR-02 | Given incomplete product information, the product lists the material missing information, explains its relevance in plain language, and asks focused clarification questions. |
| AC-03 | FR-03 | A readiness review allows progression only when all seven readiness conditions in FR-03 are satisfied; each failed condition produces a visible unresolved or blocked result, while absent non-critical technical/design details do not alone block readiness. |
| AC-04 | FR-04 | Given an AI-recommended product choice, the recommendation is visibly labeled proposed or unapproved and cannot change the approved baseline until an appropriate Human Decision is recorded. |
| AC-05 | FR-05 | Given a material ambiguity and no explicit decision, the product requests Human Decision and does not record approval or continue affected scope; silence produces no approval. |
| AC-06 | FR-06 | At an in-progress, incomplete, and blocked point, status inspection displays every field listed in FR-06 with a value consistent with the governed state. |
| AC-07 | FR-07 | Exercising each of the five required action equivalents produces its named effect: pause stops progression, resume continues eligible work, revision returns the proposal for change, rejection prevents adoption, and approval records the decision and permits only eligible continuation. |
| AC-08 | FR-08 | For one scenario in each listed decision category, affected execution cannot pass the decision point until an explicit Human Decision is recorded. |
| AC-09 | FR-09 | With a decision pending, affected work remains paused and visibly explains the decision and consequence; an attempted completion before approval is rejected rather than later legitimized retrospectively. |
| AC-10 | FR-10 | After revising or withdrawing an approval with downstream dependents, the product lists affected items, removes any now-invalid complete/approved representation, and requires their applicable review or rerun. |
| AC-11 | FR-11 | A user can inspect a single governed journey and observe every stage or capability listed in FR-11, including its state and applicable transition or decision. |
| AC-12 | FR-12 | In an authorized coding scenario, the result stays within approved scope and presents the change summary, Git trace, and verification outcome; any unverified portion is not labeled complete. |
| AC-13 | FR-13 | In separate coding-failure and authority-overrun scenarios, affected work stops, prior valid progress remains identifiable, the cause/boundary and truthful status are shown, and at least one applicable recovery or decision route is offered. |
| AC-14 | FR-14 | A verification summary for mixed outcomes identifies every executed and unexecuted check, uses only `PASS`, `FAIL`, or `NOT RUN`, maps evidence and gaps to behavior, states regression risk, and gives a truthful qualification result. |
| AC-15 | FR-15 | Attempts to label each forbidden scenario in FR-15 as verified, complete, safe, or release-ready are rejected or corrected to a truthful non-qualifying state. |
| AC-16 | FR-16 | For a representative operation failure, valid prior work remains, the failed point and understandable explanation are visible, unsafe continuation stops, and applicable recovery choices are presented. |
| AC-17 | FR-17 | Each of the four blocker classes produces a visible blocked state, prevents affected execution, and resumes only after the required resolution is recorded. |
| AC-18 | FR-18 | Given a modification request, the product identifies affected existing behaviors and data, distinguishes requested changes from preservation scope, and does not treat observed behavior alone as authority. |
| AC-19 | FR-19 | A modification result includes applicable regression outcomes and gaps; if only the requested new behavior passes, overall completion remains withheld until required regression evidence exists. |
| AC-20 | FR-20 | Without LINE or cloud deployment, a user completes a local or suitable-interface scenario that submits, resumes, inspects status, receives a decision, and approves, rejects, and requests revision. |
| AC-21 | FR-21 | One recorded demonstration traverses every link in the section 9 chain and includes observable proof for all six governing-effect statements there. |
| AC-22 | FR-22 | A future-channel product review can show all listed remote interactions without making channel availability a source of authority or changing lifecycle outcomes. |
| AC-23 | NFR-01 | Across representative unresolved-authority, failed-verification, and blocked-operation scenarios, displayed state matches evidence and uses an applicable unresolved status rather than a completion claim. |
| AC-24 | NFR-02 | A review of representative status, decision, failure, and next-action messages confirms they explain the situation and required user action without requiring programming knowledge. |
| AC-25 | NFR-03 | For a demonstrated change, the product exposes the current version, change/checkpoint, governing decision, and its `G -> requirement -> AC` links from repository/Git-backed information; loss of chat context does not erase that trace. |
| AC-26 | NFR-04 | In a cross-domain conflict scenario, the product detects and reports the conflict, blocks affected work, routes it to the authoritative owner, and records no silent override. |
| AC-27 | NFR-05 | A maintenance scenario exposes affected behavior, preservation scope, regression evidence, and unresolved risk before offering an overall completion state. |
| AC-28 | NFR-06 | Changing or removing telemetry observations does not itself change an approval, lifecycle transition, gate result, completion state, or release-readiness decision. |
| AC-29 | EC-01 | Given materially ambiguous input, no affected requirement is approved or advanced until the product displays the ambiguity and receives an answer to a focused question. |
| AC-30 | EC-02 | Given pending approval and two work items, only a demonstrably independent item may progress; the affected item remains paused and marked pending. |
| AC-31 | EC-03 | With downstream work already present, withdrawing its upstream approval produces a complete known-affected list and blocks each item from approved/complete status until applicable review or rerun succeeds. |
| AC-32 | EC-04 | An attempted out-of-authority coding change is stopped before being treated as authorized; valid in-scope progress is retained and the overrun plus authority-request route is shown. |
| AC-33 | EC-05 | Removing required evidence changes the affected result to `NOT RUN` or incomplete, identifies the missing evidence, and removes every dependent complete/verified/safe/ready claim. |
| AC-34 | EC-06 | Simulated loss of a required tool/provider leaves prior valid progress intact and presents the failed step, stopped state, and at least one applicable recovery route. |
| AC-35 | EC-07 | Each listed safety condition produces `BLOCKED`, prevents affected continuation, identifies the required resolution owner or Human Decision, and does not self-bypass. |
| AC-36 | EC-08 | In a change scenario with unavailable regression proof, the product names the exposed behavior/data risk, warns the user, and does not label the overall modification complete. |
| AC-37 | EC-09 | With remote and LINE channels unavailable, the FR-20 journey remains executable through a local or other suitable interface. |

## 8. Goal-to-Requirement Traceability

The canonical chain established here is `G-* -> FR/NFR/EC -> AC`. Later authority artifacts may extend, but must not redefine, this product-level chain.

| Approved goal | Requirements |
| --- | --- |
| G-01 — Governed idea-to-software journey | FR-01, FR-02, FR-03, FR-06, FR-07, FR-08, FR-09, FR-10, FR-11, FR-12, FR-13, FR-16, FR-18, FR-20, FR-21, EC-01, EC-02, EC-03, EC-06, EC-09, NFR-03 |
| G-02 — Accessible AI-assisted development | FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10, FR-17, FR-20, FR-21, FR-22, EC-01, EC-02, EC-04, EC-07, EC-09, NFR-02, NFR-04 |
| G-03 — Stable and maintainable software outcomes | FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-18, FR-19, FR-21, EC-03, EC-05, EC-08, NFR-05 |
| G-04 — Controlled development quality | FR-03, FR-08, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18, FR-19, FR-21, EC-01, EC-04, EC-05, EC-06, EC-07, EC-08, NFR-01, NFR-03, NFR-04, NFR-05, NFR-06 |
| G-05 — Truthful, authority-preserving remote operation | FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-17, FR-19, FR-20, FR-21, FR-22, EC-02, EC-03, EC-04, EC-05, EC-07, EC-08, EC-09, NFR-01, NFR-02, NFR-03, NFR-04, NFR-06 |

Every requirement row directly names at least one approved goal and exactly one acceptance criterion. Every acceptance criterion directly names its requirement.

## 9. MVP Completion Definition

The SDD MVP is complete at the product-requirement level only when an observable demonstration covers:

```text
IDEA
-> requirement clarification
-> approved product requirements
-> specification
-> design
-> task decomposition
-> Human Decision
-> authorized AI coding
-> testing / verification
-> Git traceability
-> truthful status/failure handling
-> maintenance change
-> regression verification
```

The demonstration must prove all of the following:

1. Authority is not bypassed.
2. AI does not independently decide product requirements.
3. Human Decision has governing effect on affected execution.
4. Blockers stop affected execution.
5. Unverified work is not represented as complete.
6. Maintenance changes receive regression protection.

Satisfying this product-level demonstration does not by itself approve this PRD, authorize implementation, establish implementation conformance, produce a Stage09 PASS, authorize release, or prove deployment.

## 10. Explicit Product Non-Goals / TBD

The current MVP does not require a Web UI, LINE, remote access, cloud deployment, multi-user collaboration, a full permission system, commercialization, a native mobile app, many AI providers, general database-management capability, or broad one-click multi-cloud deployment.

The following remain future or downstream-domain TBDs and do not block this product baseline: final cloud platform; LINE webhook architecture; exact remote transport; future Web UI or channels; organization roles and approval delegation; commercialization; additional providers; long-term support and compatibility windows; quantitative service levels; and technical choices such as APIs, schemas, storage, frameworks, modules, repository layout, test mix, authentication, hosting, and recovery mechanisms.

A TBD may remain only while it does not obscure a material product choice, change MVP scope, or prevent testable P0 behavior. Such a TBD becomes a blocker when it crosses that boundary.

## 11. Authority boundaries

- This approved current baseline owns `PRODUCT_REQUIREMENT` authority only.
- `docs/proposal.md` remains the approved `PRODUCT_INTENT` authority and the source of `G-*` goals.
- Project authority explicitly approved the substantive PRD baseline as the CURRENT prospective `PRODUCT_REQUIREMENT` authority; this is not recovered or reconstructed historical Phase02 authority.
- Framework, database technology, API schema, module structure, architecture, implementation design, repository mechanics, and tasks belong to downstream authority domains.
- Tests and current implementation may later provide evidence; they do not create or revise product requirements.
- Authority remains domain-specific. Cross-domain conflicts must be detected, reported, blocked, and routed to the authoritative owner.
- This approval creates no `TECHNICAL_CONTRACT` authority, `IMPLEMENTATION_DECISION` authority, task authority, Stage07 result, implementation authorization, Recovery Gate result, Stage09 result, or Stage10, release, or deploy authorization; downstream artifacts require independent authority approval.
- Approval of this PRD would establish only current prospective `PRODUCT_REQUIREMENT` authority. It would not imply historical Phase02 completion, Stage07 PASS, implementation authorization, Recovery Gate result, Stage09 result, Stage10 entry, release, or deployment authorization.
- Any approved upstream change requires affected downstream scope to be identified and re-evaluated under the applicable lifecycle rules.

## 12. Current PRD status

```text
CURRENT_PRODUCT_REQUIREMENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

HISTORICAL_PHASE02_RECONSTRUCTION =
NOT_AUTHORIZED

PRODUCT_REQUIREMENT_DECISIONS_COMPLETE =
YES

P0_REQUIREMENTS_DEFINED =
YES

P0_ACCEPTANCE_CRITERIA_TESTABLE =
YES

PRODUCT_REQUIREMENT_TRACEABILITY_ESTABLISHED =
YES

TECHNICAL_CONTRACT_DEFINED =
NO

IMPLEMENTATION_DESIGN_DEFINED =
NO

IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

PRD_PROJECT_AUTHORITY_REVIEW_REQUIRED =
NO

NEXT_STEP =
CURRENT_TECHNICAL_CONTRACT_DEFINITION
```
