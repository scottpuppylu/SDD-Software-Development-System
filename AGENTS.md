# Agent and Repository Governance

## 1. Authority and scope

This document is the approved CURRENT prospective Stage05 `AGENT_REPOSITORY_GOVERNANCE` authority. It governs agent conduct and repository operations. Project Authority has explicitly approved this substantive baseline through the applicable Stage05 owning-authority flow. This approval is prospective only and does not authorize historical Phase05 reconstruction.

Agents MAY inspect relevant evidence, analyze, propose, and create drafts within an eligible owning workflow. Draft creation does not establish authority. Artifact existence, filename, quality, commit, downstream use, or AI output MUST NOT be treated as approval. Substantive authority mutation MUST use the applicable owning-authority flow. Agents MUST NOT self-approve authority.

This document does not own or redefine `PRODUCT_INTENT`, `PRODUCT_REQUIREMENT`, `TECHNICAL_CONTRACT`, `IMPLEMENTATION_DECISION`, `EXECUTION_DECOMPOSITION`, `PRE_IMPLEMENTATION_GATE_DECISION`, `IMPLEMENTATION_EVIDENCE`, `IMPLEMENTATION_RECOVERY_DECISION`, `VERIFICATION_DECISION`, or `RELEASE_DECISION`.

Authority is domain-specific and non-linear. Agents MUST NOT impose a precedence such as `PRD > Spec > Design > AGENTS`. A cross-domain conflict MUST follow:

`DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`

## 2. Protected authority artifacts

The following artifacts are protected and retain their configured domain owners:

| Artifact | Authority domain / owner |
| --- | --- |
| `docs/proposal.md` | `PRODUCT_INTENT` / Stage01 |
| `docs/PRD.md` | `PRODUCT_REQUIREMENT` / Stage02 |
| `docs/spec.md` | `TECHNICAL_CONTRACT` / Stage03 |
| `docs/Design.md` | `IMPLEMENTATION_DECISION` / Stage04 |
| `AGENTS.md` | `AGENT_REPOSITORY_GOVERNANCE` / Stage05 |
| `tasks.md` | `EXECUTION_DECOMPOSITION` / Stage06 |
| `docs/handoff/pre-implementation-gate-report.md` | `PRE_IMPLEMENTATION_GATE_DECISION` / Stage07 |
| `docs/handoff/implementation-recovery-gate-report.md` | `IMPLEMENTATION_RECOVERY_DECISION` / Recovery Gate |
| `docs/handoff/verification-report.md` | `VERIFICATION_DECISION` / Stage09 |
| `docs/handoff/handoff-report.md` | `RELEASE_DECISION` / Stage10 |

An agent MAY draft or modify an artifact only within its authorized owning workflow. It MUST NOT silently mutate another authority domain. Missing, stale, withdrawn, conflicting, or out-of-scope authority MUST block affected work and be routed to its owner.

## 3. Repository start, resume, and write preconditions

Before repository writes, an agent MUST validate, as applicable:

- expected repository, branch, and HEAD or baseline;
- expected working-tree state and diff;
- known authorized in-progress changes; and
- allowed untracked files.

The agent MUST STOP affected work for an unexpected branch, baseline mismatch, unrelated pre-existing modification, unexplained untracked file, unexpected diff, or state not attributable to authorized scope. It MUST NOT absorb unrelated changes merely to proceed.

Known existing changes MAY continue only when explicitly identified, attributable, and included in authorized scope and provenance. On resume, the agent MUST reload current authority, task, state, Git status, branch, baseline/checkpoints, and verification requirements rather than rely on chat memory or stale conclusions.

## 4. Agent permissions, prohibitions, and routing

Agents MAY autonomously inspect relevant evidence, analyze, propose, draft within eligible scope, perform routine already-authorized actions, and detect/report/block conflicts. They MAY execute Stage08 only under a valid sealed authorization envelope.

Agents MUST route substantive choices as follows:

- `PRODUCT_INTENT` to its Stage01 owner;
- `PRODUCT_REQUIREMENT` to its Stage02 owner;
- `TECHNICAL_CONTRACT` to its Stage03 owner;
- `IMPLEMENTATION_DECISION` to its Stage04 owner;
- approval of `AGENT_REPOSITORY_GOVERNANCE` to the Stage05 owner;
- `EXECUTION_DECOMPOSITION` to Stage06;
- implementation authorization to Stage07;
- verification qualification to Stage09;
- release qualification to Stage10; and
- lifecycle-required Human Decisions to the appropriate human authority.

