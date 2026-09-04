# SDD Software Development System - Current Implementation Design

## 1. Authority and scope

This document is the approved CURRENT prospective Stage04 `IMPLEMENTATION_DECISION` authority for the SDD Software Development System. It answers: **How should the approved technical contracts be implemented structurally without changing product behavior or technical guarantees?** Its authoritative inputs are the approved current `PRODUCT_INTENT` in `docs/proposal.md`, `PRODUCT_REQUIREMENT` in `docs/PRD.md`, and `TECHNICAL_CONTRACT` in `docs/spec.md`. The lifecycle constraints in `.sdd/system.yaml` and `.sdd/stages.yaml` govern this authority.

This approved authority owns `IMPLEMENTATION_DECISION` only. It does not redefine requirements or technical contracts, document current implementation conformance, reconstruct historical Phase04 authority, create `AGENT_REPOSITORY_GOVERNANCE` or `EXECUTION_DECOMPOSITION` authority, grant Stage07 `PASS`, authorize Stage08 implementation, evaluate the Recovery Gate or Stage09, create Stage09 `PASS`, or create Stage10, release, or deploy authority. Existing implementation was inspected only to preserve established component terminology; that inspection is evidence, does not establish conformance, and does not adopt implementation or tests as authority. Downstream authority still requires independent approval.

Every `DES-*` below is an approved current implementation-design decision within this prospective `IMPLEMENTATION_DECISION` authority.

## 2. Approved upstream baseline

- Goals: `G-01` through `G-05`.
- Applicable P0 requirements: 34 of 34, with their approved acceptance criteria.
- Applicable P0 technical contracts: `SPEC-001` through `SPEC-017`.
- Authority is domain-specific and forms a non-linear graph. No `PRD > Spec > Design` or other linear precedence exists.
- Repository/Git is the persistent execution-state and traceability basis; chat memory is not authoritative execution state.
- Stage07 `PASS` is the only normal new-implementation authorization. Tests do not produce Stage09 `PASS`; Stage09 owns the verification decision. Stage09 `PASS` is required for Stage10 entry.
- Telemetry, where present, is observational only and cannot control authority, gates, lifecycle behavior, completion, or release qualification.
- Cross-domain conflict is handled only as `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`.

## 3. Design principles

1. Use one logical governed core with explicit responsibility boundaries; do not introduce speculative services or distributed infrastructure.
2. Keep authority records, lifecycle state, evidence, and qualification distinct even when stored together in the repository.
3. Make state transitions explicit, scoped, attributable, and validated against current persisted state.
4. Put channel and reasoning providers behind replaceable boundaries; neither boundary changes governance semantics.
5. Preserve valid completed work and record failures rather than using rollback or retries to fabricate success.
6. Prefer stable identifiers and repository references over copied conversational context.
7. Treat observed code, tests, telemetry, and current behavior as evidence, never as automatic product or technical authority.
8. Minimize sensitive data in persisted state and user reports, and stop affected work before unsafe continuation.

## 4. Top-level architecture

The intended MVP is a modular local application. Modules are logical responsibility boundaries and may initially run in one process. Their separation must remain testable; it does not require microservices.

| Component | Owned responsibility | Boundary / non-responsibility |
| --- | --- | --- |
| Interaction adapter | Translate a local or future remote request into channel-neutral operations and render understandable results. | Does not decide authority, gates, or evidence qualification. |
| SDD Orchestrator | Coordinate operations, load the governed snapshot, request evaluations, route capabilities, commit valid state transitions, and expose status. | Does not own every authority domain or invent gate results. |
| Lifecycle governor | Evaluate stage eligibility, transition invariants, pause/block/incomplete conditions, rerun rules, and qualification prerequisites. | Does not author domain content. |
| Authority resolver | Resolve domain, scope, source, approval status, freshness, dependencies, and conflicts. | Does not impose linear precedence or resolve a substantive conflict. |
| Human Decision manager | Create, present, record, revise, reject, or withdraw attributable decisions and calculate affected scope. | Does not substitute a decision for Stage07 `PASS`. |
| Reasoning-provider adapter | Supply replaceable analysis, questioning, proposal, drafting, and authorized assistance. | Provider output is not authority or evidence merely because it was generated. |
| Stage08 execution adapter | Invoke a repository-aware execution capability with a sealed authorization envelope and collect results. | Cannot enlarge scope or self-authorize another task. |
| Repository/Git state store | Persist governed state, authority references, decisions, checkpoints, execution references, and recovery facts. | Conversation is not a fallback authority store. |
| Artifact handler | Locate artifacts, identify their domain/status/version, validate required structure and links, and detect affected/stale artifacts. | Artifact existence alone is not approval. |
| Evidence registry | Record checks, outcomes, evidence references, coverage, gaps, and regression risk. | Does not create requirements or the Stage09 decision. |
| Status/reporting projector | Build plain-language, qualification-separated views from a consistent persisted snapshot. | Does not infer missing facts or upgrade qualification. |

The normal interaction is: adapter submits an operation; orchestrator loads one repository/Git-backed snapshot; authority resolver and lifecycle governor evaluate it; Human Decision, reasoning, or execution capability is invoked only if eligible; the orchestrator validates and persists the resulting transition; status/reporting projects the committed result. Failures follow the same path and are persisted as truthful outcomes.

## 5. Orchestrator and lifecycle design

### DES-001 - Governed lifecycle aggregate

