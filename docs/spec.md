# SDD Software Development System - Current Technical Specification

## 1. Authority and scope

This document is the approved CURRENT prospective Stage03 `TECHNICAL_CONTRACT` authority. Project authority explicitly approved the substantive Technical Contract baseline. It answers: **What must the system technically guarantee in order to satisfy the approved product requirements?** Its upstream authorities are the approved current `PRODUCT_INTENT` in `docs/proposal.md` and approved current `PRODUCT_REQUIREMENT` in `docs/PRD.md`.

This approval owns only `TECHNICAL_CONTRACT`. It is not recovered or reconstructed historical Phase03 authority. `PRODUCT_INTENT` remains owned by `docs/proposal.md`, and `PRODUCT_REQUIREMENT` remains owned by `docs/PRD.md`. This document defines externally verifiable technical guarantees, not implementation design. It does not select architecture, technology, modules, storage, algorithms, providers, deployment, tasks, or repository mechanics. Approval creates no `IMPLEMENTATION_DECISION`, `AGENT_REPOSITORY_GOVERNANCE`, or `EXECUTION_DECOMPOSITION` authority; no Stage07 result or implementation authorization; no Recovery Gate result; no Stage09 result; and no Stage10, release, or deployment authorization. Downstream artifacts require independent authority approval.

## 2. Approved upstream baseline

- Approved goals: `G-01` through `G-05`.
- Applicable MVP requirements: all 34 P0 requirements (`FR-01` through `FR-21`, `NFR-01` through `NFR-05`, and `EC-01` through `EC-08`).
- Acceptance criteria: `AC-01` through `AC-21`, `AC-23` through `AC-27`, and `AC-29` through `AC-36`.
- P1/P2 items are not required for P0 coverage. Telemetry remains observational where present; LINE, remote operation, and cloud deployment remain outside the current MVP requirement.

## 3. Technical contract principles

1. Authority is domain-specific and non-linear. A record, component, actor, test, inference, or downstream artifact cannot silently create, rank, replace, or override authority.
2. Repository/Git-backed artifacts and state are the persistent execution and traceability basis. Chat memory is never authoritative execution state.
3. Unresolved authority, evidence, decisions, and failures produce truthful `TBD`, `INCOMPLETE`, or `BLOCKED` outcomes; apparent progress cannot manufacture completion.
4. Cross-domain conflict follows `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`.
5. Tests are evidence, not `PRODUCT_REQUIREMENT` authority.
6. Technical guarantees are channel-independent unless an approved requirement explicitly constrains a channel.

## 4. Lifecycle and state contracts

### SPEC-001 - Governed lifecycle state

- **Upstream:** G-01, G-02, G-05 -> FR-06, FR-11, NFR-01 -> AC-06, AC-11, AC-23.
- **Applicable state/input:** Any created or resumed governed journey and every lifecycle transition.
- **Technical guarantee:** The authoritative journey state must identify the current stage; completed, current, and next work; `BLOCKED`/`INCOMPLETE` conditions; pending Human Decisions; applicable approved and unapproved authority; and whether affected execution may continue. These facts must be mutually consistent and reconstructable without chat memory.
- **Required behavior/output:** Status inspection returns each fact and distinguishes completion, approval, authorization, verification, and release readiness.
- **Failure/blocking:** Missing or contradictory required state makes the affected state `INCOMPLETE` or `BLOCKED`; progression and stronger qualification are withheld.
- **Verification expectation:** Exercise in-progress, incomplete, blocked, resumed, and completed examples; compare reported facts with persistent authority/state and prove contradictory combinations are rejected.

### SPEC-002 - Lifecycle actions and transitions

- **Upstream:** G-01, G-02, G-05 -> FR-07, FR-09, FR-10, EC-02, EC-03 -> AC-07, AC-09, AC-10, AC-30, AC-31.
- **Applicable state/input:** `PAUSE`, `RESUME`, `REQUEST_REVISION`, `REJECT_PROPOSAL`, or `APPROVE_DECISION` against identified scope.
- **Technical guarantee:** `PAUSE` prevents affected progression; `RESUME` permits only otherwise eligible work; `REQUEST_REVISION` returns affected proposed material for revision and invalidates dependent eligibility as needed; `REJECT_PROPOSAL` prevents adoption; `APPROVE_DECISION` records an explicit decision but permits only transitions whose other gates are satisfied. Revised or withdrawn approval invalidates every known affected downstream approval/completion and routes it to applicable review or rerun.
- **Required behavior/output:** Each accepted action produces an attributable state transition, affected-scope result, and next eligible route. Unrelated work may progress only after independence is established.
- **Failure/blocking:** Invalid, ambiguous, unauthorized, retrospective, or stale actions do not transition affected state and report why.
- **Verification expectation:** Verify every action from valid and invalid states, dependent invalidation, independence handling, and prevention of retrospective approval.

