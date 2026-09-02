# Current PRD Decision Brief

## 1. Purpose and authority boundary

This brief prepares the minimum project-authority decisions needed before drafting `docs/PRD.md`. It interprets the approved current `PRODUCT_INTENT` authority in `docs/proposal.md` only to identify unresolved product-level choices. It is not `PRODUCT_REQUIREMENT` authority and does not answer those choices on behalf of project authority.

This brief creates no formal requirements, edge-case identifiers, acceptance criteria, priorities, technical contracts, architecture, design, tasks, implementation authorization, Recovery Gate result, Stage09 decision, release decision, or deployment authority. Existing implementation behavior is not a source of product requirements.

## 2. Approved product-intent basis

The approved intent is an SDD software-development assistance system for a project owner and people without programming knowledge. It is intended to turn ideas into working software through a structured, governed, and verifiable journey that includes clarification, specification, design, task decomposition, AI-assisted implementation, testing, validation, and later maintenance or modification.

The MVP intent includes the complete governed core chain: idea intake, requirement clarification, specification, design, task decomposition, AI-assisted coding, testing and verification, Git traceability and checkpoints, and Human Decision. The intended end-state includes remote interaction, primarily through LINE, but LINE/webhook infrastructure is not established as an MVP requirement.

Approved constraints already require domain-specific authority, truthful state, repository/Git persistence, required lifecycle gates, human control of product authority, and observational-only telemetry. The approved proposal also establishes the current MVP non-goals listed in section 11 below.

## 3. Requirement decisions already constrained by proposal

Any later PRD must remain within these already approved boundaries:

- The user journey covers the governed core chain from an idea through a working, verified, maintainable software outcome; maximum feature breadth is not the MVP objective.
- AI may assist reasoning, drafting, coding, and verification only within granted authority. It may not independently decide product requirements, bypass Human Decision, modify authority, or release/deploy without the required gates and authorization.
- Missing decisions, authority, evidence, or testing must be reported truthfully as unresolved, incomplete, or blocked. The product must not manufacture completion.
- Cross-domain conflicts are detected, reported, blocked, and routed to the appropriate authority owner; they are not silently resolved.
- Repository and Git state, rather than chat memory, are the persistent execution and traceability basis.
- Testing is evidence rather than requirement authority. Telemetry observes but does not decide lifecycle behavior or authority.
- Required Stage07, Stage09, and Stage10 semantics cannot be skipped or weakened.
- The MVP need not include a Web UI, multi-user collaboration, a full permission system, commercialization, a native mobile app, many additional AI providers, general database-management capability, broad multi-cloud one-click deployment, or unrelated feature breadth.

These constraints narrow later choices but do not decide the exact user-visible behaviors needed for the PRD.

## 4. G-01 decision analysis

### Clearly supported product behavior

The product provides a structured, verifiable journey spanning clarification, specification, design, task decomposition, AI-assisted implementation, testing, validation, and maintenance or modification. Progress is governed rather than treated as an unstructured chat, and required gates remain meaningful.

### Product-level ambiguity

The approved intent does not yet say what users may submit initially, how incomplete an idea may be, what each user-visible part of the MVP journey must expose, or how users pause, resume, inspect, reject, revise, and recover from failure. It also does not define the observable boundary between “journey in progress,” “generated app complete,” and “SDD MVP complete.”

### Project-authority decisions

MUST decide now for the MVP PRD: the accepted idea-intake forms and minimum content; ambiguity handling; the user-visible stages/functions; pause/resume and status behavior; rejection/revision behavior; failure recovery; and the observable MVP completion outcome.

MAY remain TBD: presentation details, convenience features, and later interaction channels that do not change the core journey.

Explicit NON_GOAL: treating an informal AI conversation alone as authoritative lifecycle state or bypassing the governed chain merely to produce code faster.

## 5. G-02 decision analysis

### Clearly supported product behavior

The product is usable by a project owner and by people without programming knowledge. AI assists them in turning ideas into working software, while important decisions remain controlled by appropriate human authority.

### Product-level ambiguity

The intent does not yet define which decisions always require explicit approval, what AI may infer as a reversible drafting aid, how a non-programmer is shown unresolved choices, or what happens while approval is pending. It also does not decide whether and how a current approved product decision may be reversed.

### Project-authority decisions

MUST decide now for the MVP PRD: the boundary between permitted AI inference and required Human Decision; the always-human decision categories; waiting behavior; how decisions are explained in plain language; and whether reversal is supported and what user-visible consequence follows.

MAY remain TBD: advanced delegation policies, multiple approvers, role administration, and organization-level approval workflows.

Explicit NON_GOAL: AI independently creating product authority or treating user silence as approval.

## 6. G-03 decision analysis

### Clearly supported product behavior