- **Decision:** Represent each journey as one conceptual lifecycle aggregate containing current stage, stage eligibility, current/completed/next work, scoped `PAUSED`/`BLOCKED`/`INCOMPLETE` conditions, pending decisions, authority summary, authorization and qualification flags, and rerun/invalidation status. The lifecycle governor alone validates transitions; the repository/Git state store persists accepted transitions.
- **Upstream SPEC:** `SPEC-001`, `SPEC-016`.
- **Rationale:** A single consistency boundary prevents contradictory status while keeping approval, authorization, verification, and release distinct.
- **Responsibilities/boundary:** The governor computes eligibility from persisted inputs and gate artifacts. The orchestrator coordinates but cannot set a stronger qualification directly. State may be scoped so independent work can remain eligible.
- **Data/state interaction:** Every transition reads a current snapshot and writes an attributable new state with stage, affected scope, reason, source references, prior-state identity, and next route. Conceptual `.sdd/state` files may hold this state as configured; no conformance is assumed.
- **Failure behavior:** Missing, stale, or contradictory facts reject the transition and record `INCOMPLETE` or `BLOCKED`; no optimistic default is allowed.
- **Verification implication:** Exercise in-progress, paused, blocked, incomplete, resumed, invalidated, and completed snapshots and reject impossible qualification combinations.
- **Downstream constraints for Stage05/06/08:** Stage05 must define who may request transitions; Stage06 tasks must identify affected scope; Stage08 may update execution progress only through validated transitions.

### DES-002 - Explicit lifecycle command processing

- **Decision:** Process `PAUSE`, `RESUME`, `REQUEST_REVISION`, `REJECT_PROPOSAL`, and `APPROVE_DECISION` as identified commands with actor, target, affected scope, expected current-state identity, and reason. Validate, persist, then report each command; retries must be idempotent for the same command identity.
- **Upstream SPEC:** `SPEC-002`.
- **Rationale:** Explicit commands make governing effects visible and prevent stale, ambiguous, unauthorized, or retrospective actions.
- **Responsibilities/boundary:** Interaction adapters capture intent; the orchestrator authenticates the operation context as later governed; the lifecycle governor applies transition rules; the decision manager handles decision-specific commands.
- **Data/state interaction:** Accepted commands append an attributable transition and update the current projection. Revision/withdrawal creates invalidation links rather than erasing history. Independence is an explicit finding tied to scope.
- **Failure behavior:** Identity mismatch, stale target, ambiguity, unauthorized actor, or unmet prerequisite leaves state unchanged and returns the reason and valid route.
- **Verification implication:** Test every command in valid/invalid states, duplicate delivery, stale delivery, affected-scope blocking, and proven-independent continuation.
- **Downstream constraints for Stage05/06/08:** Governance must define allowed actors and protected operations; tasks and execution records must expose stable targets and scope for commands.

### DES-003 - Requirement-readiness evaluator

- **Decision:** Implement requirement readiness as a seven-dimension evaluation: problem, target user, MVP scope, important behavior/flow, critical exception/risk blockers, material scope-changing TBD, and current product-baseline approval. Each dimension has its own result and evidence/authority reference; readiness passes only when all required dimensions pass.
- **Upstream SPEC:** `SPEC-003`.
- **Rationale:** Independent dimensions support focused clarification and prevent downstream technical detail from becoming an improper product blocker.
- **Responsibilities/boundary:** The reasoning provider may identify omissions and draft questions; the Product authority owner decides product content; the governor consumes only recorded results.
- **Data/state interaction:** Intake references and clarification items attach to dimensions. Only affected progression is blocked; non-critical design/technical TBDs are classified outside product readiness.
- **Failure behavior:** Missing or ambiguous material product information remains unresolved; no inference, silence, or AI proposal can become approval.
- **Verification implication:** Cover each dimension independently, combined failures, all approved intake forms, focused questions, and an allowed downstream-detail TBD.
- **Downstream constraints for Stage05/06/08:** Later governance must prevent AI approval; no task or execution may workaround unresolved product readiness.

The orchestrator determines current lifecycle state only from a freshly loaded governed snapshot. It loads all artifacts required by the target operation, asks the resolver for domain-specific authority findings, asks the governor for entry/exit eligibility, and routes eligible work to a reasoning provider, Human Decision, or Stage08 provider. Missing authority or prohibited progression becomes a scoped block. Safe resume repeats all evaluations against current persisted identity; it never relies on a prior chat or cached approval.

## 6. Authority and Human Decision design

### DES-004 - Domain-scoped authority registry and conflict handling

- **Decision:** Maintain a domain-scoped authority registry whose entries identify domain, artifact path, scope, lifecycle owner, status, current version/reference, approval record, dependencies, and affected/stale state. Resolve each question in its owning domain; never compare domains using a global precedence.
- **Upstream SPEC:** `SPEC-004`, `SPEC-010`, `SPEC-016`.
- **Rationale:** Explicit domain ownership implements the non-linear authority graph and makes improper substitutions detectable.
- **Responsibilities/boundary:** The authority resolver reports findings. The owning stage/Human Decision supplies substantive resolution. The orchestrator may block and route but may not rewrite an authoritative artifact.
- **Data/state interaction:** The registry uses these mappings: `PRODUCT_INTENT -> docs/proposal.md`; `PRODUCT_REQUIREMENT -> docs/PRD.md`; `TECHNICAL_CONTRACT -> docs/spec.md`; `IMPLEMENTATION_DECISION -> docs/Design.md`; `AGENT_REPOSITORY_GOVERNANCE -> AGENTS.md`; `EXECUTION_DECOMPOSITION -> tasks.md`; `PRE_IMPLEMENTATION_GATE_DECISION -> docs/handoff/pre-implementation-gate-report.md`; `IMPLEMENTATION_EVIDENCE -> src/**, tests/**, Git`; `IMPLEMENTATION_RECOVERY_DECISION -> docs/handoff/implementation-recovery-gate-report.md`; `VERIFICATION_DECISION -> docs/handoff/verification-report.md`; `RELEASE_DECISION -> docs/handoff/handoff-report.md`.
- **Failure behavior:** A conflict produces a durable conflict record and executes `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`. Missing, expired, withdrawn, stale, or out-of-scope authority blocks only affected work unless dependency analysis proves broader impact.
- **Verification implication:** Demonstrate missing authority, same-domain status differences, cross-domain conflict, unauthorized override, and every prohibited gate substitution.
- **Downstream constraints for Stage05/06/08:** Stage05 must govern artifact mutation and resolution actors; Stage06 links tasks to exact authority versions; Stage08 accepts only the resolved sealed baseline.

