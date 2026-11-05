# Quick Start — Codex CLI / ChatGPT Login

## 1. One-time Codex login

```bash
codex login
codex login status
```

Use the browser flow to sign in with ChatGPT. No OpenAI API key is required for the default workflow.

## 2. Initialize your repository

```bash
/path/to/SDD-Software-Development-System/scripts/init-project.sh /path/to/my-project
cd /path/to/my-project
```

## 3. Install the CLI package

From the SDD distribution folder:

```bash
pip install -e .
```

## 4. Bootstrap ignored runtime authority state

After the structured repository inputs are committed and the worktree is clean:

```bash
sdd --repo /path/to/my-project authority-state-bootstrap
```

This reconstructs repository-backed runtime projections only; it creates no
Stage 07, Stage 08, Stage 09, or release authority.

## 5. Check state

```bash
sdd --repo /path/to/my-project status
```

## 6. Start the full automated workflow

```bash
sdd --repo /path/to/my-project auto \
  --semantic '01:IDEA_OR_PROBLEM=Describe the problem/idea' \
  --semantic '01:TARGET_USER_OR_USAGE_CONTEXT=Describe user/context' \
  --semantic '01:GOALS_OR_DESIRED_OUTCOME=Describe desired outcome'
```

You may optionally select a Codex model with `--model`; if omitted, Codex uses its configured default.

The default path is now:

```text
01 -> codex exec read-only -> proposal.md
02 -> fresh codex exec read-only -> PRD.md
03 -> fresh codex exec read-only -> spec.md
04 -> fresh codex exec read-only -> Design.md
05 -> fresh codex exec read-only -> AGENTS.md
06 -> fresh codex exec read-only -> tasks.md
07 -> fresh codex exec read-only -> Gate
08 -> Codex workspace-write -> tests -> Git checkpoint
09 -> fresh codex exec read-only -> Verification
10 -> fresh codex exec read-only -> Release readiness
```

Each reasoning Stage uses a fresh ephemeral Codex execution. Repository artifacts, `.sdd/state`, and Git are the persistent memory—not a long-running Codex conversation.

## 7. Human decision stop

```bash
sdd --repo /path/to/my-project decision-list --status OPEN
sdd --repo /path/to/my-project decision-show <DR-ID>
sdd --repo /path/to/my-project decision-resolve <DR-ID> --resolution '<explicit decision>'
```

Then run `sdd ... auto` again. The authoritative owner Stage is rerun; the decision gateway does not directly patch PRD/Spec/Design.

## 8. Pause safely at an Atomic Task boundary

When you want to close or shut down the notebook after the next verified Stage 08 task:

```bash
sdd --repo /path/to/my-project auto --max-steps 1
```

The runner completes the current Atomic Task, reruns verification, creates the Git checkpoint, persists implementation state, and reports `SAFE TO STOP`. Progress is printed during Stage 08 and a heartbeat is emitted every 30 seconds by default.

## 9. Recover after interruption

```bash
sdd --repo /path/to/my-project recovery
sdd --repo /path/to/my-project auto
```

Recovery is based on repository state and Git evidence, not chat memory.

## Optional API fallback

Only if you intentionally want API-based reasoning:

```bash
sdd --repo /path/to/my-project auto --reasoning-provider openai --model <supported-model> ...
```

That optional mode requires `OPENAI_API_KEY`. The default `codex` mode does not.
