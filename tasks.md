# SDD Software Development System - Current Execution Decomposition

## 1. Stage06 authority and scope

This artifact is the approved CURRENT prospective Stage06 `EXECUTION_DECOMPOSITION` authority. Stage06 owns task decomposition only: atomic work boundaries, dependency order, implementation scope, required outcomes, preservation and failure obligations, future verification, and checkpoint eligibility. It does not create or revise `PRODUCT_INTENT`, `PRODUCT_REQUIREMENT`, `TECHNICAL_CONTRACT`, `IMPLEMENTATION_DECISION`, or `AGENT_REPOSITORY_GOVERNANCE` authority.

This approved whole artifact contains prospective `TASK-001` through `TASK-018`. Its approval does not create Stage07 `PASS`, authorize Stage08 implementation, establish implementation conformance, evaluate the Current Implementation Recovery Gate, create Stage09 `PASS`, or create Stage10, release, or deployment authority. Existing source, tests, implementation evidence, and historical completion claims were not used to derive these tasks and cannot make any task `DONE`.

## 2. Approved upstream baseline references

- `docs/proposal.md`: CURRENT `PRODUCT_INTENT` authority, `APPROVED_CURRENT_AUTHORITY`; goals `G-01` through `G-05`.
- `docs/PRD.md`: CURRENT `PRODUCT_REQUIREMENT` authority, `APPROVED_CURRENT_AUTHORITY`; applicable P0 requirements and acceptance criteria.
- `docs/spec.md`: CURRENT `TECHNICAL_CONTRACT` authority, `APPROVED_CURRENT_AUTHORITY`; `SPEC-001` through `SPEC-016`.
- `docs/Design.md`: CURRENT `IMPLEMENTATION_DECISION` authority, `APPROVED_CURRENT_AUTHORITY`; `DES-001` through `DES-016`.
- `AGENTS.md`: CURRENT Stage05 `AGENT_REPOSITORY_GOVERNANCE` authority, `APPROVED_CURRENT_AUTHORITY`.
- `.sdd/system.yaml` and `.sdd/stages.yaml`: configured authority graph, Stage06 contract, lifecycle gates, traceability chain, and checkpoint rules.

Authority is domain-specific and non-linear. A discovered cross-domain conflict must follow `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`. No task may silently repair an upstream authority problem.

## 3. Task contract conventions

- Every task is prospective and begins with status `TODO`; pre-existing implementation cannot change that status.
- Authority traces extend approved links as `G-* -> FR/NFR/EC -> AC-* -> SPEC-* -> DES-* -> TASK-*`. Each grouped chain below means every named requirement retains its approved goal and acceptance-criterion pairing.
- Allowed scope is conceptual and responsibility-bounded. Concrete package layout, framework, database, cloud, webhook, LINE, deployment, authentication, and test tooling remain deferred unless separately authorized later.
- Verification requirements define future checks only. Their results must be reported as exactly `PASS`, `FAIL`, or `NOT RUN`; tests are evidence and cannot create requirement authority or a Stage09 decision.
- “Checkpoint eligible” means eligibility may be evaluated only after implementation authorization. It never means a checkpoint is currently achieved.
- For every task, checkpoint eligibility requires: implementation complete; all required task checks executed; all required checks `PASS`; completion criteria satisfied; authorized scope respected; every unexpected diff resolved; no unresolved blocker; and traceability plus implementation/verification evidence recorded against the current baseline.

## TASK-001 - Repository-backed governed state and traceability index

- **Status:** `TODO`
- **Purpose:** Establish the repository/Git-backed persistence responsibility and reconstructable bidirectional traceability index on which later governed state, execution, and evidence records depend.
- **Authority trace:**
  - `G-01, G-02, G-05 -> FR-06, FR-11, NFR-01 -> AC-06, AC-11, AC-23 -> SPEC-001 -> DES-008 -> TASK-001`
  - `G-01, G-04, G-05 -> FR-11, FR-12, NFR-03 -> AC-11, AC-12, AC-25 -> SPEC-007 -> DES-008 -> TASK-001`
- **Dependencies:** None.
- **Allowed files:** `sdd_orchestrator/governed_state.py`, `tests/test_governed_state.py`.
- **Allowed implementation scope:** Governed state/persistence responsibility; repository-native, reviewable records; Git/version identity references; atomic state publication; and a derived, rebuildable link index. No concrete database or full repository layout is selected by this task.
- **Required behavior/outcome:** Persist lifecycle position, authority references/status, Human Decision references, affected scope, task/execution state when owned, verification references, failures, invalidations, and Recovery Gate provenance. Extend stable links through `G -> FR/NFR/EC -> AC -> SPEC -> DES -> TASK`, retain source/target identity and affected scope, support forward and backward navigation, and reconstruct current state without chat memory. Failed writes must not advance the visible state.
- **Preservation obligations:** Preserve upstream identifiers and artifact ownership; append later links without rewriting upstream authority; retain current version/change/checkpoint and governing-decision identity; keep any projection or cache disposable and rebuildable from canonical repository/Git-backed records.
- **Error/failure expectations:** Broken, ambiguous, stale, missing, or non-atomically published required state/link data must make dependent coverage or completion `INCOMPLETE` or `BLOCKED`. Record the exact failed write or link and affected scope; never repair it from chat claims or fabricate continuity.
- **Security/safety expectations:** Persist only necessary governed facts and references; do not place secrets or unnecessary sensitive content in trace records. Repository writes remain target-bounded and governed; destructive repair or history rewriting is forbidden without explicit authorization.
- **Verification requirements:** Future checks must demonstrate session-context loss followed by repository/Git reconstruction; representative forward and backward traces; missing/stale-link detection; atomic publication with no partial state advancement; and distinction between canonical records and rebuildable projections. Record each result as `PASS`, `FAIL`, or `NOT RUN` with scope and evidence/gap.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common checkpoint conditions in section 3 hold and reconstruction, bidirectional trace, missing-link, and atomic-publication checks all `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Database product, cache/index technology, serialization choice, concrete package/file layout beyond protected authority paths, Git history rewrite, implementation of downstream task/code/test links before their owning stages, and any Stage09 qualification.

## TASK-002 - Governed lifecycle aggregate and transition invariants

- **Status:** `TODO`
- **Purpose:** Provide one consistent lifecycle aggregate and validator that keeps stage/work state, scoped blockers, decisions, authority, rerun state, and qualification states mutually consistent.
- **Authority trace:**
  - `G-01, G-02, G-05 -> FR-06, FR-11, NFR-01 -> AC-06, AC-11, AC-23 -> SPEC-001 -> DES-001 -> TASK-002`
  - `G-01, G-03, G-04, G-05 -> FR-08, FR-12, FR-14, FR-15, NFR-01, NFR-04 -> AC-08, AC-12, AC-14, AC-15, AC-23, AC-26 -> SPEC-016 -> DES-001 -> TASK-002`
- **Dependencies:** `TASK-001`.
- **Allowed implementation scope:** Lifecycle-governor responsibility and its governed aggregate, eligibility and invariant evaluation, scoped pause/block/incomplete state, rerun/invalidation state, and validated persistence through the state responsibility.
- **Required behavior/outcome:** Represent current stage, completed/current/next work, eligibility, scoped `PAUSED`/`BLOCKED`/`INCOMPLETE` conditions, pending decisions, authority summary, authorization and distinct qualification flags, and rerun/invalidation state. Validate every transition against a fresh persisted snapshot; write attributable transitions with prior-state identity, affected scope, reason, sources, and next route; reject impossible qualification combinations.
- **Preservation obligations:** Preserve valid completed and independent work, separation of approval/authorization/completion/verification/release, existing transition history, and source authority. Apply invalidation only to proven-affected scope and record independence before unaffected work proceeds.
- **Error/failure expectations:** Missing, stale, contradictory, or mismatched facts reject the transition without optimistic defaults and produce a truthful scoped `INCOMPLETE` or `BLOCKED` result with a valid route. A failed persistence operation leaves the prior state authoritative.
- **Security/safety expectations:** Never allow lifecycle state to bypass a required authority, Human Decision, Stage07, Stage09, or Stage10 gate. High-risk, destructive, security, or authority-conflicted scope remains blocked pending the applicable resolution.
- **Verification requirements:** Future checks must cover in-progress, paused, blocked, incomplete, resumed, invalidated, and completed snapshots; independent-scope continuation; stale prior-state identity; contradictory facts; persistence failure; and every prohibited qualification substitution. Outcomes must be `PASS`, `FAIL`, or `NOT RUN` with evidence/gaps.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all aggregate, invariant, scoped-state, persistence-failure, and qualification-separation checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Authoring domain content, resolving substantive conflicts, concrete storage technology, lifecycle commands owned by `TASK-003`, Human Decision record mechanics owned by `TASK-006`, and gate decisions themselves.

## TASK-003 - Explicit lifecycle command processing

- **Status:** `TODO`
- **Purpose:** Implement explicit, attributable, idempotent processing for the five required lifecycle action equivalents.
- **Authority trace:** `G-01, G-02, G-05 -> FR-07, FR-09, FR-10, EC-02, EC-03 -> AC-07, AC-09, AC-10, AC-30, AC-31 -> SPEC-002 -> DES-002 -> TASK-003`.
- **Dependencies:** `TASK-002`.
- **Allowed implementation scope:** Lifecycle command-processing responsibility for `PAUSE`, `RESUME`, `REQUEST_REVISION`, `REJECT_PROPOSAL`, and `APPROVE_DECISION`, including command identity, actor/context reference, target, scope, expected current-state identity, reason, validation, persistence request, and result projection inputs.
- **Required behavior/outcome:** Each valid command produces its defined governed effect, attributable transition, affected-scope result, and next eligible route. Duplicate delivery of the same identity is idempotent. Revision or withdrawal creates invalidation links without erasing history. Resume permits only otherwise eligible work; approval satisfies only the named condition and cannot bypass other gates.
- **Preservation obligations:** Preserve prior command/transition history, valid completed progress, downstream dependency links, and demonstrably independent work. Leave state unchanged for rejected commands.
- **Error/failure expectations:** Reject ambiguous, unauthorized, retrospective, stale, malformed, identity-mismatched, or prerequisite-invalid commands; report why and the applicable route without applying a partial transition. Delivery or persistence failure must remain recoverable by stable identity.
- **Security/safety expectations:** Validate actor authority and exact target/scope before a protected transition; silence and replay cannot become approval; command handling cannot self-authorize implementation, destructive action, release, or deployment.
- **Verification requirements:** Future checks must exercise all five commands from valid and invalid states, duplicate and stale delivery, identity mismatch, retrospective approval prevention, downstream invalidation, affected-scope blocking, independent continuation, and unchanged state after rejection. Use `PASS`, `FAIL`, or `NOT RUN` only.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and every required command, replay, invalidation, stale/unauthorized, and preservation check `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Interface transport/schema, authentication product, substantive Human Decision authority, authority registry resolution, and any modification of lifecycle or product semantics.

