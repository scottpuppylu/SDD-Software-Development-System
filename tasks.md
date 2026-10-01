# SDD Software Development System - Current Execution Decomposition

## 1. Stage06 authority and scope

This artifact is the approved CURRENT prospective Stage06 `EXECUTION_DECOMPOSITION` authority. Stage06 owns task decomposition only: atomic work boundaries, dependency order, implementation scope, required outcomes, preservation and failure obligations, future verification, and checkpoint eligibility. It does not create or revise `PRODUCT_INTENT`, `PRODUCT_REQUIREMENT`, `TECHNICAL_CONTRACT`, `IMPLEMENTATION_DECISION`, or `AGENT_REPOSITORY_GOVERNANCE` authority.

This approved whole artifact contains `TASK-001` through `TASK-028`. `TASK-001` through `TASK-022` retain their prospective contracts and separately preserved implementation qualifications. `TASK-023` through `TASK-025` retain their pending bounded-remediation authority. `TASK-026` through `TASK-028` are the new bounded SPEC-019/DES-020 implementation contracts allocated by this re-decomposition. Approval of this artifact does not create Stage07 `PASS`, authorize Stage08 implementation, evaluate the Current Implementation Recovery Gate, create Stage09 `PASS`, or create Stage10, release, or deployment authority.

## 2. Approved upstream baseline references