Software produced through SDD is intended to run stably and correctly and remain straightforward to maintain, modify, extend, and repair without unnecessary regression of existing behavior.

### Product-level ambiguity

The proposal does not define how a user requests a change to an existing app, what existing behavior must be identified and preserved, what regression assurance is promised, or what user-visible outcome is required when change safety cannot be established.

### Project-authority decisions

MUST decide now for the MVP PRD: the maintenance/change request experience; the product-level preservation expectation for existing behavior and data; the minimum regression outcome; and the response when preservation or regression evidence is incomplete.

MAY remain TBD: long-term support periods, compatibility windows, migration policies, and specialized repair tooling.

Explicit NON_GOAL: assuming current behavior is desirable authority merely because it exists, or claiming a modification is safe without sufficient evidence.

## 7. G-04 decision analysis

### Clearly supported product behavior

The flow must preserve clarity, reasonable architecture, correct logic and process, simplicity, controlled errors and exceptions, complete testing, controlled security, and maintainability. These qualities are governed across the journey rather than checked only at the end.

### Product-level ambiguity

The intent does not yet define the minimum testing result presented to the user, the user-facing handling of failed or incomplete evidence, the minimum safety expectations, which risky situations must be blocked, or what recovery choices are offered after a stage, tool, provider, or operation fails.

### Project-authority decisions

MUST decide now for the MVP PRD: the minimum user-visible verification outcome; prohibited completion claims; failure and incomplete-evidence reporting; required recovery choices; minimum user-facing safety expectations; and operations or conditions that must stop for explicit human action.

MAY remain TBD: quantitative service levels, performance thresholds, detailed security controls, detailed test mix, and technical recovery mechanisms.

Explicit NON_GOAL: allowing quality, security, or testing gaps to be silently auto-resolved or described as complete.

## 8. G-05 decision analysis

### Clearly supported product behavior

The intended product supports remote development interaction and Human Decision while preserving domain-specific authority, lifecycle gates, repository/Git traceability, truthful state, and observational-only telemetry. Users are intended to submit and continue requests, inspect status, receive decisions, and approve or reject important choices remotely. LINE is the intended primary end-state interface, not an exclusive permanent interface.

### Product-level ambiguity

The proposal does not decide whether remote access or LINE is part of the MVP, what minimum channel-independent interaction is required now, which traceability facts users must see, or how much status and decision history must be understandable to non-programmers.

### Project-authority decisions

MUST decide now for the MVP PRD: whether MVP interaction may be local while preserving a channel-independent user journey; the minimum user-visible status, decision, and traceability information; and whether any remote interaction capability is required for MVP completion.

MAY remain TBD: final cloud platform, LINE webhook architecture, future Web UI, additional remote channels, and presentation details.

Explicit NON_GOAL: making LINE/webhook infrastructure, a Web UI, or a specific cloud platform mandatory unless project authority now chooses it as an MVP product behavior.

## 9. Cross-goal MVP requirement decisions

The following decisions cut across all goals and must be internally consistent in the future PRD:

- Define the minimum complete user journey, including what the user sees and can do at each meaningful point.
- Define when work may continue automatically and when it must stop for project-authority input.
- Define the distinction between reversible AI assistance, unresolved choices, approved current decisions, and lifecycle-gate decisions.
- Define truthful status language and the user-visible consequences of blocked, failed, incomplete, rejected, or revised work.
- Define the minimum result delivered by AI-assisted coding without turning implementation method, framework, API, database, modules, or architecture into product decisions.
- Define the minimum testing and verification information needed before any completion claim.
- Define the product-level Git and traceability promise while leaving commit mechanics, branching conventions, file formats, and repository design to later authority.
- Define the minimum safety behavior for sensitive information, destructive actions, unauthorized scope, security concerns, and authority conflicts.
- Define how changes to an existing app preserve approved behavior and trigger appropriate re-evaluation.
- Define MVP completion for the SDD product separately from completion, verification, release, or deployment of any one generated app.

## 10. Decisions that may remain TBD

The following may remain TBD for the MVP PRD if they are not needed to state the core user-visible behavior accurately:

- final cloud platform and hosting arrangement;
- final LINE webhook architecture and exact remote transport;
- future Web UI and other channels;
- additional AI providers beyond the MVP-supported capability;
- collaboration, organization roles, and a full permission model;
- commercialization;
- native mobile applications;
- generalized database-management features;
- broad deployment support across many cloud providers;
- exact APIs, schemas, storage, frameworks, modules, architecture, repository layout, branch/commit mechanics, test types, and implementation recovery mechanisms;
- quantitative performance, availability, support, or compatibility targets not essential to the MVP promise.

A TBD may remain only when it does not prevent a clear, testable later statement of the MVP product behavior or conceal a blocking product choice.

## 11. Explicit non-goals

