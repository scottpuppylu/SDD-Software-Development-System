# Current Proposal Decision Brief

## 1. Purpose

This brief prepares the minimum explicit project-authority decisions required before drafting a current `docs/proposal.md`. It is decision preparation only. It does not establish or approve `PRODUCT_INTENT`, create canonical goal identifiers, reconstruct historical Phase01 authority, authorize implementation, or evaluate Stage09.

Stage01 owns `PRODUCT_INTENT`. Its required current content is `PRODUCT_VISION`, `USER_PROBLEM`, `TARGET_USER`, `USAGE_CONTEXT`, `DESIRED_OUTCOME`, `CORE_VALUE_PROPOSITION`, `CORE_INTERACTION_CONCEPT`, `MVP_INTENT_BOUNDARY`, `NON_GOALS`, `CONFIRMED_CONSTRAINTS`, and `EVIDENCE_ASSUMPTIONS_TBD`. Future canonical goal anchors will be required for downstream traceability, but their meanings and identifiers must be created only after the project authority approves the intent they represent.

## 2. Product-intent authority boundary

The classifications used for every candidate statement in this brief are exactly:

- `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY`: current authority supports the statement within its stated scope. This does not automatically make a lifecycle, governance, Phase04, or telemetry fact a product vision, user value, or goal.
- `CONTEXT_ONLY_REQUIRES_PROJECT_AUTHORITY_APPROVAL`: current bounded authority or evidence can inform a product-intent decision, but project-authority approval is required before it is included as `PRODUCT_INTENT`.
- `HISTORICAL_ONLY_NOT_PRODUCT_AUTHORITY`: the statement is historical evidence within its original scope and cannot establish current product intent.
- `UNSUPPORTED_REQUIRES_DECISION`: the required current product-intent statement is not established and must be decided or explicitly retained as unresolved.

Authority is domain-specific and non-linear. `docs/proposal.md`, once explicitly approved, is the authoritative artifact for `PRODUCT_INTENT`; lifecycle files, closure authority, Phase04 closure, and the telemetry contract retain their own bounded authority. Code and tests are implementation evidence and cannot be promoted directly into product authority. Historical COMPLETE / PASS records cannot be converted into current intent.

## 3. Current supported context

The following is the complete bounded context from the authorized inputs that may support proposal decisions. The product-intent relevance column prevents a supported fact from being silently promoted into a product choice.

| Candidate statement | Classification | Product-intent relevance and boundary |
| --- | --- | --- |
| This repository is the SDD Software Development System, version `3.1-codex-default`. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Supported identity context. It does not uniquely determine the current vision, users, problem, value, or intended boundary. |
| The system's currently stated purpose is to execute the SDD 01-10 lifecycle as a governed software development system, using repository artifacts as persistent state instead of manual copy/paste or chat memory. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | A current system-purpose statement that can inform `PRODUCT_VISION`, `USER_PROBLEM`, `USAGE_CONTEXT`, `DESIRED_OUTCOME`, and `CORE_VALUE_PROPOSITION`; those product-intent formulations still require explicit project-authority decisions. |
| The lifecycle is sequentially gated across Stage01-10, while knowledge dependencies form a non-linear, domain-specific authority graph. Repository and Git state are authoritative execution state; chat memory is not. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Lifecycle/governance context and a possible confirmed-constraint candidate, not by itself product value or a complete interaction concept. |
| Stage01 owns `PRODUCT_INTENT`; a current proposal must contain the eleven repository-native content categories and later stable goal anchors. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Governs proposal form and coverage. It supplies no substantive answers and creates no anchors. |
| Cross-domain conflicts follow `DETECT`, `REPORT`, `BLOCK`, and `ROUTE_TO_AUTHORITATIVE_OWNER`; no linear authority priority is allowed. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Governance context and a possible confirmed-constraint candidate. Elevation into product-level constraints requires approval. |
| The current authority package is prospective; it must not be represented as recovered or historically present Phase01-03 authority. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | A mandatory authority boundary for drafting and provenance, not a product vision or user benefit. |
| Phase04 Manifested Context Optimization is `COMPLETE / PASS / CLOSED`. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Current bounded status context only. It does not establish whole-product intent or project completion. |
| Within Phase04, authority coverage is required to be 100%, authority byte mismatch is required to be 0, `BASELINE` is canonical/default, and `OPTIMIZED` is explicit-attempt-only. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Exact Phase04 invariants. Their elevation into product-level `CONFIRMED_CONSTRAINTS` requires an explicit scope-preserving decision. |
| Phase04 also freezes fail-closed behavior for `UNKNOWN` and `MIXED_AUTHORITY`, exact governance, no invented task identity, maximum one provider/subprocess call per logical execution, no partial optimized dispatch, and no post-dispatch baseline retry. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Exact bounded operational constraints. They must not be generalized into whole-product promises without approval. |
| Phase04 authorizes neither persistence, cross-run trust, nor provider reuse; current reducible scope is `GIT_HISTORY` under `sdd.git-history.newest8-oldest2-v1`; it makes no provider-token savings claim. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Exact bounded constraints/non-claims that may inform boundary, non-goals, assumptions, or confirmed constraints only after a product-level inclusion decision. |
| Telemetry schema `sdd.measurement.stage_execution` version `1.0.4` is a bounded Phase03A naming and serialization contract. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Technical-contract context only; it is not a whole-system product contract or product goal. |
| Telemetry is observational, metadata-minimized, best-effort, and non-interfering; it is not lifecycle authority and cannot decide lifecycle behavior. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Exact telemetry constraint and a candidate product-level confirmed constraint only if project authority explicitly elevates it without expansion. |
| Telemetry persistence is disabled by default, environment-configured, external-only when safety is established, and falls back to `NullTelemetrySink`; prohibited content and secrets must not be persisted. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Exact bounded telemetry facts. Whether they belong in product intent rather than later requirements/specification must be decided. |
| No Phase05 or later numbered project phase, no unfinished numbered phase or milestone, and no new implementation are currently authorized. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Current closure and authorization boundary. It constrains this work but does not uniquely define the intended product boundary or future roadmap. |
| Current closure authority enables Stage09 whole-project verification and, only after Stage09 `PASS`, Stage10 evaluation under repository-native rules; neither result is predetermined. | `DIRECTLY_SUPPORTED_CURRENT_AUTHORITY` | Current lifecycle-purpose context. Stage09 still lacks the approved current package needed for evaluation and this fact is not itself a product outcome. |