### SPEC-003 - Requirement-readiness decision

- **Upstream:** G-01, G-02, G-04 -> FR-01, FR-02, FR-03, EC-01 -> AC-01, AC-02, AC-03, AC-29.
- **Applicable state/input:** An incomplete idea in any approved intake form and a proposed product-requirement baseline.
- **Technical guarantee:** Readiness must independently represent: problem clear/unclear; target user clear/unclear; MVP scope clear/unclear; important behavior/flow clear/unclear; critical exception/risk blockers; material scope-changing TBD; and current product-baseline approval. Stage02 completion is allowed only when all required readiness conditions pass. Missing downstream technical/design details alone do not block it.
- **Required behavior/output:** Material missing product information and ambiguity are identified, explained plainly, and routed to focused clarification; only affected progression is blocked.
- **Failure/blocking:** The system must not guess, infer approval, or mark Stage02 complete while any Product-level blocking condition remains.
- **Verification expectation:** Cover each readiness dimension independently, approved intake forms, combined failures, and a case where non-critical downstream detail remains without blocking readiness.

## 5. Authority and Human Decision contracts

### SPEC-004 - Domain authority and lifecycle gates

- **Upstream:** G-01, G-02, G-04, G-05 -> FR-04, FR-05, FR-08, FR-17, NFR-04, EC-07 -> AC-04, AC-05, AC-08, AC-17, AC-26, AC-35.
- **Applicable state/input:** Any proposed authority change, gate crossing, conflict, high-risk/destructive action, implementation request, release, or deployment request.
- **Technical guarantee:** Authority identity must include its domain, scope, status, and authoritative source. Authority domains have no linear priority. AI output and user silence are never approval. Required Human Decision blocks affected progression. No actor or component may silently create or override authority. Authority conflict executes `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`.
- **Required behavior/output:** The applicable owner, unresolved condition, affected scope, and permitted route are exposed. New implementation authorization exists only when normal Stage07 returns `PASS` with authorization; a Human Decision alone does not substitute for Stage07 `PASS`.
- **Failure/blocking:** Missing, conflicting, expired, withdrawn, or out-of-scope authority blocks affected execution; unauthorized conflict resolution is rejected.
- **Verification expectation:** Demonstrate each decision category in FR-08, silence, AI recommendation, cross-domain conflict, and attempts to treat Human Decision or another domain as Stage07 authorization.

### SPEC-005 - Human Decision record and governing effect

- **Upstream:** G-01, G-02, G-05 -> FR-05, FR-08, FR-09, FR-10, EC-02, EC-03 -> AC-05, AC-08, AC-09, AC-10, AC-30, AC-31.
- **Applicable state/input:** A material choice or lifecycle-required decision.
- **Technical guarantee:** Each decision has a unique stable identity, subject, affected scope, current status, available user decisions, recorded result when resolved, authoritative decision owner, and downstream dependencies. Pending status blocks affected work. Rejected, revised, or withdrawn results invalidate affected downstream state and require applicable review/rerun.
- **Required behavior/output:** The user can determine what is needed, why, its effect, available choices, recorded outcome, and affected work. Independence must be established before unrelated work continues.
- **Failure/blocking:** A missing/ambiguous result, identity collision, unauthorized actor, or incomplete affected-scope determination cannot unblock affected work.
- **Verification expectation:** Prove uniqueness, all result paths, pending blocking, independence, downstream invalidation, and retained decision history.

## 6. AI execution boundary contracts

### SPEC-006 - AI authority boundary

- **Upstream:** G-02, G-04, G-05 -> FR-04, FR-05, FR-12, FR-13, EC-04 -> AC-04, AC-05, AC-12, AC-13, AC-32.
- **Applicable state/input:** AI proposing, inferring, recommending, drafting, explaining, or executing work.
- **Technical guarantee:** AI may perform those actions only within granted authority and must preserve the non-authoritative status of proposals and inferences. It cannot convert inference, recommendation, silence, or its own output into approval. At insufficient authority it must `STOP`, truthfully `REPORT`, and `ROUTE` to the authoritative owner or Human Decision.
- **Required behavior/output:** Before AI-assisted implementation, approved scope and valid Stage07 implementation authorization must be identifiable. Results identify valid completed progress, change-evidence references, verification-evidence references, and any unverified portion.
- **Failure/blocking:** Out-of-scope execution stops before being treated as authorized; valid in-scope progress remains identifiable; affected continuation is blocked.
- **Verification expectation:** Attempt inference-to-approval, no-authorization coding, scope overrun, mixed valid/invalid progress, and authorized execution with complete evidence references.

