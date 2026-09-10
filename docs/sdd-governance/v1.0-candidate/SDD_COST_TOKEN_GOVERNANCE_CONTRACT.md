# SDD_COST_TOKEN_GOVERNANCE_CONTRACT.md

> Contract Version: 1.0-draft
> SDD Baseline: v0.8-cost-token-governance-rc
> Status: Accepted Governance Contract
> Owner: SDD Control Plane / Telemetry / Provider Router
> Principle: COST CONTROL MUST NOT WEAKEN GOVERNANCE

---

## 1. Purpose

This contract defines how SDD observes, budgets and limits:
- provider token usage
- API/model monetary cost
- sandbox/runtime cost
- provider call count
- time/runtime consumption

The purpose is to prevent uncontrolled autonomous spending without sacrificing:
- authority coverage
- Gate correctness
- evidence
- security
- traceability

Core rule:

`When budget and governance conflict, stop or route; do not silently weaken governance.`

---

## 2. Measurement Truth Classes

SDD distinguishes:

### ACTUAL
Direct trustworthy provider/runtime observation.

Examples:
- provider structured token usage
- provider invoice/call cost when attributable
- sandbox metered runtime cost

### ESTIMATED
Derived estimate using an explicit method/model assumption.

Must include:
- method
- version
- model assumption
- input scope
- timestamp

Estimated values MUST NOT be stored in actual-usage fields.

### CONTEXT_SIZE
Exact chars / UTF-8 bytes / component hashes.

Context-size evidence is not token evidence.

### UNAVAILABLE
No reliable actual observation exists.

Unavailable is not zero.

---

## 3. Token Provenance

Actual token usage is accepted only from a provider interface with attributable structured usage.

Canonical fields may include:

```yaml
usage:
  input_tokens: 1234
  output_tokens: 321
  cached_input_tokens: 800
  reasoning_tokens: 90
  total_tokens: 1555
  quality: actual
  source: provider_response
  provider_response_id: "..."
```

When unavailable:

```yaml
usage:
  input_tokens: null
  output_tokens: null
  total_tokens: null
  quality: unavailable
  unavailable_reason: provider_interface_did_not_expose_usage
```

Do not infer actual usage from:
- prompt characters
- UTF-8 bytes
- stdout/stderr
- Codex CLI human-readable `tokens used`
- aggregate billing dashboard
- tokenizer estimate

---

## 4. Current Provider Boundary

### OpenAI Responses-style provider
Actual usage may be recorded when valid structured usage is returned.

### Codex CLI
Until a versioned reliable machine-readable usage interface is available:

`ACTUAL_TOKEN_USAGE = NOT_RELIABLY_OBSERVABLE`

Therefore Codex CLI budgeting may use:
- provider-call count
- runtime duration
- context bytes
- optional separate estimates

but must not claim exact token consumption.

---

## 5. Budget Dimensions

A Budget Policy may constrain:

- max provider calls per logical execution
- max provider calls per Stage
- max provider calls per hour/day/month
- max actual tokens where observable
- max estimated tokens as a planning guardrail
- max monetary API cost
- max sandbox runtime minutes
- max sandbox cost
- max retries
- max wall-clock execution
- max concurrent sandboxes

Budget dimensions are independent.

---

## 6. Budget Scope

Budgets may be scoped to:

- user
- organization
- project
- environment
- run
- Stage
- task
- provider
- model
- protected action

Example:

```yaml
budget_policy:
  id: BUDGET-SDD-001
  project: project-a
  period: daily
  limits:
    provider_calls: 200
    actual_cost_usd: 20
    sandbox_minutes: 600
  warning_threshold: 0.80
  hard_stop_threshold: 1.00
```

---

## 7. Budget States

Canonical budget state:

- HEALTHY
- WARNING
- NEAR_LIMIT
- EXHAUSTED
- UNKNOWN

UNKNOWN applies when required actual monetary/token observability is missing.

Unknown does not automatically mean exhausted, but policy may prohibit high-cost autonomous continuation when cost cannot be bounded.

---

## 8. Soft vs Hard Limits

### Soft Limit
Crossing triggers:
- notification
- routing optimization
- cheaper conformant provider where policy allows
- reduced parallelism
- delayed non-critical work

No governance weakening.

### Hard Limit
Before new provider/sandbox dispatch:
- stop dispatch
- preserve state/evidence
- return `BUDGET_BLOCKED`
- request Human Decision or next budget window

Already-running protected operations must use their own safe-stop policy.

---

## 9. Pre-Dispatch Budget Check

Before any metered provider/sandbox action:

1. identify provider/model/runtime
2. identify applicable budget policies
3. inspect current attributable usage/cost
4. estimate incremental cost when possible
5. classify budget state
6. apply provider-routing policy
7. dispatch only if permitted

If exact incremental cost is unknowable:
- use declared conservative estimate or policy ceiling
- otherwise classify cost predictability as UNKNOWN

---

## 10. No Mid-Context Truncation

A token/cost budget MUST NOT cause SDD to:
- omit authority-bearing artifacts
- summarize authority where exact content is required
- drop Stage contracts
- drop governance
- drop required evidence
- change Gate vocabulary
- weaken sandbox/security
- dispatch partial optimized context

If a safe complete request cannot fit the allowed provider/context/budget envelope:

`STOP → BUDGET_OR_CAPABILITY_BLOCKED → route`

---

## 11. Context Optimization Boundary

Existing context optimization remains subordinate to governance.