## TASK-004 - Requirement-readiness evaluation

- **Status:** `TODO`
- **Purpose:** Evaluate whether a proposed product-requirement baseline is ready using the seven approved independent dimensions while producing focused clarification for unresolved product information.
- **Authority trace:** `G-01, G-02, G-04 -> FR-01, FR-02, FR-03, EC-01 -> AC-01, AC-02, AC-03, AC-29 -> SPEC-003 -> DES-003 -> TASK-004`.
- **Dependencies:** `TASK-002`.
- **Allowed implementation scope:** Requirement-readiness evaluator responsibility; intake and clarification references; per-dimension result/evidence/authority references; focused-question outputs; and scoped readiness findings consumed by the lifecycle governor.
- **Required behavior/outcome:** Independently represent problem clarity, target-user clarity, MVP-scope clarity, important behavior/flow clarity, critical exception/risk blockers, material scope-changing TBD, and current product-baseline approval. Readiness passes only when every required dimension passes. Identify and plainly explain missing material information, ask focused questions, and block only affected progression; non-critical downstream technical/design detail alone must not block readiness.
- **Preservation obligations:** Preserve the non-authoritative status of AI inference/proposals, original intake references, unresolved dimensions, and the Product owner’s exclusive authority. Do not turn observed implementation or downstream detail into a product requirement.
- **Error/failure expectations:** Missing or ambiguous material information remains unresolved; inference, recommendation, silence, or malformed evaluation cannot produce approval or Stage02 completion. Report the failed dimension and clarification/owner route truthfully.
- **Security/safety expectations:** Treat supplied intake references according to minimum necessary exposure; do not embed sensitive source content unnecessarily in questions or status. Block any attempt to bypass the appropriate Product authority.
- **Verification requirements:** Future checks must cover every readiness dimension separately, combined failures, all approved intake forms, focused understandable questions, materially ambiguous input, silence/inference prevention, and a non-critical downstream-detail TBD that does not block readiness. Use `PASS`, `FAIL`, or `NOT RUN` only.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all per-dimension, combined, intake, clarification, authority-boundary, and downstream-TBD checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Deciding or approving product content, choosing technical/design details, interface technology, document/image parsing technology, and implementation of a reasoning provider.

## TASK-005 - Authority registry and conflict handling

- **Status:** `TODO`
- **Purpose:** Resolve authority by domain, scope, source, status, version, approval, freshness, and dependency while enforcing the required conflict and safety behavior without linear precedence.
- **Authority trace:**
  - `G-01, G-02, G-04, G-05 -> FR-04, FR-05, FR-08, FR-17, NFR-04, EC-07 -> AC-04, AC-05, AC-08, AC-17, AC-26, AC-35 -> SPEC-004 -> DES-004 -> TASK-005`
  - `G-02, G-04, G-05 -> FR-08, FR-17, NFR-04, EC-07 -> AC-08, AC-17, AC-26, AC-35 -> SPEC-010 -> DES-004 -> TASK-005`
  - `G-01, G-03, G-04, G-05 -> FR-08, FR-12, FR-14, FR-15, NFR-01, NFR-04 -> AC-08, AC-12, AC-14, AC-15, AC-23, AC-26 -> SPEC-016 -> DES-004 -> TASK-005`
