- Stage 10 now receives bounded supplemental release evidence from `README.md`, `pyproject.toml`, and release-specific handoff documents when present.
- Stage 10 now receives live Git release identity (branch, HEAD, tags-at-HEAD, working-tree status, and recent commits) using the existing UTF-8-safe Git subprocess path.
- Added a Stage 10 context policy statement clarifying that supplied documents are evidence, not automatic release authorization.
- Added bounded per-file and total-size limits to avoid repeating the Stage 09 context-window failure mode.
- Added regression coverage for release-profile visibility, live Git identity, and context bounds.

## v1.1.21
- Finalize T014 evidence-index Markdown from Orchestrator-executed Verification Commands before the T014 checkpoint.
- Treat pre-verification Codex/provider narrative as provisional evidence, not runtime execution authority.
- Add an idempotent legacy reconciliation path for repositories completed under v1.1.18-v1.1.20 with contradictory T014 Markdown vs PASS runtime JSON.
- Before Stage 09, automatically create an evidence-only reconciliation checkpoint when stale T014 indexes are detected; do not rerun implementation.
- Preserve Stage 09 as the sole owner of the final Verification Decision.
- No new Python dependencies.

## v1.1.20
- Add Stage 09 Context Diet for implementation evidence.
- Prefer T014 post-implementation evidence indexes when present.
- Replace raw `.sdd/evidence` transcript/diff injection with bounded structured summaries.
- Preserve task status, verification and checkpoint metadata while omitting verbose provider payloads.
- Bound Stage 09 evidence-summary context to prevent Codex context-window exhaustion.
- No new Python dependencies.

## v1.1.19

- Fixed Stage 09/runtime-input Git subprocess decoding in `runner.py` to use explicit UTF-8 with replacement fallback on Windows.
- Added defensive handling for absent Git stdout/stderr so a failed reader thread cannot cascade into `None.strip()` errors.
- Added regression coverage for non-ASCII Git commit subjects in Stage 09 `GIT_HISTORY` collection and `stdout=None` handling.

## v1.1.18

- Fixed Stage 08 protected-path handling for T014 evidence indexing: only the explicitly task-authorized `.sdd/state/implementation-state.md` and `.sdd/state/post-implementation-verification.md` artifacts may be written/checkpointed; governance/runtime control files remain protected.
- Added safe, read-only Git verification support for `git status --short`, `git log --oneline --decorate -N`, and `git diff --check`; mutating Git commands remain blocked.
- Added Stage 08 progress output for task start, Codex completion, verification commands/results, checkpoint creation, and next task.
- Added periodic Stage 08 heartbeat output during long Codex and verification operations (`--heartbeat-seconds`, default 30; 0 disables).
- Formalized task-boundary safe pause: `auto --max-steps 1` returns `SAFE_STOP` after a verified checkpoint when another Atomic Task remains, and also reports a safe stop when the final Stage 08 task advances to Stage 09.
- Added regression coverage for T014 evidence writes, protected-state enforcement, read-only Git verification, heartbeat, and safe-stop semantics.

## v1.1.17

- Git runtime subprocesses now decode stdout/stderr explicitly as UTF-8 with replacement fallback on Windows.
- Git snapshot defensively treats absent log stdout as an empty string, preventing secondary `None.splitlines()` crashes.
- Added regression coverage for non-ASCII Git commit subjects.

# v1.1.16

- Stage 08 now treats only **untracked, reproducible Python verification artifacts** (`*.egg-info/`, `__pycache__/`, `*.pyc`) as non-authoritative dirty byproducts.
- Tracked files matching those names remain protected and participate in scope checks.
- This allows atomic-task resume after editable-install/import verification without weakening Allowed Files enforcement.

# CHANGELOG

## v1.1.13 — Stage 08 stdin execution prompt transport hotfix

- Send the complete Stage 08 Codex prompt through forced UTF-8 stdin using `codex exec -` instead of a multiline positional argv value.
- Add an explicit `BEGIN EXECUTION NOW` directive so Codex performs the Atomic Task instead of merely acknowledging governance instructions.
- Preserve workspace-write sandboxing, ephemeral sessions, UTF-8 decoding, and Orchestrator-owned verification/checkpointing.
- Added regression coverage for multiline stdin prompt transport and execution-directive presence.

## v1.1.12 — Windows UTF-8 Stage 08 subprocess hotfix

- Force UTF-8 decoding for Stage 08 Codex stdout/stderr on Windows.
- Force UTF-8 decoding for Stage 08 Verification Commands.
- Use replacement decoding for malformed bytes so reader threads cannot crash and falsely produce NO_CHANGES.
- Added regression coverage for Codex subprocess encoding.

# Changelog

## v1.1.8
- Added authoring-stage read-modify-write context for Stages 02–06.
- Existing authoritative stage output is automatically supplied on rerun/remediation.
- Preserves stable IDs and existing decomposition during targeted remediation.
- Previous gate reports are intentionally excluded from fresh Stage 07/09/10 decisions.
- Introduced Rolling Update packaging and updater bootstrap.

## v1.1.7
- Formalized Stage 06 ↔ Stage 08 machine task contract.
- Added machine-readable allowed-file fields and Verification Commands support.

## v1.1.9
- Fix lifecycle invalidation during explicit upstream remediation reruns.
- Stage 02-07 reruns no longer leave stale downstream `IN_PROGRESS` states.
- Revoke stale implementation/release authorization when upstream contracts are rerun.
- Preserve historical `.sdd/runs` and Git checkpoints while resetting only mutable lifecycle projection.
## v1.1.10
- Fix Stage 08 parsing of ordered-list `Verification Commands` (`1.`, `2.`, ...).
- Support both `**Field:**` and `**Field**:` section-heading forms without cross-line field capture.
- Add narrowly allowlisted package bootstrap/import/help verification commands used by Stage 06 T001.
- Keep arbitrary `python -c`, shell operators, and arbitrary console mutations blocked.
- Add regression coverage using the real T001 machine-contract shape observed in smoke testing.


## v1.1.11

- Fixed Stage 08 Codex CLI invocation compatibility with Codex CLI v0.147.0.
- Removed the obsolete `--ask-for-approval` argument from `codex exec`.
- Preserved the explicit `workspace-write` sandbox and ephemeral execution mode.
- Added regression coverage ensuring Stage 08 no longer emits removed approval flags.

## v1.1.15
- Resolve project console-script verification executables explicitly against the project verification PATH before subprocess launch (Windows/PATHEXT compatibility).
- Convert missing verification executables into structured return-code 127 verification evidence instead of uncaught FileNotFoundError traceback.
