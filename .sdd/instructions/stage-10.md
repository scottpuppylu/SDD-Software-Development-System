# SDD 10 — Handoff & Release

You own only the **Release Readiness Decision**. Entry requires Stage 09 PASS. Do not reopen or rewrite Product/Technical/Design decisions here.

Review release identity, required tests/build/lint/typecheck/CI, security, documentation, migration readiness, deployment readiness and rollback/recovery readiness.

Result vocabulary is exactly `READY | READY_WITH_KNOWN_ISSUES | BLOCKED`.

`READY_WITH_KNOWN_ISSUES` must never hide a P0 blocker, security blocker, data-loss blocker, unresolved authority conflict, failed required CI/build, or missing critical rollback/recovery strategy.

A release-critical migration/rollback/recovery gap is a BLOCKED release condition, even when Stage 09 and tests are PASS.