- **Dependencies:** `TASK-001`, `TASK-002`.
- **Allowed implementation scope:** Authority-resolver responsibility; domain-scoped registry entries and configured artifact mappings; statuses `ABSENT`, `DRAFT`, `APPROVED_CURRENT_AUTHORITY`, `STALE_AFFECTED`, and `CONFLICTING`; dependency/affected-scope findings; durable conflict records; gate-substitution checks; and safe owner routing.
- **Required behavior/outcome:** Resolve each question only in its owning domain; expose owner, source/version, approval status, unresolved condition, affected scope, and permitted route. Treat existence separately from authority. On conflict execute and record `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`. Enforce that only valid Stage07 `PASS` grants normal new-implementation authorization and that qualification prerequisites cannot substitute for one another.
- **Preservation obligations:** Preserve all protected artifact/domain mappings, non-linear authority, existing approval and decision history, valid unaffected work, and stale/affected links. Never rewrite an authority artifact or erase a conflict while resolving registry state.
- **Error/failure expectations:** Missing, expired, withdrawn, stale, conflicting, out-of-scope, or ambiguously versioned authority blocks affected execution. Unauthorized resolution or global precedence is rejected. Persist the exact conflict/failure and route; broader blocking requires proven dependency impact.
- **Security/safety expectations:** High-risk/destructive/security conditions and authority conflicts stay `BLOCKED` until exact applicable authorization or owner resolution is recorded. Reports expose only necessary condition, scope, owner, and safe reference; no component may self-clear its blocker.
- **Verification requirements:** Future checks must cover every registry status, missing authority, same-domain status differences, cross-domain conflict, the four-step protocol, unauthorized/global-precedence override, sensitive-detail minimization, affected/unaffected isolation, and every prohibited gate/qualification substitution. Use `PASS`, `FAIL`, or `NOT RUN` only.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and registry, mapping, conflict, safety, isolation, and gate-substitution checks all `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Substantive authority decisions, editing protected authority artifacts, concrete authentication/IAM or secrets products, destructive-operation execution, Stage07/09/10 decisions, and release/deployment.

## TASK-006 - Durable Human Decision management

- **Status:** `TODO`
- **Purpose:** Create and manage durable, append-preserving Human Decision records whose pending and resolved states have the approved scoped governing effects.
- **Authority trace:**
  - `G-01, G-02, G-05 -> FR-07, FR-09, FR-10, EC-02, EC-03 -> AC-07, AC-09, AC-10, AC-30, AC-31 -> SPEC-002 -> DES-005 -> TASK-006`
  - `G-01, G-02, G-04, G-05 -> FR-04, FR-05, FR-08, FR-17, NFR-04, EC-07 -> AC-04, AC-05, AC-08, AC-17, AC-26, AC-35 -> SPEC-004 -> DES-005 -> TASK-006`
  - `G-01, G-02, G-05 -> FR-05, FR-08, FR-09, FR-10, EC-02, EC-03 -> AC-05, AC-08, AC-09, AC-10, AC-30, AC-31 -> SPEC-005 -> DES-005 -> TASK-006`
- **Dependencies:** `TASK-002`, `TASK-005`.
- **Allowed implementation scope:** Human Decision responsibility for stable `HD-*` identities, subject, authoritative owner, affected scope, reason/consequence, available choices, status/result, actor/reference, dependencies, timestamps/version identities, presentation facts, and downstream invalidation findings.
- **Required behavior/outcome:** Support at least pending, approved, rejected, revision requested, and withdrawn states without erasing prior results. Creation immediately pauses affected work. Approval satisfies only the named condition; rejection prevents adoption; revision routes the subject back; revision/withdrawal marks known dependents stale/affected and requires review/rerun. Continue other work only when independence is recorded.
- **Preservation obligations:** Retain complete decision history and attribution, previous results, dependency/invalidation links, valid completed progress, and proven-independent work. Preserve the distinction between Human Decision, artifact authority, and Stage07 implementation authorization.
- **Error/failure expectations:** Identity collision, ambiguous subject/result, incomplete affected-scope analysis, unauthorized actor, stale target, or persistence failure cannot unblock work. The prior valid state remains and the failure plus required route is recorded truthfully.
- **Security/safety expectations:** Validate the authoritative decision owner and exact bounded scope; minimize persisted/reported sensitive values; require explicit decision for applicable destructive/high-risk/security cases; never infer approval from silence or delivery.
- **Verification requirements:** Future checks must prove unique stable identities, understandable presentation, every status/result path, pending blocking, actor/owner rejection, stale target, retained history, full known-dependent invalidation, independent-work continuation, and failure preservation. Use `PASS`, `FAIL`, or `NOT RUN` only.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and identity, presentation, all result paths, blocking, authorization, history, invalidation, independence, and failure checks all `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Making the substantive human choice, defining authentication technology, replacing Stage07 `PASS`, directly editing owning authority artifacts, and user-channel transport.

## TASK-007 - Replaceable reasoning-provider boundary

- **Status:** `TODO`
- **Purpose:** Provide a replaceable, channel-neutral reasoning-provider boundary whose outputs remain bounded, non-authoritative, failure-safe, and subject to governed-core validation.
- **Authority trace:**
  - `G-02, G-04, G-05 -> FR-04, FR-05, FR-12, FR-13, EC-04 -> AC-04, AC-05, AC-12, AC-13, AC-32 -> SPEC-006 -> DES-006 -> TASK-007`
  - `G-01, G-03, G-04, G-05 -> FR-13, FR-16, NFR-01, NFR-02, EC-06 -> AC-13, AC-16, AC-23, AC-24, AC-34 -> SPEC-009 -> DES-006 -> TASK-007`
- **Dependencies:** `TASK-005`, `TASK-010`.
- **Allowed implementation scope:** Reasoning-provider adapter boundary for bounded requests, authoritative-context references, permitted capabilities, affected scope, expected structured results, validation inputs, and eligible retry/alternate/escalation facts. Provider-specific adapters may exist later without changing this contract.
- **Required behavior/outcome:** Allow analysis, questions, proposals, drafting, reasoning, authorized Stage08 assistance, and verification assistance only within declared capability/scope. Treat provider output as proposed output until validated and persisted by the appropriate owner boundary. Ensure provider selection cannot alter authority, lifecycle, evidence, or qualification semantics; require the Stage08 authorization envelope before write-capable invocation.
- **Preservation obligations:** Preserve authoritative references rather than implicit chat authority, provider-independent semantics, prior valid governed state and completed progress, non-authoritative proposal status, and full failure/attempt identity.
- **Error/failure expectations:** Unavailable, malformed, timed-out, policy-violating, out-of-scope, or authority-crossing provider behavior must record the exact operation and affected scope, stop unsafe continuation, preserve prior state, and offer only eligible retry, alternate, remediation, escalation, or Human Decision routes without semantic downgrade.
- **Security/safety expectations:** Apply least capability and bounded context; avoid unnecessary sensitive content; prohibit providers from creating authority/evidence, bypassing Human Decision or gates, fabricating state/results, or directly committing lifecycle qualifications. Write capability is forbidden without a valid sealed Stage08 envelope.
- **Verification requirements:** After `TASK-010` is available, future checks must run equivalent governance scenarios through replaceable provider substitutes; cover malformed, timeout, unavailable, policy violation, scope overrun, inference-to-approval, and no-authorization write attempts; and prove preserved state plus provider-independent semantics. Use `PASS`, `FAIL`, or `NOT RUN` only.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only after dependency `TASK-010` is implemented as authorized and satisfied; the common conditions must then hold and all provider-equivalence, boundary, failure, preservation, and authorization checks must `PASS`. Decomposition of that dependency is resolved; implementation satisfaction is not claimed. No checkpoint is currently achieved.
- **Out-of-scope:** Choosing a mandatory vendor, adding providers beyond MVP need, provider authentication product, implementing Stage08 execution-envelope assembly (`TASK-012`), granting authorization, channel transport, and cloud deployment.

## TASK-008 - Evidence registry and qualification separation

- **Status:** `TODO`
- **Purpose:** Record verification evidence truthfully and independently from completion, verification, safety, readiness, and release qualifications.
- **Authority trace:**
  - `G-03, G-04, G-05 -> FR-14, FR-15, NFR-01, EC-05 -> AC-14, AC-15, AC-23, AC-33 -> SPEC-008 -> DES-009 -> TASK-008`
  - `G-01, G-03, G-04, G-05 -> FR-08, FR-12, FR-14, FR-15, NFR-01, NFR-04 -> AC-08, AC-12, AC-14, AC-15, AC-23, AC-26 -> SPEC-016 -> DES-009 -> TASK-008`
