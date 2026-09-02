# Pre-Existing Implementation Lifecycle Recovery Amendment

## 1. Purpose

This document establishes the approved current lifecycle amendment for the narrow case in which implementation materially existed before the current authority baseline, but the historical project-specific Stage07 decision is confirmed unavailable. It defines how current authority and lifecycle provenance may be recovered sufficiently to permit prospective Stage09 conformance verification without inventing historical authorization.

Approval of this amendment defines the recovery mechanism only. It does not mean this repository has passed the Recovery Gate, and it does not itself authorize Stage09 entry.

## 2. Authority boundary

Project authority has explicitly approved this amendment as current lifecycle recovery authority. Its operative representation is defined in `.sdd/system.yaml` and `.sdd/stages.yaml`.

The amendment does not create historical evidence, replace a missing Stage07 decision, grant implementation authorization, determine implementation conformance, issue a Recovery Gate, Stage09, or Stage10 result, or authorize release. The existing domain-specific authority model and conflict protocol remain applicable.

The following prohibitions are invariant:

```text
RETROACTIVE_STAGE07_PASS = FORBIDDEN
RETROACTIVE_IMPLEMENTATION_AUTHORIZATION = FORBIDDEN
```

## 3. Problem being corrected

Before this amendment, `.sdd/stages.yaml` defined only a sequential lifecycle in which Stage07 `PASS` authorized Stage08 and Stage08 completion led to Stage09. Its minimum completion definition required `stage_07 == PASS` and defined no provenance branch for implementation predating current recovery authority when the historical Stage07 decision is `NOT_FOUND`.

`docs/project/project-authority-reconstruction.md` truthfully records the historical Stage07 decision as `NOT_FOUND`. That absence cannot be converted into `PASS`.

The former `docs/project/whole-project-closure-authority-baseline.md` nevertheless directly authorized Stage09. That direct entry was invalid under the then-unamended lifecycle and is now prospectively superseded through this explicit recovery mechanism, without fabricating a historical Stage07 decision or treating existing implementation as proof of authorization.

## 4. Normal lifecycle preserved

The normal lifecycle remains unchanged:

```text
Stage01
-> Stage02
-> Stage03
-> Stage04
-> Stage05
-> Stage06
-> Stage07 PASS
-> Stage08
-> Stage09
-> Stage10
```

Normal development continues to require Stage07 `PASS` before Stage08. `PRE_EXISTING_IMPLEMENTATION_RECOVERY` is a distinct provenance path for legacy authority recovery and closure; it does not weaken, replace, or provide an elective alternative to Stage07 for ordinary development.

## 5. Recovery eligibility

`PRE_EXISTING_IMPLEMENTATION_RECOVERY` may be considered only when all of the following are established and recorded truthfully:

1. The implementation materially predates the current recovery authority.
2. The historical project-specific Stage07 decision is established as `NOT_FOUND`, meaning unavailable after the applicable bounded authority inquiry, rather than merely inconvenient to obtain.
3. No historical Stage07 `PASS` is inferred, synthesized, or fabricated.
4. Project authority explicitly approves use of recovery for the repository and scope at issue.
5. The recovery mechanism does not authorize new implementation work.
6. The purpose is authority, conformance, or closure recovery for pre-existing implementation, not ordinary new development.

Failure to establish any eligibility condition makes the recovery path unavailable. Recovery eligibility itself is not a recovery-gate `PASS` and does not authorize Stage09.

## 6. Current authority package prerequisite

Before `CURRENT_IMPLEMENTATION_RECOVERY_GATE` may be evaluated, all six artifacts below must both exist and be explicitly approved as the current authority package:

- `docs/proposal.md`
- `docs/PRD.md`
- `docs/spec.md`
- `docs/Design.md`
- `AGENTS.md`
- `tasks.md`

Existence alone is insufficient. Approval must be explicit and attributable to the appropriate current authority. The package must be complete enough to provide an internally consistent baseline for Stage09 conformance verification, with applicable traceability and task/completion conditions defined. A draft, missing approval, unresolved authority conflict, or incomplete required artifact prevents a recovery-gate `PASS`.

## 7. Current Implementation Recovery Gate

The current recovery gate is named:

