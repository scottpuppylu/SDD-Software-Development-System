# Current Verification Authority Package Plan

## 1. Purpose and authority boundary

This plan defines creation of a **CURRENT prospective verification authority package** consisting of:

1. `docs/proposal.md`
2. `docs/PRD.md`
3. `docs/spec.md`
4. `docs/Design.md`
5. `AGENTS.md`
6. `tasks.md`

The package is required to make Stage09 evaluable against current repository authority. This document plans the package only. It does not create any package artifact, modify source or tests, change lifecycle or telemetry authority, authorize implementation or release, or decide Stage09.

The package is new current authority after artifact-specific approval. It must never be described as recovered, reconstructed, or historically present Phase01-03 authority. Accepted historical COMPLETE / PASS evidence remains evidence within its original scope and cannot be converted into current product intent, requirements, technical guarantees, design decisions, governance, tasks, milestones, or roadmap authority.

Authority remains domain-specific and non-linear:

| Authority domain | Future authoritative artifact | Repository-native owner stage |
| --- | --- | --- |
| `PRODUCT_INTENT` | `docs/proposal.md` | Stage01 `PRODUCT_PROPOSAL` |
| `PRODUCT_REQUIREMENT` | `docs/PRD.md` | Stage02 `PRODUCT_REQUIREMENTS` |
| `TECHNICAL_CONTRACT` | `docs/spec.md` | Stage03 `TECHNICAL_SPECIFICATION` |
| `IMPLEMENTATION_DECISION` | `docs/Design.md` | Stage04 `SOFTWARE_DESIGN` |
| `AGENT_REPOSITORY_GOVERNANCE` | `AGENTS.md` | Stage05 `AGENT_GOVERNANCE` |
| `EXECUTION_DECOMPOSITION` | `tasks.md` | Stage06 `IMPLEMENTATION_TASKS` |

There is no linear authority precedence such as `PRD > Spec > Design`. Each artifact owns only its domain and reads the other domains allowed by `.sdd/system.yaml` and `.sdd/stages.yaml`. Cross-domain conflicts must be `DETECT`ed, `REPORT`ed, `BLOCK`ed, and `ROUTE_TO_AUTHORITATIVE_OWNER`; they must not be silently resolved by a downstream draft.

## 2. Why the package is required

`docs/handoff/stage09-verification-inventory.md` establishes that all six current authority artifacts are absent. Five are explicit Stage09 file inputs, and `docs/proposal.md` is the missing `G-*` origin needed for the complete canonical traceability chain:

```text
G -> FR/NFR/EC -> AC -> SPEC -> DES -> TASK -> CODE -> TEST_EVIDENCE
```

The inventory also establishes that existing implementation and test evidence cannot supply missing requirement, design, or task authority. Current-revision source-to-contract and test-to-contract review remains outstanding and was deliberately deferred. The Whole-Project Closure Authority Baseline authorizes prospective lifecycle closure evaluation but does not replace the missing domain artifacts, reconstruct Phase01-03 authority, authorize implementation, or predetermine Stage09.

The package therefore supplies the current approved comparison baseline that Stage09 needs. It is authority remediation before verification, not a verification decision and not a historical lifecycle replay.

## 3. Source-of-truth classification model

Every candidate statement for every future artifact must receive exactly one of these classifications before drafting:

| Classification | Drafting rule |
| --- | --- |
| `A. DIRECTLY_TRANSCRIBABLE_CURRENT_AUTHORITY` | Current committed authoritative content may be carried forward without changing meaning, scope, ownership, or force. Cite provenance and preserve all original boundaries. |
| `B. CURRENT_REPOSITORY_EVIDENCE_REQUIRING_INTERPRETATION` | Current committed evidence may identify questions or support a bounded proposed statement, but interpretation and later approval are required before it becomes authority. |
| `C. PROJECT_AUTHORITY_DECISION_REQUIRED` | The needed domain decision is not established. Record the decision question; do not supply an answer without explicit project-authority approval. |
| `D. HISTORICAL_ONLY_NOT_TRANSCRIBABLE` | Historical completion/status evidence may appear only as provenance. It cannot become current scope, requirements, milestones, contracts, design, governance, or tasks. |
| `E. UNSUPPORTED_DO_NOT_INVENT` | No valid basis exists. Omit the content or mark it `TBD` pending valid authority. |

