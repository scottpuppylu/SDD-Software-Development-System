
# SDD Software Development System v1.2.0 — Codex-first default

> **Default authentication:** Codex CLI + ChatGPT login. No OpenAI API key is required for the standard SDD 01–10 workflow.
>
> Stage 01–07/09/10 run as independent read-only `codex exec` reasoning jobs with structured output. Stage 08 uses Codex workspace-write for implementation. Repository + `.sdd/state` + Git remain the persistent source of truth.

This package converts the existing SDD 01–10 v2.3 governance into machine-readable runtime contracts.

## Files

- `.sdd/system.yaml` — global principles, authority map, vocabularies, runtime locations.
- `.sdd/stages.yaml` — executable contract registry for Stage 01–10, routers, and rerun rules.
- `.sdd/state/project-state.yaml` — lifecycle state.
- `.sdd/state/implementation-state.yaml` — restart/recovery contract for Stage 08.
- `.sdd/state/authority-state.yaml` — unresolved authority conflicts and routing state.

`authority-state.yaml` is ignored runtime state. On a clean clone, create it only
from validated repository-backed inputs:

```bash
sdd --repo . authority-state-bootstrap
```

The command requires a clean Git worktree, refuses to overwrite inconsistent
existing state, and never derives authority from chat or file existence.

## Core invariant

Lifecycle progression is sequential and gated, while artifact dependencies and authority routing are non-linear.

The Orchestrator may route, load artifacts, update runtime state, and grant authorization from formal gate results. It may not override Product, Technical, Design, Governance, Verification, or Release authority.

## Next milestone

M2 should implement an Orchestrator that:

1. Loads `system.yaml` and `stages.yaml`.
2. Reads `project-state.yaml`.
3. Resolves required artifacts for the current stage.
4. Validates entry conditions.
5. Runs the stage executor.
6. Parses/validates the stage result.
7. Updates state.
8. Routes to the next stage or remediation owner.
9. Creates a Git checkpoint for state-changing operations where applicable.


## M2 Orchestrator Core

A minimal Python orchestrator is included under `sdd_orchestrator/`.

Examples:

```bash
python -m sdd_orchestrator.cli --repo . status
python -m sdd_orchestrator.cli --repo . current
python -m sdd_orchestrator.cli --repo . check --stage 07
python -m sdd_orchestrator.cli --repo . record-result 07 PASS
python -m sdd_orchestrator.cli --repo . route-conflict PRODUCT_REQUIREMENT TECHNICAL_CONTRACT
```

The current implementation intentionally does **not** call an LLM or Codex yet. It first establishes deterministic repository/state/gate behavior. Stage executors are the next layer.

## M3 — Stage Executor Layer

M3 separates **machine governance** from **reasoning execution**:

```text
stages.yaml                Stage-specific Instructions
(machine contract)         (.sdd/instructions/stage-XX.md)
          \                 /
           \               /
            StageExecutionRequest
                    |
             Executor Adapter
                    |
             structured JSON result
                    |
       Output validation + scope guard
                    |
           state transition/router
```

### New capabilities

- `StageRunner.build_request()` resolves the current Stage's required artifacts automatically.
- Required artifacts are passed by content; the user no longer copy/pastes upstream documents.
- Stage-specific instruction text is loaded separately from `.sdd/instructions/stage-XX.md`.
- `ExternalCommandExecutor` defines a stable JSON stdin/stdout protocol for future OpenClaw/LLM/Codex adapters.
- `sdd packet` creates a non-mutating execution packet for inspection/debugging.
- `sdd run --executor-command ...` executes a configured adapter and validates its structured result.
- Declared outputs are mandatory before a Stage can advance.
- Non-Stage-08 executors cannot write outside their declared output scope.
- Stage 09 context includes bounded UTF-8 snapshots of `src/`, `tests/`, Git history, and `.sdd/evidence/` when present.
- Every run writes an audit record under `.sdd/runs/`.

### CLI examples

```bash
# Inspect the current stage
python -m sdd_orchestrator.cli --repo . current

# Build a request packet without executing or changing lifecycle state
python -m sdd_orchestrator.cli --repo . packet --stage 02 \
  --semantic APPROVED_PRODUCT_DECISIONS=yes

# Use any external executor that accepts request JSON on stdin and returns result JSON on stdout
python -m sdd_orchestrator.cli --repo . run --stage 02 \
  --semantic APPROVED_PRODUCT_DECISIONS=yes \
  --executor-command "python examples/json_executor_stub.py"
```

### Executor protocol

Input JSON contains:

- Stage ID/name/type and core question
- Complete machine Stage contract
- Resolved required artifact contents
- semantic inputs
- runtime evidence
- Stage-specific instruction text, when installed

Output JSON contains:

```json
{
  "status": "COMPLETED",
  "artifacts": {"docs/spec.md": "..."},
  "result": null,
  "classification": null,
  "remediation_reasons": [],
  "metadata": {}
}
```

Gate stages must return their formal result vocabulary. Stage 09 `FAIL` must additionally classify the failure as `IMPLEMENTATION_GAP` or `AUTHORITY_CONTRACT_CONFLICT`.

### Intentional boundary

M3 does **not** yet bind a real AI provider. This is deliberate: orchestration semantics, artifact loading, authority boundaries, write scope, and state transitions are deterministic before connecting OpenClaw or Codex. A real reasoning adapter can now be plugged into the stable executor protocol without changing SDD governance.

## M4 / v1.1 — Real Reasoning Adapter

The current default provider is `CodexExecReasoningExecutor`, authenticated through the user's saved Codex CLI / ChatGPT login. The OpenAI Responses adapter remains optional.

### Default single-stage reasoning

```bash
python -m sdd_orchestrator.cli --repo . run --codex --stage 03 \
  --semantic KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY="none"
```