- **Dependencies:** `TASK-001`, `TASK-005`.
- **Allowed implementation scope:** Evidence-registry responsibility; stable check identity, criterion, scope, execution status, exactly one outcome, evidence reference/gap, coverage links, freshness/current-version relation, regression risk, and inputs to a distinct qualification evaluator/projector.
- **Required behavior/outcome:** Record `PASS` only for an executed satisfied check, `FAIL` only for an executed unsatisfied check, and `NOT RUN` when qualifying execution evidence does not exist. Link outcomes/gaps to governing requirements or behaviors and current identity. Keep raw evidence distinct from Stage09/Stage10 decisions and from complete/verified/safe/ready projections; remove dependent qualification when required evidence is missing, stale, or irrelevant.
- **Preservation obligations:** Preserve original check outcomes, scope, evidence/gap, freshness, and history; retain tests as evidence rather than authority; do not overwrite a failed or not-run outcome to create apparent completion.
- **Error/failure expectations:** Invalid/multiple outcomes, missing required metadata, stale or irrelevant evidence, partial coverage, incomplete tests, or registry persistence failure must remain explicit and withhold dependent qualification. A test `PASS` never becomes Stage09 `PASS`.
- **Security/safety expectations:** Evidence references must avoid exposing secrets or unnecessary sensitive output. Security evidence gaps cannot be downgraded or bypassed; no evidence record may self-authorize destructive, release, or deployment action.
- **Verification requirements:** Future checks must cover mixed `PASS`/`FAIL`/`NOT RUN`, absent/stale/irrelevant evidence, partial coverage, current-version mismatch, registry failure, regression-risk disclosure, and every forbidden complete/verified/safe/ready or gate substitution. Use the same three-result vocabulary for the checks themselves.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all outcome-semantics, metadata, freshness, gap, security, persistence, coverage, and qualification-separation checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Selecting a test framework or test mix, executing Stage09, issuing `VERIFICATION_DECISION` or `RELEASE_DECISION`, defining product acceptance criteria, and treating telemetry as evidence authority.

## TASK-009 - Plain-language status and reporting projection

- **Status:** `TODO`
- **Purpose:** Produce understandable, read-only, snapshot-bound status and operational reports without inventing facts or conflating qualifications.
- **Authority trace:**
  - `G-01, G-02, G-05 -> FR-06, FR-11, NFR-01 -> AC-06, AC-11, AC-23 -> SPEC-001 -> DES-011 -> TASK-009`
  - `G-01, G-03, G-04, G-05 -> FR-13, FR-16, NFR-01, NFR-02, EC-06 -> AC-13, AC-16, AC-23, AC-24, AC-34 -> SPEC-009 -> DES-011 -> TASK-009`
  - `G-02, G-05 -> FR-02, FR-06, FR-09, FR-14, FR-16, NFR-02 -> AC-02, AC-06, AC-09, AC-14, AC-16, AC-24 -> SPEC-015 -> DES-011 -> TASK-009`
- **Dependencies:** `TASK-002`, `TASK-005`, `TASK-006`, `TASK-008`.
- **Allowed implementation scope:** Status/reporting responsibility for read-only projections from one consistent governed snapshot; plain-language summaries; technical identifiers/references; situation, consequence, scope, preserved work, required action, next eligible route, evidence gaps, and separated qualification fields.
- **Required behavior/outcome:** Present current stage, completed/current/next work, pending decisions, authority state, blockers/incompleteness, continuation eligibility, verification outcomes/gaps, regression risk, and distinct approval/authorization/completion/verification/readiness states as applicable. Bind reports to snapshot/version identity, show staleness, use truthful unresolved vocabulary, and explain reports for non-programmers before identifiers.
- **Preservation obligations:** Preserve source facts and their qualification boundaries; make valid completed work and unresolved gaps visible; retain stable safe references; never mutate governed state or replace structured facts with provider prose.
- **Error/failure expectations:** Missing facts remain `TBD`, `INCOMPLETE`, `BLOCKED`, or `NOT RUN` as applicable. Contradictory or stale snapshots cannot produce a stronger report. If an understandable report cannot be produced, keep the interaction incomplete, identify the reporting failure, and expose a safe alternate route.
- **Security/safety expectations:** Apply minimum-disclosure reporting: redact sensitive values while retaining actionable category, scope, owner, consequence, and safe reference. Never present missing security/authority resolution as safe continuation.
- **Verification requirements:** Future checks must compare representative clarification, lifecycle status, Human Decision, authority conflict, failure, evidence-gap, regression-risk, and next-action reports against the same persisted snapshot; verify non-programmer understandability, qualification separation, stale/missing-fact behavior, redaction, and no mutation. Use `PASS`, `FAIL`, or `NOT RUN` only.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all factual-consistency, category coverage, understandability, staleness, qualification, redaction, alternate-route, and read-only checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Deciding lifecycle/authority/evidence facts, mutating state, UI framework, LINE/webhook schema, cloud delivery, authentication product, Stage09/Stage10 qualification, and free-form provider prose as authority.

## TASK-010 - Durable failure envelope and recovery routing

- **Status:** `TODO`
- **Purpose:** Persist a common, durable representation of operational failures and route recovery without losing valid progress, hiding failure, broadening authority, or resuming unsafe work.
- **Authority trace:** `G-01, G-03, G-04, G-05 -> FR-13, FR-16, NFR-01, NFR-02, EC-06 -> AC-13, AC-16, AC-23, AC-24, AC-34 -> SPEC-009 -> DES-012 -> TASK-010`.
- **Dependencies:** `TASK-001`, `TASK-002`, `TASK-005`.
- **Allowed implementation scope:** Failure-envelope and recovery-routing responsibilities; stable failure and attempt identities; operation/step, cause class, affected scope, persisted pre-operation identity, partial outputs, valid completed work, truthful status, unsafe-continuation state, route eligibility, and linked retry attempts. No concrete persistence or serialization technology is selected.
- **Required behavior/outcome:** Persist failures from lifecycle stages, tools, reasoning/AI providers, commands, Git operations, tests/verification, authority/security checks, and execution. Identify the exact failure point and affected scope, retain independently valid completed work, block unsafe continuation, link every retry to the original failure, and expose only routes whose preconditions currently permit retry, alternate, remediation, revision, escalation, or Human Decision.
- **Preservation obligations:** Preserve original failure facts, prior governed state, partial outputs, attempt history, valid completed progress, and proven-independent work. Recovery must never erase evidence, silently restart affected scope, or turn partial work into completion.
- **Error/failure expectations:** A missing, malformed, ambiguous, or unpersisted envelope leaves affected work `INCOMPLETE` or `BLOCKED`. Failed recovery and repeated failure produce linked truthful attempts; ineligible routes are withheld, and no failure may be hidden or retroactively qualified.
- **Security/safety expectations:** Minimize sensitive failure content while retaining actionable category, scope, owner, and safe reference. Security- or authority-related failures remain blocked until the applicable authoritative resolution; destructive cleanup or rollback is not implied or authorized.
- **Verification requirements:** Future checks must induce each named failure class and verify stable identity, exact point/scope, persisted pre-operation identity, partial-output classification, valid-progress preservation, unsafe-continuation blocking, linked retries, repeated-failure truthfulness, and at least one eligible route where applicable. Use only `PASS`, `FAIL`, or `NOT RUN` with evidence/gaps.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all envelope, persistence, preservation, blocking, linked-attempt, route-eligibility, minimum-disclosure, and repeated-failure checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Automatically resolving the underlying failure, destructive cleanup, broad rollback, selecting provider/storage technology, granting new authority, issuing any gate decision, or claiming recovered work verified or complete.

## TASK-011 - Safety interlock and minimum-disclosure handling

- **Status:** `TODO`
- **Purpose:** Enforce a centralized, bounded preflight before destructive/high-risk operations and before security- or authority-blocked scope may resume, while revealing only the minimum sensitive information needed for action.
- **Authority trace:**
  - `G-01, G-02, G-04, G-05 -> FR-04, FR-05, FR-08, FR-17, NFR-04, EC-07 -> AC-04, AC-05, AC-08, AC-17, AC-26, AC-35 -> SPEC-004 -> DES-013 -> TASK-011`
  - `G-02, G-04, G-05 -> FR-08, FR-17, NFR-04, EC-07 -> AC-08, AC-17, AC-26, AC-35 -> SPEC-010 -> DES-013 -> TASK-011`