Classification is per candidate statement, not per source document. A document can support different classifications for different statements. Direct transcription is allowed only when the source currently owns the same meaning and bounded scope. Existing code or tests are implementation evidence, not automatic product, technical, or design authority. Historical status is never a substitute for current domain approval.

Allowable evidence for this package is initially the seven sources used by this plan: `docs/handoff/stage09-verification-inventory.md`, `docs/project/whole-project-closure-authority-baseline.md`, `docs/project/project-authority-reconstruction.md`, `docs/context/phase04-closure-report.md`, `docs/telemetry/measurement-contract-v1.md`, `.sdd/system.yaml`, and `.sdd/stages.yaml`. Later drafting may inspect only evidence expressly authorized for that drafting round. Source/test body inspection remains deferred until after authority remediation.

## 4. Package construction order

The establishment order is:

```text
proposal -> PRD -> spec -> Design -> AGENTS -> tasks
```

This is an authority-construction dependency order for the CURRENT verification package.

It is NOT a claim that historical Phase01-06 are being rerun.

Each artifact follows the independent gate:

```text
DRAFT -> PROJECT_AUTHORITY_REVIEW -> APPROVED_CURRENT_AUTHORITY
```

Downstream drafting may inspect upstream drafts for context, but an upstream draft is not authority. A downstream draft must carry unresolved upstream decisions forward as explicit blockers/TBDs and must not choose an answer. Changes made during approval require affected downstream drafts to be re-evaluated in accordance with `.sdd/stages.yaml` rerun semantics.

## 5. `docs/proposal.md` plan

| Planning field | Plan |
| --- | --- |
| Authority domain | `PRODUCT_INTENT` |
| Repository-native owner stage | Stage01 `PRODUCT_PROPOSAL` |
| Current package purpose | Establish current product intent and canonical `G-*` anchors sufficient for current requirements and Stage09 bidirectional traceability. |
| Minimum required lifecycle content | `PRODUCT_VISION`, `USER_PROBLEM`, `TARGET_USER`, `USAGE_CONTEXT`, `DESIRED_OUTCOME`, `CORE_VALUE_PROPOSITION`, `CORE_INTERACTION_CONCEPT`, `MVP_INTENT_BOUNDARY`, `NON_GOALS`, `CONFIRMED_CONSTRAINTS`, and `EVIDENCE_ASSUMPTIONS_TBD`; stable `G-*` identifiers. It must not create FR/NFR/AC, priorities, technical schema/architecture, or tasks. |
| Allowable sources/evidence | `.sdd/system.yaml` and `.sdd/stages.yaml` for domain/form requirements; the current closure baseline for the prospective closure boundary and explicit non-authorizations; bounded Phase04 and telemetry authority only as current constraints/evidence within their scopes; the inventory and reconstruction report for gaps and provenance. |
| Directly transcribable current authority | The repository uses the SDD 01-10 governed lifecycle with repository/Git persistent state; authority is domain-specific; the package is current/prospective only; no current unfinished numbered phase or milestone is established; no new implementation, release, deployment, telemetry change, lifecycle change, Phase05, or retroactive Phase01-03 reconstruction is authorized. Phase04 bounded invariants and telemetry observational/non-authority constraints may be transcribed only if identified as confirmed constraints, not as the whole product vision. |
| Requires interpretation | Whether the current repository behavior and bounded Phase04/telemetry artifacts imply candidate usage contexts, value propositions, interaction concepts, MVP boundaries, or non-goals. Such evidence may generate questions or proposals but cannot itself establish intent. |
| Requires project-authority decision | Current product vision; user problem; target user; usage context; desired outcome; core value proposition; core interaction concept; current MVP intent boundary; product non-goals beyond already explicit non-authorizations; mapping approved intent to canonical `G-*`; and whether bounded existing constraints belong in the current product-intent baseline. |
| Historical content forbidden from reconstruction | Phase01 purpose/title/scope/outcomes/milestones/closure criteria; Phase02/03 project vision or roadmap; an inferred whole-project roadmap or final-phase designation; product vision inferred from historical COMPLETE / PASS records; any claim that this proposal existed during Phase01-03. |
| Unsupported content | Undocumented users, markets, business goals, success metrics, workflows, future phases, features, or outcomes remain absent/`TBD`; no answer may be invented from numbering, chronology, code, or tests. |
| Approval gate | A complete draft with classified provenance and all blocking product-intent questions resolved must pass `PROJECT_AUTHORITY_REVIEW`; only explicit approval makes it `APPROVED_CURRENT_AUTHORITY`. |
| Downstream consumers | `docs/PRD.md`, `docs/spec.md`, canonical traceability, and later Stage09 verification. |
| Stage09 role | Supplies the `G-*` origin for end-to-end traceability and the intent boundary against which requirements can be understood; it does not itself decide Stage09. |

