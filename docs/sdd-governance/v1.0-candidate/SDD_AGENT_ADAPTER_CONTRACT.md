# SDD_AGENT_ADAPTER_CONTRACT.md

> Contract Version: 1.0-draft
> SDD Baseline: v0.4-agent-adapter-rc
> Status: Accepted Architecture Contract / Runtime migration pending
> Owner: SDD Orchestrator / Control Plane
> Applies to: Codex, Claude Code, OpenAI API providers, external-command agents, future providers

---

## 1. Purpose

The Agent Adapter Contract defines how an LLM / Coding Agent may connect to SDD without acquiring SDD lifecycle authority.

The invariant is:

```text
SDD owns governance, authority, stage progression, evidence policy and authorization.
Agent owns provider-specific reasoning and/or authorized workspace execution.
```

Changing providers must not require changing the canonical Stage 01–10 lifecycle.

---

## 2. Provider-Agnostic Architecture

```text
                    SDD Orchestrator
                         │
              ┌──────────┴──────────┐
              │                     │
      Reasoning Adapter     Implementation Adapter
              │                     │
      01–07 / 09 / 10              08
              │                     │
       structured result      authorized edits
                                    │
                              Orchestrator Verify
                                    │
                               Git Checkpoint
```

One provider may implement one or both adapter roles.

Examples:

- Codex CLI: reasoning + implementation
- OpenAI Responses API: reasoning; implementation only if a separately governed tool/workspace implementation exists
- Claude Code: intended reasoning + implementation adapter
- External command: only capabilities explicitly declared and validated

---

## 3. Absolute Authority Boundary

An Agent Adapter MUST NOT:

- create its own lifecycle stage
- change Stage entry/exit conditions
- grant implementation authorization
- grant release authorization
- invent a Stage 07 / 09 / 10 formal result outside the requested stage result contract
- overwrite another domain's authoritative artifact to resolve a conflict
- bypass protected paths
- infer permission from provider capability
- infer permission from existing source code
- treat chat/session memory as project execution authority
- retroactively create historical authorization
- treat provider narrative as runtime execution evidence

Provider power never enlarges SDD authority.

---

## 4. Adapter Roles

### 4.1 Reasoning Adapter

Used primarily for:

- Stage 01–07
- Stage 09
- Stage 10
- Initialization classification when an AI-assisted classifier is permitted
- other non-workspace reasoning tasks explicitly authorized by SDD

Minimum interface:

```text
execute_reasoning(request) -> reasoning_result
```

Canonical semantics:

- receives an SDD-built context/envelope
- operates without unauthorized repository mutation
- returns machine-parseable structured output
- emits only allowed artifacts
- cannot claim commands/tests ran unless supplied runtime evidence proves them

Default sandbox expectation:
`READ_ONLY`

---

### 4.2 Implementation Adapter

Used for Stage 08 authorized execution.

Minimum interface:

```text
execute_implementation(task_envelope) -> agent_execution_result
```

The implementation adapter may:

- read repository files allowed by execution policy
- edit only task-authorized paths
- run provider-local safe checks if permitted

It does NOT own final verification, checkpoint authorization, or task completion truth.

Default sandbox expectation:
`WORKSPACE_WRITE_SCOPED`

---

## 5. Common Adapter Capability Manifest

Every adapter must declare capabilities before selection.

Logical schema:

```yaml
adapter:
  id: "codex_cli"
  version: "..."
  provider: "openai"
  roles:
    reasoning: true
    implementation: true

  transport:
    type: "subprocess_stdin"

  authentication:
    mode: "saved_session"

  sandbox:
    reasoning: "read-only"
    implementation: "workspace-write"

  capabilities:
    structured_output: true
    repository_read: true
    repository_write: true
    command_execution: true
    streaming: false
    usage_reporting: false

  limitations:
    - "actual token usage not reliably observable"

  supported_sdd_contract_version: "1.x"
```

