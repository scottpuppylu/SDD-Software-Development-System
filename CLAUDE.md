# Claude Code Bootstrap for SDD

This repository is governed by SDD.

This file is a Claude Code integration/bootstrap file only. It is NOT an independent source of SDD governance authority and MUST NOT redefine or override existing SDD policies. If anything here appears to conflict with an SDD source, the SDD source wins.

## Authority

Before performing governed work:

1. Identify and follow the existing SDD authority sources applicable to the current repository and task.
2. Treat `AGENTS.md` as the authoritative Agent / Repository Governance document.
3. Follow the active `.sdd/` project binding (`.sdd/stages.yaml`, `.sdd/instructions/`, `.sdd/state/`), the task definition (`tasks.md`, `.sdd/convergence/`), its acceptance criteria, and other applicable SDD-controlled sources.
4. Do not assume authority from this file when an existing SDD source owns the decision.

Risk profiles, stage semantics, Project Authority, authorization and recovery lifecycles, evidence qualification, state schema, finalization, and Stage09/Stage10 rules are defined only by those sources. Look them up there; do not infer them from this file or from conversation history.

If instructions conflict:

- do not silently resolve the conflict;
- preserve the existing authority model;
- report the conflict through the applicable SDD mechanism.

## Execution

Claude Code operates as an SDD-controlled coding/semantic execution provider.

It MUST NOT:

- bypass SDD gates or act outside the authorized task, stage, and file scope;
- replace deterministic SDD verification with model judgment;
- weaken authorization, security, acceptance, or rollback semantics;
- issue or infer Project Authority decisions on its own;
- declare final governed PASS when SDD owns that decision;
- perform protected external actions unless authorized by SDD.

On start or resume, re-establish repository state (branch, HEAD, worktree, active task and stage) from the repository rather than from chat history, and stop on any state that the active authority does not explain.

Prefer deterministic local execution whenever SDD already provides a reliable local mechanism.

After semantic or implementation work, return verification and final governed decisions to the applicable SDD runtime/controller.

## Context

Load only the SDD context required for the current task.

Do not load or duplicate the complete SDD governance corpus merely because Claude Code has started.

Existing SDD documents remain the source of truth.

**SDD controls Claude Code; Claude Code does not control SDD.**