## 7. Traceability and evidence contracts

### SPEC-007 - Persistent bidirectional traceability

- **Upstream:** G-01, G-04, G-05 -> FR-11, FR-12, NFR-03 -> AC-11, AC-12, AC-25.
- **Applicable state/input:** Every governed artifact, material change, checkpoint, decision, implementation result, and verification result.
- **Technical guarantee:** Repository/Git-backed information must persistently support `G -> FR/NFR/EC -> AC -> SPEC`; later stages must extend, without redefining, this chain through `DES -> TASK -> CODE -> TEST_EVIDENCE`. Links must be navigable in both directions for affected scope and tied to current version/change/checkpoint and governing decisions.
- **Required behavior/output:** Loss of chat context does not erase state or traceability; missing downstream links remain explicit until their owning stages exist.
- **Failure/blocking:** Broken required links or unverifiable current identity make dependent coverage/completion `INCOMPLETE`; reconstructed chat claims cannot repair them.
- **Verification expectation:** Trace representative requirements forward and evidence backward, remove chat context, and detect a deliberately missing link.

### SPEC-008 - Verification evidence and qualification

- **Upstream:** G-03, G-04, G-05 -> FR-14, FR-15, NFR-01, EC-05 -> AC-14, AC-15, AC-23, AC-33.
- **Applicable state/input:** Executed, failed, skipped, unavailable, or missing verification.
- **Technical guarantee:** Each required verification has exactly one truthful outcome: `PASS`, `FAIL`, or `NOT RUN`, with identified scope, execution/evidence reference when run, and evidence gap when not run. Summaries link evidence/gaps to requirements or behaviors, disclose known regression risk, and separately qualify complete, verified, safe, and ready claims.
- **Required behavior/output:** `PASS` means the identified verification executed and satisfied its criterion; `FAIL` means it executed and did not; `NOT RUN` means no qualifying execution evidence exists. Tests remain evidence, never requirement authority.
- **Failure/blocking:** Incomplete tests cannot be verified; partial PASS cannot be complete; no evidence cannot be safe; Stage09 other than `PASS` cannot be release-ready. Missing required evidence withholds every dependent qualification.
- **Verification expectation:** Verify mixed outcomes, missing evidence, partial coverage, stale/irrelevant evidence, regression risk, and every forbidden qualification.

## 8. Failure, recovery, and safety contracts

### SPEC-009 - Failure and recovery envelope

- **Upstream:** G-01, G-03, G-04, G-05 -> FR-13, FR-16, NFR-01, NFR-02, EC-06 -> AC-13, AC-16, AC-23, AC-24, AC-34.
- **Applicable state/input:** Failure of lifecycle stage, tool, AI provider/service, command, Git operation, test/verification, or security-related operation.
- **Technical guarantee:** Failure handling preserves valid completed work, identifies the exact failed step and affected scope, blocks unsafe continuation, and records truthful status without fabricating results.
- **Required behavior/output:** An understandable report offers applicable remediation, retry, alternate, revision, escalation, or Human Decision routes and states what remains valid.
- **Failure/blocking:** A recovery route cannot erase the failure, broaden authority, retroactively qualify work, or resume affected execution until its preconditions hold.
- **Verification expectation:** Induce one representative failure per listed class and verify preservation, identity, blocking, truthful reporting, and at least one applicable route.

### SPEC-017 - Append-only post-checkpoint implementation-evidence recovery