An agent MUST NOT create authority because a recommendation is sensible, user silence occurred, or downstream work depends on it. Unaffected work MAY continue only when independence is established and recorded.

## 5. Commit and Git governance

Outside an explicitly authorized checkpoint workflow, an agent MUST NOT commit automatically unless explicitly instructed.

For authority artifacts, substantive Project Authority or owning-authority approval MUST exist before promotion to approved authority. A Git commit alone never means approval. Host or reviewer validation MUST occur before the approval commit when the governing workflow requires it.

A valid Stage07 `PASS` MAY authorize the defined Stage08 execution scope. Within that already authorized scope, a checkpoint commit MAY occur only after all configured atomic checkpoint prerequisites pass: implementation complete, required verification `PASS`, completion criteria satisfied, scope respected, unexpected diff reviewed, and no unresolved blocker. A new Project Authority decision is not required for every valid Stage08 checkpoint unless another governed condition requires it.

Without explicit authorization, an agent MUST NOT amend, rebase, perform a reset that discards or rewrites state, force push, or rewrite history.

## 6. Command and environment governance

Agents MUST use the minimum privilege sufficient for authorized work. Relevant read-only repository inspection is normally permitted. Repository-writing commands MUST remain inside authorized scope. Tests, formatters, and generators MAY run only when applicable to authorized work.

Package installation, dependency mutation, environment change, external/network access, or other higher-impact operation MUST have demonstrated necessity and remain within applicable authorization. Destructive commands require explicit, target-bounded authorization.

Agents MUST prefer the existing environment and toolchain. They MUST NOT silently rebuild or recreate an environment, replace an interpreter or toolchain, change system configuration or execution policy, or install dependencies for convenience. A missing dependency or interpreter mismatch MUST be reported.

When sandbox and host capabilities differ, the agent MUST report the limitation truthfully. It MAY use an already valid host capability when the governing workflow permits it. A failed sandbox execution MUST NOT be represented as proof that the host environment is invalid. Material repair or recreation requires applicable authorization.

## 7. Stage07 authorization and Stage08 sealed execution

Normal new implementation MUST NOT begin unless Stage07 has returned a valid `PASS` with implementation authorization.

Only when a defect in the SDD governance/runtime infrastructure prevents normal Stage07 reevaluation, explicit Project Authority approval MAY authorize a specifically named and bounded bootstrap remediation limited to that infrastructure and directly necessary regression verification separately authorized by the approval. The approval MUST explicitly name every permitted file, and the remediation MUST be independently validated and checkpointed. This exception is not a Stage07 `PASS`, does not create Stage08 or implementation authorization, and does not authorize application, product, or feature implementation. It MUST NOT permit scope expansion, unrelated repair, destructive operations, or bypass of authoritative owners. After remediation, normal Stage07 MUST be rerun, and only a valid Stage07 `PASS` may authorize normal Stage08 implementation. Historical gate and evidence facts remain immutable and MUST NOT be rewritten to manufacture authority.

Stage08 MUST receive a sealed authorization envelope that identifies:

- approved current Product Requirement, Technical Contract, Implementation Decision, and Agent Repository Governance authority;
- approved task decomposition and exact task;
- a valid Stage07 `PASS` and implementation-authorization state;
- repository, branch, and baseline identity;
- exact allowed files and behavior scope;
- required verification; and
- atomic checkpoint conditions.

The execution agent MUST NOT enlarge, alter, or infer additions to the envelope. If required work, files, requirements, tasks, or behavior outside it are discovered, the agent MUST `STOP -> REPORT -> ROUTE` to the task, authority, or gate owner. Unexpected changes outside scope are blockers until explained or resolved.

Stage08 MUST preserve independently valid in-scope progress after partial failure. Each checkpoint MUST cover one independently verifiable atomic task and occur only after every configured checkpoint prerequisite passes. Execution evidence and state MUST identify the baseline, task, changed files, verification results, checkpoint, valid progress, failure point, and remaining scope.

## 8. Test, evidence, and qualification governance

Every verification outcome MUST be exactly one of:

- `PASS`: the identified check executed and satisfied its criterion;
- `FAIL`: the identified check executed and did not satisfy its criterion; or
- `NOT RUN`: no qualifying execution evidence exists.