- `docs/proposal.md`: CURRENT `PRODUCT_INTENT` authority, `APPROVED_CURRENT_AUTHORITY`; goals `G-01` through `G-05`.
- `docs/PRD.md`: CURRENT `PRODUCT_REQUIREMENT` authority, `APPROVED_CURRENT_AUTHORITY`; applicable P0 requirements and acceptance criteria.
- `docs/spec.md`: CURRENT `TECHNICAL_CONTRACT` authority, `APPROVED_CURRENT_AUTHORITY`; `SPEC-001` through `SPEC-019`.
- `docs/Design.md`: CURRENT `IMPLEMENTATION_DECISION` authority, `APPROVED_CURRENT_AUTHORITY`; `DES-001` through `DES-020`.
- `AGENTS.md`: CURRENT Stage05 `AGENT_REPOSITORY_GOVERNANCE` authority, `APPROVED_CURRENT_AUTHORITY`.
- `.sdd/system.yaml` and `.sdd/stages.yaml`: configured authority graph, Stage06 contract, lifecycle gates, traceability chain, and checkpoint rules.
- `.sdd/decisions/HD-A2-ARCH-IDENTIFIER-RESOLUTION-001.yaml` and `.sdd/decisions/HD-A2-PRD-NAMESPACE-CORRECTION-002.yaml`: approved durable authority establishing `ARCH-AC-01` through `ARCH-AC-09` and correcting the separate PRD namespace to `AC-01` through `AC-37` without semantic change.

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
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_governed_state.py`.
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
- **Allowed files:** `sdd_orchestrator/core.py`, `tests/test_orchestrator.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_orchestrator.py`.
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
- **Allowed files:** `sdd_orchestrator/system_controller.py`, `tests/test_orchestrator.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_orchestrator.py`.
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
- **Allowed files:** `sdd_orchestrator/pipeline.py`, `tests/test_stage02_product_convergence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_stage02_product_convergence.py`.
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
- **Allowed files:** `sdd_orchestrator/core.py`, `tests/test_orchestrator.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_orchestrator.py`.
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
- **Allowed files:** `sdd_orchestrator/decisions.py`, `tests/test_m7_decision_gateway.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m7_decision_gateway.py`.
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
- **Allowed files:** `sdd_orchestrator/providers.py`, `tests/test_m4_reasoning_pipeline.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m4_reasoning_pipeline.py`.
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
- **Allowed files:** `sdd_orchestrator/evidence_writer.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_v1118_safe_pause_and_evidence.py`.
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
- **Allowed files:** `sdd_orchestrator/result_serialization.py`, `tests/test_runner.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_runner.py`.
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
- **Allowed files:** `sdd_orchestrator/errors.py`, `sdd_orchestrator/runner.py`, `tests/test_m5_git_recovery.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m5_git_recovery.py`.
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
- **Allowed files:** `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/path_scope_policy.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_v1118_safe_pause_and_evidence.py`.
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
- **Allowed files:** `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/task_parser.py`, `sdd_orchestrator/verification_policy.py`, `tests/test_m6_codex_adapter.py`, `tests/test_v117_machine_task_contract.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m6_codex_adapter.py tests/test_v117_machine_task_contract.py`.
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
- **Allowed files:** `sdd_orchestrator/governed_state.py`, `tests/test_governed_state.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_governed_state.py`.
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
- **Allowed files:** `sdd_orchestrator/verification_execution.py`, `sdd_orchestrator/verification_runtime.py`, `tests/test_v1114_project_runtime.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_v1114_project_runtime.py`.
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
- **Allowed files:** `sdd_orchestrator/cli.py`, `sdd_orchestrator/system_controller.py`, `tests/test_orchestrator.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_orchestrator.py`.
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
- **Allowed files:** `sdd_orchestrator/evidence_writer.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_v1118_safe_pause_and_evidence.py`.
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
- **Allowed files:** `sdd_orchestrator/runner.py`, `sdd_orchestrator/system_controller.py`, `tests/test_runner.py`, `tests/test_orchestrator.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_runner.py tests/test_orchestrator.py`.
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
- **Authority trace:** Every approved P0 chain (`G-01` through `G-05` to `FR-01` through `FR-21`, `NFR-01` through `NFR-05`, and `EC-01` through `EC-08`, each paired with `AC-01` through `AC-21`, `AC-23` through `AC-27`, and `AC-29` through `AC-36`) reaches `SPEC-001` through `SPEC-017` and `DES-001` through `DES-017` according to the approved upstream trace tables and section 6 below, then extends to `TASK-018`.
- **Dependencies:** `TASK-016`, `TASK-017`, `TASK-019`.
- **Allowed files:** `tests/test_orchestrator.py`, `tests/test_runner.py`, `tests/test_m7_decision_gateway.py`, `tests/test_m4_reasoning_pipeline.py`, `tests/test_m5_git_recovery.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_orchestrator.py tests/test_runner.py tests/test_m7_decision_gateway.py tests/test_m4_reasoning_pipeline.py tests/test_m5_git_recovery.py tests/test_v1118_safe_pause_and_evidence.py`.
- **Allowed implementation scope:** Scenario definitions, fixtures/inputs conceptually required by approved contracts, expected governed outcomes, requirement/SPEC/DES/TASK coverage links, rejection and failure variants, preservation and regression obligations, evidence metadata expectations, repeatability requirements, and explicit gaps. Concrete test framework and file layout remain deferred.
- **Required behavior/outcome:** Define repeatable scenarios for all 34 applicable P0 requirements and acceptance criteria, all 17 SPEC and DES identifiers, every task's required behaviors and error paths, the end-to-end journey, gate/qualification non-substitution, session recovery, post-checkpoint evidence recovery, authority conflict, safety blocking, partial-progress preservation, modification impact, and regression coverage. Each scenario must state scope, criterion, expected `PASS`/`FAIL`/`NOT RUN` evidence semantics, and trace targets.
- **Preservation obligations:** Preserve approved acceptance criteria and contract meaning, negative/rejection paths, evidence gaps, current-version identity, existing valid scenario results, and separation between test evidence and authority/Stage09 qualification. Do not weaken coverage to obtain a passing summary.
- **Error/failure expectations:** Missing scenario coverage, ambiguous criterion, unrepeatable setup, broken trace, stale/irrelevant evidence, or unavailable execution remains an explicit gap/`NOT RUN` and withholds dependent completion. Partial scenario success cannot qualify the whole P0 scope.
- **Security/safety expectations:** Include safe negative scenarios for unauthorized, destructive/high-risk, security, authority-conflict, scope-overrun, secret/minimum-disclosure, and bypass behavior without performing an unapproved destructive or sensitive operation. Test data must minimize sensitive content.
- **Verification requirements:** Future meta-checks must prove one-to-many coverage in both directions for all P0 requirements/ACs, SPECs, DESs, tasks, required task verification obligations, failure/rejection classes, lifecycle integration, preservation, regression, and the observable MVP chain; detect deliberate omissions and stale evidence; and record only `PASS`, `FAIL`, or `NOT RUN`. This task produces evidence requirements only and must not issue Stage09 `PASS`.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions hold and all scenario completeness, repeatability, negative-path, preservation/regression, traceability, omission-detection, and evidence-semantics checks `PASS`. Eligibility or a checkpoint cannot create Stage09 qualification. No checkpoint is currently achieved.
- **Out-of-scope:** Running Stage09, issuing `VERIFICATION_DECISION`, selecting a test framework, claiming implementation conformance, authorizing implementation, destructive testing, release, or deployment.

## TASK-019 - Post-checkpoint implementation-evidence recovery

- **Status:** `TODO`
- **Purpose:** Implement the explicitly authorized, append-only post-checkpoint `IMPLEMENTATION_EVIDENCE` recovery capability for an unchanged immutable historical implementation checkpoint without weakening ordinary Stage08 evidence or lifecycle authority boundaries.
- **Authority trace:** `G-01, G-03, G-04, G-05 -> FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, NFR-01, NFR-03, NFR-04, EC-05, EC-06, EC-07 -> AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-23, AC-25, AC-26, AC-33, AC-34, AC-35 -> SPEC-017 -> DES-017 -> TASK-019`; applicable approved Stage05 recovery governance in `AGENTS.md` is an enforcement dependency, not a substituted trace authority.
- **Dependencies:** `TASK-001`, `TASK-005`, `TASK-008`, `TASK-010`, `TASK-011`, `TASK-012`.
- **Allowed files:** `sdd_orchestrator/evidence_writer.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/git_runtime.py`, `sdd_orchestrator/verification_execution.py`, `sdd_orchestrator/verification_runtime.py`, `tests/test_v1118_safe_pause_and_evidence.py`, `tests/test_m5_git_recovery.py`, `tests/test_m6_codex_adapter.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_v1118_safe_pause_and_evidence.py tests/test_m5_git_recovery.py tests/test_m6_codex_adapter.py`.
- **Allowed implementation scope:** The `SPEC-017`/`DES-017` recovery capability only: accept and seal an explicit current Project Authority recovery authorization; create stable attempt identity; bind exact task, applicable authority baseline and task-contract digest, repository/branch/baseline, full immutable historical checkpoint and tree/diff/content identity, exact task-authoritative verification command, execution/environment provenance, and pre/post no-implementation-mutation observations; validate checkpoint existence, governed-history reachability, parent/diff identity, changed-path task scope, and later-history compatibility; execute the exact command against an isolated exact checkpoint view; record truthful `PASS`, `FAIL`, or `NOT RUN`, exit/timeout/completeness facts, and bounded output references; atomically append a versioned recovery attestation; determine `QUALIFYING` versus stable non-qualifying reasons; detect identical duplicates, conflicts, replay, and split-brain state; retain linked failed attempts; and expose only a repository-backed eligibility reference for a later separately governed implementation-state reconciliation.
- **Required behavior/outcome:** A valid, unexpired, unconsumed, task/checkpoint/command/scope-bound recovery authorization can produce qualifying append-only evidence only after the historical checkpoint remains reachable and unchanged, its task-attributable content and paths match authority, fresh verification completes with exit zero and `PASS`, provenance is complete, no implementation mutation occurred, persistence succeeds, and no unresolved evidence conflict exists. Missing or mismatched bindings fail closed with a deterministic reason. An identical record/attempt retry is idempotently recognized without multiplying qualification. A persistence interruption preserves a safe linked attempt and permits only the authorization-compatible resume defined by Stage05/DES-017. A prior failed attempt remains immutable; a separately authorized later valid attempt may qualify without relabeling it. Qualification exposes reconciliation eligibility but performs no reconciliation.
- **Preservation obligations:** Preserve the exact historical checkpoint and governed Git history; ordinary Stage08 atomic evidence/checkpoint behavior; sealed execution-envelope enforcement; existing evidence-registry semantics outside the explicit recovery discriminator; existing checkpoint/failure/recovery behavior; exact task and command authority; every attempt and failure; append-only audit history; minimum privilege and bounded disclosure; fail-closed defaults; and separation among implementation evidence, state reconciliation, Stage07 authorization, Stage09 verification qualification, Stage10/release, and deployment.
- **Error/failure expectations:** Refuse missing, ambiguous, expired, consumed, withdrawn, overbroad, stale, or mismatched recovery authority; wrong task, repository, branch, baseline, authority, checkpoint, parent, tree/diff/content, path scope, or command; missing/unreachable/rewritten checkpoint; stale/unbound verification; nonzero/`FAIL`; unavailable execution/`NOT RUN`; timeout or incomplete capture; implementation mutation; arbitrary later evidence-only commit; unsupported schema; replay with changed content; conflicting evidence or overlapping incompatible authorizations; persistence/checkpoint failure; changed HEAD during the attempt; and split-brain evidence/state. Preserve facts, emit the stable non-qualifying reason, leave implementation state unchanged, and route to the applicable owner without normalization, substitution, fallback, cleanup, or history rewrite.
- **Security/safety expectations:** Require the Stage05 protected-operation authorization and safety interlock; use minimum privilege; permit host/elevated verification only when explicitly authorized and separately approved where runtime policy requires; reject secret/unnecessary-output capture and authorization enlargement; restrict writes to the sealed TASK-019 file envelope during implementation and to explicitly authorized recovery/audit artifacts during a future recovery operation; and prohibit amend, rebase, destructive reset, force/history rewrite, fabricated-equivalent checkpoint, arbitrary evidence injection, or self-authorization.
- **Verification requirements:** Positive checks must cover one valid authorized recovery against an exact reachable immutable checkpoint, fresh execution of the exact authoritative command, qualifying append-only evidence with complete provenance and deterministic task/checkpoint/content binding, identical duplicate/idempotent handling, persistence-interruption recovery, retained prior failure followed by a separately authorized valid attempt, and reconciliation eligibility after qualification without automatic state mutation. Negative checks must cover missing authority; wrong task; wrong, unreachable, rewritten, or content-mismatched checkpoint; out-of-scope checkpoint content; wrong authority baseline or command; stale/chat/Stage07-only result; nonzero/`FAIL`; timeout, incomplete capture, and `NOT RUN`; expired, consumed, withdrawn, overbroad, or mismatched authority; unauthorized implementation mutation; arbitrary evidence-only commit; replay with changed payload; conflicting evidence; overlapping incompatible authorization; persistence and evidence-checkpoint failure; changed HEAD/split-brain state; reconciliation blocked before qualification; ordinary Stage08 evidence and checkpoint-recovery regression; sealed-envelope non-weakening; and refusal to create Stage07, Stage09, Stage10/release, or deployment authority. Use only `PASS`, `FAIL`, or `NOT RUN` for executed checks.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions in section 3 hold; the declared TASK-019 command executes and all required positive, negative, persistence, retry, integrity, authorization, provenance, compatibility, and authority-separation checks `PASS`; `git diff --check` passes; the diff contains only TASK-019 allowed files; no authority artifact or implementation-state artifact changed; no historical checkpoint or governed history was rewritten; no T012 evidence recovery or state reconciliation occurred; and the checkpoint records only implementation and evidence for the recovery capability. Eligibility or checkpoint completion cannot imply T012 evidence recovery, implementation-state reconciliation, Stage07 `PASS`, Stage09 qualification, Stage10/release, or deployment. No checkpoint is currently achieved.
- **Out-of-scope:** Performing T012 or any other evidence recovery; modifying T012 implementation to reconstruct evidence; changing tests outside TASK-019 verification scope; reconciling `.sdd/state/implementation-state.yaml`; amending, rebasing, resetting, replacing, or rewriting a historical checkpoint; fabricating or backdating original evidence; automatically qualifying an arbitrary evidence-only commit; changing any authority artifact or task contract during Stage08; creating or rerunning Stage07; implementing T013 or another unrelated task; Stage09 qualification; Stage10/release; deployment; or issuing recovery, implementation, gate, verification, or release authority.

## TASK-020 - Multi-task implementation qualification state

- **Status:** `TODO`
- **Purpose:** Implement the `SPEC-018`/`DES-018` task-indexed implementation qualification state so ordinary and recovered task qualifications coexist truthfully without using singleton workflow summaries as qualification history.
- **Authority trace:** `G-01, G-02, G-03, G-04, G-05 -> FR-06, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, NFR-01, NFR-03, NFR-04, EC-05, EC-06, EC-07 -> AC-06, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-23, AC-25, AC-26, AC-33, AC-34, AC-35 -> SPEC-018 -> DES-018 -> TASK-020`.
- **Dependencies:** `TASK-001`, `TASK-008`, `TASK-012`, `TASK-019`.
- **Allowed files:** `sdd_orchestrator/git_runtime.py`, `sdd_orchestrator/evidence_writer.py`, `sdd_orchestrator/codex_adapter.py`, `tests/test_m5_git_recovery.py`, `tests/test_m6_codex_adapter.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m5_git_recovery.py tests/test_m6_codex_adapter.py tests/test_v1118_safe_pause_and_evidence.py`.
- **Allowed implementation scope:** Implement implementation-state schema `2.0` with a deterministic `task_qualifications` mapping supporting zero, one, or many canonical task records; exact task/status, immutable implementation-checkpoint, repository-backed qualifying-evidence path/kind/digest/commit, truthful `PASS`, and reconciliation identity/sequence/time/source metadata; strict key/value and schema validation; separation of qualification history from workflow cursors; deterministic ancestry-latest compatibility projections; one-way schema `1.0` migration; task-specific qualification lookup; ordinary Stage08 checkpoint integration; `DES-017` recovered-evidence reconciliation input; deterministic YAML serialization; atomic persistence, reload validation, and interruption recovery. Preserve evidence qualification as an input boundary rather than allowing the state writer to invent qualification.
- **Required behavior/outcome:** Load schema `2.0` directly and migrate schema `1.0` only during an authorized state mutation. Migration preserves valid non-qualification state and `current_task`/`next_task`, creates only repository-proven qualification records, and fails atomically on ambiguous or conflicting legacy facts. Migrate the current proven T019 singleton state in fixtures by validating its immutable implementation checkpoint and qualifying T019 recovery evidence, then support a later fixture reconciliation of the qualifying T012 recovery record as an additional sequence without replacing T019. Recompute `last_completed_task`/`last_verified_commit` only as DES-018 ancestry-latest projections, leaving them T019 in the T019-then-older-T012 case. Provide exact task lookup where a valid qualified record satisfies a dependency, an absent record is unsatisfied, and malformed, non-PASS, conflicting, or unverifiable state blocks rather than falling back to task numbering or singleton ordering. Reconciliation must be idempotent across repeats, caller timeout, and fresh-runner reload, must not select a next task, and must preserve every prior valid record.
- **Preservation obligations:** Preserve the current T019 qualification and all independently valid task records; `current_task`, `next_task`, and equivalent workflow cursors unless separately authorized; ordinary Stage08 sealed-envelope, evidence, checkpoint, and sequential qualification behavior; SPEC-017/DES-017 recovery admissibility; evidence registry semantics; historical Git identities; deterministic repository reconstruction; monotonic qualification facts; and Stage07/08/09/10 separation. Do not add deletion, revocation, downgrade, checkpoint replacement, primary-evidence replacement, or silent migration fallback.
- **Error/failure expectations:** Reject unsupported schema; duplicate YAML task keys; task key/value mismatch; missing or malformed required record fields; non-PASS qualification; absent/stale/changed evidence blob or digest; unreachable or mismatched evidence/checkpoint commit; fabricated qualification lacking admissible evidence; same task with a different checkpoint; incompatible or ordinary-versus-recovery evidence conflict; corrupt/reused reconciliation sequence or identity; ambiguous/incomplete legacy pair; stale compatibility projection that cannot be deterministically repaired; lost prior record; partial/temp/replace/reload persistence failure; and dependency lookup from singleton fields alone. Preserve the last valid state, identify the conflicting bindings, leave cursors and authority unchanged, and return a blocking diagnostic without silent overwrite or partial publication.
- **Security/safety expectations:** Use repository-relative bounded evidence paths, strict task/Git/digest formats, duplicate-key rejection, atomic same-directory persistence, and minimum required writes. Never accept path traversal, chat/filename/Stage07 prose as qualification, arbitrary evidence injection, implementation mutation during reconciliation, historical checkpoint rewrite, authority inference, or state changes outside the sealed TASK-020 scope.
- **Verification requirements:** Positive checks must cover empty/one/many schema `2.0` state; schema `1.0` to `2.0` migration with empty and cursor-bearing state; current T019 proof-backed migration; T019 plus later-added T012 with both records preserved and T019 compatibility projections unchanged; ordinary sequential qualification; recovered-evidence reconciliation through the existing qualifier; exact task-specific dependency lookup for T012 and T019; idempotent repeated reconciliation; retry after write interruption and caller timeout; fresh-runner reconstruction; null cursor preservation and no automatic next-task selection; stable task/key ordering; and byte-stable serialization. Negative checks must cover absent task record; malformed/non-PASS record; singleton-only false qualification; fabricated or missing evidence; conflicting checkpoint; conflicting or changed-digest evidence; duplicate/conflicting task entry; ambiguous/incomplete migration; stale unrepairable projection; partial/atomic-write and reload failure; loss of another task's qualification; unsupported deletion/revocation; and any attempted Stage07, Stage09, Stage10/release, or deployment upgrade. Regression checks must keep ordinary Stage08 checkpoint/evidence recovery and SPEC-017/DES-017 recovery qualification behavior green, using only `PASS`, `FAIL`, or `NOT RUN` outcomes.
- **Checkpoint eligibility:** Atomic-checkpoint eligible only when the common conditions in section 3 hold; the exact TASK-020 verification command fully `PASS`es; schema migration, T019 preservation, T019/T012 coexistence, task-specific dependency lookup, idempotency, conflict, atomic persistence/retry, fresh-runner, deterministic serialization, ordinary Stage08, and recovery-regression checks all pass; `git diff --check` passes; and the diff contains only TASK-020 allowed files. No live T012 reconciliation or evidence recovery may occur; no live implementation-state artifact, qualifying evidence, authority artifact, historical checkpoint, Stage07/09/10 artifact, or unrelated task may change. Completion means only that the schema `2.0` capability is implemented and verified; it does not qualify or reconcile T012, select a next task, create Stage07 `PASS`, or create Stage09/Stage10/release authority.
- **Out-of-scope:** Modifying live `.sdd/state/implementation-state.yaml`; performing T012 reconciliation; performing T012/T019 evidence recovery; modifying or fabricating qualifying evidence; implementing T013 or another task; changing SPEC-018, DES-018, AGENTS.md, or any authority artifact; changing Stage07 authority semantics; selecting or executing a next task; qualification deletion/revocation; historical Git rewrite; Stage09 qualification; Stage10/release; or deployment.

## 4. Stage04/05 Architecture Constitution impact evaluation

This evaluation used the current source tree, import graph, tests, qualified `TASK-001` through `TASK-020` evidence, the Stage04 and Stage05 run artifacts/checkpoints, both approved A2 decisions, and the normative security, cost/token, agent-adapter, and Human Approval contracts. A documentation statement alone was not treated as enforcement. Existing qualifications remain intact because no historical task contract or checkpoint was disproved.

### 4.1 Candidate disposition

| Impact candidate | Classification | Repository finding and governed disposition |
| --- | --- | --- |
| `CORE_AND_HARNESS_RESPONSIBILITY_IMPORT_REVIEW` | `ALREADY_IMPLEMENTED_AND_EVIDENCED` | `core.py` has no inward `sdd_orchestrator` imports and owns lifecycle/authority/policy coordination; provider construction remains in CLI bootstrap and capability behavior remains in modules. Qualified T002/T005/T017/T018 evidence plus current architecture-targeted tests support the boundary. |
| `PROVIDER_CROSS_IMPORT_REVIEW` | `ALREADY_IMPLEMENTED_AND_EVIDENCED` | Provider implementations remain behind `ReasoningProvider`/`ReasoningProviderBoundary`; Core has no provider import and `system_controller.py` receives the reasoning executor by injection. T007 evidence and `tests/test_m4_reasoning_pipeline.py` prove substitute-provider equivalence and non-authoritative provider output. |
| `IDENTITY_AUTHORIZATION_SECURITY_COST_SANDBOX_TOOL_PREFLIGHT` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Fresh repository identity, authority, sealed Stage08 scope, sandbox, timeout, path safety, and verification-command policy exist, but there is no single mandatory envelope covering authentication, data class, security policy, budget, network/secret/deployment limits, exact tool call, audit output, and approval binding before every material dispatch. `TASK-021` through `TASK-023` close only those missing dimensions. |
| `CAPABILITY_CLASS_ENFORCEMENT` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | The reasoning boundary has an allowlisted capability vocabulary and denies unknown/empty capabilities; Stage08 write requires a sealed envelope. It does not implement the complete Stage05 capability-class grant schema or default-deny matching for every tool, network, credential, Git, external-side-effect, deployment, and protected-production capability. `TASK-021` owns the delta. |
| `COST_TOKEN_NETWORK_DEPLOYMENT_SECRET_LIMITS` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Runtime timeout, file/Git scope, token provenance measurement, redaction, and release/deployment authority separation exist. Pre-dispatch hard budgets, call/resource counters, network destination grants, credential/secret grants, and explicit deployment-action limits are absent. `TASK-022` and `TASK-023` own the delta. |
| `EDGE_SPOKE_SKILL_MODULE_REPLACEABILITY` | `ALREADY_IMPLEMENTED_AND_EVIDENCED` | Provider, Git, decision, evidence, verification, context, telemetry, and execution responsibilities are isolated modules with stable call contracts and focused tests. T001, T006-T010, T013-T017 and current provider-boundary tests evidence independent substitution/failure containment; no inward provider dependency was found. |
| `tests/test_m7_decision_gateway.py` | `TEST_FIXTURE_GAP` | The fixture copies the repository `.sdd` tree and then asserts `DecisionGateway.list()` is empty. The current run produced 126 passes and one failure only because the two legitimate approved A2 decisions are present. Gateway persistence, collision, scope, history, and authority behavior remained green. `TASK-025` owns fixture isolation only. |
| `IDENTITY_AUTHENTICATION_PROJECT_ENVIRONMENT_BINDING` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Actor, command, repository, branch, baseline, task, attempt, and provider identities are partially represented. Authentication method/non-secret credential reference and actor-project-environment binding are not uniformly required or validated before dispatch. `TASK-021` owns the delta. |
| `SENSITIVE_DATA_CLASSIFICATION_ENCRYPTION_AND_REDACTION` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Key/pattern-based output redaction and minimum-disclosure references exist and are tested. No pre-transmission sensitivity classification or enforceable retention/encryption/environment decision is bound to dispatch. `TASK-022` owns the delta while preserving current redaction. |
| `PROMPT_INJECTION_AND_MALICIOUS_INSTRUCTION_CONTAINMENT` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Authority references, output schemas, output-path checks, and forbidden authority claims constrain provider results, but untrusted embedded instructions are not classified or blocked by a dedicated pre-side-effect policy. `TASK-022` owns the delta. |
| `TOOL_ALLOW_DENY_ARGUMENT_TARGET_AND_SIDE_EFFECT_VALIDATION` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Verification commands are parsed without a shell and allowlisted; Stage08 paths and post-run diffs are checked. General agent/tool calls do not yet bind exact tool, arguments, target, approval class, and expected side effects to the current envelope. `TASK-021` owns the delta. |
| `SANDBOX_FILESYSTEM_NETWORK_CREDENTIAL_BOUNDARY_ENFORCEMENT` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Reasoning uses read-only sandbox configuration; Stage08 uses workspace-write plus exact path/diff enforcement. Network destinations, credential classes/references, environment binding, and sandbox-class compatibility are not enforced by one policy boundary. `TASK-022` owns the delta. |
| `COST_TOKEN_TOOL_CALL_RUNTIME_RESOURCE_LIMIT_ENFORCEMENT` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Timeouts, payload bounds, provider usage provenance, and measurement exist, but hard/soft budget state, provider/tool-call counts, actual-versus-estimated token limits, process/resource limits, retry accounting, and exhaustion stops are incomplete. `TASK-023` owns the delta. |
| `PROVIDER_CHANGE_FALLBACK_AND_DEFAULT_PROMOTION_CONFORMANCE_GATE` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Providers are replaceable and failures expose alternate-provider routes, but fallback is not executed through a capability/security/budget conformance gate and default promotion has no evidence-bound decision. `TASK-024` owns the delta. |
| `AUDIT_EVIDENCE_AND_HUMAN_APPROVAL_BINDING_ENFORCEMENT` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK` | Durable Human Decisions, safety authorization, failure records, Stage run artifacts, Stage08 evidence, and qualification separation are implemented and qualified. Material dispatch audit records do not uniformly bind the complete control envelope, actual side effects/limits, approval class/reference, and invalidation conditions. `TASK-021` owns this incremental binding gap. |