For this decision brief and the current MVP boundary:

- no Web UI is required;
- no multi-user collaboration or full permission system is required;
- no commercialization capability is required;
- no native mobile app is required;
- no broad set of additional AI providers is required;
- no general database-management capability is required;
- no broad one-click multi-cloud deployment capability is required;
- LINE, webhook, final cloud infrastructure, and actual deployment are not presumed mandatory for MVP;
- implementation behavior, tests, or historical status do not define product requirements;
- the PRD will not own APIs, database choices, framework choices, module structure, architecture, or implementation design;
- the SDD MVP is not complete merely because one generated app produces code, passes some tests, or appears usable;
- no authority, evidence, gate result, completion state, or history may be fabricated.

## 12. Project-authority questions

### 1. Idea intake

`DECISION_STATUS = APPROVED`

What may a user provide as the initial idea (for example, plain language, files, or references), how little information is acceptable, and should SDD respond to material ambiguity by asking focused questions and pausing the affected work rather than guessing?

### 2. Requirement clarification

`DECISION_STATUS = APPROVED`

Which product choices may AI tentatively infer for review, which must always remain unresolved until a human answers, and what plain-language condition means the idea is clear enough to proceed into specification?

### 3. User-visible development flow

`DECISION_STATUS = APPROVED`

Which parts of the governed chain must the MVP expose to users, and must users be able to pause/resume, inspect current status and unresolved items, and reject or request revision of a proposed decision?

### 4. Human Decision

`DECISION_STATUS = APPROVED`

Which categories always need explicit human approval, what should users see while work is waiting, and may a user reverse a current approval with affected later work visibly returned for review?

### 5. AI-assisted coding

`DECISION_STATUS = APPROVED`

What user-visible result must coding produce, and if coding cannot finish or goes outside approved scope, must SDD stop, preserve truthful progress, explain the problem, and offer retry, revision, or escalation without claiming completion?

### 6. Testing and verification

`DECISION_STATUS = APPROVED`

What minimum testing/verification summary must users receive, what must it say when tests fail or evidence is incomplete, and which claims—such as complete, verified, ready, released, or safe—must be forbidden until their governing decisions actually permit them?

### 7. Git and traceability

`DECISION_STATUS = APPROVED`

What must a non-programmer be able to see or rely on about the current version, changes, checkpoints, decision history, and links from goals through verification, while leaving repository mechanics to later technical and design authority?

### 8. Errors and recovery

`DECISION_STATUS = APPROVED`

When a stage, tool, AI service, or operation fails, should SDD preserve completed work, identify the affected point, avoid unsafe automatic continuation, and offer understandable retry, alternate-path, revision, or human-help choices—and which of these are mandatory for MVP?

### 9. Security and safety

`DECISION_STATUS = APPROVED`

What minimum user-facing protections must the MVP promise for sensitive information, destructive actions, unauthorized scope, security concerns, and conflicting authority, and which situations must always be blocked for explicit human action?

### 10. Maintenance and modification

`DECISION_STATUS = APPROVED`

How should users request changes to an existing app, what approved behavior or data must SDD attempt to preserve, and what regression evidence or warning is required before the change may be described as complete?

### 11. Remote and LINE interaction

`DECISION_STATUS = APPROVED`

May the MVP use a local or otherwise non-LINE interaction while providing the same essential submit, continue, status, decision, approve, and reject journey, or is any remote capability required now? Which LINE/cloud details should remain future TBDs?

### 12. MVP completion

`DECISION_STATUS = APPROVED`

What observable end-to-end demonstration proves the SDD product MVP is complete, distinct from the completion of one generated app, and must that demonstration include intake, clarification, governed decisions, coding, verification, traceability, failure/status reporting, and a maintenance change?

## 13. Approved Product Requirement Decisions

The following CURRENT `PRODUCT_REQUIREMENT` decisions are approved by project authority. They authorize drafting the PRD baseline but do not themselves create the formal authority artifact.

### A. Idea intake

The MVP accepts highly incomplete input, including a vague one-sentence idea, plain-language requirements, documents, images or UI references, website or system references, and an existing program or app to modify. SDD is responsible for clarifying requirements from incomplete ideas.

### B. AI inference boundary

AI may infer possibilities, identify likely omissions, propose options, recommend a preferred option, and explain its reasoning. An AI recommendation is not authority: AI must not treat an important inferred product choice as approved or resolve material ambiguity affecting functionality, scope, or user behavior without required Human Decision.

### C. Requirement readiness

Requirements may proceed when the problem, target users, core MVP scope, and important behaviors or flows are clear; no unresolved critical exception or risk remains; no material scope-changing TBD remains; and project authority has approved the current requirement baseline. Non-critical implementation or technical details may remain for Spec or Design.