Proposal drafting cannot proceed to approval merely by restating that Phase04 is closed or that Stage09 is authorized. Permitted current evidence does not establish the complete vision/problem/user/outcome set, so those items are presently `PROJECT_AUTHORITY_DECISION_REQUIRED`.

## 6. `docs/PRD.md` plan

| Planning field | Plan |
| --- | --- |
| Authority domain | `PRODUCT_REQUIREMENT` |
| Repository-native owner stage | Stage02 `PRODUCT_REQUIREMENTS` |
| Current package purpose | Establish current product requirements, scope priorities, edge cases, and testable acceptance criteria traceable to approved `G-*` intent. |
| Minimum required lifecycle content | Stable `FR-*`, `NFR-*`, and `EC-*`; explicit P0/P1/P2 scope; testable acceptance criteria for every P0; traceability to product goals; resolved product-level clarifications/conflicts; explicit product-owner approval of the final baseline. It must not decide framework, database, API schema, or module structure. |
| Allowable sources/evidence | Approved current `docs/proposal.md`; `.sdd/system.yaml` and `.sdd/stages.yaml` for domain/form/gate rules; current bounded closure, Phase04, and telemetry authority as constraints or question-generating evidence only within scope; inventory/reconstruction for known absence and historical boundary. Source/test bodies are not allowable in the current planning/drafting round. |
| Directly transcribable current authority | Explicit current non-authorizations and bounded product-relevant constraints may be carried forward only without semantic expansion. The need for testable P0 acceptance criteria, explicit priority scope, goal traceability, and product-owner authorization is directly transcribable lifecycle authority. No current full product requirement set is directly transcribable from the permitted sources. |
| Requires interpretation | Bounded Phase04 operational behavior and telemetry contract behavior may identify candidate product questions or possible acceptance concerns. Existing implementation/test evidence may later help discover questions, but cannot be promoted to requirements. |
| Requires project-authority decision | The current FR/NFR/EC inventory; P0/P1/P2 allocation; each acceptance criterion; externally meaningful product behavior; error/user-visible behavior; security/privacy and performance expectations at the product level; applicability of bounded existing behaviors to current product scope; and final product baseline authorization. |
| Historical content forbidden from reconstruction | Phase01-03 requirements, priorities, acceptance criteria, milestone scope, or product outcomes inferred from COMPLETE / PASS; a requirement set reverse-engineered from historical tests, reports, code, telemetry, or Phase04 closure; any claim that the PRD existed historically. |
| Unsupported content | Features, priorities, personas, acceptance thresholds, compatibility commitments, service levels, security/privacy promises, and edge cases lacking approved product basis remain absent/`TBD`. |
| Approval gate | The draft must trace to an approved current proposal, classify every candidate requirement, contain testable P0 ACs, expose all product conflicts/TBDs, and receive explicit project-authority approval before becoming current authority. |
| Downstream consumers | `docs/spec.md`, `docs/Design.md`, `AGENTS.md`, `tasks.md`, Stage07, Stage08, and Stage09. |
| Stage09 role | Supplies current P0 requirements and acceptance criteria for conformance checks and `FR/NFR/EC -> AC` traceability. |

Code behavior does not automatically become product authority. Reverse-engineering the current implementation may later reveal clarification questions, but cannot establish the PRD.

## 7. `docs/spec.md` plan