## 4. Items that are not yet product authority

| Candidate statement or information | Classification | Why it cannot currently be product authority |
| --- | --- | --- |
| Phase01-03 COMPLETE / PASS records, Phase02 and Phase03 names, and incomplete recovered Phase03A context establish the historical product vision, problem, users, scope, milestones, outcomes, or roadmap. | `HISTORICAL_ONLY_NOT_PRODUCT_AUTHORITY` | Historical evidence remains bounded evidence; complete historical authority is unrecoverable and reconstruction is not authorized. |
| Phase04 closure establishes the whole-product vision, primary user problem, target users, core value, interaction model, or present MVP. | `CONTEXT_ONLY_REQUIRES_PROJECT_AUTHORITY_APPROVAL` | Phase04 authority is complete only for manifested context optimization and cannot be expanded into whole-product intent. |
| The telemetry contract establishes a product goal, a required user-facing capability, the whole-system technical contract, or the primary value proposition. | `CONTEXT_ONLY_REQUIRES_PROJECT_AUTHORITY_APPROVAL` | It is exact only for bounded Phase03A measurement and is explicitly observational rather than lifecycle authority. |
| Lifecycle and governance rules automatically constitute the product vision or user value. | `CONTEXT_ONLY_REQUIRES_PROJECT_AUTHORITY_APPROVAL` | They define system operation and authority handling; the project authority must decide which, if any, are product-level intent or constraints. |
| Existing repository behavior, source, or tests establish what the product is intended to do. | `CONTEXT_ONLY_REQUIRES_PROJECT_AUTHORITY_APPROVAL` | Implementation evidence cannot create product authority, and source/test body inspection is outside this brief's authorization. |
| Current market, business objective, success measures, personas, user workflows, features, roadmap, future phases, and promised outcomes. | `UNSUPPORTED_REQUIRES_DECISION` | The authorized current inputs do not establish them. They must be decided, omitted where not required, or marked as explicit assumptions/TBDs. |
| A complete current `PRODUCT_VISION`, `USER_PROBLEM`, `TARGET_USER`, `USAGE_CONTEXT`, `DESIRED_OUTCOME`, `CORE_VALUE_PROPOSITION`, or `CORE_INTERACTION_CONCEPT`. | `UNSUPPORTED_REQUIRES_DECISION` | Current authority supplies partial context but not approved, complete product-intent statements. |
| The current `MVP_INTENT_BOUNDARY` and product-level `NON_GOALS`. | `UNSUPPORTED_REQUIRES_DECISION` | Existing non-authorizations and bounded subsystem exclusions constrain the decision but do not uniquely select the intended product boundary. |
| Which bounded lifecycle, closure, Phase04, and telemetry facts are product-level `CONFIRMED_CONSTRAINTS`. | `UNSUPPORTED_REQUIRES_DECISION` | Same-domain, scope-preserving elevation into product intent requires project-authority approval. |
| Which uncertainties should remain in `EVIDENCE_ASSUMPTIONS_TBD`. | `UNSUPPORTED_REQUIRES_DECISION` | No current authority decides which unresolved matters are acceptable for proposal drafting or which block it. |
| The meanings, grouping, wording, numbering, or count of future canonical goal anchors. | `UNSUPPORTED_REQUIRES_DECISION` | Anchors must represent approved intent. No goal identifiers may be created during decision preparation. |