```text
CURRENT_IMPLEMENTATION_RECOVERY_GATE
```

Its core question is:

> Does this pre-existing implementation now have a complete, approved, internally consistent current authority baseline and sufficient lifecycle provenance to enter Stage09 verification without fabricating historical Stage07 authorization?

The gate must evaluate recovery eligibility, explicit project-authority approval, approval and consistency of the complete current authority package, truthful historical provenance, and the absence of any claim that recovery authorizes new implementation. Its decision must be explicit and recorded in `docs/handoff/implementation-recovery-gate-report.md` under the `IMPLEMENTATION_RECOVERY_DECISION` authority domain. This amendment defines the gate but does not issue a result.

## 8. Result semantics

The result vocabulary is:

```text
PASS
FAIL
INCOMPLETE
```

No result is issued by this amendment.

`PASS` means only that all recovery prerequisites are satisfied and Stage09 entry is permitted for conformance verification of the pre-existing implementation against approved current authority.

`PASS` does not mean that Stage07 historically passed, Stage08 was historically authorized, existing code conforms, all tasks are `DONE`, tests pass, Stage09 passes, or release is authorized. It is neither historical Stage07 `PASS`, retrospective implementation authorization, proof of conformance, nor Stage09 `PASS`.

`FAIL` means a substantive recovery eligibility, authority, consistency, provenance, or anti-bypass condition is not satisfied. It routes to the applicable authority owner for remediation and does not authorize Stage09.

`INCOMPLETE` means required evidence, an artifact, approval, provenance record, or gate input is missing or insufficient to decide. It routes to authority remediation and does not authorize Stage09.

## 9. Stage08 relationship

Recovery distinguishes historical existing implementation from new Stage08 work. It does not retroactively validate or reconstruct historical Stage08 authorization and does not create a shortcut into Stage08.

If Stage09 later identifies an `IMPLEMENTATION_GAP` that requires new implementation work, that work remains unauthorized until separately routed through valid current authority and the normal Stage07-to-Stage08 authorization path before execution. This amendment does not allow a recovery-gate `PASS` to authorize convergence work, source changes, test changes, or any other new implementation activity.

## 10. Stage09 relationship

Direct Stage09 entry is invalid under the current lifecycle without an approved `CURRENT_IMPLEMENTATION_RECOVERY_GATE` `PASS`. Only after the gate returns `PASS` may Stage09 begin under recovery provenance.

In that case, Stage09 is solely prospective verification of the pre-existing implementation against the complete, approved current authority. Stage09 remains an independent gate and may return `PASS`, `FAIL`, or `INCOMPLETE`. Recovery-gate `PASS` neither predicts nor constrains its result. Stage10 entry continues to require Stage09 `PASS`.

## 11. Completion-provenance model

The lifecycle distinguishes two mutually clear provenance branches for whole-project completion eligibility:

```text
NORMAL_PROVENANCE:
stage_07 == PASS

RECOVERY_PROVENANCE:
pre_existing_implementation_recovery == APPROVED
AND historical_stage_07_decision == NOT_FOUND
AND current_implementation_recovery_gate == PASS
AND retroactive_stage_07_pass == FORBIDDEN
AND retroactive_implementation_authorization == FORBIDDEN
```

Whichever provenance branch applies, completion eligibility must also require:

- all applicable required task and completion conditions under the approved current authority model;
- `stage_09 == PASS`; and
- `stage_10 in [READY, READY_WITH_KNOWN_ISSUES]`.

Stage09 and Stage10 retain their normal independent result semantics. Recovery provenance supplies neither result and does not itself establish whole-project completion.

## 12. Anti-bypass safeguards

This amendment enforces these safeguards:

1. Only implementation materially predating current recovery authority qualifies.
2. Explicit project-authority approval is required for recovery selection.
3. Historical Stage07 must be established as unavailable and `NOT_FOUND`, not merely inconvenient.
4. Recovery cannot be selected for ordinary or new development.
5. Recovery cannot authorize new implementation or convergence work.
6. All six current authority artifacts must exist and be explicitly approved.
7. The recovery-gate result must be explicit and recorded.
8. Eligibility, approvals, historical absence, and gate provenance must be recorded truthfully.
9. No historical Stage07 `PASS` may be inferred, synthesized, or fabricated.
10. Recovery must not retrospectively validate historical Stage08 authorization.
11. Stage09 remains mandatory and independent.
12. Stage10 remains conditional on Stage09 `PASS` and retains its normal decision vocabulary.
13. A `FAIL` or `INCOMPLETE` recovery result routes to authority remediation and cannot authorize Stage09.
14. Any new work discovered in verification must follow current authority and the normal required authorization path.