- **Upstream:** G-01, G-03, G-04, G-05 -> FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, NFR-01, NFR-03, NFR-04, EC-05, EC-06, EC-07 -> AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-23, AC-25, AC-26, AC-33, AC-34, AC-35.
- **Applicable state/input:** An immutable implementation checkpoint whose required ordinary Stage08 `IMPLEMENTATION_EVIDENCE` is absent or non-qualifying because evidence persistence failed, was interrupted, or was discovered after the checkpoint to be incomplete, while the checkpoint itself remains identifiable and unchanged. Recovery is exceptional and may be attempted only under an explicit, current, task- and checkpoint-bounded recovery authorization issued by the applicable authority. It is ineligible when ordinary Stage08 execution is still in progress; the checkpoint is missing, unreachable, rewritten, content-mismatched, or not attributable to the task; implementation content would need modification; applicable task or authority identity is ambiguous, stale, withdrawn, or conflicting; required verification cannot be executed as authorized; or recovery would substitute for a lifecycle gate or qualification.
- **Technical guarantee:** Post-checkpoint recovery may create new qualifying proof for an existing checkpoint, but cannot change or backdate the checkpoint, its contents, its original execution facts, or the evidence state that existed when it was created. A recovery record must be append-only and distinguish itself from ordinary atomic Stage08 evidence. It must bind deterministically to the exact task identity, exact immutable Git checkpoint identity, applicable authority baseline, exact authoritative verification command, recovery authorization identity, recovery execution time, verification outcome and exit status, execution environment/tool provenance sufficient to evaluate the result, and proof that implementation content was not modified during recovery. The referenced checkpoint must remain reachable through the governed repository history and its task-attributable content identity must match the recovered record.
- **Required behavior/output:** Qualifying recovered evidence requires every required binding to validate, an authorized verification execution against the bound checkpoint, the exact authoritative command without implicit normalization or substitution, complete captured execution evidence, exit status zero, and a truthful `PASS`. Verification must be freshly executed during the authorized recovery unless the recovery authorization identifies a different repository-backed evidence instance and the governing contract explicitly permits its reuse. Chat claims, reconstructed memory, Stage07 prose, unbound logs, partial output, stale results, or an asserted prior success cannot establish recovered evidence. Timeout, missing execution, incomplete capture, unavailable or materially mismatched environment, or inability to prove the executed checkpoint produces `NOT RUN`, `FAIL`, or `BLOCKED` as applicable and cannot qualify.
- **Admissibility and audit behavior:** A later evidence-only change does not qualify a historical checkpoint merely by existing. Admissibility requires validation of the explicit recovery authorization and every task, checkpoint, content, authority, command, execution, result, provenance, and no-implementation-mutation binding. Wrong-task, wrong-checkpoint, wrong-command, wrong-authority, stale-result, mismatched-content, unauthorized, incomplete, or unverifiable recovery fails closed. Identical duplicate records may be retained or deterministically recognized as duplicates but cannot multiply qualification. Conflicting records remain immutable, are reported together, block dependent reconciliation until authoritative resolution, and cannot be silently selected or overwritten. Every attempt, including failed attempts followed by a valid attempt, remains attributable in the append-only audit history; a later valid attempt does not erase or relabel an earlier failure.
- **State and lifecycle boundary:** Implementation-state reconciliation remains blocked until recovered evidence qualifies under this contract. Qualifying recovery evidence permits only a separately authorized reconciliation of the checkpoint's implementation-evidence state; it does not itself perform or authorize that reconciliation, create Stage07 `PASS` or normal Stage08 authorization, qualify Stage09, permit Stage10/release, or authorize deployment. Ordinary Stage08 must continue to create its required evidence atomically under its sealed authorization and checkpoint conditions. This recovery path is not a fallback for normal execution and cannot weaken ordinary task, scope, verification, evidence, envelope, or checkpoint requirements.
- **Failure/blocking:** If any required identity, reachability, integrity, authority, command, execution, provenance, result, immutability, or no-mutation fact cannot be proved, the recovery outcome is deterministically non-qualifying and affected reconciliation and progression remain `BLOCKED`. The system must report the failed binding and applicable authoritative route; it must not normalize, repair, infer, silently substitute, or broaden authority or fall back to another evidence path.
- **Verification expectation:** Exercise qualifying recovery and rejection cases for absent authorization; ordinary-execution fallback; wrong or unreachable checkpoint; rewritten or mismatched content; wrong task, authority baseline, or command; non-zero exit, `FAIL`, `NOT RUN`, timeout, partial output, stale result, environment mismatch, and chat/Stage07-only claims; implementation mutation; arbitrary later evidence-only changes; matching duplicates; conflicting records; multiple failed and successful attempts; immutable audit retention; reconciliation before and after qualification; and attempts to derive Stage07, Stage09, Stage10/release, or deployment authority. Also prove that ordinary atomic Stage08 evidence behavior remains unchanged.

### SPEC-018 - Task-indexed implementation qualification state