An adapter MUST fail closed if required capabilities are missing.

---

## 6. Common Request Envelope

Provider-specific prompts are rendered from an SDD-owned request envelope.

Minimum fields:

```yaml
request:
  request_id: "..."
  stage_id: "08"
  stage_name: "IMPLEMENTATION"
  role: "implementation"

  stage_contract: {}
  stage_instructions: "..."

  authority:
    owned_domains: []
    forbidden_domains: []
    protected_artifacts: []

  artifacts: {}
  semantic_inputs: {}
  runtime_inputs: {}

  authorization:
    implementation_authorized: true
    release_authorized: false

  execution_scope:
    task_id: "T001"
    allowed_paths: []
    verification_commands: []
    prohibited_paths: []

  evidence_refs: []
  metadata: {}
```

The SDD envelope is authoritative over any provider-specific default behavior.

---

## 7. Reasoning Result Contract

Minimum logical result:

```yaml
result:
  status: "COMPLETED | BLOCKED | FAILED"
  artifacts: {}
  result: null
  classification: null
  remediation_reasons: []
  convergence_tasks: []
  provider_metadata: {}
```

For Gate stages, the stage-specific schema constrains the formal result vocabulary.

An adapter cannot broaden allowed Stage vocabulary.

---

## 8. Implementation Result Contract

The provider result is evidence about what the agent attempted, not final truth.

Minimum logical result:

```yaml
agent_execution_result:
  provider_status: "COMPLETED | FAILED | TIMEOUT | BLOCKED"
  attempted_task_id: "T001"
  claimed_changed_paths: []
  stdout_summary: null
  stderr_summary: null
  provider_metadata: {}
```

The Orchestrator MUST independently determine:

- actual changed paths
- protected-path violations
- actual Git diff
- actual verification command results
- task completion eligibility
- checkpoint eligibility

Provider-declared changed paths may be recorded, but never substitute for repository inspection.

---

## 9. Stage 08 Execution Envelope

Before dispatching an implementation agent, SDD must establish:

- Stage 07 PASS or valid approved recovery/continuation path as applicable
- implementation authorization is current
- Atomic Task identity
- allowed paths
- prohibited/protected paths
- relevant PRD / SPEC / DES references
- declared verification commands
- Git/repository baseline
- unresolved conflict/TBD state
- current task/recovery state

If any required field cannot be trusted:

`STOP → REPORT → ROUTE`

Do not dispatch the provider.

---

## 10. Verification Ownership

This is a critical invariant:

```text
Agent edits.
Orchestrator verifies.
Git records.
Stage 09 decides conformance.
Stage 10 decides release.
```

An adapter may run local checks, but those checks do not become authoritative merely because the provider reports them.

Authoritative runtime evidence requires Orchestrator-controlled or independently validated execution evidence.

---

## 11. Protected Authority Artifacts

By default, Stage 08 implementation adapters must treat these as protected:

- `docs/PRD.md`
- `docs/spec.md`
- `docs/Design.md`
- `AGENTS.md`
- `tasks.md`

Additional `.sdd/*` control/state files may also be protected unless explicitly writable by the relevant runtime contract.

If an Agent determines that an authoritative artifact must change:

```text
STOP affected implementation
→ report required authority change
→ route to owner Stage
→ propagate downstream
→ re-run applicable Gate
```

---

## 12. Error Normalization

Provider-specific errors must map into SDD-neutral categories.

Canonical categories:

- `ADAPTER_UNAVAILABLE`
- `AUTHENTICATION_REQUIRED`
- `CAPABILITY_MISMATCH`
- `PROVIDER_TIMEOUT`
- `PROVIDER_FAILURE`
- `INVALID_STRUCTURED_OUTPUT`
- `SCOPE_VIOLATION`
- `PROTECTED_PATH_VIOLATION`
- `RUNTIME_EVIDENCE_MISMATCH`
- `UNKNOWN_PROVIDER_ERROR`