### 4.2 Architecture Constitution impact

| Criterion | Stage06 impact result |
| --- | --- |
| `ARCH-AC-01` | `ALREADY_IMPLEMENTED_AND_EVIDENCED`: lifecycle/authority/policy coordination remains in Core; complex provider, context, Git, decision, evidence, verification, recovery, and telemetry behavior remains at Edge/Spoke/Module boundaries. |
| `ARCH-AC-02` | `ALREADY_IMPLEMENTED_AND_EVIDENCED`: CLI/controller/runner provide bootstrap, injection, dispatch, and lifecycle integration while cohesive capability modules remain independently tested. Provider selection branching in CLI is adapter binding, not provider-specific lifecycle or domain behavior. |
| `ARCH-AC-03` | `ALREADY_IMPLEMENTED_AND_EVIDENCED`: no provider dependency enters Core; substitute-provider tests preserve behavior and provider outputs remain proposed/non-authoritative. |
| `ARCH-AC-04` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK`: existing preflight is substantial but lacks all mandatory identity/authentication/data/security/budget/network/secret/tool/audit fields. `TASK-021` through `TASK-023`. |
| `ARCH-AC-05` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK`: reasoning and verification subsets are default-deny, but the complete capability classes and exact tool/network/credential/deployment grants are absent. `TASK-021` and `TASK-022`. |
| `ARCH-AC-06` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK`: timeout, filesystem, Git, and some provider bounds exist; cost/token/call/resource/network/deployment/secret hard-limit enforcement is incomplete. `TASK-022` and `TASK-023`. |
| `ARCH-AC-07` | `DOCUMENTATION_ONLY_GAP`: Stage04 and Stage05 now define the architecture requirements and this Stage06 maps every proven gap to bounded tasks. A fresh Stage07 must independently evaluate `ARCH-AC-01` through `ARCH-AC-08` and cannot issue `PASS` for missing/unverifiable coverage; Stage06 does not execute or pre-decide that gate. |
| `ARCH-AC-08` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK`: governance coverage is complete, while the enforcement deltas are bounded by `TASK-021` through `TASK-023`. |
| `ARCH-AC-09` | `IMPLEMENTATION_GAP_REQUIRING_BOUNDED_TASK`: adapter replaceability is evidenced, but provider change/fallback/default-promotion conformance is not enforced. `TASK-024`. |

No prior task is reopened. The original remediation tasks extend current authority without altering `TASK-001` through `TASK-020`, their checkpoints, qualification records, or evidence. The original identifier allocation continued the repository's sequential `TASK-NNN` convention from the then-highest identifier `TASK-020`.

### 4.3 SPEC-019 / DES-020 re-decomposition and ownership reconciliation

Stage03 `SPEC-019`, Stage04 `DES-020`, and the Stage05 affected-scope revalidation add three implementation-gap families without changing the already-qualified facts for `TASK-001` through `TASK-022`: (A) a provider-neutral bounded coding-worker Work Package plus local verification levels; (B) durable Stage08 phase state, SAFE_PAUSE, and precise resume; and (C) observational phase-consumption telemetry. The smallest independently checkpointable decomposition is three ordered tasks because A establishes the provider and verification contract consumed by B, while C needs the stable attempt/phase identities produced by B and has a separate telemetry compatibility risk surface.

The new identifier allocation continues the repository-authoritative sequential `TASK-NNN` convention from the existing highest identifier `TASK-025`, allocating `TASK-026`, `TASK-027`, and `TASK-028`. These identifiers are allocated only by this Stage06 authority. They do not imply execution order outside the declared dependency graph, implementation qualification, Stage07 `PASS`, or Stage08 authorization.

#### Existing cost/resource task ownership slicing

The existing `TASK-023` contract remains authoritative and unchanged. It owns resource/budget/exhaustion **enforcement**: budget lookup and reservation, provider/tool/retry counters as enforceable budget state, hard/soft limits, cumulative accounting, runtime/process/resource constraints, and exhaustion stop/route. `TASK-028` owns only observational phase measurement needed to explain Stage08 consumption and efficiency. It neither decides budget state nor stops/allows dispatch.

| Concern | Ownership classification | Current authority disposition |
| --- | --- | --- |
| `codex_invocation_count` and `remediation_count` as non-authoritative phase observations | `MOVES_TO_NEW_STAGE8_OPTIMIZATION_TASK` | `TASK-028` records attributable counts; no threshold, reservation, or dispatch decision is permitted. |
| Provider/tool/retry counters used for budgets, limits, cumulative accounting, or exhaustion | `REMAINS_TASK023` | `TASK-023` remains the sole enforcement owner. It may consume independently trustworthy observations but must establish its own governed accounting semantics. |
| Provider-active, local/FAST/TARGET/FULL verification durations and effectiveness ratio | `MOVES_TO_NEW_STAGE8_OPTIMIZATION_TASK` | `TASK-028` measures phase duration using the existing telemetry framework and cannot create lifecycle authority. |
| Runtime duration/resource limits and timeout/exhaustion stop/route | `REMAINS_TASK023` | `TASK-023` retains policy evaluation, hard/soft limit enforcement, and exhaustion behavior. |
| Existing telemetry models/measurement primitives | `SHARED_DEPENDENCY_WITH_NON_OVERLAPPING_AUTHORITY` | `TASK-028` adds versioned observational phase events; `TASK-023` adds enforcement/accounting behavior. Fresh baselines and exact task scopes prevent silent authority merging. |
| Unavailable/actual/estimated/context-size usage truth | `SHARED_DEPENDENCY_WITH_NON_OVERLAPPING_AUTHORITY` | Both tasks preserve the Cost/Token truth classes; `TASK-028` reports only attributable observations, while `TASK-023` governs budget policy and enforcement. |
| Budget state, reservation, approved increase, deployment limit, or exhaustion classification | `REMAINS_TASK023` | No new SPEC-019 task may implement or infer these controls. |