Authority status is modeled explicitly:

- `ABSENT`: the expected artifact/reference is missing.
- `DRAFT`: content exists but has no approved authority force.
- `APPROVED_CURRENT_AUTHORITY`: explicit approval exists for the identified domain, scope, and version.
- `STALE_AFFECTED`: a dependency changed or a decision was revised/withdrawn; re-review/rerun is required.
- `CONFLICTING`: two authoritative statements cannot both govern the affected scope; substantive owner resolution is required.

`EXISTS` is an observable file fact, not an authority status. Approval is never inferred from existence, filename, commit, content quality, historical state, or downstream use.

### DES-005 - Durable Human Decision records

- **Decision:** Use durable, append-preserving Human Decision records with a stable `HD-*` identity, subject, authoritative owner, affected scope, reason, consequence, available choices, current status, recorded result, actor/reference, dependencies, and timestamps/version identities. Status supports at least pending, approved, rejected, revision requested, and withdrawn without erasing prior results.
- **Upstream SPEC:** `SPEC-005`, `SPEC-002`, `SPEC-004`.
- **Rationale:** A first-class record makes pending effect, owner, choice, and downstream invalidation inspectable across sessions.
- **Responsibilities/boundary:** The decision manager creates and validates records; the relevant human authority supplies the result; dependency analysis identifies downstream effects; the lifecycle governor decides resulting eligibility.
- **Data/state interaction:** Creation immediately pauses affected work. Approval satisfies only the named decision/authority condition. Rejection prevents adoption. Revision returns subject material to its owner. Withdrawal or revision marks known dependents stale/affected and routes review/rerun. Independence must be recorded before other work continues.
- **Failure behavior:** Collision, ambiguous subject/result, incomplete scope, unauthorized decision actor, or stale decision target cannot unblock work.
- **Verification implication:** Verify uniqueness, understandable presentation, every result path, retained history, pending blocking, independent work, and complete known-dependent invalidation.
- **Downstream constraints for Stage05/06/08:** Governance must define decision authority; tasks must reference required `HD-*`; Stage08 must stop if a referenced decision is pending, stale, revised, rejected, or withdrawn.

A Human Decision approving an upstream artifact can satisfy that artifact's authority requirement. It does not itself create normal new-implementation authorization; only a valid Stage07 `PASS` can do that.

## 7. AI and execution-provider design

### DES-006 - Replaceable reasoning-provider port

- **Decision:** Define a channel-neutral reasoning-provider port that accepts a bounded request, authoritative context references, permitted capabilities, affected scope, and expected structured result. Adapters may support Codex CLI with ChatGPT authentication, an API-backed provider, or a future external command.
- **Upstream SPEC:** `SPEC-006`, `SPEC-009`.
- **Rationale:** Governance truth remains in the governed core rather than any model/vendor, while providers remain replaceable.
- **Responsibilities/boundary:** Providers may analyze, ask, propose, draft, reason, implement only during authorized Stage08, and assist verification. They may not create authority, fabricate state/evidence, bypass Human Decision, override gates, or directly commit lifecycle qualifications.
- **Data/state interaction:** Requests carry references and capability constraints, not implicit chat authority. Results remain proposed/provider output until validated and persisted by the appropriate owner boundary.
- **Failure behavior:** Unavailable, malformed, timed-out, or policy-violating provider output records the exact failed operation, preserves prior state, and offers eligible retry/alternate/escalation routes without semantic downgrade.
- **Verification implication:** Run equivalent governance scenarios through provider substitutes and prove provider choice cannot alter authority, lifecycle, or qualification semantics.
- **Downstream constraints for Stage05/06/08:** Stage05 governs provider permissions; Stage06 describes provider-independent outcomes; Stage08 supplies the authorization envelope before any write-capable invocation.

### DES-007 - Sealed Stage08 execution envelope

- **Decision:** Invoke Stage08 only with an immutable execution envelope identifying approved current PRD, Spec, Design, AGENTS governance, approved task decomposition, valid Stage07 `PASS` report, authorization state, exact task and allowed scope, repository/branch/baseline identity, required verification, and checkpoint conditions.
- **Upstream SPEC:** `SPEC-006`, `SPEC-007`, `SPEC-009`, `SPEC-016`.
- **Rationale:** A sealed envelope separates governance authorization from execution and makes scope overrun objectively detectable.
- **Responsibilities/boundary:** The orchestrator assembles and validates the envelope; the execution adapter enforces it; the coding provider changes only authorized scope; Git records checkpoints; evidence registry records verification. Execution cannot amend the envelope.
- **Data/state interaction:** Each attempt records task, baseline, changed files, diff/checkpoint reference, verification references, valid completed progress, current failure point, and remaining scope. One independently verifiable atomic task is eligible per checkpoint only after configured preconditions hold.
- **Failure behavior:** Missing/invalid Stage07 `PASS`, dirty or mismatched baseline as governed later, unexpected diff, authority overrun, or unmet checkpoint condition stops affected execution. Preserve identifiable valid in-scope progress; do not checkpoint or call it complete unless all checkpoint prerequisites pass. Route additional work back through authority/task/gate owners.
- **Verification implication:** Attempt no-authorization execution, stale authorization, changed authority, scope overrun, partial failure, unexpected diff, and successful authorized atomic execution with evidence.
- **Downstream constraints for Stage05/06/08:** Stage05 must define repository commands, protected scope, and checkpoint rules; Stage06 must make tasks atomic with scope and verification; Stage08 must report files and evidence and never self-authorize follow-on work.

## 8. Persistence and traceability design

### DES-008 - Repository-backed state and bidirectional link index