Provider-specific wording can be kept as metadata, not governance state.

---

## 13. Authentication Boundary

Authentication is adapter-specific, but credentials are not SDD authority artifacts.

Allowed examples:

- saved CLI login/session
- environment-provided API credential
- cloud workload identity
- delegated provider token

Requirements:

- secrets must not be persisted into normal SDD run packets
- auth state must not grant additional repository scope
- auth failure must fail closed
- provider identity/version should be recorded when observable

---

## 14. Telemetry / Cost Boundary

Adapters should expose usage when the provider supplies trustworthy structured usage.

Rules:

- provider-reported actual usage may be recorded with provenance
- unavailable actual usage must remain unknown/null
- prompt length or stdout size must not be presented as actual billed tokens
- telemetry is non-authoritative for lifecycle progression unless a future explicit budget Gate says otherwise

---

## 15. Provider Selection Rules

Provider selection is separate from lifecycle authority.

Selection may consider:

- adapter availability
- declared capabilities
- stage role
- sandbox compatibility
- model quality
- reliability
- latency
- cost / token policy
- user/org policy

Selection MUST NOT consider a provider eligible when it lacks mandatory SDD capabilities.

No automatic provider fallback may silently weaken:

- sandbox
- output schema
- authority protection
- verification
- evidence
- auth boundary

---

## 16. Codex Adapter Mapping

Current Codex integration maps as follows:

### Codex Reasoning
- role: Reasoning Adapter
- transport: subprocess/stdin
- sandbox: read-only
- structured output: yes
- auth: saved Codex / ChatGPT login

### Codex Stage 08
- role: Implementation Adapter
- transport: subprocess/stdin
- sandbox: workspace-write
- repository-aware: yes
- final runtime verification: Orchestrator-owned
- Git checkpoint: Orchestrator-governed

Existing Codex-specific classes may remain during migration, but their behavior must converge to this contract.

---

## 17. Claude Code Adapter Target

Claude Code is approved as an adapter target, not declared implemented.

A future Claude Code adapter MUST satisfy the same contract:

- same authority envelope
- same protected-path rules
- same Stage 08 authorization gate
- same Orchestrator verification ownership
- same normalized results/errors
- same fail-closed rules

No Claude-specific capability may bypass SDD governance.

---

## 18. API / Remote Agent Compatibility

The contract supports:

- CLI subprocess adapters
- HTTPS/API reasoning adapters
- remote/cloud coding agents
- sandbox services

Transport differences belong inside the adapter.

The Orchestrator should not need provider-specific lifecycle rules.

---

## 19. Adapter Conformance Test Suite

A provider is not "SDD-compatible" until it passes common conformance tests.

Minimum tests:

1. Reject unsupported role/capability.
2. Reasoning adapter cannot mutate repository under read-only contract.
3. Structured result outside schema is rejected.
4. Output artifact outside allowed output paths is rejected.
5. Stage 08 cannot run without current implementation authorization.
6. Stage 08 cannot write protected authority artifact.
7. Actual diff outside allowed paths is detected independently of provider claim.
8. Provider-claimed test PASS cannot replace Orchestrator verification.
9. Timeout maps to normalized timeout category.
10. Auth failure fails closed.
11. Chat/session memory cannot establish project state.
12. Provider cannot grant release authorization.
13. Provider swap does not change stage transition semantics.
14. Recovery rules remain identical across providers.
15. Adapter metadata records provider/adapter identity when observable.

---

## 20. Migration Rule

Current implementation has separate Codex reasoning and Codex Stage 08 classes.

Migration SHOULD proceed incrementally:

1. freeze this common contract
2. add common capability/result/error types
3. wrap existing Codex reasoning adapter
4. wrap existing Codex Stage 08 adapter
5. run conformance suite against Codex
6. add Claude Code adapter
7. run the same conformance suite
8. only then enable provider selection/routing

Do not rewrite the mature Codex runner merely for abstraction elegance before conformance tests exist.