| Planning field | Plan |
| --- | --- |
| Authority domain | `TECHNICAL_CONTRACT` |
| Repository-native owner stage | Stage03 `TECHNICAL_SPECIFICATION` |
| Current package purpose | Define current technical guarantees needed to support every applicable approved P0 requirement and their verification expectations. |
| Minimum required lifecycle content | Stable `SPEC-*`; traceability to PRD; applicable state, data, API, error, security/privacy, and NFR contracts; verification expectations; technical coverage for each applicable P0; no silent change to product behavior; no implementation-design decisions. |
| Allowable sources/evidence | Approved current proposal and PRD; `.sdd/system.yaml` and `.sdd/stages.yaml`; `docs/telemetry/measurement-contract-v1.md` only for its actual bounded Phase03A telemetry authority; current Phase04 authority only for its bounded approved guarantees; closure baseline/inventory/reconstruction for boundaries and gaps. |
| Directly transcribable current authority | Lifecycle technical-contract structure and conflict rules. Exact telemetry field names, enums, nullability, canonicalization, persistence, minimization, observability, configuration, and non-interference guarantees may be transcribed only into an explicitly bounded telemetry subsection when an approved PRD requirement needs them. Applicable exact Phase04 guarantees may likewise be carried forward only within Phase04's bounded scope. |
| Requires interpretation | Mapping approved PRD requirements to technical coverage; deciding which state/data/API/error/security/NFR categories apply; integrating separately bounded telemetry or Phase04 guarantees into a coherent current spec without expanding them; using repository evidence to propose technical questions. |
| Requires project-authority decision | Technical guarantees not already bounded by current authority; state machines, data and API contracts, error semantics, security/privacy controls, NFR thresholds, verification expectations, system boundaries, and resolution of any technical/product cross-domain conflict. |
| Historical content forbidden from reconstruction | Complete Phase02 or Phase03 technical authority inferred from their names/status; promotion of the Phase03A measurement contract into a whole-system contract; lost Phase01-03 technical decisions; specifications reverse-engineered from code/tests; any claim that this spec existed historically. |
| Unsupported content | Unapproved APIs, schemas, protocols, state transitions, security claims, performance targets, dependencies, compatibility guarantees, and verification thresholds remain absent/`TBD`. |
| Approval gate | The draft must be based on approved current proposal/PRD, cover all applicable P0s, keep bounded authorities bounded, expose conflicts/TBDs, and receive explicit project-authority approval before becoming current authority. |
| Downstream consumers | `docs/Design.md`, `AGENTS.md`, `tasks.md`, Stage07, Stage08, and Stage09. |
| Stage09 role | Supplies the technical guarantees checked for state/data/API/error/security/NFR conformance and `SPEC-*` traceability. |

The telemetry measurement contract is current direct authority only for its bounded Phase03A measurement scope. It must not be presented as the whole-system technical contract.

## 8. `docs/Design.md` plan

| Planning field | Plan |
| --- | --- |
| Authority domain | `IMPLEMENTATION_DECISION` |
| Repository-native owner stage | Stage04 `SOFTWARE_DESIGN` |
| Current package purpose | Record current approved implementation decisions that implement, without redefining, the approved technical contract. |
| Minimum required lifecycle content | Stable `DES-*` (and approved `ADR-*` where needed); architecture, module, dependency, data-flow, and repository mapping sufficient for task decomposition; implementation-design coverage for P0 technical contracts; no unresolved authority conflict. |
| Allowable sources/evidence | Approved current PRD and spec; `.sdd/system.yaml` and `.sdd/stages.yaml`; bounded current Phase04 design constraints and telemetry contract constraints where applicable; repository structure and, only in a later expressly authorized round, implementation evidence as interpretive evidence. |
| Directly transcribable current authority | Lifecycle design-domain boundaries and conflict rules. Exact currently authoritative Phase04 implementation invariants may be transcribed only for that bounded manifested-context scope. Exact telemetry constraints that restrict implementation may be referenced/transcribed only within the bounded telemetry design area and without turning technical-contract text into a new design choice. |
| Requires interpretation | Mapping approved technical contracts to candidate architecture/modules/dependencies/data flows; assessing current repository structure or later implementation evidence as possible design; distinguishing a contract constraint from an implementation decision. |
| Requires project-authority decision | Architecture, module boundaries, dependencies, data flows, repository mapping, integration strategy, implementation patterns, approved deviations, ADR choices, and adoption or rejection of observed current implementation as the prospective approved design. |
| Historical content forbidden from reconstruction | Phase01-03 architecture/design inferred from status or current code; undocumented design decisions attributed retroactively to prior phases; promotion of Phase04 closure into whole-system design; any claim that this Design file existed historically. |
| Unsupported content | Unapproved architecture rationale, ownership boundaries, dependencies, module maps, alternatives considered, migration design, and implementation patterns remain absent/`TBD`. |
| Approval gate | The draft must implement an approved current spec, cover applicable P0 technical contracts, clearly separate evidence from decisions, resolve or block conflicts, and receive explicit project-authority approval. |
| Downstream consumers | `AGENTS.md`, `tasks.md`, Stage07, Stage08, and Stage09. |
| Stage09 role | Supplies the approved design baseline for design-conformance verification and `DES-*` traceability. |