- **Upstream:** G-01, G-02, G-03, G-04, G-05 -> FR-06, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, NFR-01, NFR-03, NFR-04, EC-05, EC-06, EC-07 -> AC-06, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-23, AC-25, AC-26, AC-33, AC-34, AC-35. This contract extends the persistent-state guarantees of `SPEC-001`, the traceability and evidence guarantees of `SPEC-007` and `SPEC-008`, the failure guarantees of `SPEC-009`, the recovery boundary of `SPEC-017`, and the qualification separation of `SPEC-016`; it does not redefine recovery admissibility.
- **Applicable state/input:** Zero, one, or many tasks whose implementation qualification has been established through ordinary Stage08 evidence or a qualifying `SPEC-017` recovery record, including a task reconciled after chronologically later or higher-numbered tasks have already qualified, plus any legacy implementation state that exposes only singleton completed-task or verified-checkpoint summaries.
- **Per-task qualification guarantee:** Implementation state must represent qualification independently for every qualified task. Each task-specific qualification fact must bind a unique task identity to its qualification status, immutable implementation checkpoint, repository-backed qualifying `IMPLEMENTATION_EVIDENCE` reference, evidence kind sufficient to distinguish ordinary evidence from post-checkpoint recovery, truthful verification outcome, and an attributable reconciliation identity or repository-backed ordering fact sufficient to reconstruct when the qualification entered implementation state. A bare boolean, cursor position, task number, chat claim, or unbound checkpoint cannot establish task qualification.
- **Qualification history and execution cursor:** Task-specific qualification history is authoritative for which tasks are implementation-qualified. Workflow cursors and summaries—including current task, next task, most recently executed task, most recently reconciled or qualified task, legacy last-completed task, and last-verified commit—are distinct concepts and cannot substitute for the history. A singleton summary never represents the complete set of qualified tasks. Current or next task selection remains governed by applicable task dependencies, project state, and Stage07; qualification history alone neither selects work nor authorizes execution.
- **Ordering and ordinary execution:** Qualification records must support ordinary sequential Stage08 execution without requiring recovery semantics and must also support out-of-order qualification. When an older, lower-numbered, or earlier-implemented task later qualifies through legitimate recovery, reconciliation adds its task-specific fact without deleting, replacing, reordering, or misrepresenting newer qualification facts. Task identifiers, implementation chronology, evidence chronology, and reconciliation chronology must remain distinguishable; none may be inferred solely from another.
- **Checkpoint and evidence linkage:** Every affirmative task qualification must deterministically resolve to the exact repository-backed implementation checkpoint and exact qualifying evidence that justify it. Those references must remain mutually consistent with task authority and applicable ordinary or recovery admissibility rules. Dependency evaluation for a required task must query that task's own qualifying record and bindings, not infer satisfaction from a cursor, numeric ordering, another task's qualification, or a singleton last-completed value.
- **Reconciliation semantics:** Implementation-state reconciliation records facts already proven by qualifying evidence; it performs no implementation or verification, creates no evidence, and grants no Stage07, Stage08, Stage09, Stage10, release, or deployment authority. Reconciliation of the same task, checkpoint, and qualifying evidence is idempotent and cannot multiply or reorder qualification. It must preserve every independently valid prior task record and advance no cursor unless a separate governing rule establishes the cursor transition.
- **Conflict semantics:** An existing record with the same task, checkpoint, and evidence is an idempotent match. The same task and checkpoint with a different independently qualifying evidence record may be retained as additional audit provenance only when the governing evidence contract declares the records compatible; it cannot silently replace the established binding. The same task with a different implementation checkpoint, multiple incompatible purported qualifying checkpoints, conflicting evidence, or a legacy summary that contradicts repository-backed task evidence is a conflict. Conflicts must preserve available facts, block affected reconciliation and dependency satisfaction, expose the competing identities, and route to the authoritative owner; no record or summary may be silently selected, normalized, or overwritten.
- **Legacy compatibility and migration:** Valid singleton schema state may be treated only as a compatibility projection and migration input, never as complete qualification history. Migration may create a task-specific record only when repository-backed task, checkpoint, and qualifying-evidence bindings can be proved under the applicable contract. It must not infer missing tasks from numbering, commit order, cursor values, chat, or downstream state. Legacy summary fields may remain as deprecated compatibility projections, but they must be deterministically derived from the task-indexed model under an explicitly defined downstream ordering rule and must never contradict it. Ambiguous, partial, failed, or conflicting migration is atomic and fail-closed: preserve the prior state, report the unresolved bindings, and withhold affected qualification and progression rather than fabricate history.
- **Monotonicity and auditability:** Adding a valid task qualification is append-preserving across the set of qualified tasks. Previously valid qualification facts cannot silently disappear or change identity. Any future invalidation or revocation capability requires separate explicit authority and an attributable audit record; this contract does not authorize one. Repository reconstruction must identify all qualified tasks, each task's implementation checkpoint and qualifying evidence, ordinary-versus-recovery provenance, and the repository-backed reconciliation ordering fact without relying on chat memory.
- **Stage and status separation:** Implementation qualification means only that the task's implementation checkpoint has qualifying `IMPLEMENTATION_EVIDENCE` and has been reconciled into implementation state. It is distinct from task selection, Stage07 gate outcome, normal Stage08 authorization, Stage09 verification qualification, Stage10/release decision, and deployment authority. Neither an individual task record nor any derived summary upgrades those domains.
- **Required coexistence behavior:** State must truthfully support `TASK-019` remaining qualified while `TASK-012` is reconciled later from qualifying recovered evidence, with both task/checkpoint/evidence relationships retained, no current or next task selected unless separately governed, and no Stage07 `PASS` inferred.
- **Failure/blocking:** Missing or unverifiable task identity, checkpoint, evidence, provenance, reconciliation ordering, migration source, or required consistency produces a non-qualifying or `BLOCKED` result for affected reconciliation and dependency use. Unexpected loss of a prior valid task record, summary/history contradiction, or unsupported schema semantics blocks persistence; the system must preserve the last valid repository-backed state and route the gap or conflict to its owner.
- **Verification expectation:** Exercise empty, single-task, and multi-task state; ordinary sequential qualification; higher-numbered or later task qualified before an older task; later recovered qualification without loss of newer facts; task-specific dependency queries; no automatic next-task selection; idempotent reconciliation; compatible additional evidence; every conflicting checkpoint/evidence combination; legacy singleton migration with complete, incomplete, ambiguous, and contradictory proof; summary derivation and contradiction rejection; atomic migration failure; monotonic preservation; repository reconstruction without chat; and attempts to infer Stage07, Stage08, Stage09, Stage10/release, or deployment authority. Include the coexistence of qualified `TASK-019` and later-reconciled `TASK-012` with no selected task.