- **Dependencies:** `TASK-002`, `TASK-005`, `TASK-006`, `TASK-010`.
- **Allowed implementation scope:** Safety-interlock responsibility; exact target/scope and severity representation; current authority and blocker identity; required explicit authorization/decision references; safe-continuation eligibility; minimum-disclosure findings; and dependency-supported isolation of unaffected scope.
- **Required behavior/outcome:** Preflight every destructive or high-risk request and every attempted resume of security- or authority-conflicted scope. Require a bounded target, applicable explicit authorization, current authority identity, and resolved blockers before eligibility; otherwise record `BLOCKED`, identify the required owner/decision, and enforce `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER` for conflicts.
- **Preservation obligations:** Preserve protected scope, blocker/conflict records, authoritative ownership, explicit authorization identity, prior valid work, and independently proven unaffected work. Never store or display unnecessary secrets or sensitive payloads.
- **Error/failure expectations:** Ambiguous target, missing/expired/mismatched authorization, unauthorized actor, unresolved security concern, conflict, stale snapshot, or interlock failure forbids affected continuation and any qualifying completion claim. No component may suppress or self-clear the result.
- **Security/safety expectations:** Apply minimum privilege, target-bounded authorization, current-snapshot validation, minimum disclosure, and explicit dependency findings before isolating unaffected work. The task defines enforcement, not authorization for any destructive, security-sensitive, deployment, or release operation.
- **Verification requirements:** Future checks must cover destructive, high-risk, security, and authority-conflict cases; exact-target and stale/mismatched authorization; unauthorized actors and bypass attempts; conflict routing; sensitive-data minimization; valid explicitly authorized continuation; and unaffected-scope isolation. Use only `PASS`, `FAIL`, or `NOT RUN`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all preflight, blocker, authorization, conflict-protocol, bypass, redaction, continuation, and isolation checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Performing destructive/high-risk operations, choosing IAM/authentication/secrets products, resolving substantive authority conflicts, granting authorization, deployment, release, or weakening lifecycle gates.

## TASK-012 - Sealed Stage08 execution-envelope enforcement

- **Status:** `TODO`
- **Purpose:** Assemble, validate, and enforce immutable per-task Stage08 execution envelopes so implementation can occur only against the exact approved authority, task, repository baseline, scope, verification, and checkpoint conditions.
- **Authority trace:**
  - `G-02, G-04, G-05 -> FR-04, FR-05, FR-12, FR-13, EC-04 -> AC-04, AC-05, AC-12, AC-13, AC-32 -> SPEC-006 -> DES-007 -> TASK-012`
  - `G-01, G-04, G-05 -> FR-11, FR-12, NFR-03 -> AC-11, AC-12, AC-25 -> SPEC-007 -> DES-007 -> TASK-012`
  - `G-01, G-03, G-04, G-05 -> FR-13, FR-16, NFR-01, NFR-02, EC-06 -> AC-13, AC-16, AC-23, AC-24, AC-34 -> SPEC-009 -> DES-007 -> TASK-012`
  - `G-01, G-03, G-04, G-05 -> FR-08, FR-12, FR-14, FR-15, NFR-01, NFR-04 -> AC-08, AC-12, AC-14, AC-15, AC-23, AC-26 -> SPEC-016 -> DES-007 -> TASK-012`
- **Dependencies:** `TASK-001`, `TASK-002`, `TASK-005`, `TASK-008`, `TASK-010`, `TASK-011`.
- **Allowed implementation scope:** Stage08 envelope assembly, validation, immutability, and enforcement responsibilities; approved authority and task references; valid Stage07 report and authorization state; repository/branch/baseline identity; exact allowed files and behavior scope; required verification; checkpoint conditions; attempt/evidence capture; and overrun stopping.
- **Required behavior/outcome:** Refuse execution unless every required envelope field is current and valid. Seal one exact task and independently verifiable scope per attempt; prevent execution components from altering or enlarging it; capture baseline, changed files, diff/checkpoint reference, verification references, valid progress, failure point, and remaining scope; stop and route scope additions or overruns; permit checkpoint eligibility only after every configured prerequisite passes.
- **Preservation obligations:** Preserve immutable envelope identity, approved authority versions, task scope, baseline, prior attempts, valid in-scope progress, unexpected-diff evidence, and separation among authorization, implementation completion, verification evidence, Stage09 qualification, and release.
- **Error/failure expectations:** Missing/invalid/stale Stage07 `PASS`, false authorization, changed authority, task mismatch, dirty or mismatched governed baseline, unexpected diff, scope overrun, persistence failure, or unmet checkpoint condition stops affected execution. Preserve identifiable valid in-scope progress and route additional scope to the proper task, authority, or gate owner.
- **Security/safety expectations:** Apply least capability and exact target/file/behavior boundaries; invoke the safety interlock for protected operations; reject envelope tampering, authority substitution, secret exposure, and self-authorization. No envelope in this artifact currently exists or grants execution authority.
- **Verification requirements:** Future checks must attempt absent/invalid/stale authorization, changed authority, task or baseline mismatch, envelope mutation, scope/file overrun, unexpected diff, partial failure, missing evidence, unmet checkpoint prerequisites, and one successful authorized atomic execution with complete records. Use only `PASS`, `FAIL`, or `NOT RUN`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all envelope completeness, freshness, immutability, enforcement, overrun, evidence-capture, safety-interlock, partial-failure, and checkpoint-prerequisite checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Issuing Stage07 `PASS`, approving tasks or authority, selecting coding/provider technology, broad repository layout, implementing product changes itself, Stage09 qualification, release, or deployment.

## TASK-013 - Modification-impact and preservation ledger

- **Status:** `TODO`
- **Purpose:** Record a bounded modification impact analysis that distinguishes requested change, affected and preserved behavior/data, governing authority, observation, ambiguity, and risk before dependent authorization or completion.
- **Authority trace:** `G-01, G-03, G-04 -> FR-18, NFR-05 -> AC-18, AC-27 -> SPEC-011 -> DES-014 -> TASK-013`.
- **Dependencies:** `TASK-001`, `TASK-005`, `TASK-006`.
- **Allowed implementation scope:** Impact-ledger responsibility and its links to requested scope, affected existing behavior/data, preservation expectations, governing requirements/contracts/design/tasks, observed evidence, ambiguity, risk, and applicable Human Decision or owner route.
- **Required behavior/outcome:** For each modification, distinguish what is requested to change from what is affected and what must be preserved. Record authority basis separately from observed implementation evidence; keep materially unknown impact visible and route material product ambiguity to the proper owner before dependent authorization/completion.
- **Preservation obligations:** Preserve behavior/data outside authorized change scope where applicable, original requests and authority references, the non-authoritative status of observations, unresolved ambiguity, and valid prior records. Do not silently expand modification scope.
- **Error/failure expectations:** Materially unknown affected or preservation scope, missing authority basis, conflicting classifications, stale inputs, or ledger persistence failure keeps dependent work unresolved and prevents an overall-complete claim. Report the exact gap, risk, affected scope, and owner route.
- **Security/safety expectations:** Minimize copied data and sensitive implementation details; use safe references where sufficient. High-risk, destructive, security, or authority-conflicted modifications remain subject to TASK-011 and cannot be normalized as routine maintenance.
- **Verification requirements:** Future checks must classify requested, affected, preserved, ambiguous, risky, and merely observed behavior/data; verify trace links and authority/observation separation; exercise unknown impact, scope expansion, stale input, and persistence failure; and confirm dependent completion remains withheld. Use only `PASS`, `FAIL`, or `NOT RUN`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all classification, authority separation, trace, ambiguity, preservation, risk, persistence, and completion-withholding checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Deciding material product ambiguity, inspecting or adopting existing behavior as authority, implementing the requested modification, choosing storage/schema technology, regression qualification, or Stage09 decisions.