Documenting existing code is not sufficient to create design authority. Existing implementation may inform a later draft, but adoption of it as approved current design requires an explicit decision.

## 9. `AGENTS.md` plan

| Planning field | Plan |
| --- | --- |
| Authority domain | `AGENT_REPOSITORY_GOVERNANCE` |
| Repository-native owner stage | Stage05 `AGENT_GOVERNANCE` |
| Current package purpose | Define current repository agent permissions, prohibitions, authority handling, lifecycle operation, testing, Git checkpointing, protected scope, and escalation without enlarging existing authorization. |
| Minimum required lifecycle content | `AUTHORITY_MODEL`, `AGENT_PERMISSIONS`, `AGENT_PROHIBITIONS`, `CROSS_DOMAIN_CONFLICT_HANDLING`, `STAGE_07_10_LIFECYCLE`, `ATOMIC_EXECUTION`, `TESTING`, `GIT_CHECKPOINT`, `START_RESUME`, `PROTECTED_SCOPE`, `ESCALATION`, and `STAGE_09_10_HANDOFF`; preserve the invariant that an agent may detect/report/block but may not silently modify upstream authority. |
| Allowable sources/evidence | `.sdd/system.yaml` and `.sdd/stages.yaml` as primary direct current governance authority; approved current PRD/spec/Design for repository-specific scope; closure baseline for explicit non-authorizations; bounded telemetry and Phase04 authority for protected-scope/non-interference constraints where relevant. |
| Directly transcribable current authority | Domain-specific/non-linear authority; conflict protocol; repository/Git as execution state; chat memory non-authority; orchestration permissions and prohibitions; human-intervention rules; Stage07-10 inputs, gates, result vocabularies, routing, Stage08 atomic loop/checkpoint prerequisites, Stage09 conflict classifications, Stage10 entry rule, rerun rules, and existing explicit non-authorizations, provided wording preserves exact semantics. |
| Requires interpretation | Repository-specific protected paths/scope; concrete testing and Git command conventions; start/resume procedures mapped onto approved repository structure; how exact lifecycle rules should be organized for agents. Interpretation may narrow or operationalize existing authority but cannot grant new capability. |
| Requires project-authority decision | Any repository-specific permission, prohibition, protected scope, destructive-operation rule, testing mandate, Git convention, escalation owner, or operational constraint not already exact in current authority; any proposed delegation or authorization beyond `.sdd`; approval of the repository-specific governance baseline. |
| Historical content forbidden from reconstruction | Prior agent permissions, Stage07 decisions, implementation authorization, testing policy, or Git practices inferred from historical work/commits; historical gate passage inferred from COMPLETE / PASS; any claim that AGENTS.md existed historically. |
| Unsupported content | New write permissions, autonomous authority modification, release/deployment permission, destructive-operation authority, unestablished commands, CI policy, branch policy, owners, or exception mechanisms remain absent/`TBD`. |
| Approval gate | The draft must be semantically checked against `.sdd`, introduce no expanded permission, incorporate approved repository-specific authority, expose every undecided governance item, and receive explicit project-authority approval. |
| Downstream consumers | `tasks.md`, Stage07, Stage08, Stage09, Stage10, and repository-aware agents. |
| Stage09 role | Provides the governance baseline for verification conduct, evidence handling, conflict routing, protected scope, and Stage09-to-Stage10 boundaries. |