## 13. Implemented lifecycle representation

The approved lifecycle representation does the following:

- adds an explicit `PRE_EXISTING_IMPLEMENTATION_RECOVERY` eligibility and provenance model;
- defines the authority owner, inputs, decision artifact, and evaluation semantics for `CURRENT_IMPLEMENTATION_RECOVERY_GATE`;
- encodes `PASS`, `FAIL`, and `INCOMPLETE` without issuing a project-specific result;
- requires explicit approval of the complete six-artifact current authority package before gate evaluation;
- permits Stage09 entry only after an approved amendment and recovery-gate `PASS`;
- preserves normal Stage07-to-Stage08 authorization for all new implementation;
- prevents recovery from authorizing Stage08 or convergence implementation;
- updates completion eligibility to support the normal and recovery provenance branches while preserving shared task, Stage09, and Stage10 conditions; and
- defines truthful, auditable provenance recording without silently deciding or disguising historical facts.

The exact representation is now encoded in `.sdd/system.yaml` and `.sdd/stages.yaml`. It issues no project-specific Recovery Gate result.

## 14. Closure-baseline correction

`docs/project/whole-project-closure-authority-baseline.md` formerly contained an invalid direct-Stage09 sequence and direct Stage09 authorization. That portion has been prospectively superseded and corrected to require current authority package completion and a Recovery Gate `PASS` before Stage09 entry.

The correction preserves Stage09 independence and the condition that Stage10 may begin only after Stage09 `PASS`. It creates neither historical Stage07 `PASS` nor retrospective Stage08 authorization.

## 15. Explicit non-authorizations

This amendment does not:

- infer or create historical Stage07 `PASS`;
- retrospectively authorize implementation or historical Stage08;
- issue a recovery-gate result;
- approve the current authority package;
- authorize Stage09 under the current lifecycle;
- predetermine Stage09 or Stage10;
- establish implementation conformance, task completion, or passing tests;
- authorize new implementation, source changes, test changes, release, or deployment; or
- declare the project complete.

## 16. Current authority status

This amendment is explicitly approved current lifecycle recovery authority. Approval defines the recovery mechanism only; it does not approve the six-artifact current authority package, issue a Recovery Gate result, or authorize Stage09. The next step is current authority package completion.

LIFECYCLE_RECOVERY_AMENDMENT =
APPROVED_CURRENT_AUTHORITY

RECOVERY_MODEL =
PRE_EXISTING_IMPLEMENTATION_RECOVERY

NORMAL_STAGE07_REQUIREMENT_CHANGED =
NO

HISTORICAL_STAGE07_PASS_INFERRED =
NO

RETROACTIVE_STAGE07_PASS =
FORBIDDEN

RETROACTIVE_IMPLEMENTATION_AUTHORIZATION =
FORBIDDEN

NEW_IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_AUTHORITY_PACKAGE_REQUIRED =
YES

CURRENT_IMPLEMENTATION_RECOVERY_GATE_DEFINED =
YES

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

DIRECT_STAGE09_UNDER_CURRENT_LIFECYCLE =
INVALID_WITHOUT_APPROVED_RECOVERY_GATE_PASS

STAGE09_AFTER_APPROVED_RECOVERY_GATE_PASS =
AUTHORIZED

STAGE09_RESULT =
NOT_EVALUATED

STAGE10_RESULT =
NOT_EVALUATED

CLOSURE_BASELINE_CORRECTION_REQUIRED =
NO

SDD_LIFECYCLE_FILES_MODIFIED =
YES

PROJECT_AUTHORITY_REVIEW_REQUIRED =
NO

NEXT_STEP =
CURRENT_AUTHORITY_PACKAGE_COMPLETION
