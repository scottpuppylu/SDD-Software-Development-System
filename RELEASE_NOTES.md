## v1.2.0-baseline

Release readiness: **READY_WITH_KNOWN_ISSUES**.

Since `v1.1.22-baseline`, this baseline completes Stage 02 product convergence and hardens Stage 08 recovery, evidence handling, and convergence. It strengthens `SAFE_STOP` and `max_tasks` behavior, protects completed (`DONE`) tasks, cleans up T014 handling, makes evidence and convergence writes atomic, and revokes stale release authorization when Stage 10 becomes `BLOCKED`.

Validation completed: Stage 08 hardening closure COMPLETE; Stage 08 regression 73 passed + 14 subtests; Stage 07→10 cross-stage smoke 9 passed; Stage 10 blocker targeted regression PASS; runner + orchestrator 17 passed.

Known issues (deferred; not release blockers):

1. Deferred P1: checkpoints may include pre-existing staged paths.
2. Deferred P1: historical reconciliation has not yet verified actual commit diff scope against allowed, protected, and evidence paths.
3. Coverage gap: Stage 09 non-PASS → Stage 10 entry rejection lacks an independent regression test.

### Stage 10 Release Context Collection

Stage 10 previously evaluated only its static required inputs and Stage 09 report. Release evidence added after verification—such as `docs/handoff/release-profile.md`, README setup/recovery instructions, and `pyproject.toml` version metadata—could exist in Git but remain invisible to the release reasoning request. This caused false `BLOCKED` results claiming that release identity, CI applicability, migration applicability, smoke strategy, and recovery evidence had not been supplied.

v1.1.22 adds a bounded Stage 10 supplemental context packet containing release-relevant repository artifacts and live Git identity. Stage 10 remains the sole Release Decision authority; the patch only makes existing evidence visible and does not convert evidence presence into `READY`.

## v1.1.21 — Post-Verification Evidence Reconciliation

This rolling patch fixes the T014 evidence inconsistency discovered by Stage 09: Codex could write final-looking Markdown before the Orchestrator ran the declared verification commands, leaving a stale BLOCKED/INCOMPLETE narrative even when the machine verification later passed and a T014 checkpoint was created.

For new T014 runs, the Orchestrator now finalizes the two task-authorized evidence indexes from the actual Verification Command return codes before checkpointing. Provider narrative remains useful as a draft, but it is not runtime execution authority. Stage 09 still exclusively owns the final PASS/FAIL/INCOMPLETE decision.

For repositories already affected under v1.1.18-v1.1.20, entering Stage 09 performs an idempotent evidence-only reconciliation from the latest PASS T014 JSON, creates a dedicated reconciliation checkpoint only when needed, updates implementation-state.yaml to that checkpoint, and then proceeds to Stage 09. No Todo implementation tasks are rerun.

No Python dependencies were added.

## v1.1.20 — Stage 09 Context Diet

This rolling patch fixes the Stage 09 Codex context-window exhaustion observed after the successful T014 checkpoint. Stage 09 no longer injects complete Stage 08 evidence JSON payloads containing Codex transcripts, raw stdout/stderr, prompts, patches, and diffs. Instead it receives bounded structured evidence summaries and, when available, the T014 post-implementation evidence indexes.

Task/result, verification, checkpoint, and timestamp metadata remain available for traceability. Source code, tests, authoritative PRD/Spec/Design/AGENTS/tasks, implementation state, and Git history remain part of the Stage 09 reasoning packet. The evidence-summary budget is capped and explicitly marks omitted verbose data rather than silently truncating authority contracts.

No project code or Stage 08 checkpoints need to be rerun. After applying the patch, resume `sdd auto` from the existing T014 checkpoint and re-enter Stage 09. No Python dependencies were added.

## v1.1.19 — Stage 09 Git UTF-8 runtime-input hotfix

This rolling patch fixes the Windows CP950 crash observed immediately after the T014 Stage 08 checkpoint while Stage 09 was collecting `GIT_HISTORY`. `runner.py` now applies the same explicit UTF-8/replacement decoding contract already used by the Git runtime layer, and treats missing subprocess stdout/stderr defensively.

No project code or Stage 08 checkpoints need to be rerun. After applying the patch, resume `sdd auto` from the existing repository state; the orchestrator should enter Stage 09 from the completed T014 checkpoint. No Python dependencies were added.

## v1.1.18 — Stage 08 evidence path, progress, and safe-stop update

This rolling patch resolves the smoke-test blocker at T014 without weakening SDD authority protection. T014 may write only its two explicitly declared Stage 09 evidence-state artifacts under `.sdd/state/`; other `.sdd` control files remain protected. The T014 read-only Git verification commands are now preserved and safely allowlisted.

Stage 08 now prints task/Codex/verification/checkpoint progress plus periodic heartbeat output. For deliberate notebook shutdowns, `sdd ... auto --max-steps 1` is a supported task-boundary safe-stop mode: the runner exits only after verification, Git checkpoint, and implementation-state persistence.

No Python dependencies were added. Existing v1.1.17 installations can apply this rolling patch and resume the current smoke test from T014; T001–T013 do not need to be rerun.

## v1.1.17

- Git runtime subprocesses now decode stdout/stderr explicitly as UTF-8 with replacement fallback on Windows.
- Git snapshot defensively treats absent log stdout as an empty string, preventing secondary `None.splitlines()` crashes.
- Added regression coverage for non-ASCII Git commit subjects.

# v1.1.16

- Stage 08 now treats only **untracked, reproducible Python verification artifacts** (`*.egg-info/`, `__pycache__/`, `*.pyc`) as non-authoritative dirty byproducts.
- Tracked files matching those names remain protected and participate in scope checks.
- This allows atomic-task resume after editable-install/import verification without weakening Allowed Files enforcement.

# SDD Software Development System v1.1.13

## Stage 08 execution prompt transport hotfix

Stage 08 now sends its full Atomic Task execution prompt to Codex via forced UTF-8 stdin (`codex exec -`) rather than as a multiline positional command-line argument. This avoids Windows prompt-transport truncation/quoting issues observed when Codex received only the first governance line and returned an acknowledgement with no file changes.

The prompt also ends with an explicit execution directive requiring Codex to begin the authorized task immediately. Orchestrator-owned verification and Git checkpointing remain unchanged.

# SDD Software Development System v1.1.12

## Windows Stage 08 UTF-8 subprocess hotfix

Stage 08 now explicitly decodes Codex CLI and verification subprocess output as UTF-8 with safe replacement fallback. This prevents Windows CP950 reader-thread crashes that previously discarded successful Codex output and caused false `NO_CHANGES` results.

No Python dependencies were added. Existing v1.1.11 installations can apply the rolling patch and continue the current Stage 08 repository without re-running Stage 06 or Stage 07 authoring.

## v1.1.15 — Windows project console-script verification
Stage 08 now resolves commands such as `todo --help` to the executable installed in the selected project Python's `Scripts` directory before launching them. Missing executables are reported as verification failures rather than crashing the orchestrator.