## 5. Project-authority decisions required

Six grouped questions are the smallest sufficient set covering all Stage01 required content. They intentionally do not recommend or supply answers.

### Question 1: Product vision, problem, outcome, and value

- **Decision needed:** What is the current `PRODUCT_VISION`; what primary `USER_PROBLEM` does the SDD system solve; what `DESIRED_OUTCOME` matters; and what is its `CORE_VALUE_PROPOSITION`?
- **Why required:** These four statements provide the causal product-intent spine needed to determine why the product exists and to support later requirements and goal traceability.
- **Current evidence that can inform it:** The system is an SDD Software Development System whose stated purpose is governed execution of Stage01-10 using repository/Git artifacts as persistent state instead of manual copy/paste or chat memory; current closure authority seeks a valid Stage09 comparison baseline and eventual Stage10 evaluation.
- **Must not be inferred:** Historical Phase01 vision; business or market goals; user value from Phase04 completion; token-savings value; whole-product intent from telemetry; or intended behavior from code/tests.
- **Downstream impact:** Establishes the intent basis for future canonical anchors and PRD goal traceability; constrains Spec and Design without defining their contracts or choices; supplies Stage09's top-level intent lineage but does not decide Stage09.

### Question 2: Target users, usage context, and interaction concept

- **Decision needed:** Who are the primary `TARGET_USER` or user groups, in what `USAGE_CONTEXT` do they use the system, and what is the `CORE_INTERACTION_CONCEPT` by which they engage with it?
- **Why required:** Stage01 requires an explicit answer to “for whom” and a usable interaction concept; later requirements cannot reliably distinguish primary workflows, actors, or externally meaningful behavior without it.
- **Current evidence that can inform it:** The system executes a governed lifecycle; repositories and Git provide persistent execution state; reasoning stages, an implementation runner, gates, authority owners, and human intervention for missing authoritative decisions are established lifecycle context.
- **Must not be inferred:** That the primary user is a developer, product owner, coding agent, operator, or any combination; a CLI, API, chat, file-editing, or orchestration workflow as the primary interaction; user skill level, organization type, or deployment model.
- **Downstream impact:** Determines PRD actors and workflows, Spec interfaces and interaction contracts where applicable, Design boundaries, and which Stage09 evidence is relevant to intended use.

### Question 3: Current intended boundary and explicit non-goals

- **Decision needed:** What is inside the current `MVP_INTENT_BOUNDARY`, and what explicit product-level `NON_GOALS` are outside it?
- **Why required:** A current proposal needs a bounded system intent so downstream authors do not invent features, phases, requirements, implementation, or release scope.
- **Current evidence that can inform it:** No Phase05 or unfinished numbered milestone is established; no new implementation, release, deployment, telemetry change, or lifecycle change is authorized; Phase04 future-only work requires separate authority; Stage09 and conditional Stage10 evaluation are the current closure path.
- **Must not be inferred:** That the current MVP equals all existing code, Phase04, telemetry, the closure package, or the Stage01-10 lifecycle in every detail; that deferred Phase04 items are permanent product non-goals; that absence of authorization means permanent exclusion; or that Stage09 authorization defines product scope.
- **Downstream impact:** Controls PRD scope and priorities, limits Spec and Design coverage, prevents unauthorized tasks or implementation, and defines the boundary against which Stage09 traceability and conformance can later be evaluated.

### Question 4: Product-level confirmed constraints

- **Decision needed:** Which exact, bounded lifecycle/governance, closure, Phase04, and telemetry facts should be elevated into product-level `CONFIRMED_CONSTRAINTS`, with what unchanged scope and wording?
- **Why required:** The facts are valid current authority in their own domains, but inclusion in product intent is a separate domain decision. Only product-relevant constraints should shape downstream requirements.
- **Current evidence that can inform it:** Domain-specific authority and conflict handling; repository/Git persistence; Phase04's 100% authority coverage, zero byte mismatch, canonical `BASELINE`, explicit-only `OPTIMIZED`, fail-closed and call-cardinality invariants; telemetry's observational, metadata-minimized, non-interfering, external-safe, schema-1.0.4 boundaries; and current non-authorizations.
- **Must not be inferred:** That every technical or governance invariant is a product constraint; that any bounded fact applies system-wide; that telemetry is a product feature; that Phase04 creates a provider-token savings promise; or that current non-authorization is necessarily a permanent non-goal.
- **Downstream impact:** Approved constraints become inputs to PRD decisions and, where applicable, later Spec and Design coverage. Unapproved facts remain bounded authority/context only and cannot be used as product-level Stage09 criteria.