### SPEC-010 - Security, destructive action, and authority-conflict safety

- **Upstream:** G-02, G-04, G-05 -> FR-08, FR-17, NFR-04, EC-07 -> AC-08, AC-17, AC-26, AC-35.
- **Applicable state/input:** Detected high-risk condition, destructive action, security blocker/failure, or authority conflict.
- **Technical guarantee:** Affected scope and severity can be represented; required explicit authorization is identifiable; affected execution remains `BLOCKED` until authoritative resolution is recorded. Sensitive/security failures cannot be silently bypassed, and an unauthorized actor cannot resolve an authority conflict.
- **Required behavior/output:** Report the condition, affected scope, required owner/decision, and safe continuation eligibility without exposing sensitive material unnecessarily.
- **Failure/blocking:** Missing authorization, unresolved security risk, or authority conflict forbids affected continuation and any qualifying completion claim.
- **Verification expectation:** Exercise all condition classes, unauthorized/bypass attempts, explicit authorization where required, and unaffected-scope isolation.

## 9. Maintenance and regression contracts

### SPEC-011 - Modification scope and preservation

- **Upstream:** G-01, G-03, G-04 -> FR-18, NFR-05 -> AC-18, AC-27.
- **Applicable state/input:** Request to modify an existing program/app.
- **Technical guarantee:** The requested change scope, affected existing behavior/data, and behavior/data expected to be preserved must be identifiable before overall completion. Observed existing behavior is evidence for impact analysis, not automatic product authority.
- **Required behavior/output:** Change scope and preservation scope are distinguished, with unresolved impact/risk visible.
- **Failure/blocking:** Materially unknown affected or preservation scope keeps dependent work unresolved and prevents an overall-complete claim.
- **Verification expectation:** Use a change with affected, preserved, ambiguous, and non-authoritative observed behavior and verify correct classification.

### SPEC-012 - Regression evidence

- **Upstream:** G-03, G-04, G-05 -> FR-19, NFR-05, EC-08 -> AC-19, AC-27, AC-36.
- **Applicable state/input:** Verification of a modification.
- **Technical guarantee:** Applicable regression evidence links to each affected behavior/data risk; gaps and known risks remain visible. New-behavior success cannot establish overall completion.
- **Required behavior/output:** Report regression outcomes, uncovered scope, and whether non-regression is established.
- **Failure/blocking:** Missing required regression evidence withholds overall completion and produces a warning naming the exposed behavior/data risk.
- **Verification expectation:** Demonstrate full evidence, partial evidence, no evidence, and new-feature-only PASS cases.

## 10. Interface-independent interaction contracts

### SPEC-013 - Channel-independent intake and governed interaction