Because `.sdd` already establishes much of the governance domain, that content appears substantially derivable. Repository-specific permissions, commands, protected scope, and escalation details remain decisions wherever the current sources are not exact.

## 10. `tasks.md` plan

| Planning field | Plan |
| --- | --- |
| Authority domain | `EXECUTION_DECOMPOSITION` |
| Repository-native owner stage | Stage06 `IMPLEMENTATION_TASKS` |
| Current package purpose | Establish the current required execution inventory, if any, only after upstream current authority converges, so Stage09 can evaluate task completion and traceability. |
| Minimum required lifecycle content | Stable `T*` identifiers for every required task and, for each task, `TASK_ID`, `TITLE`, `STATUS`, `OBJECTIVE`, `TRACEABILITY`, `DEPENDENCIES`, `IMPLEMENTATION_SCOPE`, `VERIFICATION`, and `DONE_WHEN`; independent executability/verifiability; preservation of upstream authority; requirement/spec/design traceability; decomposition of all required P0 implementation scope. |
| Allowable sources/evidence | Approved current proposal, PRD, spec, Design, and AGENTS; `.sdd/system.yaml` and `.sdd/stages.yaml`; the closure baseline's explicit statement that no unfinished numbered phase/milestone or new implementation is currently authorized; inventory evidence of absent current task authority. |
| Directly transcribable current authority | The atomic-task schema, status vocabulary, traceability requirements, Stage07/08/09 task rules, and checkpoint semantics are direct lifecycle authority. It is also direct current authority that no new implementation and no unfinished numbered phase/milestone are presently authorized; this constrains but does not by itself decide the correct task inventory. |
| Requires interpretation | Whether approved upstream authority reveals any verification/remediation work that belongs in execution decomposition; how a legitimate zero-required-implementation-task artifact would represent lifecycle-required fields without fabricating tasks; distinction between authority-package drafting work and implementation/verification tasks. |
| Requires project-authority decision | Whether the approved current package legitimately requires (a) zero implementation tasks or (b) verification/remediation-only decomposition; the exact inventory, statuses, dependencies, verification clauses, and done conditions if tasks are required; whether any newly discovered gap may be authorized for remediation. |
| Historical content forbidden from reconstruction | Historical Phase01-03 or Phase04 task lists inferred from completion evidence, commits, code, or tests; retroactive task status; an inferred Stage07 PASS or Stage08 authorization; unfinished milestones invented from prior work; any claim that tasks.md existed historically. |
| Unsupported content | New implementation tasks, convergence tasks, verification commands, task completion claims, checkpoint claims, priorities, dependencies, or remediation scope without approved upstream authority remain absent/`TBD`. |
| Approval gate | Drafting begins only after the five upstream current artifacts have converged sufficiently. The selected inventory model and every required task must pass project-authority review. Approval of `tasks.md` does not itself authorize implementation; repository-native Stage07 rules remain applicable. |
| Downstream consumers | Stage07, Stage08, Stage09, implementation state, code/test evidence traceability, and later convergence routing. |
| Stage09 role | Supplies the current task inventory, completion baseline, and `TASK -> CODE -> TEST_EVIDENCE` links needed for task-completion and bidirectional traceability checks. |

The correct current artifact may legitimately contain zero required implementation tasks or a verification/remediation-only decomposition. Existing authority does not unambiguously choose between those forms. That choice is presently `PROJECT_AUTHORITY_DECISION_REQUIRED`; this plan does not decide it. No task inventory may authorize implementation indirectly.

## 11. Project-authority decision inventory

The following known decisions require project authority before the package can be completed. Answers are intentionally not supplied.