### Question 5: Evidence, assumptions, and unresolved TBDs

- **Decision needed:** Which matters should be recorded under `EVIDENCE_ASSUMPTIONS_TBD`; which are evidence only; which assumptions, if any, are provisionally acceptable; and which unresolved decisions block proposal drafting?
- **Why required:** Stage01 requires explicit handling of evidence, assumptions, and TBDs, while the proposal approval gate requires blocking product-intent questions to be resolved rather than hidden.
- **Current evidence that can inform it:** Historical Phase01-03 gaps remain unrecoverable; Phase04 and telemetry are bounded; current users, market, metrics, workflows, and whole-product outcomes are not established; source/test body review is deferred; Stage09 is not evaluated.
- **Must not be inferred:** Missing information from chronology, phase numbering, filenames, implementation, tests, historical status, or telemetry observations; nor may an assumption be silently promoted to approved intent.
- **Downstream impact:** Identifies blockers for proposal drafting and approval, prevents PRD/Spec/Design from silently resolving upstream uncertainty, and determines whether Stage09 remains unevaluable for lack of intent authority.

### Question 6: Future canonical goal-anchor plan

- **Decision needed:** After Questions 1-5 are approved, which approved intent statements warrant future canonical goal anchors, how should they be grouped, and what stable meanings must each preserve? Do not assign identifiers yet.
- **Why required:** The repository-native traceability chain begins with goal anchors, but anchors cannot precede the intent decisions they represent.
- **Current evidence that can inform it:** Stage01 requires stable goal anchors; Stage02 requirements must trace to product goals; Stage09 requires bidirectional traceability across `G -> FR/NFR/EC -> AC -> SPEC -> DES -> TASK -> CODE -> TEST_EVIDENCE`.
- **Must not be inferred:** Goal count, numbering, wording, priority, acceptance criteria, requirements, technical guarantees, design decisions, or tasks. Historical milestones and Phase04/telemetry identifiers must not be repurposed as product goals.
- **Downstream impact:** Once later created in an approved proposal, the anchors provide the canonical origin for PRD traceability and the full Stage09 chain. This brief creates none and grants no drafting approval.

## 6. Proposed decision sequence

1. Decide the product vision, primary problem, desired outcome, and core value proposition.
2. Decide primary users, usage context, and core interaction concept against that intent spine.
3. Decide the current intended boundary and explicit product non-goals.
4. Decide which bounded current facts are elevated as product-level confirmed constraints.
5. Decide the evidence/assumption/TBD disposition and resolve every proposal-blocking uncertainty.
6. Approve the semantic plan for future canonical goal anchors without creating or numbering them in this brief.

This sequence is a decision dependency order, not a historical reconstruction or lifecycle replay.

## 7. Proposal drafting gate

Drafting `docs/proposal.md` is not authorized by this brief. The drafting gate opens only after project authority explicitly answers Questions 1-6 sufficiently to cover all eleven Stage01 content categories, identifies acceptable unresolved items, and authorizes a separate proposal-drafting task.

The later draft must preserve provenance and classifications, keep bounded authority bounded, avoid formal FR/NFR/AC, priorities, schemas, architecture, and tasks, and create canonical goal identifiers only from approved intent. Draft status alone will not create authority; the completed proposal will require independent `PROJECT_AUTHORITY_REVIEW` and explicit approval before becoming current `PRODUCT_INTENT` authority.

Until that sequence completes, PRD, Spec, Design, and Stage09 lack an approved current product-intent origin. Stage09 remains `NOT_EVALUATED`; no implementation, convergence, release, or project-complete decision follows from this brief.

## 8. Final decision-preparation status

The authorized current inputs support a narrow system identity, lifecycle purpose, governance context, current closure boundary, and bounded Phase04 and telemetry facts. They do not support a complete current product vision, problem, users, usage context, outcome, value proposition, interaction concept, intended boundary, product non-goals, product-level constraint selection, unresolved-item disposition, or canonical goal-anchor set. Six grouped project-authority questions therefore remain unanswered.

CURRENT_PROPOSAL_DECISION_BRIEF =
COMPLETE

PRODUCT_INTENT_CURRENT_AUTHORITY_COMPLETE =
NO

PROJECT_AUTHORITY_DECISIONS_REQUIRED =
YES

HISTORICAL_PHASE01_PRODUCT_INTENT_RECONSTRUCTION =
NOT_AUTHORIZED

DIRECT_CODE_TO_PRODUCT_INTENT_PROMOTION =
FORBIDDEN

G_IDS_CREATED =
NO

PROPOSAL_DRAFT_AUTHORIZED =
NO

STAGE09_DECISION =
NOT_EVALUATED

NEXT_STEP =
PROJECT_AUTHORITY_PRODUCT_INTENT_DECISIONS