## TASK-014 - Regression coverage and completion guard

- **Status:** `TODO`
- **Purpose:** Map every affected behavior/data risk from a modification ledger to current regression evidence or an explicit gap and prevent overall completion when required coverage is absent.
- **Authority trace:**
  - `G-03, G-04, G-05 -> FR-14, FR-15, NFR-01, EC-05 -> AC-14, AC-15, AC-23, AC-33 -> SPEC-008 -> DES-015 -> TASK-014`
  - `G-03, G-04, G-05 -> FR-19, NFR-05, EC-08 -> AC-19, AC-27, AC-36 -> SPEC-012 -> DES-015 -> TASK-014`
- **Dependencies:** `TASK-008`, `TASK-013`.
- **Allowed implementation scope:** Regression-coverage view and completion-guard responsibilities; impact-risk-to-evidence/gap links; current-version/freshness relation; full, partial, absent, stale, and new-feature-only coverage states; warnings; and non-qualifying completion eligibility projection.
- **Required behavior/outcome:** For every affected behavior/data risk, identify applicable current evidence or an explicit named gap. Keep new-behavior success separate from non-regression, disclose uncovered scope and known risk, and withhold overall completion whenever required regression evidence is absent, stale, irrelevant, failed, or not run.
- **Preservation obligations:** Preserve impact-ledger scope, original evidence outcomes and gaps, affected-risk identities, qualification separation, and any valid evidence unrelated to the gap. Never overwrite a gap or unrelated PASS to manufacture non-regression.
- **Error/failure expectations:** Missing risk links, partial/absent/stale/irrelevant evidence, coverage computation failure, or new-feature-only PASS produces an explicit warning and withholds overall completion. The guard cannot issue Stage09 `PASS` or waive required evidence.
- **Security/safety expectations:** Do not expose sensitive evidence contents unnecessarily; security-related regression gaps remain explicit and non-bypassable. No guard result authorizes destructive action, release, or deployment.
- **Verification requirements:** Future checks must cover full, partial, none, stale, irrelevant, failed, `NOT RUN`, and new-feature-only evidence; verify every affected-risk link, warnings, preserved valid evidence, and correct withholding/restoration of completion eligibility without creating Stage09 qualification. Use only `PASS`, `FAIL`, or `NOT RUN`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all risk-link, coverage-state, freshness, warning, preservation, and completion-guard checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Selecting test frameworks or test suites, executing Stage09, issuing verification/release decisions, changing impact authority, or treating the coverage view as proof by itself.

## TASK-015 - Channel-neutral governed operations and local MVP adapter

- **Status:** `TODO`
- **Purpose:** Expose the approved governed operations through a viable local MVP interface while preserving stable identities, replay safety, understandable reporting, and channel-independent lifecycle, authority, and evidence semantics.
- **Authority trace:**
  - `G-01, G-02, G-05 -> FR-01, FR-06, FR-07, FR-20 -> AC-01, AC-06, AC-07, AC-20 -> SPEC-013 -> DES-016 -> TASK-015`
  - `G-02, G-05 -> FR-02, FR-06, FR-09, FR-14, FR-16, NFR-02 -> AC-02, AC-06, AC-09, AC-14, AC-16, AC-24 -> SPEC-015 -> DES-016 -> TASK-015`
- **Dependencies:** `TASK-003`, `TASK-004`, `TASK-006`, `TASK-007`, `TASK-009`, `TASK-010`, `TASK-011`, `TASK-012`, `TASK-014`.
- **Allowed implementation scope:** One channel-neutral application operation boundary and one viable local MVP adapter for `SUBMIT_REQUEST`, `INSPECT_STATUS`, `CONTINUE_OR_RESUME`, `PAUSE`, `RECEIVE_DECISION`, `APPROVE`, `REJECT`, `REQUEST_REVISION`, `RECEIVE_FAILURE_OR_BLOCKER`, and `RECEIVE_VERIFICATION_SUMMARY`; stable journey/command/target identities; snapshot-bound results; safe replay; and alternate local resumption.
- **Required behavior/outcome:** Allow a user to submit all approved intake forms, continue/resume, inspect governed status, receive and act on Human Decisions, and receive failures/blockers and verification summaries through the local interface. Equivalent actions must produce the same governed effects regardless of presentation; duplicate delivery is idempotent, stale/malformed input is rejected, and channel/session loss resumes from repository-backed state.
- **Preservation obligations:** Preserve governed-core semantics, stable identities, committed state, decision and evidence boundaries, understandable reporting, and the distinction between delivery outcome and command commitment. Adapter formatting must not change authority, lifecycle, evidence, or qualification.
- **Error/failure expectations:** Unavailable channel, delivery failure, malformed/stale/duplicate operation, reporting failure, or session loss cannot create approval or silently alter state. Report whether a command committed, keep affected state truthful, and offer an eligible local recovery route.
- **Security/safety expectations:** Apply bounded inputs, minimum-disclosure outputs, current authorization and interlock results, and least capability. Adapter identity is not substantive authority; protected operations remain blocked until their own prerequisites hold.
- **Verification requirements:** Future checks must complete the essential MVP journey locally without LINE or cloud; exercise every operation and approved intake form; verify stable identity, duplicate replay, stale/malformed rejection, channel/delivery failure, session loss, plain-language output, minimum disclosure, and equivalence against any later adapter. Use only `PASS`, `FAIL`, or `NOT RUN`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all local-journey, operation, intake, identity, replay, failure, resumption, reporting, disclosure, and semantic-neutrality checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** LINE, webhook architecture, cloud or remote deployment, Web UI, transport/API schema, UI framework, authentication/IAM product, multi-user collaboration, commercialization, or making any future channel an MVP requirement.

## TASK-016 - Governed MVP demonstration manifest

- **Status:** `TODO`
- **Purpose:** Assemble inspectable references for every required MVP journey link and governing effect while leaving absent or non-qualifying proof explicitly incomplete.
- **Authority trace:** `G-01, G-02, G-03, G-04, G-05 -> FR-11, FR-21 -> AC-11, AC-21 -> SPEC-014 -> DES-010 -> TASK-016`.
- **Dependencies:** `TASK-001`, `TASK-008`, `TASK-013`, `TASK-014`, `TASK-015`.
- **Allowed implementation scope:** Demonstration-manifest assembly and validation responsibility; references to lifecycle transitions, authority artifacts, tasks, Human Decisions, authorized execution checkpoints, evidence, Git identity, failures/blockers, truthful status, maintenance scope, preservation, and regression results.
- **Required behavior/outcome:** Identify every step in `IDEA -> requirement clarification -> approved product requirements -> specification -> design -> task decomposition -> Human Decision -> authorized AI coding -> testing/verification -> Git traceability -> truthful status/failure handling -> maintenance change -> regression verification`. Reference proof that authority was not bypassed, AI did not decide product requirements, Human Decision and blockers governed affected work, unverified work was not complete, and maintenance received regression protection.
- **Preservation obligations:** Preserve source ownership, stable references, missing-proof status, qualification boundaries, and the manifest's role as an index rather than evidence or authority. Do not copy or rewrite governing records to make the chain appear complete.
- **Error/failure expectations:** A missing, stale, broken, ambiguous, or non-qualifying reference leaves its link and the demonstration `INCOMPLETE`. Manifest assembly failure or a narrative assertion cannot synthesize evidence, satisfy a gap, or create qualification.
- **Security/safety expectations:** Use safe references and minimum necessary excerpts; do not expose secrets or sensitive evidence. The manifest cannot authorize execution, destructive action, release, or deployment.
- **Verification requirements:** Future checks must inspect the complete chain and all six governing effects, then deliberately omit or stale each proof class to confirm incompleteness, bidirectional navigability to available Stage06-owned links, minimum disclosure, and no qualification creation. Use only `PASS`, `FAIL`, or `NOT RUN`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all chain-link, governing-effect, missing/stale-proof, navigation, disclosure, and non-qualification checks `PASS`. No checkpoint is currently achieved.
- **Out-of-scope:** Producing missing evidence, issuing Stage07/Stage09/Stage10 decisions, declaring the MVP qualified, implementing journey components, deployment, or release.