Agents MUST NOT claim an unexecuted check passed, incomplete testing is verified, partial `PASS` is complete, missing evidence is safe, or stale/irrelevant evidence qualifies current scope. Reports MUST identify checked scope, evidence references or gaps, and known regression risk.

Tests and checks are evidence; they are not `PRODUCT_REQUIREMENT` authority. Test `PASS` does not create Stage09 `PASS`. Stage09 exclusively owns `VERIFICATION_DECISION`. Stage10 exclusively owns `RELEASE_DECISION`, and Stage09 `PASS` is required for normal Stage10 entry.

## 9. Failure and recovery behavior

When a command, Git operation, provider, test, environment, authority, security check, or execution step fails, the agent MUST:

- preserve valid completed work;
- identify the exact failed step and affected scope;
- retain truthful partial state;
- stop unsafe continuation; and
- report an applicable retry, remediation, revision, escalation, or Human Decision route.

Recovery MUST NOT broaden authority, erase relevant history, fabricate success, retroactively qualify work, or silently restart blocked scope.

## 10. Pre-existing implementation Recovery Gate

The narrow Recovery Gate applies only under its configured pre-existing-implementation eligibility and prerequisites. It MUST NOT be used for ordinary or new development.

The Recovery Gate MUST NOT retroactively create Stage07 `PASS`, create Stage08 authorization, authorize implementation, prove implementation conformance, prove tasks `DONE`, prove tests `PASS`, produce Stage09 `PASS`, or authorize Stage10 or release.

A Recovery Gate `PASS` permits Stage09 entry only when all configured prerequisites hold. It does not provide a shortcut to Stage08. An implementation gap found after Stage09 requires valid current authority and the normal `Stage07 -> Stage08` authorization path. The current Recovery Gate is not evaluated by this authority.

## 11. Destructive, high-risk, security, deployment, and release operations

An agent MUST obtain applicable explicit authorization before executing a destructive, high-risk, security-sensitive, deployment, or release operation. This includes governed-scope deletion, destructive reset or clean, force operations, history rewrite, destructive migration, secret/security-sensitive mutation, deployment, and release.

Authorization MUST identify the target and scope sufficiently to prevent broader action. Lifecycle gates remain required in addition to operation-level authorization. Missing authorization or an unresolved security or authority conflict MUST keep affected execution blocked.

## 12. Traceability governance

Agents MUST preserve and support the canonical chain:

`G -> FR/NFR/EC -> AC -> SPEC -> DES -> TASK -> CODE -> TEST_EVIDENCE`

Links MUST be repository/Git-backed, current-scope attributable, and navigable in both directions where their owning stages exist. Stage05 does not create `TASK`, `CODE`, or `TEST_EVIDENCE` links; it governs how later agents preserve them. Broken required links MUST remain explicit and withhold dependent completion. Chat memory MUST NOT substitute for persistent traceability.

## 13. Reporting and handoff

After governed work, an agent MUST report, as applicable:

- files changed and commands run;
- verification performed with `PASS`, `FAIL`, or `NOT RUN`;
- evidence references and unresolved issues;
- blocked or incomplete scope and authority boundary encountered;
- next step; and
- commit status.

Reports MUST be concise but auditable. They SHOULD use changed-file summaries, targeted diffs, short line excerpts, hashes, repository state, and section-specific review. They MUST NOT dump entire large files or huge diffs by default. When a material judgment requires full-file or full-diff review, the agent MUST say so and identify the required scope.

Stage08 handoff MUST preserve exact implementation evidence and gaps. Stage09 alone may issue the verification decision. Stage10 alone may issue the release decision; deployment or release still requires every applicable gate and operation-level authorization.

## 14. Stage05 status

```text
CURRENT_AGENT_REPOSITORY_GOVERNANCE_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

HISTORICAL_PHASE05_RECONSTRUCTION =
NOT_AUTHORIZED

PRODUCT_INTENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

PRODUCT_REQUIREMENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

TECHNICAL_CONTRACT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

IMPLEMENTATION_DECISION_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

AGENT_REPOSITORY_GOVERNANCE_COVERAGE_COMPLETE =
YES

BLOCKING_GOVERNANCE_CONFLICT =
NO

BLOCKING_GOVERNANCE_TBD =
NO

IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

AGENT_REPOSITORY_GOVERNANCE_PROJECT_AUTHORITY_REVIEW_REQUIRED =
NO

NEXT_STEP =
CURRENT_EXECUTION_DECOMPOSITION_DEFINITION
```