There is no `TASK-023` authority amendment: its objective, dependencies, files, acceptance obligations, and historical identity remain unchanged. File overlap in `codex_adapter.py`, `codex_cli.py`, and telemetry modules is an explicit scheduling/rebase concern, not duplicated semantic authority. Stage07 must bind each task to its own fresh baseline and sealed scope. `TASK-024` and `TASK-025` are unaffected and retain their existing intent, dependencies, files, and verification commands.

## TASK-021 - Unified pre-dispatch governance envelope and capability enforcement

- **Status:** `TODO`
- **Purpose:** Enforce one current, fail-closed control envelope before material agent, provider, tool, Git-write, or protected dispatch, while preserving existing sealed Stage08 and safety behavior.
- **Authority trace:** `ARCH-AC-04, ARCH-AC-05, ARCH-AC-07, ARCH-AC-08 -> DES-019 -> TASK-021`; supporting current contracts are `AGENTS.md` sections 4, 7, 11, and 14, `SDD_AGENT_ADAPTER_CONTRACT.md`, `SDD_REMOTE_SANDBOX_SECURITY_CONTRACT.md`, and `SDD_HUMAN_APPROVAL_BOUNDARY_MATRIX.md`.
- **Dependencies:** `TASK-003`, `TASK-005`, `TASK-006`, `TASK-007`, `TASK-008`, `TASK-010`, `TASK-011`, `TASK-012`, `TASK-017`.
- **Allowed files:** `sdd_orchestrator/governance_envelope.py`, `sdd_orchestrator/providers.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/system_controller.py`, `sdd_orchestrator/runner.py`, `sdd_orchestrator/evidence_writer.py`, `tests/test_governance_envelope.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_governance_envelope.py tests/test_m4_reasoning_pipeline.py tests/test_m6_codex_adapter.py tests/test_v1118_safe_pause_and_evidence.py`.
- **Allowed implementation scope:** A provider-neutral immutable control-envelope model and validator; current identity/authentication-reference/project/environment binding; explicit capability classes and grants; exact action/tool/arguments/target/scope/side-effect matching; authorization, Stage07, Human Decision/approval, audit/evidence, and expiry bindings; integration immediately before existing reasoning, Stage08, lifecycle-tool, and Git-write dispatch boundaries; and post-dispatch actual-scope/effect reconciliation. Do not implement provider-specific domain behavior or change upstream authority semantics.
- **Required behavior/outcome:** Every applicable dispatch fails closed before side effect when a required identity, authentication reference, authority/gate/approval, capability, exact call target, scope, expiry, policy, limit reference, or evidence obligation is missing, stale, ambiguous, conflicting, unverified, or out of scope. Unlisted capability classes/actions/tools/arguments/paths/Git actions/external effects are denied. Existing sealed Stage08 envelopes remain necessary and are referenced, not weakened or replaced. Material audit/evidence records bind the non-secret envelope identity, outcome, observed effects, failure route, and exact current approval class/reference.
- **Preservation obligations:** Preserve provider independence, current lifecycle/authority/Human Decision semantics, existing Stage08 evidence/checkpoint atomicity, qualified task records, minimum disclosure, and all historical A2 decisions. Do not infer authentication or authority from credential possession, provider capability, prior success, or silence.
- **Error/failure expectations:** Reject malformed, missing, stale, expired, reused, overbroad, mismatched, or unsupported envelopes/grants before dispatch; contain post-dispatch scope/effect mismatch, preserve valid work, record a bounded failure, and route to the exact authority/security/Human Decision owner without fallback or permission enlargement.
- **Security/safety expectations:** Default deny and least capability are mandatory. Approval binds exact action, target, scope, baseline, environment, risk, provider capability, and validity; security-sensitive values remain references and are never persisted.
- **Verification requirements:** Prove positive least-capability dispatch and negative cases for every absent/unknown class, actor/project/environment mismatch, unauthenticated or stale reference, missing Stage07/approval binding, tool/argument/target mismatch, scope or side-effect overrun, expired grant, reused approval after material change, provider-output authority claim, missing audit obligation, and unchanged existing Stage08/safety behavior. Use only `PASS`, `FAIL`, or `NOT RUN` outcomes.
- **Checkpoint eligibility:** Eligible only when the declared command passes, the diff is limited to allowed files, every relevant dispatch path uses the non-bypassable validator, all negative cases prove no side effect, existing Stage08 evidence/checkpoint tests remain green, and no authority/state/evidence artifact is rewritten.
- **Out-of-scope:** Implementing sensitive-data/prompt/network/credential policy details owned by `TASK-022`; budget/resource enforcement owned by `TASK-023`; provider promotion/fallback owned by `TASK-024`; changing authority documents; running Stage07/08/09/10; deployment; or historical qualification mutation.

## TASK-022 - Security, data, prompt-injection, sandbox, network, and credential containment

- **Status:** `TODO`
- **Purpose:** Supply the security-policy decisions consumed by the unified envelope for data sensitivity, malicious instructions, sandbox class, filesystem, network, credential, and secret access.
- **Authority trace:** `ARCH-AC-04, ARCH-AC-05, ARCH-AC-06, ARCH-AC-08 -> DES-013, DES-019 -> TASK-022`; supporting current contracts are `AGENTS.md` sections 6, 11, and 14 and `SDD_REMOTE_SANDBOX_SECURITY_CONTRACT.md`.
- **Dependencies:** `TASK-011`, `TASK-021`.
- **Allowed files:** `sdd_orchestrator/security_policy.py`, `sdd_orchestrator/governance_envelope.py`, `sdd_orchestrator/providers.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/codex_cli.py`, `sdd_orchestrator/evidence_writer.py`, `sdd_orchestrator/result_serialization.py`, `tests/test_security_policy.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_security_policy.py tests/test_m4_reasoning_pipeline.py tests/test_m6_codex_adapter.py tests/test_v1118_safe_pause_and_evidence.py`.
- **Allowed implementation scope:** Data-class and handling-policy references; pre-transmission classification decision; required redaction/retention/encryption/environment compatibility; untrusted-instruction and malicious/escalating tool-call findings; sandbox-class compatibility; exact filesystem, network destination/purpose, credential-class/reference, secret-access, process, and production-boundary grants; stop-before-side-effect enforcement; and minimum-disclosure security audit integration. Preserve existing redaction and path-scope components as compatible subcontrols.
- **Required behavior/outcome:** Unknown or prohibited data class, absent required encryption/retention rule, suspected prompt injection or confused-deputy escalation, sandbox mismatch, unlisted path/endpoint/purpose/credential/secret/process, cross-project/session reuse, or proposed production credential in a general Stage08 sandbox denies dispatch. The result identifies only safe categories/references, preserves prior state, and routes to security, authority owner, or Human Decision. Allowed cases expose no secret value and post-dispatch checks catch actual boundary overrun.
- **Preservation obligations:** Preserve current safety preflight, sealed Stage08 paths, read-only reasoning default, atomic evidence, provider-independent contracts, and existing minimum-disclosure output. Do not add an authentication/IAM, encryption, secrets, cloud, or network product choice.
- **Error/failure expectations:** Fail closed on missing classification, policy, environment, endpoint, credential reference, sandbox compatibility, or safe audit path; never probe alternate encodings/tools/providers/endpoints or weaken policy to continue.
- **Security/safety expectations:** Secret values are never accepted as ordinary governance payloads or persisted. Encryption/retention requirements are validated as policy/evidence bindings; the task does not implement a storage or cryptography product.
- **Verification requirements:** Cover all sandbox classes and environment bindings; default-denied network/credential/secret access; exact allowlisted destination/purpose; path traversal and post-run diff overrun; prompt-injection and malicious tool escalation before side effect; sensitive-data classification/redaction/encryption-policy cases; cross-project/provider-session isolation; suspected exposure handling; and unchanged existing safety/redaction behavior.
- **Checkpoint eligibility:** Eligible only when every negative test proves no protected dispatch or secret persistence, positive grants are exact and attributable, declared regression tests pass, and only allowed files change.
- **Out-of-scope:** Selecting security products, live network/secret/production access, budget enforcement, provider promotion, authority changes, test-fixture repair, or Stage07/08/09/10 execution.

## TASK-023 - Cost, token, call, runtime, resource, and deployment-limit enforcement

- **Status:** `TODO`
- **Purpose:** Enforce explicit pre-dispatch and cumulative resource limits without weakening governance, truncating required authority/evidence, or misrepresenting measurement truth.
- **Authority trace:** `ARCH-AC-04, ARCH-AC-05, ARCH-AC-06, ARCH-AC-08 -> DES-019 -> TASK-023`; supporting current contracts are `AGENTS.md` sections 6, 11, and 14, `SDD_COST_TOKEN_GOVERNANCE_CONTRACT.md`, and `SDD_REMOTE_SANDBOX_SECURITY_CONTRACT.md`.
- **Dependencies:** `TASK-021`, `TASK-022`.
- **Allowed files:** `sdd_orchestrator/resource_policy.py`, `sdd_orchestrator/governance_envelope.py`, `sdd_orchestrator/providers.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/codex_cli.py`, `sdd_orchestrator/context_evaluation.py`, `sdd_orchestrator/telemetry/measurement.py`, `sdd_orchestrator/telemetry/models.py`, `tests/test_resource_policy.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_resource_policy.py tests/test_m42_evaluation_metrics.py tests/test_telemetry_measurement.py tests/test_telemetry_models.py tests/test_telemetry_stage08_phase.py tests/test_stage08_phase_resume.py tests/test_m6_codex_adapter.py`.
- **Allowed implementation scope:** Provider/model/runtime identity; applicable budget lookup and state; trustworthy actual versus estimated/unavailable measurement; provider/tool-call and retry counters; actual/estimated token, cost, duration, process/resource, filesystem, network, Git, deployment, and secret-access hard/soft bounds; pre-dispatch reservation/check; post-dispatch accounting; deterministic exhaustion stop/route; and approval binding for budget/deployment changes. Reuse existing timeout and telemetry primitives without making telemetry lifecycle authority.
- **Required behavior/outcome:** Required hard limits must be known and sufficient before dispatch; exhausted/unknown-when-required budgets stop new calls without truncating mandatory context/evidence. Actual usage is accepted only from attributable structured provider/runtime evidence; Codex CLI tokens remain unavailable, not zero or estimated actual. Retries consume their declared budget. Deployment remains a separately granted capability even after Stage09/10 and cannot proceed from credential possession alone.
- **Preservation obligations:** Preserve measurement truth classes, context reconstruction integrity, provider-independent routing, Stage09/10 separation, valid completed work, and current timeouts. Cost optimization cannot downgrade security, authority, evidence, provider conformance, or required context.
- **Error/failure expectations:** Missing policy, invalid counters, insufficient reservation, hard-limit exhaustion, incomplete actual usage, accounting conflict, or deployment grant mismatch stops the affected dispatch and records truthful bounded state plus valid next routes; no silent continuation or retroactive usage fabrication.
- **Security/safety expectations:** Cost ledgers contain no prompts, secrets, or raw credentials. Material budget increases and protected deployment actions require their current approval class/reference.
- **Verification requirements:** Cover actual/estimated/context-size/unavailable truth classes; pre-dispatch hard and soft limits; cumulative provider/tool/retry counts; token/cost/runtime/resource exhaustion; no mid-context truncation; Codex unavailable token semantics; safe conformant cheaper route versus prohibited downgrade; approval-bound budget increase; explicit deployment denial/grant; atomic accounting failure; TASK-028 observational telemetry reuse without duplicate phase measurement; no double accounting across SAFE_PAUSE, resume, remediation, reconstructed phase history, reused verification, or persistence retry; TASK-027 resume/provenance compatibility; and telemetry non-authority regression.
- **Checkpoint eligibility:** Eligible only when declared tests pass, all metered dispatch paths consume the policy, hard-limit negative cases cause no new dispatch, accounting is deterministic and attributable, regression tests remain green, and only allowed files change.
- **Out-of-scope:** Billing-provider integration, cloud/deployment execution, altering budgets as authority, provider-default selection, authority document changes, or Stage07/08/09/10 execution.