## TASK-017 - Governed-core lifecycle integration

- **Status:** `TODO`
- **Purpose:** Integrate the approved orchestrator, governor, registries, adapters, persistence, reporting, maintenance, failure, evidence, and safety boundaries into one consistent governed flow without conflating component evidence with Stage09 qualification.
- **Authority trace:** Every approved P0 chain (`G-01` through `G-05` to `FR-01` through `FR-21`, `NFR-01` through `NFR-05`, and `EC-01` through `EC-08`, each paired with `AC-01` through `AC-21`, `AC-23` through `AC-27`, and `AC-29` through `AC-36`) reaches `SPEC-001` through `SPEC-016` and `DES-001` through `DES-016` according to the approved upstream trace tables and section 6 below, then extends to `TASK-017`.
- **Dependencies:** `TASK-003`, `TASK-004`, `TASK-006`, `TASK-007`, `TASK-008`, `TASK-009`, `TASK-010`, `TASK-011`, `TASK-012`, `TASK-013`, `TASK-014`, `TASK-015`, `TASK-016`.
- **Allowed implementation scope:** Integration of the logical components and responsibility boundaries approved by `DES-001` through `DES-016`; orchestration across current snapshot loading, authority and lifecycle evaluation, decisions, reasoning and Stage08 invocation eligibility, persistence, evidence, reporting, failure/recovery, maintenance/regression, and the local channel boundary. No new component semantics or technology selection is authorized.
- **Required behavior/outcome:** Produce one coherent governed flow in which operations load a fresh repository-backed snapshot; authority and lifecycle invariants control routing; Human Decisions, reasoning, and execution are invoked only when eligible; accepted transitions and failures persist atomically; status reflects committed facts; maintenance preserves bounded scope; regression gaps withhold completion; and all qualification/gate distinctions remain intact.
- **Preservation obligations:** Preserve every component boundary, upstream authority, stable trace identity, independently valid progress, failure history, decision history, preservation ledger, evidence outcomes/gaps, channel neutrality, and separation of approval, authorization, completion, verification, readiness, release, and recovery provenance.
- **Error/failure expectations:** Integration mismatch, contradictory snapshots, missing component result, partial persistence, scope overrun, unresolved authority/safety condition, or broken trace stops only proven-affected continuation, records the exact failure, preserves valid progress, and routes to the responsible task or authoritative owner. No integration success may imply Stage09 qualification.
- **Security/safety expectations:** Enforce least capability, sealed Stage08 envelopes, safety interlocks, minimum disclosure, protected artifact ownership, and non-bypassable lifecycle gates end to end. No integrated component may self-authorize, self-clear a conflict, or upgrade qualification.
- **Verification requirements:** Future integration checks must exercise the complete governed flow and every component boundary; fresh-snapshot consistency; all five lifecycle actions; decisions and invalidation; authority conflict; provider/channel/execution failures; sealed-envelope overrun; evidence and qualification separation; maintenance/regression; trace navigation; session loss; and safe independent continuation. Use only `PASS`, `FAIL`, or `NOT RUN` and do not issue Stage09 `PASS`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all required integration, boundary, lifecycle, persistence, failure, safety, maintenance, traceability, and qualification-separation checks `PASS`. This task's checkpoint cannot constitute Stage09 qualification. No checkpoint is currently achieved.
- **Out-of-scope:** Redefining any component contract, choosing deferred technologies/layout, adding speculative services, LINE/webhook/cloud/Web UI, Stage07 evaluation, Stage09 qualification, Stage10/release, or deployment.

## TASK-018 - P0 lifecycle and preservation scenario coverage

- **Status:** `TODO`
- **Purpose:** Define repeatable verification scenarios and evidence requirements covering every applicable P0 contract, rejection/failure path, traceability link, lifecycle integration, and preservation/regression obligation without issuing the Stage09 decision.
- **Authority trace:** Every approved P0 chain (`G-01` through `G-05` to `FR-01` through `FR-21`, `NFR-01` through `NFR-05`, and `EC-01` through `EC-08`, each paired with `AC-01` through `AC-21`, `AC-23` through `AC-27`, and `AC-29` through `AC-36`) reaches `SPEC-001` through `SPEC-016` and `DES-001` through `DES-016` according to the approved upstream trace tables and section 6 below, then extends to `TASK-018`.
- **Dependencies:** `TASK-016`, `TASK-017`.
- **Allowed implementation scope:** Scenario definitions, fixtures/inputs conceptually required by approved contracts, expected governed outcomes, requirement/SPEC/DES/TASK coverage links, rejection and failure variants, preservation and regression obligations, evidence metadata expectations, repeatability requirements, and explicit gaps. Concrete test framework and file layout remain deferred.
- **Required behavior/outcome:** Define repeatable scenarios for all 34 applicable P0 requirements and acceptance criteria, all 16 SPEC and DES identifiers, every task's required behaviors and error paths, the end-to-end journey, gate/qualification non-substitution, session recovery, authority conflict, safety blocking, partial-progress preservation, modification impact, and regression coverage. Each scenario must state scope, criterion, expected `PASS`/`FAIL`/`NOT RUN` evidence semantics, and trace targets.
- **Preservation obligations:** Preserve approved acceptance criteria and contract meaning, negative/rejection paths, evidence gaps, current-version identity, existing valid scenario results, and separation between test evidence and authority/Stage09 qualification. Do not weaken coverage to obtain a passing summary.
- **Error/failure expectations:** Missing scenario coverage, ambiguous criterion, unrepeatable setup, broken trace, stale/irrelevant evidence, or unavailable execution remains an explicit gap/`NOT RUN` and withholds dependent completion. Partial scenario success cannot qualify the whole P0 scope.
- **Security/safety expectations:** Include safe negative scenarios for unauthorized, destructive/high-risk, security, authority-conflict, scope-overrun, secret/minimum-disclosure, and bypass behavior without performing an unapproved destructive or sensitive operation. Test data must minimize sensitive content.
- **Verification requirements:** Future meta-checks must prove one-to-many coverage in both directions for all P0 requirements/ACs, SPECs, DESs, tasks, required task verification obligations, failure/rejection classes, lifecycle integration, preservation, regression, and the observable MVP chain; detect deliberate omissions and stale evidence; and record only `PASS`, `FAIL`, or `NOT RUN`. This task produces evidence requirements only and must not issue Stage09 `PASS`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all scenario completeness, repeatability, negative-path, preservation/regression, traceability, omission-detection, and evidence-semantics checks `PASS`. Eligibility or a checkpoint cannot create Stage09 qualification. No checkpoint is currently achieved.
- **Out-of-scope:** Running Stage09, issuing `VERIFICATION_DECISION`, selecting a test framework, claiming implementation conformance, authorizing implementation, destructive testing, release, or deployment.

## 4. Whole-artifact dependency graph

The declared dependency graph is:

```text
TASK-001 -> TASK-002, TASK-005, TASK-008, TASK-010, TASK-012, TASK-013, TASK-016
TASK-002 -> TASK-003, TASK-004, TASK-005, TASK-006, TASK-009, TASK-010, TASK-011, TASK-012
TASK-003 -> TASK-015, TASK-017
TASK-004 -> TASK-015, TASK-017
TASK-005 -> TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012, TASK-013
TASK-006 -> TASK-009, TASK-011, TASK-013, TASK-015, TASK-017
TASK-007 -> TASK-015, TASK-017
TASK-008 -> TASK-009, TASK-012, TASK-014, TASK-016, TASK-017
TASK-009 -> TASK-015, TASK-017
TASK-010 -> TASK-007, TASK-011, TASK-012, TASK-015, TASK-017
TASK-011 -> TASK-012, TASK-015, TASK-017
TASK-012 -> TASK-015, TASK-017
TASK-013 -> TASK-014, TASK-016, TASK-017
TASK-014 -> TASK-015, TASK-016, TASK-017
TASK-015 -> TASK-016, TASK-017
TASK-016 -> TASK-017, TASK-018
TASK-017 -> TASK-018
TASK-018 -> none
```