| Domain | Decision required | Why existing current authority is insufficient | Required before |
| --- | --- | --- | --- |
| `PRODUCT_INTENT` | Approve current product vision, user problem, target user, usage context, desired outcome, core value proposition, core interaction concept, MVP boundary, non-goals, and `G-*` mapping. | Permitted current sources define lifecycle/closure and bounded subsystem constraints, not a complete current product-intent baseline. | Proposal approval |
| `PRODUCT_INTENT` | Decide which bounded Phase04/telemetry/current closure constraints belong in the product-intent baseline without expanding their scope. | Their authority is current but bounded; inclusion as product intent requires a domain decision. | Proposal approval |
| `PRODUCT_REQUIREMENT` | Approve the current FR/NFR/EC inventory and trace each item to approved goals. | No current whole-product PRD exists; code/tests cannot create requirements. | PRD approval |
| `PRODUCT_REQUIREMENT` | Approve P0/P1/P2 allocation and testable acceptance criteria for every P0. | Lifecycle requires these, but current sources do not supply the product choices. | PRD approval |
| `PRODUCT_REQUIREMENT` | Approve product-level security/privacy, error, compatibility, performance, and edge-case expectations where applicable. | Applicability and promised behavior are not completely established. | PRD approval |
| `TECHNICAL_CONTRACT` | Approve technical coverage for every applicable P0 and applicability of state/data/API/error/security/NFR contract categories. | `.sdd` requires coverage but does not specify this repository's whole-system guarantees. | Spec approval |
| `TECHNICAL_CONTRACT` | Decide how bounded telemetry and Phase04 guarantees relate to the approved current PRD without promoting them beyond scope. | Existing authority is exact only within its bounded domains. | Spec approval |
| `TECHNICAL_CONTRACT` | Resolve any product/technical conflict and approve verification expectations and all new technical guarantees. | Downstream technical drafting cannot silently decide product behavior. | Spec approval |
| `IMPLEMENTATION_DECISION` | Approve current architecture, modules, dependencies, data flows, repository mapping, integration choices, and required ADRs. | Existing implementation/design evidence is not automatically approved current design. | Design approval |
| `IMPLEMENTATION_DECISION` | Decide whether observed current implementation, if reviewed later, is adopted, amended, or rejected as prospective design. | Documentation of code alone cannot create design authority. | Design approval |
| `AGENT_REPOSITORY_GOVERNANCE` | Approve repository-specific protected scope, testing rules/commands, Git conventions, start/resume procedure, escalation ownership, and any details not exact in `.sdd`. | Core lifecycle governance is derivable, but repository-specific operational choices are incomplete in the permitted sources. | AGENTS approval |
| `AGENT_REPOSITORY_GOVERNANCE` | Confirm that the drafted governance grants no permissions beyond current authority and approve the final repository governance baseline. | Exact-semantic transcription still requires artifact approval; any operational interpretation needs review. | AGENTS approval |
| `EXECUTION_DECOMPOSITION` | Choose whether current `tasks.md` contains zero required implementation tasks or verification/remediation-only decomposition. | No unfinished milestone or new implementation is authorized, but existing authority does not unambiguously determine the artifact form. | Tasks approval |
| `EXECUTION_DECOMPOSITION` | If tasks are approved, approve exact task inventory, traceability, status, dependencies, scope, verification, and done conditions. | No current task inventory exists, and no task may be invented from code/history. | Tasks approval |
| `EXECUTION_DECOMPOSITION` | Decide whether any later-discovered remediation gap is authorized for task decomposition. | Stage09 has not begun or classified a gap, and implementation is not authorized. | Any remediation task approval |

No domain is fully complete as an approved artifact because all six files are absent and each requires its own approval. The core `AGENT_REPOSITORY_GOVERNANCE` semantics appear substantially derivable from `.sdd/system.yaml` and `.sdd/stages.yaml`, specifically the domain model, permissions/prohibitions, conflict protocol, Stage07-10 rules, atomic execution, checkpoints, rerun routing, and result vocabularies. That exact basis reduces—but does not eliminate—AGENTS decisions. The lifecycle-required structure of every artifact is likewise directly derivable from those two files; structure is not substantive domain authority.

## 12. Approval gates

Every artifact is governed independently by:

```text
DRAFT
-> PROJECT_AUTHORITY_REVIEW
-> APPROVED_CURRENT_AUTHORITY
```