## TASK-024 - Provider change, fallback, and default-promotion conformance gate

- **Status:** `TODO`
- **Purpose:** Prevent provider/model/adapter addition, switch, fallback, upgrade, or default promotion unless current evidence proves Architecture Constitution and required capability conformance.
- **Authority trace:** `ARCH-AC-03, ARCH-AC-07, ARCH-AC-09 -> DES-006, DES-019 -> TASK-024`; supporting current contracts are `AGENTS.md` section 14, `SDD_AGENT_ADAPTER_CONTRACT.md`, `SDD_COST_TOKEN_GOVERNANCE_CONTRACT.md`, and `SDD_HUMAN_APPROVAL_BOUNDARY_MATRIX.md`.
- **Dependencies:** `TASK-007`, `TASK-021`, `TASK-022`, `TASK-023`.
- **Allowed files:** `sdd_orchestrator/provider_conformance.py`, `sdd_orchestrator/providers.py`, `sdd_orchestrator/cli.py`, `sdd_orchestrator/runner.py`, `sdd_orchestrator/system_controller.py`, `tests/test_provider_conformance.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_provider_conformance.py tests/test_m4_reasoning_pipeline.py tests/test_m41_atomic_executor.py tests/test_v114_provider_schema.py`.
- **Allowed implementation scope:** Versioned provider/adapter capability manifests; common conformance evidence; required architecture, lifecycle, authority, sandbox, security, budget, capability, evidence, and approval checks; current default-selection identity; explicit change/fallback/promotion decision; and fail-closed integration at provider construction/routing. Existing alternate-provider failure routes remain recommendations until this gate passes.
- **Required behavior/outcome:** A provider is eligible only when current evidence covers every mandatory capability and control for the requested role. Adding, changing, falling back, or promoting never silently weakens a control. Newer, stronger, cheaper, available, or benchmark-leading status alone is insufficient. A conformant fallback preserves the same request/envelope and records the change; missing/stale/failed evidence blocks with a safe route and no automatic provider dispatch.
- **Preservation obligations:** Preserve provider-neutral Core/Harness semantics, existing provider-output non-authority, exact context and task envelopes, evidence truth, Human Decision classes, and current OpenAI/Codex adapters until a separately authorized change qualifies.
- **Error/failure expectations:** Reject absent/ambiguous/stale manifests or evidence; unsupported capability; changed auth/sandbox/security/budget environment; weaker fallback; default mutation without decision; and mismatch between declared and observed adapter identity. Preserve the prior valid default and record affected scope.
- **Security/safety expectations:** Conformance metadata contains references, not credentials. Provider availability or authentication does not create authority or justify policy downgrade.
- **Verification requirements:** Use substitute providers to prove equal lifecycle/authority semantics; cover conformant and non-conformant additions, upgrades, switches, fallbacks, default promotions, stale evidence, changed capability/environment, cost-only selection, prior-default preservation, and no provider invocation before gate success.
- **Checkpoint eligibility:** Eligible only when the common conformance suite and declared regressions pass, every provider construction/routing entry uses the gate, negative cases make no provider call/default change, and only allowed files change.
- **Out-of-scope:** Adding a new real provider, changing model defaults, external benchmarks, live API calls, product/technical/design changes, deployment, or Stage07/08/09/10 execution.

## TASK-025 - Decision Gateway fixture isolation from durable repository decisions

- **Status:** `TODO`
- **Purpose:** Make Decision Gateway unit-test initial state explicit so legitimate repository-backed A2 decisions do not violate a test-only empty-store assumption.
- **Authority trace:** `ARCH-AC-07 -> DES-005, DES-019 -> TASK-025`; this is a test-maintenance task and does not alter decision authority or production behavior.
- **Dependencies:** `TASK-006`.
- **Allowed files:** `tests/test_m7_decision_gateway.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m7_decision_gateway.py`.
- **Allowed implementation scope:** Fixture setup/isolation and assertions only. Create an explicit empty decision store for tests that require one while retaining separate coverage that existing approved durable decisions load truthfully. Do not change `DecisionGateway` production code or either A2 decision.
- **Required behavior/outcome:** The independent-scope rejection test proves no new decision was persisted relative to its controlled initial state, without assuming the source repository has no durable decisions. All Decision Gateway tests pass with both current A2 records present in the source repository.
- **Preservation obligations:** Preserve production gateway semantics, durable decision history/content, collision and path-safety checks, scoped blocking, append-only events, owner routing, and all existing test intent unrelated to fixture state.
- **Error/failure expectations:** The test must still fail for an unexpected newly persisted decision, mutation of a copied A2 record, or production behavior regression; fixture cleanup must remain isolated to its temporary directory.
- **Security/safety expectations:** No repository decision may be deleted, rewritten, masked, or treated as non-authoritative to obtain a green test.
- **Verification requirements:** Run the exact declared test file and confirm every test passes with the repository containing both A2 records; inspect the diff to prove test-only scope.
- **Checkpoint eligibility:** Eligible only when the declared command passes, only `tests/test_m7_decision_gateway.py` changes, no production/authority/state/evidence file changes, and the fix isolates fixture state rather than weakening an assertion.
- **Out-of-scope:** Production Decision Gateway changes, decision-store migration, A2 mutation/removal, broader test cleanup, implementation qualification changes, or Stage07/08/09/10 execution.

## TASK-026 - Structured coding-worker Work Package and local verification levels

- **Status:** `TODO`
- **Purpose / objective:** Introduce the provider-neutral structured Codex Work Package and controller-owned FAST/TARGET/FULL verification plan so Codex remains a bounded patch worker and deterministic verification runs locally without an active provider session.
- **Authority trace:** `SPEC-019 -> DES-020 -> TASK-026`; applicable Architecture Constitution mappings are `ARCH-AC-01`, `ARCH-AC-02`, `ARCH-AC-03`, `ARCH-AC-04`, `ARCH-AC-05`, `ARCH-AC-06`, `ARCH-AC-07`, and `ARCH-AC-08`. Supporting governance is `AGENTS.md` sections 3 through 9 and 14 plus the Agent Adapter, Remote Sandbox Security, Cost/Token, and Human Approval contracts.
- **Dependencies:** `TASK-007`, `TASK-011`, `TASK-012`, `TASK-014`, `TASK-017`, `TASK-021`, `TASK-022`.
- **Allowed files:** `sdd_orchestrator/stage08_work_package.py`, `sdd_orchestrator/task_parser.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/verification_policy.py`, `sdd_orchestrator/verification_execution.py`, `sdd_orchestrator/verification_runtime.py`, `tests/test_stage08_work_package.py`, `tests/test_stage08_verification_levels.py`, `tests/test_m6_codex_adapter.py`, `tests/test_v1113_codex_stdin_prompt.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_stage08_work_package.py tests/test_stage08_verification_levels.py tests/test_m6_codex_adapter.py tests/test_v1113_codex_stdin_prompt.py tests/test_v1118_safe_pause_and_evidence.py`.
- **Allowed implementation scope:** A versioned immutable provider-neutral Work Package model; canonical content binding; `INITIAL_PATCH_PACKAGE` and minimum-disclosure `REMEDIATION_PACKAGE`; authoritative field suppliers; structured worker result identity; worker-only prompt restrictions; versioned FAST/TARGET/FULL command grouping; local command planning/execution; backward-compatible mapping of every legacy Verification Command to TARGET unless stronger authority exists; and explicit authority validation before Stage08 FULL execution.
- **Required behavior/outcome:** Every provider invocation receives all SPEC-019 bindings and only the relevant redacted context. Codex may analyze and edit authorized files or return a bounded structured result, but cannot commit, finalize evidence/state, own deterministic verification, or inspect unrelated scope. FAST and TARGET run locally; required task commands are never skipped; FULL does not run implicitly and never substitutes for Stage09. A failed applicable check creates only a minimal remediation package.
- **Acceptance criteria:** `CODEX_WORKER_ONLY_BOUNDARY`; `MINIMAL_STRUCTURED_WORK_PACKAGE`; `LOCAL_VERIFICATION_INDEPENDENT_OF_CODEX_SESSION`; `FAST_TARGET_FULL_POLICY_ENFORCED`; `NO_IMPLICIT_FULL_REGRESSION`; `TASK_CONTRACT_REQUIRED_COMMANDS_NEVER_SKIPPED`; `MINIMAL_FAILURE_PACKAGE`; `NO_FULL_CONTEXT_REBUILD_ON_REMEDIATION`; `TASK021_AND_TASK022_GOVERNANCE_PRESERVED`; `STAGE09_FULL_REGRESSION_UNCHANGED`; `LEGACY_STAGE08_TASKS_REMAIN_COMPATIBLE`.
- **Preservation obligations:** Preserve Stage07 authorization and sealed-envelope semantics, exact allowed-file enforcement, TASK-021 pre-dispatch governance, TASK-022 classification/redaction/injection/sandbox controls, existing verification-command behavior, historical evidence, Stage09 full regression, Stage10 finalization, provider independence, and qualified TASK-001 through TASK-022 facts.
- **Error/failure expectations:** Missing/stale/ambiguous package bindings, unsafe or overbroad context, unauthorized file/tool/capability, absent legacy command, unapproved FULL request, malformed worker result, or local-verification policy/runtime mismatch fails closed before the affected dispatch or checkpoint. No error permits broader context, weaker policy, provider-owned verification, or a green-seeking substitute command.
- **Security/safety expectations:** Package construction passes through the TASK-021 control envelope and TASK-022 security policy. Secrets and credentials are references only; untrusted content is data; failure output is redacted and minimized; filesystem/network/process capability remains exact and default-deny.
- **Checkpoint eligibility / done when:** The exact command passes; all acceptance criteria are proven by positive and negative tests; local checks run with no active Codex session; unauthorized paths and implicit FULL produce no side effect; legacy tests remain green; only allowed files change; and qualifying evidence binds the package/verification-plan identities without changing upstream authority or implementation state prematurely.
- **Forbidden scope / out-of-scope:** Durable phase-state persistence or resume owned by `TASK-027`; phase telemetry owned by `TASK-028`; resource/budget/exhaustion enforcement owned by `TASK-023`; provider promotion owned by `TASK-024`; Decision Gateway fixture work owned by `TASK-025`; Stage09 behavior changes; task/authority/state/evidence rewriting; deployment; or Stage07/08/09/10 execution outside the later sealed workflow.

## TASK-027 - Durable Stage08 phase state, SAFE_PAUSE, and precise resume

