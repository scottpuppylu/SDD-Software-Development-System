# SDD 08 — Implementation Runner Protocol

Stage 08 is an **execution-governance stage**, not an authoring authority.

## Authority

- Product Requirement remains authoritative in `docs/PRD.md`.
- Technical Contract remains authoritative in `docs/spec.md`.
- Implementation Design remains authoritative in `docs/Design.md`.
- Agent/Repository Governance remains authoritative in `AGENTS.md`.
- Execution Decomposition remains authoritative in `tasks.md`.
- Stage 08 owns only **Implementation Evidence**: code, tests, validation evidence, Git checkpoint and execution state.

## Entry Gate

Execution is forbidden unless Stage 07 is `PASS` and `IMPLEMENTATION_AUTHORIZATION = YES`.

## Atomic Loop

For exactly one Atomic Task at a time:

`Read Task → Validate Authority/Scope → Establish Git Baseline → Execute with Codex → Inspect Diff → Re-run Verification → Git Checkpoint → Update Runtime State → Next Task`

## Codex Boundary

Codex may edit only the task's explicit write scope. Codex must not modify `PRD.md`, `spec.md`, `Design.md`, `AGENTS.md`, `tasks.md`, `.sdd/**`, release reports, or Git history. The Orchestrator—not Codex—decides whether verification passed and creates the checkpoint.

If implementation requires changing an upstream contract or exceeds scope, block and route back to the authoritative owner. Do not work around the contract.