- **Decision:** Persist important governed state as repository-native, reviewable records and Git identities, with a derived link index for navigation. Persist lifecycle position, authority references/status, Human Decisions, affected scope, task/execution state when owned later, verification references, failures, invalidations, and Recovery Gate provenance. Conversation content may be referenced only after it is deliberately recorded in an owned artifact/state record.
- **Upstream SPEC:** `SPEC-001`, `SPEC-007`.
- **Rationale:** Repository/Git survival and inspectability satisfy cross-session recovery without selecting a database or coupling truth to chat.
- **Responsibilities/boundary:** Artifact owners own substantive documents; the state store owns runtime records; Git supplies version/change/checkpoint identity; the link index is reconstructable and cannot outrank its sources.
- **Data/state interaction:** Stable links extend `G -> FR/NFR/EC -> AC -> SPEC -> DES -> TASK -> CODE -> TEST_EVIDENCE`. Every link names source and target identity plus affected scope; later stages append links without rewriting upstream identifiers.
- **Failure behavior:** Failed writes do not advance the projected state. Broken, ambiguous, or stale required links mark dependent coverage/completion `INCOMPLETE`; chat reconstruction cannot repair them.
- **Verification implication:** Remove session context, reconstruct current state from repository/Git, trace forward and backward, detect a missing/stale link, and verify atomic state publication.
- **Downstream constraints for Stage05/06/08:** Stage05 chooses safe repository conventions; Stage06 must extend `DES -> TASK`; Stage08 must extend `TASK -> CODE -> TEST_EVIDENCE` and attach Git identities.

No specific database is selected. If a future projection/cache is introduced, it must be disposable and rebuildable from repository/Git-backed canonical records.

## 9. Verification and evidence design

### DES-009 - Evidence registry separated from qualification

- **Decision:** Record each verification check independently with stable check identity, criterion, scope, execution status, exactly one result (`PASS`, `FAIL`, `NOT RUN`), execution/evidence reference when run, evidence gap when not run, coverage links, freshness/current-version relation, and regression risk. A separate qualification evaluator consumes these records and gate decisions.
- **Upstream SPEC:** `SPEC-008`, `SPEC-016`.
- **Rationale:** Separating raw evidence from qualification prevents tests or partial success from becoming authority or Stage09 `PASS`.
- **Responsibilities/boundary:** Execution/verification providers emit evidence candidates; evidence registry validates and persists them; Stage09 owns `VERIFICATION_DECISION`; Stage10 owns release decision. Reporting displays both without conflation.
- **Data/state interaction:** `PASS` requires an executed check satisfying its criterion; `FAIL` requires execution not satisfying it; `NOT RUN` means no qualifying execution evidence. Required missing/stale/irrelevant evidence creates a gap and removes dependent qualification.
- **Failure behavior:** Incomplete tests are not verified, partial PASS is not complete, absent evidence is not safe, and non-PASS Stage09 is not release-ready. A test PASS never becomes Stage09 PASS.
- **Verification implication:** Exercise mixed outcomes, missing/stale/irrelevant evidence, partial coverage, forbidden substitutions, and separate complete/verified/safe/ready projections.
- **Downstream constraints for Stage05/06/08:** Stage05 governs evidence commands; Stage06 defines required task checks; Stage08 records outcomes truthfully; Stage09 independently decides conformance.

### DES-010 - Recorded MVP demonstration assembly

- **Decision:** Assemble the MVP demonstration as a manifest of references to governed lifecycle transitions, artifacts, decisions, execution checkpoints, evidence, failures, maintenance scope, and regression results rather than as an independent claim of success.
- **Upstream SPEC:** `SPEC-014`.
- **Rationale:** A reference manifest makes every chain link and governing effect inspectable and prevents narrative claims from replacing evidence.
- **Responsibilities/boundary:** The orchestrator gathers references; owning stages produce the referenced authority/decisions/evidence; Stage09 evaluates completeness and conformance.
- **Data/state interaction:** The manifest identifies every required chain step and proof for authority preservation, AI boundary, Human Decision effect, blocker effect, truthful unverified state, and maintenance regression protection.
- **Failure behavior:** Missing or non-qualifying references leave the demonstration `INCOMPLETE`; the assembler cannot synthesize evidence or a gate result.
- **Verification implication:** Review the complete manifest and deliberately omit each proof class to confirm that completion is withheld.
- **Downstream constraints for Stage05/06/08:** Later artifacts and execution must emit stable references suitable for the manifest; no task may declare the overall MVP qualified by itself.

### DES-011 - Plain-language status projection

- **Decision:** Build status and reports as read-only projections of one consistent governed snapshot, with a plain-language summary followed by identifiers/references. Every report states situation, consequence, affected scope, what remains valid, required user action, next eligible route, and distinct qualification states.
- **Upstream SPEC:** `SPEC-015`, `SPEC-001`, `SPEC-009`.
- **Rationale:** A shared projector prevents channels/providers from inventing semantics while serving non-programmer users.
- **Responsibilities/boundary:** Domain components supply facts; the projector explains but does not decide or mutate them; interaction adapters only format/deliver the projection.
- **Data/state interaction:** Reports carry snapshot/version identity so later inspection can identify staleness. Sensitive detail is replaced with the minimum safe reference/explanation.
- **Failure behavior:** Missing facts remain `TBD`, `INCOMPLETE`, `BLOCKED`, or `NOT RUN` as applicable. If an understandable report cannot be produced, affected interaction remains incomplete and exposes a safe alternate route.
- **Verification implication:** Compare representative clarification, status, decision, failure, evidence-gap, and next-action reports with persisted facts and non-programmer comprehension criteria.
- **Downstream constraints for Stage05/06/08:** Later stages must emit structured facts and safe references; they must not rely on free-form provider prose as the authoritative state.

## 10. Failure, recovery, and safety design

### DES-012 - Durable failure envelope and recovery router