- **Upstream:** G-01, G-02, G-05 -> FR-01, FR-06, FR-07, FR-20 -> AC-01, AC-06, AC-07, AC-20.
- **Applicable state/input:** User interaction through any suitable current-MVP channel.
- **Technical guarantee:** Without requiring LINE or cloud, a channel can submit approved intake forms, continue/resume a journey, inspect governed status, receive a Human Decision, approve, reject, and request revision. Channel translation cannot change authority, lifecycle, or evidence semantics.
- **Required behavior/output:** Equivalent user actions yield the same governed effects and understandable outcomes independent of presentation.
- **Failure/blocking:** Channel absence/failure cannot create approval or silently alter state; unavailable action delivery leaves affected state truthful and recoverable through a suitable channel.
- **Verification expectation:** Complete the essential journey through a non-LINE, non-cloud channel and compare action/state semantics across any additional available channel.

## 11. MVP demonstration contracts

### SPEC-014 - Observable governed chain

- **Upstream:** G-01, G-02, G-03, G-04, G-05 -> FR-11, FR-21 -> AC-11, AC-21.
- **Applicable state/input:** A recorded MVP demonstration.
- **Technical guarantee:** The demonstration can traverse and identify `IDEA -> requirement clarification -> approved product requirements -> specification -> design -> task decomposition -> Human Decision -> authorized AI coding -> testing/verification -> Git traceability -> truthful status/failure handling -> maintenance change -> regression verification`.
- **Required behavior/output:** Evidence must prove authority was not bypassed; AI did not decide product requirements; Human Decision governed affected work; blockers stopped affected work; unverified work was not complete; and maintenance received regression protection.
- **Failure/blocking:** A missing link or proof prevents the demonstration and MVP from being represented as complete.
- **Verification expectation:** Record the full chain and deliberately exercise at least one pending decision, blocker, failure, unverified result, and maintenance regression case.

### SPEC-015 - Plain-language operational reporting

- **Upstream:** G-02, G-05 -> FR-02, FR-06, FR-09, FR-14, FR-16, NFR-02 -> AC-02, AC-06, AC-09, AC-14, AC-16, AC-24.
- **Applicable state/input:** Status, clarification, decision, failure, evidence-gap, or next-action reporting.
- **Technical guarantee:** Reports expose the governing facts required by their contracts and explain situation, consequence, and required user action without requiring programming knowledge.
- **Required behavior/output:** Technical identifiers may be included for traceability, but do not replace an understandable explanation.
- **Failure/blocking:** An opaque report cannot satisfy the associated user-visible contract; affected interaction remains incomplete until an understandable route is available.
- **Verification expectation:** Review representative reports from every listed category with the facts in persistent state and the approved non-programmer target-user context.

### SPEC-016 - Qualification and gate separation

- **Upstream:** G-01, G-03, G-04, G-05 -> FR-08, FR-12, FR-14, FR-15, NFR-01, NFR-04 -> AC-08, AC-12, AC-14, AC-15, AC-23, AC-26.
- **Applicable state/input:** Any request to represent work as approved, authorized, complete, verified, ready, released, or recoverable.
- **Technical guarantee:** These qualifications are distinct and require their own authoritative prerequisites. Stage07 `PASS` is the only normal new-implementation authorization gate. Stage09 `PASS` is required before Stage10 entry/release-ready evaluation. A Human Decision, test PASS, artifact approval, Recovery Gate result, or another qualification cannot substitute for either gate.
- **Required behavior/output:** The system states which qualification is held, which prerequisite/evidence establishes it, and which remains unavailable.
- **Failure/blocking:** Missing prerequisites force a non-qualifying truthful state. The current Recovery Gate and Stage09 cannot be inferred from historical or present artifacts.
- **Verification expectation:** Attempt every prohibited substitution and verify that only the defined gate prerequisites permit the relevant qualification.

## 12. Requirement-to-SPEC traceability

The canonical chain is `G-* -> FR/NFR/EC -> AC -> SPEC-*`. Goal and AC mappings are inherited unchanged from the approved PRD.