- **Status:** `TODO`
- **Purpose / objective:** Persist an atomic, reconstructable Stage08 attempt/phase history and enforce authority-bound SAFE_PAUSE/resume without repeating completed provider work or still-valid successful deterministic verification.
- **Authority trace:** `SPEC-019 -> DES-020 -> TASK-027`; applicable Architecture Constitution mappings are `ARCH-AC-01`, `ARCH-AC-02`, `ARCH-AC-03`, `ARCH-AC-04`, `ARCH-AC-05`, `ARCH-AC-06`, `ARCH-AC-07`, and `ARCH-AC-08`.
- **Dependencies:** `TASK-001`, `TASK-002`, `TASK-010`, `TASK-011`, `TASK-012`, `TASK-017`, `TASK-021`, `TASK-022`, `TASK-026`.
- **Allowed files:** `sdd_orchestrator/stage08_phase_state.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/codex_cli.py`, `sdd_orchestrator/codex_results.py`, `sdd_orchestrator/git_runtime.py`, `sdd_orchestrator/path_scope_policy.py`, `sdd_orchestrator/evidence_writer.py`, `sdd_orchestrator/result_serialization.py`, `sdd_orchestrator/system_controller.py`, `tests/test_stage08_phase_resume.py`, `tests/test_m5_git_recovery.py`, `tests/test_m6_codex_adapter.py`, `tests/test_v1118_safe_pause_and_evidence.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_stage08_phase_resume.py tests/test_m5_git_recovery.py tests/test_m6_codex_adapter.py tests/test_v1118_safe_pause_and_evidence.py`.
- **Allowed implementation scope:** Versioned attempt journals for every DES-020 phase; atomic hash-bound transitions; attempt/task/authorization/envelope/branch/entry-head/baseline/task-authority/allowed-files/diff bindings; verification fingerprints; normalized `CODEX_QUOTA_EXHAUSTED`, `CODEX_INTERRUPTED`, and `CODEX_TIMEOUT`; fail-closed SAFE_PAUSE classification; precise resume revalidation; bounded remediation invocation history; integration with existing Git scope/provenance, RecoveryManager, `pending_evidence_write`, evidence, and status projections.
- **Required behavior/outcome:** Phase state reconstructs deterministically and never implies qualification. An interruption becomes SAFE_PAUSE only when authorization, scope, provenance, security handling, and absence of unknown side effects are proven; otherwise it blocks. Resume revalidates every SPEC-019 binding, does not repeat a valid completed initial coding invocation or still-current successful verification, never expands authority/capabilities/files, and binds final evidence/checkpoint to the complete phase history.
- **Acceptance criteria:** `PHASE_STATE_ATOMIC_AND_RECONSTRUCTABLE`; `QUOTA_INTERRUPTION_TIMEOUT_SAFE_PAUSE_WHEN_PROVEN_SAFE`; `RESUME_REVALIDATES_AUTHORIZATION_BASELINE_ENVELOPE_AND_ALLOWED_FILES`; `COMPLETED_CODEX_INVOCATION_NOT_REPEATED`; `SUCCESSFUL_VERIFICATION_NOT_REPEATED_WHEN_STILL_VALID`; `UNAUTHORIZED_DIFF_FAILS_CLOSED`; `EVIDENCE_AND_CHECKPOINT_BIND_PHASE_HISTORY`; `TASK021_AND_TASK022_GOVERNANCE_PRESERVED`; `LEGACY_STAGE08_TASKS_REMAIN_COMPATIBLE`.
- **Preservation obligations:** Preserve immutable Stage07 authorization, sealed envelopes, existing pending-evidence recovery, task qualification monotonicity, historical evidence, exact verification semantics from TASK-026, TASK-021/TASK-022 enforcement, Stage09/10 ownership, and valid legacy Stage08 behavior. Phase state is not a Git implementation checkpoint or qualification record.
- **Error/failure expectations:** Corrupt/unknown schema, broken transition/digest chain, stale authorization, branch/head/baseline mismatch, changed authority or allowed-files digest, unexplained dirty/untracked path, unprovable diff provenance, unknown side effect, changed verification fingerprint, or unsafe sensitive data blocks without resetting/discarding valid progress or fabricating completion.
- **Security/safety expectations:** Resume repeats TASK-021 and TASK-022 pre-dispatch checks. No stale approval, provider session, credential possession, historical chat, or prior success enlarges authority. Journals and status projections use minimum disclosure and contain no secret values or unsafe raw error output.
- **Checkpoint eligibility / done when:** The exact command passes; every legal/illegal phase transition, atomic-write interruption, corruption path, all three interruption classes, safe/unsafe resume, invocation/verification reuse, dirty-scope rejection, pending-evidence compatibility, fresh-process reconstruction, and final evidence binding behave as required; only allowed files change; no Stage09/10 or historical evidence/state fact is upgraded.
- **Forbidden scope / out-of-scope:** Work Package/verification-level ownership already bounded by `TASK-026`; observational phase telemetry owned by `TASK-028`; resource/budget/exhaustion enforcement owned by `TASK-023`; provider promotion, fixture repair, upstream authority changes, destructive Git recovery, or automatic execution of another task.

## TASK-028 - Observational Stage08 phase-consumption telemetry

- **Status:** `TODO`
- **Purpose / objective:** Extend the existing telemetry framework with non-authoritative, minimum-disclosure Stage08 phase measurements that separate provider-active time from local verification and total Stage08 time without implementing resource or budget enforcement.
- **Authority trace:** `SPEC-019 -> DES-020 -> TASK-028`; applicable Architecture Constitution mappings are `ARCH-AC-01`, `ARCH-AC-02`, `ARCH-AC-03`, `ARCH-AC-06`, `ARCH-AC-07`, and `ARCH-AC-08`; `ARCH-AC-04`, `ARCH-AC-05`, and `ARCH-AC-09` controls remain preserved and cannot be weakened by telemetry.
- **Dependencies:** `TASK-021`, `TASK-022`, `TASK-027`.
- **Allowed files:** `sdd_orchestrator/telemetry/models.py`, `sdd_orchestrator/telemetry/measurement.py`, `sdd_orchestrator/telemetry/recorder.py`, `sdd_orchestrator/codex_adapter.py`, `sdd_orchestrator/codex_cli.py`, `tests/test_telemetry_stage08_phase.py`, `tests/test_telemetry_models.py`, `tests/test_telemetry_measurement.py`, `tests/test_telemetry_stage08_task.py`, `tests/test_telemetry_application_wiring.py`, `tests/test_telemetry_storage_contract.py`.
- **Verification Commands:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_telemetry_stage08_phase.py tests/test_telemetry_models.py tests/test_telemetry_measurement.py tests/test_telemetry_stage08_task.py tests/test_telemetry_application_wiring.py tests/test_telemetry_storage_contract.py`.
- **Allowed implementation scope:** A versioned `STAGE08_PHASE` event and compatible measurement/recorder wiring for `codex_invocation_count`, `codex_active_duration`, `local_verification_duration`, `fast_verify_duration`, `target_verify_duration`, `full_verify_duration`, `remediation_count`, `resume_count`, total Stage08 duration, and the derivable `CODEX_ACTIVE_TIME / TOTAL_STAGE8_TIME` ratio. Reuse existing sinks and provider-call provenance; prevent double-counting across resumes/remediation.
- **Required behavior/outcome:** Every metric is attributable to the TASK-027 attempt/phase identity, uses the existing telemetry recorder/store, preserves frozen `STAGE08_TASK` compatibility and usage truth classes, emits no raw package/diff/prompt/error/secret content, and remains observational. Unavailable token usage remains unavailable rather than zero or estimated actual. Telemetry cannot authorize, qualify, checkpoint, pause, resume, enforce a limit, or alter Stage09/10.
- **Acceptance criteria:** `EXISTING_TELEMETRY_FRAMEWORK_REUSED`; `TELEMETRY_TRUTH_CLASSES_PRESERVED`; `TASK023_RESOURCE_ENFORCEMENT_NOT_DUPLICATED`; `TASK021_AND_TASK022_GOVERNANCE_PRESERVED`; `LEGACY_STAGE08_TASKS_REMAIN_COMPATIBLE`; all eight required counts/durations and the effectiveness ratio are derivable without overlap or fabricated usage.
- **Preservation obligations:** Preserve existing telemetry schemas/readers/sinks, the frozen `STAGE08_TASK` event, provider-call provenance, Cost/Token truth classes, TASK-021/TASK-022 security, historical telemetry/evidence, provider independence, Stage09 full regression, Stage10 finalization, and TASK-023's exclusive enforcement authority.
- **Error/failure expectations:** Missing or ambiguous attempt correlation, negative/non-monotonic/overlapping duration, duplicate resume event, unsupported schema, sensitive payload, fabricated token/cost value, recorder/sink failure, or any attempted control-plane decision remains explicit and cannot affect governed execution truth.
- **Security/safety expectations:** Record only safe identities, phase/outcome, durations, and bounded counters. Apply TASK-022 minimum-disclosure/redaction before recording; never persist prompts, relevant-source payloads, raw tracebacks, credentials, or secrets.
- **Checkpoint eligibility / done when:** The exact command passes; versioned phase-event compatibility, metric derivation, resume/remediation de-duplication, unavailable-token truth, sensitive-data exclusion, non-authority behavior, existing telemetry storage/application wiring, and legacy Stage08 regressions all pass; only allowed files change.
- **Forbidden scope / out-of-scope:** Budget policy/state, reservation, hard/soft limits, cumulative enforcement counters, resource/runtime/deployment constraints, exhaustion stop/route, approval-bound budget increase, or any other `TASK-023` behavior; parallel telemetry stores; provider promotion; upstream authority changes; or Stage07/08/09/10 execution.

## 5. Whole-artifact dependency graph

The declared dependency graph is:

```text
TASK-001 -> TASK-002, TASK-005, TASK-008, TASK-010, TASK-012, TASK-013, TASK-016, TASK-019, TASK-020, TASK-027
TASK-002 -> TASK-003, TASK-004, TASK-005, TASK-006, TASK-009, TASK-010, TASK-011, TASK-012, TASK-027
TASK-003 -> TASK-015, TASK-017, TASK-021
TASK-004 -> TASK-015, TASK-017
TASK-005 -> TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012, TASK-013, TASK-019, TASK-021
TASK-006 -> TASK-009, TASK-011, TASK-013, TASK-015, TASK-017, TASK-021, TASK-025
TASK-007 -> TASK-015, TASK-017, TASK-021, TASK-024, TASK-026
TASK-008 -> TASK-009, TASK-012, TASK-014, TASK-016, TASK-017, TASK-019, TASK-020, TASK-021
TASK-009 -> TASK-015, TASK-017
TASK-010 -> TASK-007, TASK-011, TASK-012, TASK-015, TASK-017, TASK-019, TASK-021, TASK-027
TASK-011 -> TASK-012, TASK-015, TASK-017, TASK-019, TASK-021, TASK-022, TASK-026, TASK-027
TASK-012 -> TASK-015, TASK-017, TASK-019, TASK-020, TASK-021, TASK-026, TASK-027
TASK-013 -> TASK-014, TASK-016, TASK-017
TASK-014 -> TASK-015, TASK-016, TASK-017, TASK-026
TASK-015 -> TASK-016, TASK-017
TASK-016 -> TASK-017, TASK-018
TASK-017 -> TASK-018, TASK-021, TASK-026, TASK-027
TASK-018 -> none
TASK-019 -> TASK-018, TASK-020
TASK-020 -> none
TASK-021 -> TASK-022, TASK-023, TASK-024, TASK-026, TASK-027, TASK-028
TASK-022 -> TASK-023, TASK-024, TASK-026, TASK-027, TASK-028
TASK-023 -> TASK-024
TASK-024 -> none
TASK-025 -> none
TASK-026 -> TASK-027
TASK-027 -> TASK-028
TASK-028 -> none
```

Analysis of the actual dependency declarations found no cycle, self-dependency, nonexistent task reference, or missing dependency required by the stated task scopes. `TASK-021` through `TASK-024` retain the control-enforcement sequence; test-only `TASK-025` remains independent after its already-qualified `TASK-006` dependency. The SPEC-019 sequence is `TASK-026 -> TASK-027 -> TASK-028`. It intentionally has no dependency on `TASK-023`: observational phase measurement is permitted only after `TASK-027`, while `TASK-023` independently retains resource/budget/exhaustion enforcement. File overlap is explicit and requires a fresh baseline per Stage07/08 task, but it is not a semantic dependency. The graph preserves parallel work where dependencies permit it.

## 6. Whole-artifact traceability and P0/architecture coverage

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
| `SPEC-017` | `DES-017` | `TASK-019` |
| `SPEC-018` | `DES-018` | `TASK-020` |
| `SPEC-019` | `DES-020` | `TASK-026`, `TASK-027`, `TASK-028` |

Coverage analysis confirms:

- All 34 applicable P0 requirements are covered: `FR-01` through `FR-21`, `NFR-01` through `NFR-05`, and `EC-01` through `EC-08`.
- All applicable P0 acceptance criteria are covered: `AC-01` through `AC-21`, `AC-23` through `AC-27`, and `AC-29` through `AC-36`.
- `SPEC-001` through `SPEC-019` and `DES-001` through `DES-020` are covered.
- `TASK-001` through `TASK-028` each have upstream authority; orphan task count is zero.
- All 28 tasks contain the full task contract. `TASK-023` through `TASK-028` remain prospective `TODO` contracts; implementation qualification for `TASK-001` through `TASK-022` remains exclusively in `.sdd/state/implementation-state.yaml` and its bound evidence.
- `ARCH-AC-01` through `ARCH-AC-09` have explicit Stage06 mappings. The original enforcement gaps remain bounded by `TASK-023` through `TASK-025`; the SPEC-019/DES-020 gaps are assigned to `TASK-026` through `TASK-028` without changing Architecture Constitution semantics or reopening qualified work.
- The dependency graph closes with zero unresolved forward references and is a DAG.
- Approved Design reports no blocking Design TBD; this decomposition introduces no blocking task TBD and detects no cross-domain conflict.

Therefore whole-artifact P0 task coverage is complete for the approved current Stage06 authority. This coverage analysis and Stage06 approval do not constitute Stage07 evaluation, implementation authorization, implementation conformance, or Stage09 qualification.

## 7. Stage07-readiness support

This approved current authority supplies Stage07 with reviewable support for all of the following, without evaluating Stage07 or assigning it a gate result:

- bounded task purpose and allowed implementation scope;
- explicit actual dependencies and a closed acyclic graph;
- common and task-specific atomic checkpoint criteria;
- task-specific future verification requirements using truthful result semantics;
- preservation obligations and independently valid progress boundaries;
- explicit error/failure expectations and recovery routing;
- task-specific security/safety obligations where applicable;
- Stage08 scope boundaries, sealed-envelope requirements, and overrun stops; and
- complete upstream traceability through `TASK` for all P0 requirements, acceptance criteria, SPECs, DESs, and Architecture Constitution remediation scope.

Fresh Stage07 evaluation must use `.sdd/state/implementation-state.yaml` rather than prospective labels to distinguish qualified and unqualified work. `TASK-001` through `TASK-022` remain separately repository-qualified; `TASK-023` through `TASK-028` remain unqualified prospective tasks. Under the Project Authority hold and this reconciliation result, the first selected task is `TASK-026`; it alone may be evaluated next. Stage07 must validate its exact dependencies and scope and enforce all applicable `ARCH-AC-01` through `ARCH-AC-08` checks. It must not authorize `TASK-023` through `TASK-025` or infer any qualification from this authority artifact.

Stage07 must independently inspect the approved artifact state, repository/Git readiness, testability, conflicts, security blockers, critical TBDs, traceability, and every other configured entry/check condition. Nothing in this section is a Stage07 `PASS` or `FAIL` decision.

## 8. Recovery and authority boundary

- This `tasks.md` is the approved prospective current `EXECUTION_DECOMPOSITION` authority; it is not historical Phase06 reconstruction.
- Tasks are prospective work contracts, not historical implementation facts. Existing implementation cannot make a task `DONE` or prove conformance.
- This Stage06 impact evaluation inspected code, tests, imports, and existing evidence as non-authoritative evidence solely to classify the Stage04/05 candidates. It did not modify implementation/tests, execute recovery, issue Stage09 conformance, authorize release/deployment, or turn observed behavior into upstream authority.
- Approval of this Stage06 authority does not create Stage07 `PASS` or authorize Stage08 implementation. Normal implementation remains unauthorized until Stage07 independently returns a valid `PASS` with implementation authorization.
- A Current Implementation Recovery Gate `PASS`, if later applicable under its narrow prerequisites, permits Stage09 entry only. It never creates retroactive Stage07 `PASS`, Stage08 authorization, implementation authorization, implementation conformance, task completion, test `PASS`, Stage09 `PASS`, Stage10 authority, or release authority.
- An implementation gap found after Stage09 returns to valid current authority and the normal `Stage07 -> Stage08` path.
- Programming language, framework, full module/package/file layout, database, serialization format, test framework, cloud platform, webhook architecture, LINE implementation, authentication/IAM product, and deployment topology remain deferred non-decisions.

## 9. Current Stage06 authority status

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
28

P0_TASK_COVERAGE_COMPLETE =
YES

ARCHITECTURE_IMPACT_CANDIDATES_EVALUATED =
15_OF_15

NEW_BOUNDED_REMEDIATION_TASKS =
TASK-021_THROUGH_TASK-025

SPEC019_NEW_BOUNDED_TASKS =
TASK-026_THROUGH_TASK-028

TASK023_AUTHORITY_RESULT =
UNCHANGED_RESOURCE_BUDGET_EXHAUSTION_ENFORCEMENT_OWNER

SPEC019_PHASE_MEASUREMENT_OWNER =
TASK-028_OBSERVATIONAL_ONLY

EXISTING_TASKS_REOPENED =
NONE

IMPLEMENTATION_QUALIFICATION_PRESERVED =
TASK-001_THROUGH_TASK-022

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
FRESH_STAGE07_PRE_IMPLEMENTATION_GATE_FOR_TASK-026_ONLY
```

