# OpenClaw + LINE Human Decision Interface

LINE is treated only as a **human interaction channel**. It does not become an SDD authority.

## Intended flow

```text
SDD Orchestrator
  -> normal stage: continue automatically
  -> Decision Request required: WAIT_FOR_HUMAN_DECISION
OpenClaw
  -> presents DR-ID + question + options in LINE
User
  -> explicitly chooses/resolves
OpenClaw
  -> records decision through `decision-resolve`
SDD Orchestrator
  -> reruns the authoritative owner stage
```

## Configuration principles

- Install/configure the official OpenClaw LINE channel plugin according to the OpenClaw version you run.
- Store the LINE channel access token and channel secret in OpenClaw's supported secret/config mechanism, never in the SDD repository.
- Prefer direct-message interaction for approval/decision workflows unless group-channel policy is explicitly designed.
- Require an explicit decision containing the DR-ID or an unambiguous resolution; never treat casual conversation as approval.
- Do not display secrets, internal environment variables, or raw credentials in LINE.

## Suggested human message format

```text
SDD needs your decision
Decision: DR-...
Stage: 03 -> Product owner Stage 02
Question: ...
Impact: ...
Options:
A. ...
B. ...
Reply with: DR-... A
```

The channel adapter should translate that reply into the local `decision-resolve` CLI call. The authoritative owner stage must then rerun; the LINE/OpenClaw layer must not edit the contract itself.