- **Decision:** Represent every AI/provider, command, Git, test, lifecycle, authority, security, or execution failure in a common failure envelope: stable identity, operation/step, affected scope, cause class, persisted pre-operation identity, valid completed work, partial outputs, truthful status, unsafe-continuation flag, and eligible routes.
- **Upstream SPEC:** `SPEC-009`.
- **Rationale:** One minimal envelope gives all failure classes consistent preservation and reporting without pretending their remedies are identical.
- **Responsibilities/boundary:** The failing adapter supplies facts; the orchestrator persists the envelope; authority resolver/lifecycle governor determine eligibility; the recovery router offers only precondition-valid retry, alternate, remediation, revision, escalation, or Human Decision routes.
- **Data/state interaction:** Retry creates a linked attempt and never erases the original. Partial work is retained and classified; only independently valid completed work remains complete.
- **Failure behavior:** Recovery cannot broaden authority, hide the exact failure, retroactively qualify work, or resume unsafe affected scope. Repeated failure stays truthful rather than becoming apparent completion.
- **Verification implication:** Induce each named failure class and verify exact point/scope, preservation, safe blocking, linked retry, and an applicable route.
- **Downstream constraints for Stage05/06/08:** Governance defines permitted recovery operations; tasks expose resumable boundaries; Stage08 reports partial progress without unauthorized cleanup or continuation.

### DES-017 - Append-only post-checkpoint implementation-evidence recovery

