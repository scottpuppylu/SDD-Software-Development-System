# Installation — v1.1.3

## Default architecture

The default SDD reasoning provider is now **Codex CLI authenticated with your ChatGPT account**. An OpenAI API key is **not required** for the normal 01–10 workflow.

```text
Stage 01–07 / 09 / 10 -> Codex CLI, read-only sandbox, structured final output
Stage 08              -> Codex CLI, workspace-write sandbox, task-scoped implementation
Repository + Git      -> persistent state, evidence, checkpoint and recovery
```

The OpenAI Responses API adapter remains available as an optional provider.

## Prerequisites

- Python 3.10+
- Git
- Codex CLI installed
- A ChatGPT account/plan with Codex access
- Optional: OpenAI API access only if you deliberately select the `openai` reasoning provider
- Optional: OpenClaw for outer orchestration / human-decision messaging
- Optional: OpenClaw LINE channel for LINE interaction

## 1. Install the SDD CLI

From the extracted distribution directory:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -e .
```

## 2. Install and authenticate Codex CLI

Install Codex CLI using the current official OpenAI instructions, then authenticate once:

```bash
codex login
```

Complete the browser sign-in with your ChatGPT account. Verify the saved login:

```bash
codex login status
```

Do **not** copy `~/.codex/auth.json` into the project, Git, chat, tickets, or documentation. Treat it like a password.

## 3. Initialize a project

```bash
./scripts/init-project.sh /path/to/your-project
```

The initializer refuses to overwrite an existing `.sdd` directory.

## 4. No API key is needed by default

Do not set `OPENAI_API_KEY` for the default path. The SDD CLI calls `codex exec`, which reuses your saved Codex/ChatGPT authentication.

If you intentionally want the optional API provider, select it explicitly:

```bash
export OPENAI_API_KEY='...'
sdd --repo /path/to/project pipeline --provider openai --model <supported-model>
```

## 5. Security model

Reasoning stages run Codex with:

```text
--sandbox read-only
--ephemeral
--output-schema <generated-schema>
--output-last-message <temporary-result-file>
```

Codex returns a structured result. It does **not** directly write Proposal/PRD/Spec/Design/Gate artifacts during reasoning stages; the SDD Orchestrator validates authority and output paths, then performs the write.

Stage 08 is intentionally different: Codex receives `workspace-write`, but the Orchestrator still validates actual Git diff, Task scope, verification results and checkpoint conditions.

## Optional OpenClaw / LINE

Install the included OpenClaw skill only after the local SDD + Codex path works:

```bash
./integrations/openclaw/install-skill.sh
```

For LINE, follow `integrations/openclaw/line/README.md`. LINE/OpenClaw credentials belong in their own configuration, never in the SDD repository.
