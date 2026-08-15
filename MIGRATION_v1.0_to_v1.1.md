# Migration: v1.0.0 → v1.1.1

## What changed

The default reasoning provider changed from `OpenAIResponsesExecutor` to `CodexExecReasoningExecutor`.

## What did not change

- SDD 01–10 authority ownership
- Stage contracts and gate semantics
- Stage 08 implementation authorization requirement
- Stage 09 convergence behavior
- Git checkpoint / recovery model
- Human Decision Gateway
- OpenClaw / LINE role boundaries

## Authentication

Default v1.1.1 setup:

```bash
codex login
codex login status
```

No `OPENAI_API_KEY` is required for the default path.

## Default execution split

```text
01–07, 09, 10: codex exec / read-only / ephemeral / structured output
08:             codex exec / workspace-write / task-scoped coding
```

## Optional API fallback

The API adapter remains available. Select it explicitly with `--provider openai` or `--reasoning-provider openai` and configure `OPENAI_API_KEY` outside the repository.

## Existing projects

Existing `.sdd` artifacts remain compatible. For a project already initialized from v1.0.0, update its `.sdd/system.yaml` from the v1.1.1 distribution if you want the machine-readable provider metadata to reflect the new default. The runtime CLI itself selects Codex by default regardless.