- **Decision:** Add a distinct, explicitly authorized recovery-attestation path alongside, not inside or in place of, ordinary atomic Stage08 evidence creation. A recovery attestation is a versioned repository record with these required conceptual fields: `record_kind=POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY`; evidence schema/version; stable recovery-attempt identity and deterministic sequence relation to earlier attempts; task identity; historical implementation checkpoint commit identity and its Git tree identity; task-attributable checkpoint changed paths and content/diff digest; applicable authority-baseline identities and task-contract digest; exact authoritative verification-command text and command digest; truthful verification outcome, exit status, complete-result indicator, bounded stdout/stderr references or captures, start/end time, and timeout state; recovery-authorization identity, scope digest, status, and validity interval or single-use state as later governed; execution adapter/tool identity and version plus interpreter, host-or-sandbox mode, working-directory/repository identity, and material environment facts; pre- and post-verification HEAD, tracked implementation-tree identity, and worktree observations proving no implementation mutation; record creation time; links to prior attempt and ordinary evidence, when present; and a canonical record-content digest. Field representation and canonical serialization are selected here as a versioned JSON object because the current evidence registry already persists Stage08 evidence as JSON; schema evolution must reject unsupported required semantics and must not reinterpret older ordinary records.
- **Upstream SPEC:** `SPEC-017`, preserving `SPEC-007`, `SPEC-008`, `SPEC-009`, and `SPEC-016`.
- **Rationale:** An independently typed, content-bound attestation can establish new proof about an unchanged historical checkpoint without amending Git history or pretending the proof existed at checkpoint time. Reusing the ordinary record shape or ordinary checkpoint validator would make arbitrary later evidence indistinguishable from authorized recovery.
- **Ordinary/recovery discriminator:** Ordinary evidence retains its existing record kind or legacy ordinary interpretation, atomic checkpoint membership, sealed-envelope bindings, and qualification rules unchanged. Only the exact recovery discriminator enters this recovery pipeline. Missing, unknown, or contradictory discriminator/schema information is non-qualifying; the ordinary writer and validator never infer recovery, and the recovery validator never upgrades an ordinary record that failed ordinary atomicity.
- **Checkpoint linkage and integrity:** Resolve the attestation's full checkpoint commit identity without symbolic-name substitution; require the commit to exist and be an ancestor of the governed current history; compare its recorded Git tree identity with Git; reconstruct the checkpoint's task-attributable diff against its governed parent; require every changed implementation path to be within the bound task scope; and compare the ordered path/content or diff digest with the attestation and bound task contract. Later commits do not invalidate recovery merely because they follow the checkpoint, but cannot change the historical objects, supply missing checkpoint content, or be included in the verified implementation snapshot. Verification executes against an isolated exact view of the historical checkpoint while persistence occurs only on the current governed branch after confirming that branch and history remained unchanged. Merge ambiguity, missing parent identity, rewritten ancestry, content mismatch, or inability to isolate the checkpoint blocks recovery. No recovery operation amends, rebases, replaces, or otherwise mutates the historical commit.
- **Verification execution:** Obtain the command as exact stored text from the applicable authorized task contract after validating that contract and authority baseline against the recovery authorization. Preserve that text byte-for-byte as command identity; parsing into an argument vector may enforce the existing command policy but cannot normalize, rewrite, substitute, or broaden it. The existing verification policy validates the command, and the existing verification execution boundary runs it once against the isolated checkpoint, capturing bounded stdout/stderr, start/end time, exit status, timeout, environment/tool provenance, and completeness. Exit zero plus complete criterion satisfaction records `PASS`; an executed nonzero or unsatisfied criterion records `FAIL`; no qualifying start or unavailable execution records `NOT RUN`; timeout or incomplete capture records the deterministic non-qualifying outcome selected by the existing verification contract and retains the timeout/incompleteness fact. Results from another attempt are never reused unless an explicit recovery authorization and applicable contract allow the exact repository-backed instance; chat, Stage07 prose, and unbound logs are never inputs to qualification.
- **Recovery authorization:** The orchestrator accepts only a repository-backed authorization reference whose validated content identifies authorization ID, `POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY`, task, full checkpoint identity, repository/branch, authority baseline, exact command or digest, permitted evidence/state artifacts, validity conditions, and expiry/single-use rule. The recovery attempt seals these values and records their digest before verification. Missing, ambiguous, expired, consumed, withdrawn, mismatched, stale, or overbroad authorization blocks before execution or persistence. Stage05 owns who may issue the authorization and its repository-operation policy; this decision defines only the data and enforcement boundary needed to implement SPEC-017.
- **Persistence and keying:** Persist each recovery attempt as a new JSON record under the existing `.sdd/evidence/` registry namespace, using a collision-resistant key that includes sortable creation time, exact task ID, the `recovery` discriminator, and stable attempt ID. Publish through write-to-temporary, flush/close, atomic replace-if-absent semantics; never overwrite, rename over, or delete ordinary or recovery evidence. The recovery evidence checkpoint may contain only the new authorized recovery/audit artifacts and must never be treated as the implementation checkpoint. Canonical content digest plus the semantic key `(task, historical checkpoint, authority baseline, authoritative command, attempt)` detects replay. A byte/semantic-identical duplicate is idempotently recognized and creates no additional qualification. A reused attempt identity with different content, incompatible records claiming the same execution, or irreconcilable checkpoint/command/authority claims is a conflict: retain all records, report them, and block reconciliation pending authoritative resolution. Sequential failed attempts followed by a separately authorized valid attempt are not erased or conflated; the later attempt may qualify if independently valid and no unresolved conflict applies.
- **Qualification pipeline and ownership:** The SDD Orchestrator first loads a fresh repository snapshot and delegates authority validation to the authority resolver. The Stage08 execution adapter coordinates the sealed recovery attempt. The Git state boundary validates commit identity, ancestry, tree/diff content, task-scope paths, current branch/HEAD stability, and no-mutation observations. The verification-policy and verification-execution boundaries validate and run the exact command. The evidence registry writes the candidate and owns schema/provenance validation. A recovery-evidence admissibility function at the evidence-registry boundary then validates, in order: supported schema/discriminator; authorization; task and task-contract digest; authority baseline; checkpoint existence/reachability/tree/diff/scope integrity; exact command; fresh complete execution; `PASS` and exit zero; environment/tool provenance; no implementation mutation; append-only persistence identity; and duplicate/conflict state. It emits only `QUALIFYING` or a stable non-qualifying reason code such as `AUTHORITY_INVALID`, `TASK_MISMATCH`, `CHECKPOINT_UNREACHABLE`, `CHECKPOINT_CONTENT_MISMATCH`, `SCOPE_MISMATCH`, `COMMAND_MISMATCH`, `VERIFICATION_FAILED`, `VERIFICATION_NOT_RUN`, `VERIFICATION_INCOMPLETE`, `IMPLEMENTATION_MUTATED`, `EVIDENCE_CONFLICT`, or `PERSISTENCE_FAILED`; unknown conditions fail closed. No new module is architecturally required.
- **Existing module ownership:** `sdd_orchestrator/evidence_writer.py` owns the versioned recovery record model, atomic append-only writer, duplicate/conflict inspection, and admissibility result; `sdd_orchestrator/codex_adapter.py` coordinates preflight, authorization sealing, isolated verification, evidence qualification, and refusal without changing ordinary Stage08 flow; `sdd_orchestrator/git_runtime.py` owns commit/ancestry/tree/diff/scope integrity, stable repository observations, evidence-only checkpointing, and the later separately invoked implementation-state reconciliation boundary; `sdd_orchestrator/verification_policy.py` owns exact-command policy, while `sdd_orchestrator/verification_execution.py` and `sdd_orchestrator/verification_runtime.py` own execution and environment provenance. The orchestrator/lifecycle boundary consumes qualification but cannot manufacture it. Concrete class/function names remain downstream implementation detail.
- **State reconciliation boundary:** A qualifying attestation emits an immutable reference that can satisfy only the evidence prerequisite of a separately authorized implementation-state reconciliation operation. The evidence writer never updates implementation state. The reconciliation boundary reloads Git, authorities, task state, all relevant evidence, and conflicts; it refuses non-qualifying, missing, stale, or conflicting references and advances no farther than the proven checkpoint/task. Persistence of evidence does not produce Stage07 `PASS`, normal Stage08 authorization, Stage09 qualification, Stage10/release authority, or deployment authority.
- **Atomic failure and resume behavior:** Verification and recovery-record publication are separate atomic boundaries because verification cannot be rolled back. If verification succeeds but publication fails, persist or report a non-qualifying linked failure envelope without advancing state; a retry requires current authorization and must either idempotently publish the exact captured result when its sealed provenance remains eligible or execute fresh verification when reuse is not explicitly permitted. If evidence publishes but its evidence-only Git checkpoint fails, retain the uncommitted record as blocked recoverable state and refuse reconciliation until repository-backed publication qualifies. If qualifying evidence is committed but later reconciliation fails, keep evidence immutable and retry only reconciliation from a fresh snapshot. Resume discovers records and pending failure state by stable attempt/content identity, never by chat. Divergent duplicate contents, evidence/state disagreement, changed HEAD/branch during the attempt, or multiple incompatible qualifying candidates is split-brain and blocks with all facts preserved.
- **Compatibility and failure behavior:** Existing ordinary Stage08 atomic evidence, sealed-envelope enforcement, checkpoint-history recovery, evidence registry outcomes, and Stage09/10 separation remain unchanged. Recovery cannot qualify an arbitrary evidence-only commit, rewrite history, mutate implementation scope, replace ordinary evidence, infer authorization, or silently fall back. Any failed binding returns its stable reason, leaves historical and current implementation state unchanged, records the attempt when safely possible, and routes to the applicable owner.
- **Verification implication:** Stage06 must make the implementation work independently verifiable for: valid recovery; wrong task/checkpoint/command; unreachable checkpoint; altered tree/diff/content; out-of-scope checkpoint paths; nonzero/`FAIL`; timeout, incomplete result, and `NOT RUN`; chat/Stage07/stale-result substitution; absent, expired, consumed, mismatched, stale, or overbroad authority; implementation mutation; later unrelated commits; identical duplicate; conflicting evidence; prior failed then valid attempt; persistence and evidence-checkpoint failure; idempotent retry; interrupted resume; split-brain detection; reconciliation blocked before and permitted after qualification; ordinary Stage08 evidence/checkpoint recovery regression; sealed-envelope non-weakening; and rejection of Stage07, Stage09, Stage10/release, or deployment upgrade.
- **Downstream constraints for Stage05/06/08:** Stage05 must govern the recovery-authority issuer, protected operations, allowed artifact scope, expiry/consumption, and checkpoint policy. Stage06 must decompose the capability into an atomic task with explicit files, dependencies, exact verification, preservation obligations, and negative cases; this decision neither creates nor authorizes that task. Stage08 may implement or execute recovery only after a fresh valid Stage07 authorization for that exact task and scope.