Required invariants for any optimization:
- authority coverage = 100%
- authority byte mismatch = 0
- semantic regression = 0
- lifecycle regression = 0
- Gate regression = 0
- complete atomic dispatch

Measured byte reduction may be reported as byte/context reduction only.

Token savings may be claimed only with trustworthy provider usage or proven provider-boundary measurements.

---

## 12. Retry Budget

Retries are cost-bearing actions.

Each policy must define:
- retryable error classes
- max retry count
- backoff
- whether retry consumes same run budget

Forbidden:
- infinite retry
- retry after a provider call merely because context optimization failed post-dispatch
- retry with weaker governance/provider capability to save cost

---

## 13. Provider Routing for Cost

Cost-aware routing is allowed only among SDD-conformant adapters.

Provider selection may consider:
- capability
- reliability
- model quality
- actual/estimated cost
- latency
- remaining budget

But cost MUST NOT silently downgrade:
- required reasoning/coding capability
- structured output
- sandbox
- authority handling
- verification
- evidence

If no cheaper conformant option exists, block or ask Human Decision.

---

## 14. Quality Tier Policy

Projects may define task tiers:

- CRITICAL
- STANDARD
- ECONOMY

Example:
- Stage 07/09/10 critical governance may require CRITICAL-capable providers.
- routine formatting/document cleanup may permit ECONOMY.
- Stage 08 task model tier may depend on complexity/risk.

Tier is a provider-selection constraint, not lifecycle authority.

---

## 15. Autonomous Spending Boundary

Default autonomous mode may spend only within an explicitly configured budget.

Without a configured monetary budget:
- subscription/session-based providers may continue subject to their platform limits
- metered paid API/cloud resources must not be assumed unlimited
- creation of new paid resources requires Human Approval under the Human Approval contract

Budget changes that increase monetary exposure materially are A2.

---

## 16. Subscription / Quota-Based Providers

Some providers expose quota/capacity instead of per-call billable cost.

SDD may track:
- provider availability
- quota remaining when reliably observable
- rate-limit/capacity errors
- reset windows if supplied

Do not invent a monetary cost from subscription quota.

Quota exhaustion maps to a provider availability/budget condition, not Stage failure.

---

## 17. Cost Ledger

SDD should maintain a non-authoritative Cost Ledger.

Minimum logical record:

```yaml
cost_event:
  event_id: "..."
  run_id: "..."
  stage_id: "08"
  provider: "..."
  model: "..."
  usage_quality: actual | estimated | unavailable
  actual_tokens: null
  estimated_tokens: null
  actual_cost: null
  estimated_cost: null
  sandbox_minutes: 4.2
  currency: USD
  provenance: "..."
```

Cost Ledger does not become Product/Technical/Gate authority.

---

## 18. Reporting

Recommended user-facing reporting:

- current project spend
- period budget
- warning threshold
- provider-call count
- actual vs estimated vs unavailable breakdown
- sandbox runtime
- top cost-driving stages/tasks
- blocked due to budget

Never merge estimated and actual totals without labeling.

---

## 19. Budget + Human Approval

Human Approval classes:

### A0
Routine execution within approved budget.

### A1
Budget warning notification.

### A2
- increase project/API/cloud budget materially
- continue beyond hard budget
- create new paid resource
- switch to materially more expensive provider outside policy

A3 is generally not required merely for cost unless another protected action also applies.

---

## 20. Budget Exhaustion Behavior

On hard-limit exhaustion:

1. stop new metered dispatch
2. preserve repository/snapshot/evidence
3. mark `BUDGET_BLOCKED`
4. identify safely completed work
5. report remaining/unknown cost state
6. offer:
   - resume next budget window
   - Human-approved budget increase
   - cheaper conformant provider if available
   - reduce non-authoritative optional work

Never mark project FAIL solely because budget is exhausted.

---

## 21. Cost Estimate Rules

If estimates are used, they must be conservative and separately labeled.

Estimate must not:
- overwrite actual usage
- be described as provider billing truth
- be used to prove optimization savings
- be proportionally allocated to components unless methodology explicitly supports it

---

## 22. Security and Privacy

Cost telemetry must not persist:
- secrets
- auth headers
- full prompts by default
- sensitive environment variables

Hashes do not automatically anonymize low-entropy secrets.

---

## 23. Stage Impact

Cost governance does not change Stage 01–10 semantics.

Possible effect:
- dispatch may pause with `BUDGET_BLOCKED`

It does not create:
- Stage 07 FAIL
- Stage 09 FAIL
- Stage 10 BLOCKED

unless the Stage itself requires a funded/available production resource as an explicit release prerequisite.

Budget blocking is an operational/control-plane state.

---

## 24. Acceptance Tests

1. Actual provider usage is recorded only from valid structured source.
2. Codex CLI unavailable tokens remain null, not zero.
3. Byte reduction cannot be labeled token savings.
4. Estimate never populates actual usage fields.
5. Soft threshold creates warning without lifecycle mutation.
6. Hard limit blocks new dispatch.
7. Budget exhaustion preserves Git/evidence state.
8. Hard budget does not truncate authority context.
9. No cheaper non-conformant provider fallback is allowed.
10. Valid cheaper conformant provider may be selected.
11. Retry count respects budget policy.
12. Subscription quota is not converted into invented monetary spend.
13. Cost ledger is non-authoritative.
14. Material budget increase requires A2.
15. Budget block is not Stage 09 FAIL.
16. Unknown actual cost remains UNKNOWN, not zero.