### D. User-visible development flow

MVP users must see the current stage, completed work, current work, next step, `BLOCKED` or `INCOMPLETE` state, pending Human Decision, approved and unapproved authority, and whether execution may continue. The MVP must provide product-level actions equivalent to `PAUSE`, `RESUME`, `REQUEST_REVISION`, `REJECT_PROPOSAL`, and `APPROVE_DECISION`.

### E. Human Decision

Explicit Human Decision is required for material product-requirement or MVP-scope changes, formal authority-artifact approval, upstream authority conflicts requiring a choice, high-risk or destructive operations, new implementation authorization, release or deployment decisions, and every lifecycle-defined Human Decision. Affected work pauses while a decision is pending and cannot be completed before retrospective approval. Revised or withdrawn approval requires affected downstream artifacts and work to be identified and re-reviewed or re-run.

### F. AI-assisted coding product behavior

Successful coding remains within approved scope, reports changes, preserves Git traceability, performs applicable verification, and never claims unverified work complete. On failure or an authority overrun, affected work stops while valid progress is preserved; the boundary or failure is reported truthfully; and an appropriate retry, revision, remediation, escalation, or Human Decision route is provided. Out-of-authority work follows `STOP -> REPORT -> REQUEST AUTHORITY / HUMAN DECISION`.

### G. Testing and verification

Users must be able to determine what verification ran, its `PASS`, `FAIL`, or `NOT RUN` state, which requirements or behaviors have evidence, which lack evidence, known regression risk, and whether the state may truthfully be called complete, verified, or ready. Incomplete tests cannot mean verified, partial PASS cannot mean fully complete, absence of evidence cannot mean safe, and a non-PASS Stage09 cannot mean release-ready.

### H. Error, security, and recovery

When a stage, tool, AI service, command, test, Git operation, or security-related operation fails, the MVP preserves valid completed work, identifies the failure point, stops unsafe continuation, explains the issue understandably, and provides applicable retry, alternate, revision, or Human Decision routes. High-risk, destructive, security, and authority-conflict conditions block rather than being silently bypassed.

### I. Maintenance and modification

For an existing program or app, the MVP identifies affected existing behavior, preserves behavior and data not requested to change where applicable, performs applicable regression verification, and explicitly warns when non-regression cannot be established. Success of the requested new behavior alone does not prove the overall modification complete.

### J. Remote MVP boundary

LINE and cloud deployment are not required for the current MVP. A local CLI or other suitable interface is acceptable when the essential journey supports submitting a request, continuing or resuming, inspecting status, receiving Human Decision, and approving, rejecting, or revising.

### K. Future LINE and remote capability

The intended future remote or LINE experience supports new ideas and change requests, stage and status inspection, pause and continue, Human Decision requests, approve, reject, and request revision actions, plus errors, `BLOCKED` state, test summaries, and verification summaries. Webhook provider, hosting, message format, authentication, and related implementation choices remain Technical or Design authority.

### L. SDD MVP completion

MVP completion requires an observable end-to-end demonstration of `IDEA -> requirement clarification -> approved product requirements -> specification -> design -> task decomposition -> Human Decision -> authorized AI coding -> testing / verification -> Git traceability -> truthful status/failure handling -> maintenance change -> regression verification`, not merely one generated app. The demonstration must show that authority is not bypassed, AI does not independently decide product requirements, Human Decision governs execution, blockers stop affected work, unverified work is not called complete, and maintenance changes receive regression protection.

## 14. PRD readiness status

Project authority has approved the 12 product-requirement decisions above. The decisions are complete enough to authorize drafting `docs/PRD.md`, but the draft must still be reviewed and approved before it becomes current formal `PRODUCT_REQUIREMENT` authority. Matters listed as permitted TBDs may remain unresolved only if they do not block the approved product choices.

`PRD_DRAFT_AUTHORIZED = YES` does not mean `PRODUCT_REQUIREMENT` authority is approved. `docs/PRD.md` must still follow:

```text
DRAFT
-> PROJECT_AUTHORITY_REVIEW
-> APPROVED_CURRENT_AUTHORITY
```

Recovery Gate and Stage09 remain unevaluated.

```text
CURRENT_PRD_DECISION_BRIEF =
COMPLETE

PRODUCT_REQUIREMENT_DECISIONS_COMPLETE =
YES

PRODUCT_REQUIREMENT_AUTHORITY_COMPLETE =
NO

FORMAL_FR_NFR_EC_CREATED =
NO

ACCEPTANCE_CRITERIA_CREATED =
NO

PRIORITIES_ASSIGNED =
NO

TECHNICAL_AUTHORITY_CREATED =
NO

IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

PRD_DRAFT_AUTHORIZED =
YES

NEXT_STEP =
CURRENT_PRD_DRAFT
```