### DES-013 - Safety interlock and minimum-disclosure reporting

- **Decision:** Place a safety interlock before destructive/high-risk operations and before resuming security- or authority-blocked scope. It validates exact target/scope, required explicit authorization, current authority identity, and absence of unresolved blockers. Reports minimize sensitive values while retaining actionable category, scope, owner, and safe reference.
- **Upstream SPEC:** `SPEC-010`, `SPEC-004`.
- **Rationale:** Centralized preflight prevents automatic bypass and avoids leaking secrets in otherwise useful reports.
- **Responsibilities/boundary:** Adapters identify proposed operation; the interlock requests authorization/owner resolution; Human Decision handles required explicit consent; authority owner resolves conflicts. No component may self-clear its own blocker.
- **Data/state interaction:** Persist confirmation identity and bounded target, not unnecessary sensitive content. Security blockers propagate to all proven-dependent work; unaffected isolation requires an explicit dependency finding.
- **Failure behavior:** Ambiguous target, missing confirmation, unauthorized scope, security concern, or authority conflict yields `BLOCKED`. Conflicts follow the required four-step protocol; automatic continuation remains forbidden.
- **Verification implication:** Exercise destructive, high-risk, security, and conflict cases; bypass attempts; sensitive-data redaction; authorized safe continuation; and unaffected-scope isolation.
- **Downstream constraints for Stage05/06/08:** Stage05 must define concrete protected operations and confirmation policy; Stage06 must expose risk/scope; Stage08 must call the interlock and cannot suppress its result.

### Existing-implementation recovery path

The lifecycle governor maintains two distinct provenance paths:

```text
NORMAL:
Stage01 -> Stage02 -> Stage03 -> Stage04 -> Stage05 -> Stage06
-> Stage07 PASS -> Stage08 -> Stage09 -> Stage10

PRE-EXISTING IMPLEMENTATION RECOVERY:
approved current authority package + approved recovery authority
-> Current Implementation Recovery Gate
-> if PASS, Stage09 entry only
```

The Recovery Gate is eligible only for materially pre-existing implementation, historical project-specific Stage07 decision `NOT_FOUND`, explicit project-authority recovery approval, and the other configured recovery prerequisites. It never retroactively creates Stage07 `PASS` or Stage08 authorization and does not prove code conformance, tasks done, tests PASS, Stage09 PASS, Stage10 authorization, or release authorization. Any implementation gap found after Stage09 must return to valid current authority and the normal `Stage07 -> Stage08` path. This authority does not evaluate the current Recovery Gate.

## 11. Maintenance and regression design

### DES-014 - Modification impact and preservation ledger

- **Decision:** Before qualifying a modification, create an impact ledger that separates requested behavior/data change, affected existing behavior/data, preservation scope, authority basis, observed implementation evidence, ambiguity, and risk. Observed behavior can inform the ledger but cannot become product authority.
- **Upstream SPEC:** `SPEC-011`.
- **Rationale:** Explicit separation keeps maintenance scope bounded and makes preservation obligations visible.
- **Responsibilities/boundary:** Reasoning may propose impact analysis; authority resolver identifies governing requirements/contracts; Human Decision resolves material product ambiguity; Stage08 changes only authorized scope.
- **Data/state interaction:** Ledger entries link to requirements, SPEC/DES, later tasks/code/evidence, and explicit preservation expectations. Unknown material impact remains marked.
- **Failure behavior:** Materially unknown affected or preservation scope blocks dependent authorization/completion and routes clarification to the appropriate owner.
- **Verification implication:** Classify affected, preserved, ambiguous, and merely observed behavior/data and verify observed evidence is not promoted to authority.
- **Downstream constraints for Stage05/06/08:** Stage06 tasks must carry change and preservation scope; Stage08 must report deviations; Stage09 checks both requested change and preservation.

### DES-015 - Regression coverage and completion guard

- **Decision:** Derive a regression coverage view from the impact ledger and evidence registry, linking every affected behavior/data risk to applicable evidence or an explicit gap. An overall-completion guard withholds completion unless required regression evidence qualifies.
- **Upstream SPEC:** `SPEC-012`, `SPEC-008`.
- **Rationale:** This prevents new-feature success from masking unverified regression risk.
- **Responsibilities/boundary:** Stage06 later defines task verification, Stage08 produces evidence, evidence registry records it, and Stage09 decides verification. The guard projects eligibility only.
- **Data/state interaction:** Full, partial, absent, stale, and new-feature-only evidence remain distinguishable; gaps name exposed behavior/data risk and restriction.
- **Failure behavior:** Missing required regression evidence warns the user and withholds overall completion; it cannot be waived by unrelated PASS evidence.
- **Verification implication:** Exercise full, partial, none, stale, and new-feature-only coverage with correct qualifications.
- **Downstream constraints for Stage05/06/08:** Tasks must include applicable regression checks and evidence links; execution cannot mark the modification complete from new behavior alone.

The modification workflow is therefore:

```text
request -> identify affected behavior/data -> identify preservation scope
-> authority check -> Stage07-authorized change -> regression verification
-> unresolved-risk reporting -> Stage09/Stage10-owned qualification
```

## 12. Interaction-channel design

### DES-016 - Channel-neutral governed operation port