## 10. Stage09 machine-verification execution contract

### 10.1 Authority and repair classification

This section is a narrowly bounded Stage06 `EXECUTION_DECOMPOSITION` repair. Stage06 owns the executable verification decomposition recorded in `tasks.md`; Stage09 exclusively owns the later `VERIFICATION_DECISION`. This repair does not alter Product, Technical Contract, Design, Agent Governance, task objective, dependency, acceptance, implementation, evidence, Recovery Gate, or release authority.

The repaired gap is `GOVERNANCE_CONTRACT_GAP`: the prior Stage09 entry stopped with `INCOMPLETE` because no exact repository-authoritative machine-verification command existed. That historical result remains unchanged. This section creates no Stage09 result, executes no Stage09 qualification, reopens no task, and allocates no task ID.

The Current Implementation Recovery Gate `PASS` at commit `2d70c439ebbefe30c917116ea16b886747645bb4` remains preserved as the conditional Stage09 entry authority only when `PRE_EXISTING_IMPLEMENTATION_RECOVERY` applies. It is not a prerequisite for the normal current-authority `Stage07 PASS -> Stage08 completed -> Stage09` route. Its result is not rerun or reinterpreted by this repair.

### 10.2 Entry prerequisites

Before executing the commands below, Stage09 must independently establish all configured entry facts against one exact baseline:

- exactly one applicable entry route is satisfied: either (a) the normal current-authority route has a valid Stage07 `PASS`, implementation authorization valid for the executed Stage08 scope, successful Stage08 completion, required Stage08 evidence/checkpoint/finalization, and no unresolved implementation task; or (b) `PRE_EXISTING_IMPLEMENTATION_RECOVERY` applies and the Current Implementation Recovery Gate is `PASS`;
- the implementation graph is complete, every required task qualification and dependency is intact, and no implementation task or transaction is active;
- the branch, HEAD, runtime, authority package, worktree, index, evidence, checkpoints, state finalization, and recovery state are current and internally coherent;
- no active `SAFE_PAUSE`, remediation-required phase, execution lock, unexplained dirty path, or unresolved recovery obligation exists; and
- Stage10, release, deployment, and Upgrade Gate work have not started.

Missing, stale, ambiguous, conflicting, or unverifiable entry input makes Stage09 `INCOMPLETE`; it is not normalized into a test failure or a best-effort run.

### 10.3 Authoritative machine-verification commands

Execute each command exactly and independently from the repository root, without shell chaining or substitution, before creating the Stage09 report:

1. `.\.venv\Scripts\python.exe -m pytest -q tests`
2. `git diff --check`
3. `git diff --cached --check`
4. `git status --porcelain=v1`

The pytest command is the integrated repository-local suite, not a promotion of any one historical task command. It includes all existing unit, contract, integration, regression, lifecycle, security, resource-policy, provider-conformance, DecisionGateway, Stage08 optimization, recovery, telemetry, and compatibility tests under `tests/`. The Git commands prove that the entry verification baseline has no whitespace-error diff, staged whitespace-error diff, or unexplained tracked/untracked change. Command 4 passes only with empty output.

The machine suite is necessary but not sufficient for Stage09 `PASS`. Green tests cannot create requirement authority or substitute for the required bidirectional traceability, evidence/checkpoint integrity, repository integrity, Architecture Constitution, governance regression, or authority-deviation review.

### 10.4 Coverage mapping

| Required Stage09 category | Machine-evidence coverage in the integrated suite | Additional Stage09 review required |
| --- | --- | --- |
| Implementation graph, lifecycle, task completion, state machine, and convergence routing | `test_governed_state.py`, `test_orchestrator.py`, `test_runner.py`, `test_m10_convergence_auto.py`, Stage07/runtime reconciliation tests | Validate all current qualification records, dependencies, active cursors, and required traceability against authority and Git. |
| Governance, authorization, default deny, Human Approval, and audit | `test_governance_envelope.py`, `test_m4_reasoning_pipeline.py`, `test_m41_atomic_dispatch.py`, `test_m41_atomic_executor.py`, `test_m7_decision_gateway.py` | Confirm current envelopes, approvals, decision records, and audit/evidence bindings remain applicable. |
| Security, minimum disclosure, injection containment, filesystem/network/secret bounds | `test_security_policy.py`, `test_stage08_work_package.py`, `test_v1118_safe_pause_and_evidence.py` | Review current security authority and any recorded deviations or sensitive-data findings. |
| Resource policy, truth classes, reservation/accounting, limits, and exhaustion | `test_resource_policy.py`, `test_m42_evaluation_metrics.py`, telemetry measurement/model tests | Confirm TASK-023 evidence and current provider/model/runtime identity remain bound and no unavailable value is treated as zero. |
| Provider conformance, default preservation, fallback, and promotion | `test_provider_conformance.py`, `test_m41_atomic_executor.py`, `test_v114_provider_schema.py`, provider telemetry-envelope tests | Confirm TASK-024 evidence, manifest/evidence identity, approval, security, and resource-policy compatibility. |
| DecisionGateway fixture isolation and approval/denial/fail-closed behavior | `test_m7_decision_gateway.py` | Confirm TASK-025 changed no production DecisionGateway code and durable A2 coverage/evidence remains intact. |
| Stage08 Work Package and FAST/TARGET/FULL local verification | `test_stage08_work_package.py`, `test_stage08_verification_levels.py`, `test_m6_codex_adapter.py`, `test_v1113_codex_stdin_prompt.py` | Confirm TASK-026 checkpoint/evidence and local authoritative-verification ownership. |
| Durable phase state, SAFE_PAUSE, precise resume, provenance, and no duplicate work | `test_stage08_phase_resume.py`, `test_m5_git_recovery.py`, `test_v1118_safe_pause_and_evidence.py` | Confirm TASK-027 journals are complete historical attempts with no active recovery obligation. |
| Observational telemetry, deterministic identity, truth classes, storage, and de-duplication | `test_telemetry_*.py` | Confirm TASK-028 evidence and telemetry remain observational and do not acquire lifecycle authority. |
| Architecture Constitution `ARCH-AC-01` through `ARCH-AC-09` | Cross-cutting governance, security, resource, provider, lifecycle, recovery, Stage08, and telemetry tests above | Perform explicit rule-by-rule integrated qualification against current code, authority, evidence, and repository state. |
| Evidence/checkpoint immutability and repository integrity | `test_governed_state.py`, `test_m5_git_recovery.py`, `test_m6_codex_adapter.py`, `test_v1118_safe_pause_and_evidence.py`; Git commands 2-4 | Validate every required evidence blob, referenced commit, checkpoint, separate finalization commit, Git reachability, and historical/nonqualifying-record preservation. |

