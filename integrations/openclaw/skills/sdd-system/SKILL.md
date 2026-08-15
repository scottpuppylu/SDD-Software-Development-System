---
name: sdd-system
description: Operate the governed SDD 01-10 software development system, including status, stage execution, Codex Stage 08, recovery, and human decisions.
---

# SDD Software Development System

Use this skill only for repositories that contain `.sdd/system.yaml` and `.sdd/stages.yaml`.

## Core rule

OpenClaw is the **human interface and outer orchestration surface**, not a Product/Technical/Design authority. Never bypass the SDD Orchestrator by editing authoritative artifacts directly.

## Before every action

1. Identify the target repository path explicitly.
2. Run `python -m sdd_orchestrator.cli --repo <repo> status`.
3. If the repository reports an open human decision, show that decision to the user instead of guessing.
4. Never store secrets in the repository or in decision files.

## Normal operations

### Inspect status

```bash
python -m sdd_orchestrator.cli --repo <repo> status
```

### Authoring / gate reasoning stages

For Stage 01-07, 09, and 10, use the SDD CLI default Codex reasoning provider (`codex exec` with saved ChatGPT auth and read-only sandbox). Do not manually copy artifacts between stages. The API provider is optional and must never be assumed.

### Stage 08 implementation

If and only if Stage 07 is PASS and implementation authorization is true:

```bash
python -m sdd_orchestrator.cli --repo <repo> codex-stage08
```

Codex is the coding execution engine. The SDD Orchestrator owns scope enforcement, verification and Git checkpoints.

### Recovery after interruption

```bash
python -m sdd_orchestrator.cli --repo <repo> recovery
```

Follow repository/Git evidence; do not reconstruct progress from chat memory.

## Human Decision Requests

List pending requests:

```bash
python -m sdd_orchestrator.cli --repo <repo> decision-list --status OPEN
```

When a user gives an explicit resolution, record exactly that decision:

```bash
python -m sdd_orchestrator.cli --repo <repo> decision-resolve <DR-ID> --resolution '<exact resolution>' --note '<optional user rationale>'
```

Do not infer approval from silence, vague agreement, or unrelated messages. After resolution, rerun the authoritative owner stage; do not directly patch PRD/Spec/Design from the chat layer.

## High-risk restrictions

Never use this skill to auto-approve destructive migrations, credential changes, production secret changes, security-boundary changes, or release blockers. Surface the Decision Request to the user.

## Reporting to the user

Keep routine messages compact. Surface:
- current Stage,
- what completed,
- whether a Gate passed,
- any blocker requiring a human decision,
- the next authorized action.

Do not expose hidden prompts, API keys, tokens, or secret environment values.