- **Decision:** Expose one application boundary for `SUBMIT_REQUEST`, `INSPECT_STATUS`, `CONTINUE_OR_RESUME`, `PAUSE`, `RECEIVE_DECISION`, `APPROVE`, `REJECT`, `REQUEST_REVISION`, `RECEIVE_FAILURE_OR_BLOCKER`, and `RECEIVE_VERIFICATION_SUMMARY`. Each operation uses stable journey/target identities and returns the same governed result regardless of adapter.
- **Upstream SPEC:** `SPEC-013`, `SPEC-015`.
- **Rationale:** The MVP can remain local while a future `LINE -> webhook -> SDD Orchestrator -> AI/development execution -> repository/Git/verification` route reuses identical semantics.
- **Responsibilities/boundary:** Local CLI or other MVP adapter handles presentation/delivery; future LINE/webhook adapters translate transport only; orchestrator/governor own operations and effects.
- **Data/state interaction:** Adapter input becomes an attributable command; output is a snapshot-bound status/report. Delivery failure never changes approval or lifecycle state unless the governed command was already validly committed.
- **Failure behavior:** Duplicate, stale, malformed, or unavailable-channel operations are rejected or safely replayed by identity. A suitable alternate channel may resume from repository state; channel silence is never approval.
- **Verification implication:** Complete the essential journey locally, compare semantics across any later adapter, and test duplicate delivery, channel failure, and session loss.
- **Downstream constraints for Stage05/06/08:** Do not bind governance or tasks to LINE, webhook schema, hosting, or vendor technology; execution is invoked only through the governed core.

No webhook provider, message schema, networking stack, hosting platform, or cloud architecture is selected.

## 13. Requirement/SPEC-to-DES traceability

The approved upstream `G -> FR/NFR/EC -> AC -> SPEC` links remain unchanged. This approved current authority extends them as follows:

| P0 technical contract | Implementation-design coverage |
| --- | --- |
| `SPEC-001` | `DES-001`, `DES-008`, `DES-011` |
| `SPEC-002` | `DES-002`, `DES-005` |
| `SPEC-003` | `DES-003` |
| `SPEC-004` | `DES-004`, `DES-005`, `DES-013` |
| `SPEC-005` | `DES-005` |
| `SPEC-006` | `DES-006`, `DES-007` |
| `SPEC-007` | `DES-007`, `DES-008` |
| `SPEC-008` | `DES-009`, `DES-015` |
| `SPEC-009` | `DES-006`, `DES-007`, `DES-011`, `DES-012` |
| `SPEC-010` | `DES-004`, `DES-013` |
| `SPEC-011` | `DES-014` |
| `SPEC-012` | `DES-015` |
| `SPEC-013` | `DES-016` |
| `SPEC-014` | `DES-010` |
| `SPEC-015` | `DES-011`, `DES-016` |
| `SPEC-016` | `DES-001`, `DES-004`, `DES-007`, `DES-009` |
| `SPEC-017` | `DES-017` |

Coverage is 17 of 17 applicable P0 technical contracts. Stage06 must extend each applicable chain from `DES -> TASK`; Stage08 must extend `TASK -> CODE -> TEST_EVIDENCE`; Stage09 must verify bidirectional navigation and cannot infer missing links.

## 14. Deferred implementation choices / TBDs

The following choices are deliberately deferred because no approved SPEC requires them now: programming language; framework; package/class names; concrete file layout beyond authoritative artifact and evidence-namespace paths; database product; cache/index technology; API or webhook schema; local UI technology; test framework and commands; Git branch/commit convention beyond governed checkpoint semantics; cloud/hosting/network provider; LINE integration details; authentication/IAM product; secrets product; deployment topology; and additional AI vendors.

These are non-blocking Design TBDs. Stage05 may decide repository-governance details in its own domain; Stage06 may decompose only approved implementation scope. Any future choice that changes approved product behavior or a technical guarantee must be detected as a cross-domain conflict and routed upstream, not decided as implementation detail.

## 15. Authority boundaries

- This document is the approved CURRENT prospective authority for `IMPLEMENTATION_DECISION` content only.
- It does not create or modify `PRODUCT_INTENT`, `PRODUCT_REQUIREMENT`, or `TECHNICAL_CONTRACT` authority.
- It does not define `AGENT_REPOSITORY_GOVERNANCE`, `EXECUTION_DECOMPOSITION`, implementation evidence, gate results, verification decisions, or release decisions.
- Artifact existence, this authority's completeness, and its approval do not authorize implementation.
- Normal implementation remains `Stage05 -> Stage06 -> Stage07 PASS -> Stage08`.
- Stage07, Stage09, and Stage10 retain their distinct owning semantics.
- Tests and code are evidence, not requirement/design authority. Limited implementation inspection supplied terminology only and did not establish conformance or adopt implementation as authority; tests were not evaluated.
- Telemetry remains observational and outside control paths.
- Cross-domain review found no decision requiring a change to approved product requirements or technical contracts. A later discovered conflict must follow `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`.
- This authority does not create Stage07 `PASS`, authorize Stage08 implementation, evaluate the Recovery Gate, create Stage09 `PASS`, or create Stage10, release, or deploy authority. Every downstream authority requires independent approval.

## 16. Current Implementation Design status

```text
CURRENT_IMPLEMENTATION_DECISION_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

HISTORICAL_PHASE04_RECONSTRUCTION =
NOT_AUTHORIZED

PRODUCT_INTENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

PRODUCT_REQUIREMENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

TECHNICAL_CONTRACT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

P0_DESIGN_COVERAGE_COMPLETE =
YES

PRODUCT_REQUIREMENT_CONFLICT =
NONE_DETECTED

TECHNICAL_CONTRACT_CONFLICT =
NONE_DETECTED

BLOCKING_DESIGN_TBD =
NO

IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

IMPLEMENTATION_DESIGN_PROJECT_AUTHORITY_REVIEW_REQUIRED =
NO

NEXT_STEP =
CURRENT_AGENT_REPOSITORY_GOVERNANCE_DEFINITION
```