The full `tests` tree was selected only after repository inventory established that all 53 current test files are local and collection-safe, and that narrower task suites omit cross-task and legacy regression coverage required by Stage09. Stage06 path-readiness inspection collected 598 tests without executing them. No live external API is part of the contract; provider/network behavior in the suite must remain substituted, mocked, or otherwise locally bounded.

### 10.5 Result and evidence criteria

Stage09 may return `PASS` only when all four commands execute with their required outcomes, every applicable configured Stage09 category passes, bidirectional traceability is complete, all required evidence/checkpoint/state/repository integrity checks pass, `ARCH-AC-01` through `ARCH-AC-09` pass integrated qualification, no unresolved authority deviation exists, and `docs/handoff/verification-report.md` truthfully binds the exact baseline, commands, outputs, duration, counts, findings, and Stage10 eligibility consequence.

Stage09 returns `FAIL` only after qualifying verification executed and a required criterion was not satisfied:

- a confirmed code/test/behavior/evidence defect under clear authority is `IMPLEMENTATION_GAP` and routes to a bounded convergence task followed by the normal applicable Stage07/Stage08 path and a fresh Stage09 run;
- a confirmed authority contradiction is `AUTHORITY_CONTRACT_CONFLICT` and routes to the affected authoritative owner stage(s), propagates affected scope, and requires the applicable downstream gate reruns before implementation.

Stage09 returns `INCOMPLETE` when a required command cannot legally or completely execute, the environment/toolchain or command contract is missing/stale, a required input or proof is absent/ambiguous/unverifiable, or the outcome cannot truthfully be classified. Environment/tooling failures route to the applicable runtime owner without changing implementation. A stale Stage09 verification command routes to Stage06 `EXECUTION_DECOMPOSITION`. Missing evidence or integrity input routes to its owning lifecycle domain; confirmed invalid implementation evidence is classified under the Stage09 failure rules rather than repaired in place.

Stage09 must preserve the exact command output and the non-machine review references needed to reproduce the decision. It must not modify production or tests, silently repair a failure, invent a green alternative, reinterpret an unavailable result as success, or use future Upgrade Wave capability as a V1 prerequisite.

### 10.6 Checkpoint, state, and hard-stop rules

A completed Stage09 decision must be recorded in `docs/handoff/verification-report.md`, the protected `VERIFICATION_DECISION` artifact owned by Stage09. The decision becomes repository-backed only through a dedicated Stage09 report checkpoint that does not amend implementation or Recovery Gate commits. If the repository-owned lifecycle state requires a separate update after that checkpoint, it must be a separate state-finalization commit and may advance no farther than the proven Stage09 result.

Only a repository-backed Stage09 `PASS` makes Stage10 entry eligible. `FAIL` and `INCOMPLETE` do not. Stage09 execution must stop before Stage10, V1 tagging/release, deployment, Upgrade Gate #2, or Upgrade Wave work unless a later operation supplies their separate authority.

This contract repair itself requires only the Stage06 `tasks.md` authority checkpoint and its Stage06 run audit. It requires no implementation-state mutation or separate state-finalization commit. After that checkpoint, Stage09 may be freshly re-entered from the new complete baseline; Stage09 is not executed by this repair.

## 11. Bounded SPEC-017 historical-evidence recovery work packages

### 11.1 Authority, representation, and common boundary

This section is a Stage06 `EXECUTION_DECOMPOSITION` work-package definition implementing the approved Stage03/Stage04 decision `LEGACY_COMPATIBILITY_FORBIDDEN` for the identified TC008 through TC011 ordinary-evidence records. It creates recovery-operation definitions only. It creates no implementation convergence task, does not alter any historical evidence or implementation checkpoint, does not issue a recovery authorization, and does not authorize execution.

Each `RECOVERY-*` identifier below is a recovery-operation identifier, not a `TASK-*` or `TC*` implementation-task identifier. The repository's recovery executor resolves the existing named TC task contract and requires a separate, active, Project Authority `POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY` authorization bound to that exact task, checkpoint, baseline, authority versions, command, and single-use attempt. The only planned execution outputs are a new append-only `.sdd/evidence/*-<TC>-recovery-<attempt>.json` attestation, its authorized audit/pending artifacts, and an evidence-only checkpoint when the authorization permits it.

Every recovery operation must execute the exact listed command freshly in an isolated view of its immutable checkpoint; capture its natural exit status, complete stdout/stderr, timestamps, environment, and explicit recovery execution provenance; preserve the original evidence and checkpoint; prove no implementation mutation; and record `PASS`, `FAIL`, or `NOT RUN` truthfully. It must not infer a historical `codex.returncode`, rerun normal Stage07 or Stage08, modify implementation/tests/authority/state, or invoke the Recovery Gate, Stage09, Stage10, or deployment.

The four recovery operations are independent. They share no sequential dependency; each instead depends on its own Project Authority authorization and its unchanged checkpoint/evidence/task bindings.

### 11.2 RECOVERY-TC008-ORDINARY-EVIDENCE-001

- **Target task:** `TC008` — existing task contract `.sdd/convergence/TC008.yaml`.
- **Original implementation checkpoint:** `6cbb7df678a671493520fa0f6abaddcc9bf61557`.
- **Immutable original evidence:** `.sdd/evidence/20260924T103204.2963462Z-TC008.json`.
- **Exact fresh verification command:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m41_runner_context_integration.py`.
- **Allowed outputs:** Only the authorization-bound append-only TC008 recovery attestation and explicitly authorized recovery audit/pending artifacts under `.sdd/evidence/`, plus its evidence-only checkpoint.
- **Forbidden scope:** Original evidence; implementation checkpoint/history; `src/**`; `tests/**`; `tasks.md`; authority artifacts; `.sdd/state/**`; normal Stage07/Stage08; Recovery Gate; Stage09/Stage10.
- **Authorization prerequisite:** A unique active Project Authority `POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY` authorization for this exact task/checkpoint/command.

### 11.3 RECOVERY-TC009-ORDINARY-EVIDENCE-001

- **Target task:** `TC009` — existing task contract `.sdd/convergence/TC009.yaml`.
- **Original implementation checkpoint:** `81b95bc0a6e659ede01149041309d5eb298abbef`.
- **Immutable original evidence:** `.sdd/evidence/20260924T153812.4217508Z-TC009.json`.
- **Exact fresh verification command:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_m10_convergence_auto.py`.
- **Allowed outputs:** Only the authorization-bound append-only TC009 recovery attestation and explicitly authorized recovery audit/pending artifacts under `.sdd/evidence/`, plus its evidence-only checkpoint.
- **Forbidden scope:** Original evidence; implementation checkpoint/history; `src/**`; `tests/**`; `tasks.md`; authority artifacts; `.sdd/state/**`; normal Stage07/Stage08; Recovery Gate; Stage09/Stage10.
- **Authorization prerequisite:** A unique active Project Authority `POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY` authorization for this exact task/checkpoint/command.

### 11.4 RECOVERY-TC010-ORDINARY-EVIDENCE-001

- **Target task:** `TC010` — existing task contract `.sdd/convergence/TC010.yaml`.
- **Original implementation checkpoint:** `694cc04e42072b3819c97735421908de08ed3076`.
- **Immutable original evidence:** `.sdd/evidence/20260924T155644.2073715Z-TC010.json`.
- **Exact fresh verification command:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_telemetry_stage08_task.py`.
- **Allowed outputs:** Only the authorization-bound append-only TC010 recovery attestation and explicitly authorized recovery audit/pending artifacts under `.sdd/evidence/`, plus its evidence-only checkpoint.
- **Forbidden scope:** Original evidence; implementation checkpoint/history; `src/**`; `tests/**`; `tasks.md`; authority artifacts; `.sdd/state/**`; normal Stage07/Stage08; Recovery Gate; Stage09/Stage10.
- **Authorization prerequisite:** A unique active Project Authority `POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY` authorization for this exact task/checkpoint/command.

### 11.5 RECOVERY-TC011-ORDINARY-EVIDENCE-001

- **Target task:** `TC011` — existing task contract `.sdd/convergence/TC011.yaml`.
- **Original implementation checkpoint:** `840034da3c598729780524a7bce9528af31fae50`.
- **Immutable original evidence:** `.sdd/evidence/20260924T081605.981214Z-TC011.json`.
- **Exact fresh verification command:** `.\.venv\Scripts\python.exe -m pytest -q tests/test_v1114_project_runtime.py tests/test_v1115_windows_console_resolution.py`.
- **Allowed outputs:** Only the authorization-bound append-only TC011 recovery attestation and explicitly authorized recovery audit/pending artifacts under `.sdd/evidence/`, plus its evidence-only checkpoint.
- **Forbidden scope:** Original evidence; implementation checkpoint/history; `src/**`; `tests/**`; `tasks.md`; authority artifacts; `.sdd/state/**`; normal Stage07/Stage08; Recovery Gate; Stage09/Stage10.
- **Authorization prerequisite:** A unique active Project Authority `POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY` authorization for this exact task/checkpoint/command.

### 11.6 QUALIFICATION-STATE-RECONCILIATION-001

This is one later state-only operation, not an implementation task. It may begin only after all four named recovery attestations are independently qualifying and repository-backed.

- **Prerequisites:** Qualifying append-only recovery evidence for TC008, TC009, TC010, and TC011; all original evidence/checkpoints remain immutable and reachable; clean current baseline; no unresolved recovery attempt or evidence conflict; explicit authority for the state operation.
- **Allowed file:** `.sdd/state/implementation-state.yaml` only.
- **Required outcome:** Correct TC007 to its canonical evidence binding; bind TC008 through TC011 only to their qualifying recovery evidence; preserve all original evidence/checkpoint references as historical facts; preserve unaffected records and cursors except deterministic ancestry-latest projections; and complete full authoritative `_validate_v2` validation before any state checkpoint.
- **Forbidden scope:** Evidence mutation; checkpoint/history mutation; validator behavior; tests/production code; verification execution; Stage07/Stage08; Recovery Gate; Stage09/Stage10; release/deployment.

The reconciliation operation depends on all four recovery operations. It must not run after only a partial subset and must not treat a recovery attestation as an automatic state write.

### 11.7 Governance and TC012 preservation

Each recovery operation uses `SDD_STANDARD` with the additional mandatory Project Authority recovery authorization and exact single-use authorization bindings required by SPEC-017/DES-017. `QUALIFICATION-STATE-RECONCILIATION-001` uses `SDD_STRICT` because it changes multiple protected qualification bindings and must validate the entire state atomically.

TC012's Stage08 result, implementation checkpoint `6f3f91c005a17f70e6d4a808dc0aac5ea64358a9`, and evidence `.sdd/evidence/20261001T004229.839108Z-TC012.json` remain preserved. TC012 requires no Stage08 reexecution. Its finalization remains paused until all four recovery operations and the shared reconciliation have completed successfully.