### Default multi-stage reasoning pipeline

```bash
python -m sdd_orchestrator.cli --repo . pipeline \
  --provider codex \
  --stop-before 04 \
  --semantic '01:IDEA_OR_PROBLEM=Describe the product idea here' \
  --semantic '01:TARGET_USER_OR_USAGE_CONTEXT=Describe the user/context' \
  --semantic '01:GOALS_OR_DESIRED_OUTCOME=Describe the desired outcome'
```

`--provider codex` is the default and may be omitted. Each Stage uses a fresh ephemeral `codex exec` job with read-only sandbox and schema-constrained final output.

### Optional OpenAI API provider

```bash
export OPENAI_API_KEY="..."
python -m sdd_orchestrator.cli --repo . pipeline \
  --provider openai \
  --model <supported-model> \
  --stop-before 04 \
  --semantic '01:IDEA_OR_PROBLEM=...' \
  --semantic '01:TARGET_USER_OR_USAGE_CONTEXT=...' \
  --semantic '01:GOALS_OR_DESIRED_OUTCOME=...'
```

The API path is retained for portability but is not required.

### Stage Instructions

Stage-specific instructions live under `.sdd/instructions/stage-01.md` through `stage-10.md`. Machine-readable contracts remain the control layer; instruction files remain the reasoning layer.

### Authority boundary

Reasoning Codex runs read-only and returns artifact contents in a structured response. The Orchestrator validates allowed outputs and writes them. Stage 08 alone uses the dedicated coding runner with workspace-write permissions.


## M5 — Git Checkpoint & Recovery

M5 turns Git and `.sdd/state/implementation-state.yaml` into restart evidence rather than treating chat history as execution state.

### Inspect Git/runtime state

```bash
python -m sdd_orchestrator.cli --repo . git-status
python -m sdd_orchestrator.cli --repo . recovery
```

`recovery` reconciles the implementation restart contract with Git HEAD, recent commits, and dirty worktree state, then returns a recommended action such as `INSPECT_DIRTY_WORKTREE`, `RESUME_CURRENT_TASK`, `SELECT_NEXT_TASK`, or `RECONCILE_TASK_STATE`.

### Safe atomic checkpoint

```bash
python -m sdd_orchestrator.cli --repo . checkpoint \
  --task T023 \
  --summary "implement retry transition" \
  --type feat \
  --scope assessment \
  --path src/assessment/retry.py \
  --path tests/assessment/test_retry.py \
  --next-task T024
```

Safety rules:

- Explicit paths are mandatory; automatic `git add -A` is intentionally not used.
- Unrelated dirty files block the checkpoint unless explicitly overridden.
- Paths escaping the repository are rejected.
- A successful checkpoint updates `last_completed_task`, `current_task`, `last_verified_commit`, and test status in the implementation restart contract.

This prepares the next milestone: a Stage 08 Codex adapter that executes one authorized Atomic Task at a time and delegates checkpointing to this Git runtime.

## M6 — Stage 08 Codex Adapter

Stage 08 now has a dedicated Codex CLI adapter. It uses Codex non-interactively as the coding execution engine while the SDD Orchestrator retains gate, scope, verification, and checkpoint authority.

### Safety model

- Stage 07 must be `PASS` and implementation authorization must be true.
- `tasks.md` must expose a machine-detectable Implementation Scope / Allowed Paths and verification command for each executable task.
- Codex runs with `workspace-write` sandbox and no interactive approval prompts by default; use only inside the repository workspace.
- Codex is explicitly forbidden from committing or modifying authoritative SDD contracts.
- The Orchestrator compares the pre/post Git working tree and rejects out-of-scope writes.
- Verification commands are re-run by the Orchestrator using a conservative command allowlist and no shell operators.
- Only after verification passes does the Orchestrator create an explicit-path Git checkpoint and update implementation state.
- Completion of Stage 08 transitions to Stage 09; it never asserts conformance itself.

### Commands

```bash
python -m sdd_orchestrator.cli --repo . codex-task --task T001
python -m sdd_orchestrator.cli --repo . codex-stage08 --max-tasks 100
```

For a deliberate task-boundary pause, run the full controller with one Stage 08 task per invocation:

```bash
sdd --repo /path/to/project auto --max-steps 1
```

After a verified task checkpoint the CLI prints `SAFE TO STOP`, the last completed task, and the next task. Stage 08 also emits progress messages and a heartbeat every 30 seconds by default; use `--heartbeat-seconds 0` to disable heartbeat output.

Codex must already be installed and authenticated on the machine running the Orchestrator.

## M7 — Human Decision Gateway

The system now creates persistent Decision Requests only for genuine authority/product/high-risk decisions. A decision is stored under `.sdd/decisions/DR-*.yaml`; normal artifact handoff remains automatic.

A human resolution is **not** allowed to directly rewrite PRD/Spec/Design. The resolution is recorded as authoritative input, then the owning stage must rerun and update its own artifact. This preserves domain-specific authority.

```bash
python -m sdd_orchestrator.cli --repo . decision-list --status OPEN
python -m sdd_orchestrator.cli --repo . decision-show DR-...
python -m sdd_orchestrator.cli --repo . decision-resolve DR-... --resolution DISALLOW --note "Must PASS first"
```

## M8/M9 — OpenClaw + LINE Interface Package

The package now includes an OpenClaw Agent Skill under `integrations/openclaw/skills/sdd-system/` and a LINE decision-interface guide under `integrations/openclaw/line/`.

OpenClaw is deliberately an outer interaction/orchestration layer: it inspects status, launches authorized SDD commands, surfaces Decision Requests, and records explicit human resolutions. It does not become a Product/Technical/Design authority.

An installer script is included at `integrations/openclaw/install-skill.sh`.