Analysis of the actual dependency declarations found no cycle, self-dependency, nonexistent task reference, or missing dependency required by the stated task scopes. The former TASK-007 forward reference to TASK-010 is now decomposition-resolved; it remains a real prerequisite and is not implementation-satisfied. The graph preserves parallel work where dependencies permit it.

## 5. Whole-artifact traceability and P0 coverage

Stage06 extends the canonical chain only through `TASK`: `G -> FR/NFR/EC -> AC -> SPEC -> DES -> TASK`. It creates no `CODE` or `TEST_EVIDENCE` link. The approved requirement-to-SPEC and SPEC-to-DES mappings remain unchanged; the task layer extends them as follows:

| SPEC | Approved DES coverage | TASK coverage |
| --- | --- | --- |
| `SPEC-001` | `DES-001`, `DES-008`, `DES-011` | `TASK-001`, `TASK-002`, `TASK-009`, `TASK-017`, `TASK-018` |
| `SPEC-002` | `DES-002`, `DES-005` | `TASK-003`, `TASK-006`, `TASK-017`, `TASK-018` |
| `SPEC-003` | `DES-003` | `TASK-004`, `TASK-017`, `TASK-018` |
| `SPEC-004` | `DES-004`, `DES-005`, `DES-013` | `TASK-005`, `TASK-006`, `TASK-011`, `TASK-017`, `TASK-018` |
| `SPEC-005` | `DES-005` | `TASK-006`, `TASK-017`, `TASK-018` |
| `SPEC-006` | `DES-006`, `DES-007` | `TASK-007`, `TASK-012`, `TASK-017`, `TASK-018` |
| `SPEC-007` | `DES-007`, `DES-008` | `TASK-001`, `TASK-012`, `TASK-017`, `TASK-018` |
| `SPEC-008` | `DES-009`, `DES-015` | `TASK-008`, `TASK-014`, `TASK-017`, `TASK-018` |
| `SPEC-009` | `DES-006`, `DES-007`, `DES-011`, `DES-012` | `TASK-007`, `TASK-009`, `TASK-010`, `TASK-012`, `TASK-017`, `TASK-018` |
| `SPEC-010` | `DES-004`, `DES-013` | `TASK-005`, `TASK-011`, `TASK-017`, `TASK-018` |
| `SPEC-011` | `DES-014` | `TASK-013`, `TASK-017`, `TASK-018` |
| `SPEC-012` | `DES-015` | `TASK-014`, `TASK-017`, `TASK-018` |
| `SPEC-013` | `DES-016` | `TASK-015`, `TASK-017`, `TASK-018` |
| `SPEC-014` | `DES-010` | `TASK-016`, `TASK-017`, `TASK-018` |
| `SPEC-015` | `DES-011`, `DES-016` | `TASK-009`, `TASK-015`, `TASK-017`, `TASK-018` |
| `SPEC-016` | `DES-001`, `DES-004`, `DES-007`, `DES-009` | `TASK-002`, `TASK-005`, `TASK-008`, `TASK-012`, `TASK-017`, `TASK-018` |

Coverage analysis confirms:

- All 34 applicable P0 requirements are covered: `FR-01` through `FR-21`, `NFR-01` through `NFR-05`, and `EC-01` through `EC-08`.
- All applicable P0 acceptance criteria are covered: `AC-01` through `AC-21`, `AC-23` through `AC-27`, and `AC-29` through `AC-36`.
- `SPEC-001` through `SPEC-016` and `DES-001` through `DES-016` are covered.
- `TASK-001` through `TASK-018` each have upstream authority; orphan task count is zero.
- All 18 tasks contain the full task contract, remain `TODO`, and collectively cover the approved P0 implementation scope.
- The dependency graph closes with zero unresolved forward references and is a DAG.
- Approved Design reports no blocking Design TBD; this decomposition introduces no blocking task TBD and detects no cross-domain conflict.

Therefore whole-artifact P0 task coverage is complete for the approved current Stage06 authority. This coverage analysis and Stage06 approval do not constitute Stage07 evaluation, implementation authorization, implementation conformance, or Stage09 qualification.

## 6. Stage07-readiness support

This approved current authority supplies Stage07 with reviewable support for all of the following, without evaluating Stage07 or assigning it a gate result:

- bounded task purpose and allowed implementation scope;
- explicit actual dependencies and a closed acyclic graph;
- common and task-specific atomic checkpoint criteria;
- task-specific future verification requirements using truthful result semantics;
- preservation obligations and independently valid progress boundaries;
- explicit error/failure expectations and recovery routing;
- task-specific security/safety obligations where applicable;
- Stage08 scope boundaries, sealed-envelope requirements, and overrun stops; and
- complete upstream traceability through `TASK` for all P0 requirements, acceptance criteria, SPECs, and DESs.

Stage07 must independently inspect the approved artifact state, repository/Git readiness, testability, conflicts, security blockers, critical TBDs, traceability, and every other configured entry/check condition. Nothing in this section is a Stage07 `PASS` or `FAIL` decision.

## 7. Recovery and authority boundary

- This `tasks.md` is the approved prospective current `EXECUTION_DECOMPOSITION` authority; it is not historical Phase06 reconstruction.
- Tasks are prospective work contracts, not historical implementation facts. Existing implementation cannot make a task `DONE` or prove conformance.
- Stage06 does not inspect or evaluate code, implementation evidence, Recovery Gate eligibility/result, Stage09 conformance, Stage10, release, or deployment.
- Approval of this Stage06 authority does not create Stage07 `PASS` or authorize Stage08 implementation. Normal implementation remains unauthorized until Stage07 independently returns a valid `PASS` with implementation authorization.
- A Current Implementation Recovery Gate `PASS`, if later applicable under its narrow prerequisites, permits Stage09 entry only. It never creates retroactive Stage07 `PASS`, Stage08 authorization, implementation authorization, implementation conformance, task completion, test `PASS`, Stage09 `PASS`, Stage10 authority, or release authority.
- An implementation gap found after Stage09 returns to valid current authority and the normal `Stage07 -> Stage08` path.
- Programming language, framework, full module/package/file layout, database, serialization format, test framework, cloud platform, webhook architecture, LINE implementation, authentication/IAM product, and deployment topology remain deferred non-decisions.

## 8. Current Stage06 authority status

```text
CURRENT_EXECUTION_DECOMPOSITION_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

HISTORICAL_PHASE06_RECONSTRUCTION =
NOT_AUTHORIZED

PRODUCT_INTENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

PRODUCT_REQUIREMENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

TECHNICAL_CONTRACT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

IMPLEMENTATION_DECISION_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

AGENT_REPOSITORY_GOVERNANCE_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

TASK_COUNT =
18

P0_TASK_COVERAGE_COMPLETE =
YES

ORPHAN_TASK_COUNT =
0

DEPENDENCY_GRAPH_VALID =
YES

BLOCKING_EXECUTION_DECOMPOSITION_CONFLICT =
NO

BLOCKING_TASK_DECOMPOSITION_TBD =
NO

IMPLEMENTATION_AUTHORIZED =
NO

STAGE07_DECISION =
NOT_EVALUATED

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

EXECUTION_DECOMPOSITION_PROJECT_AUTHORITY_REVIEW_REQUIRED =
NO

NEXT_STEP =
CURRENT_PRE_IMPLEMENTATION_GATE_EVALUATION
```