At `DRAFT`, all candidate content must carry one of the five source-of-truth classifications, provenance must be recorded, and all `C` and `E` items must remain explicit decisions/TBDs. A draft has no authoritative force.

At `PROJECT_AUTHORITY_REVIEW`, the relevant domain owner must verify scope, meaning, traceability, cross-domain consistency, historical boundary, and absence of invented authority. A conflict is detected, reported, blocked, and routed to the owner of each affected domain. Review may not use a downstream artifact to settle an upstream choice.

At `APPROVED_CURRENT_AUTHORITY`, explicit project-authority approval establishes only that artifact's current domain authority. Approval is prospective and does not imply historical existence, retroactive Stage01-06 passage, Stage07 PASS, implementation authorization, Stage09 result, Stage10 entry, release, or project completion.

Approval order and minimum dependencies are:

| Artifact | Review dependency | Approval consequence |
| --- | --- | --- |
| `docs/proposal.md` | Product-intent decisions resolved | Establishes current `PRODUCT_INTENT` only |
| `docs/PRD.md` | Approved proposal | Establishes current `PRODUCT_REQUIREMENT` only |
| `docs/spec.md` | Approved proposal and PRD | Establishes current `TECHNICAL_CONTRACT` only |
| `docs/Design.md` | Approved PRD and spec | Establishes current `IMPLEMENTATION_DECISION` only |
| `AGENTS.md` | Approved PRD, spec, and Design | Establishes current `AGENT_REPOSITORY_GOVERNANCE` only |
| `tasks.md` | Upstream current authority converged, including approved AGENTS | Establishes current `EXECUTION_DECOMPOSITION` only; it does not authorize implementation |

## 13. Stage09 relationship

Stage09 remains `NOT_EVALUATED`.

Stage09 host verification must not begin until all six required current authority artifacts exist and each has passed its approval gate as current authority. The package must provide an internally consistent, domain-correct baseline and the canonical traceability anchors needed for later verification. Artifact existence without approval is insufficient.

Source/test body review remains deferred until after authority remediation. No test, build, lint, typecheck, host-verification, or source/test conformance command is authorized by this plan. After approval of the six-file package, a later authorized Stage09 preparation/run may inspect source and test bodies, establish current host commands and evidence, evaluate conformance, classify gaps or authority conflicts, and only then produce a Stage09 decision under repository-native rules.

This plan does not create `docs/handoff/verification-report.md`, authorize convergence tasks, authorize Stage08 implementation, authorize Stage10, or authorize release.

## 14. Final planning decision

The current prospective verification authority package plan is established. The next step is a separately authorized current `docs/proposal.md` draft, beginning with explicit project-authority decisions for the current product vision, problem, target user/usage context, desired outcome, value proposition, interaction concept, MVP boundary, non-goals, constraints, and canonical `G-*` anchors.

CURRENT_VERIFICATION_AUTHORITY_PACKAGE_PLAN =
ESTABLISHED

PACKAGE_SCOPE =
CURRENT_PROSPECTIVE_VERIFICATION_AUTHORITY_ONLY

HISTORICAL_PHASE01_03_RECONSTRUCTION =
NOT_AUTHORIZED

PROPOSAL_REQUIRED =
YES

PRD_REQUIRED =
YES

SPEC_REQUIRED =
YES

DESIGN_REQUIRED =
YES

AGENTS_REQUIRED =
YES

TASKS_REQUIRED =
YES

PACKAGE_CONSTRUCTION_ORDER =
PROPOSAL_PRD_SPEC_DESIGN_AGENTS_TASKS

DIRECT_CODE_TO_PRODUCT_AUTHORITY_PROMOTION =
FORBIDDEN

DIRECT_HISTORICAL_STATUS_TO_AUTHORITY_PROMOTION =
FORBIDDEN

PROJECT_AUTHORITY_APPROVAL_REQUIRED_PER_ARTIFACT =
YES

SOURCE_TEST_BODY_REVIEW_NOW =
NO

STAGE09_DECISION =
NOT_EVALUATED

STAGE09_HOST_VERIFICATION_AUTHORIZED_NOW =
NO

NEXT_STEP =
CURRENT_AUTHORITY_PACKAGE_PROPOSAL_DRAFT