| Applicable P0 requirement | AC | Technical coverage |
| --- | --- | --- |
| FR-01 | AC-01 | SPEC-003, SPEC-013 |
| FR-02 | AC-02 | SPEC-003, SPEC-015 |
| FR-03 | AC-03 | SPEC-003 |
| FR-04 | AC-04 | SPEC-004, SPEC-006 |
| FR-05 | AC-05 | SPEC-004, SPEC-005, SPEC-006 |
| FR-06 | AC-06 | SPEC-001, SPEC-013, SPEC-015, SPEC-018 |
| FR-07 | AC-07 | SPEC-002, SPEC-013 |
| FR-08 | AC-08 | SPEC-004, SPEC-005, SPEC-010, SPEC-016 |
| FR-09 | AC-09 | SPEC-002, SPEC-005, SPEC-015 |
| FR-10 | AC-10 | SPEC-002, SPEC-005 |
| FR-11 | AC-11 | SPEC-001, SPEC-007, SPEC-014, SPEC-017, SPEC-018 |
| FR-12 | AC-12 | SPEC-006, SPEC-007, SPEC-016, SPEC-017, SPEC-018 |
| FR-13 | AC-13 | SPEC-006, SPEC-009, SPEC-017, SPEC-018 |
| FR-14 | AC-14 | SPEC-008, SPEC-015, SPEC-016, SPEC-017, SPEC-018 |
| FR-15 | AC-15 | SPEC-008, SPEC-016, SPEC-017, SPEC-018 |
| FR-16 | AC-16 | SPEC-009, SPEC-015, SPEC-017, SPEC-018 |
| FR-17 | AC-17 | SPEC-004, SPEC-010 |
| FR-18 | AC-18 | SPEC-011 |
| FR-19 | AC-19 | SPEC-012 |
| FR-20 | AC-20 | SPEC-013 |
| FR-21 | AC-21 | SPEC-014 |
| NFR-01 | AC-23 | SPEC-001, SPEC-008, SPEC-009, SPEC-016, SPEC-017, SPEC-018 |
| NFR-02 | AC-24 | SPEC-009, SPEC-015 |
| NFR-03 | AC-25 | SPEC-007, SPEC-017, SPEC-018 |
| NFR-04 | AC-26 | SPEC-004, SPEC-010, SPEC-016, SPEC-017, SPEC-018 |
| NFR-05 | AC-27 | SPEC-011, SPEC-012 |
| EC-01 | AC-29 | SPEC-003 |
| EC-02 | AC-30 | SPEC-002, SPEC-005 |
| EC-03 | AC-31 | SPEC-002, SPEC-005 |
| EC-04 | AC-32 | SPEC-006 |
| EC-05 | AC-33 | SPEC-008, SPEC-017, SPEC-018 |
| EC-06 | AC-34 | SPEC-009, SPEC-017, SPEC-018 |
| EC-07 | AC-35 | SPEC-004, SPEC-010, SPEC-017, SPEC-018 |
| EC-08 | AC-36 | SPEC-012 |

Coverage total: **34 of 34 applicable P0 requirements**.

## 13. Technical TBDs / non-decisions

The following are downstream/future `TBD` and do not block this contract: programming language; framework; class/module/package layout; API schema and transport; storage/data representation and database product; algorithms; queue/provider technology; authentication/IAM product; secrets product; test mix and concrete commands; hosting/cloud/deployment topology; LINE webhook design; repository branch/commit strategy; recovery implementation; future channels/providers; and quantitative service levels not approved in the PRD.

Later Design must choose only what is needed to implement an approved contract and must not change product behavior. No `BLOCKING_TBD` was found at Stage03.

## 14. Authority boundaries

- Project authority explicitly approved this substantive baseline as the CURRENT prospective `TECHNICAL_CONTRACT` authority; the approval owns only `TECHNICAL_CONTRACT`.
- This is not recovered or reconstructed historical Phase03 authority.
- `PRODUCT_INTENT` remains owned by `docs/proposal.md`, and `PRODUCT_REQUIREMENT` remains owned by `docs/PRD.md`; this approval neither adds nor revises product behavior.
- Approval creates no `IMPLEMENTATION_DECISION`, `AGENT_REPOSITORY_GOVERNANCE`, or `EXECUTION_DECOMPOSITION` authority. Downstream artifacts require independent authority approval.
- Approval creates no Stage07 result, implementation authorization, Recovery Gate result, Stage09 result, or Stage10/release/deploy authorization.
- Authority changes require known affected downstream scope to be invalidated/re-reviewed under applicable rerun rules.
- Any later discovered product/technical conflict must be detected, reported, blocked, and routed to the authoritative owner; Stage03 cannot self-resolve it.
- Historical Phase03 reconstruction is not authorized. Current implementation and tests were not evaluated.

## 15. Current Technical Specification status

```text
CURRENT_TECHNICAL_CONTRACT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

HISTORICAL_PHASE03_RECONSTRUCTION =
NOT_AUTHORIZED

PRODUCT_INTENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

PRODUCT_REQUIREMENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

P0_TECHNICAL_COVERAGE_COMPLETE =
YES

PRODUCT_REQUIREMENT_CONFLICT =
NONE_DETECTED

BLOCKING_TECHNICAL_TBD =
NO

IMPLEMENTATION_DESIGN_DEFINED =
NO

IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

TECHNICAL_CONTRACT_PROJECT_AUTHORITY_REVIEW_REQUIRED =
NO

NEXT_STEP =
CURRENT_IMPLEMENTATION_DESIGN_DEFINITION
```
