# SDD_REMOTE_SANDBOX_SECURITY_CONTRACT.md

> Contract Version: 1.0-draft
> SDD Baseline: v0.7-remote-sandbox-security-rc
> Status: Accepted Architecture / Security Contract
> Owner: SDD Control Plane / Sandbox Runtime
> Security Posture: FAIL-CLOSED + LEAST CAPABILITY

---

## 1. Purpose

Remote Sandbox is the execution substrate for Zero-DevEnv SDD.

Its purpose is to let users avoid local setup while ensuring that an LLM / Coding Agent never gains broader authority merely because it runs in the cloud.

Core invariant:

`Sandbox capability <= SDD-authorized capability`

Provider/runtime capability MUST NOT enlarge:
- lifecycle authority
- repository scope
- credential access
- network reach
- production access
- destructive-action authority

---

## 2. Trust Boundaries

Canonical architecture:

```text
User / Web UI
      ↓
SDD Control Plane
      ↓
Authorization / Policy / Evidence
      ↓
Remote Sandbox
  ├─ Agent Runtime
  ├─ Project Workspace
  ├─ Tool Runtime
  ├─ Build/Test
  ├─ Git
  └─ Temporary Credentials
      ↓
Explicitly Allowed External Services
```

The sandbox is not the SDD authority owner.

The Control Plane remains responsible for:
- lifecycle state
- authorization
- approval class
- sandbox policy
- credential issuance
- audit/evidence
- snapshot/release identity

---

## 3. Isolation Unit

Default isolation unit:

`one governed execution workspace per project execution context`

A sandbox MUST NOT share writable project filesystem state with another unrelated project or tenant.

Minimum isolation dimensions:
- filesystem
- process namespace/runtime
- environment variables
- credentials
- writable temp space
- network policy
- execution logs
- artifact namespace

Cross-project/tenant data access is forbidden unless explicitly authorized by a separate integration contract.

---

## 4. Sandbox Lifecycle

Default lifecycle:

```text
ALLOCATE
→ PROVISION
→ LOAD exact project baseline
→ INJECT bounded runtime policy
→ INJECT short-lived credentials if required
→ EXECUTE
→ VERIFY / COLLECT EVIDENCE
→ EXPORT approved artifacts/state
→ REVOKE credentials
→ DESTROY sandbox
```

Default sandbox is ephemeral.

Persistence belongs in governed external stores such as:
- Git repository
- SDD state/evidence store
- approved artifact store
- approved cache store

Do not depend on hidden sandbox disk persistence for recovery.

---

## 5. Sandbox Classes

### S0 — READ_ONLY_REASONING

For Stage 01–07 / 09 / 10 reasoning when repository context is required.

- repository read: yes
- repository write: no
- command execution: only non-mutating commands allowed by policy
- network: denied or allowlisted as required
- production credentials: no

### S1 — WORKSPACE_WRITE

For Stage 08 implementation.

- project workspace write: task-scoped
- protected authority artifact write: denied by default
- command execution: bounded
- network: denied by default / explicit allowlist
- production write access: no

### S2 — STAGING_OPERATION

For approved staging deploy/integration operations.

- staging credentials only
- no production credentials
- environment-target restricted
- auditable external side effects

### S3 — PROTECTED_PRODUCTION_ACTION

Not a general coding sandbox.

Only for exact approved protected action with A2/A3 or valid pre-authorization.

Examples:
- production deploy
- credential rotation
- controlled migration
- rollback

Must use a narrow action runner rather than an unrestricted general-purpose Agent workspace whenever practical.

---

## 6. Credential Boundary

Secrets MUST NOT be persisted in:
- repository files
- normal SDD run packets
- prompts unless the provider specifically requires an opaque delegated credential mechanism
- chat transcripts
- artifact outputs
- logs

Preferred credential model:
- short-lived
- least-privilege
- target-specific
- environment-specific
- revocable
- auditable

Credential issuance must bind to:
- project
- action
- sandbox identity
- environment
- expiration
- approval/pre-authorization where required

Sandbox termination must revoke or expire credentials.

---

## 7. Production Credential Rule

General Stage 08 sandboxes MUST NOT receive production-write credentials.

Production credentials may only be issued to a protected-action context after:
- exact action identified
- Human Approval Boundary satisfied
- Stage/release prerequisites satisfied
- target/environment verified
- scope checked
- rollback/recovery requirements checked

Broad reusable production admin credentials are forbidden as the default model.

---

## 8. Network Policy

Default:
`DENY EXCEPT REQUIRED`

Network access must be declared by capability/policy.

Possible classes:
- NONE
- PACKAGE_REGISTRY_ONLY
- DOCUMENTATION_READ_ONLY
- APPROVED_API_READ_ONLY
- APPROVED_SERVICE_WRITE
- PROTECTED_PRODUCTION_ENDPOINT

Wildcard unrestricted internet access is not the default for autonomous execution.

Network policy must distinguish read from write where feasible.

---

## 9. Package / Dependency Access

Package installation may be allowed when:
- package source is approved
- lockfile/reproducibility expectations are respected
- dependency changes remain inside task scope
- security policy permits it

Agent must not silently add unrelated dependencies.

Production secret access is never justified merely because a package needs it.

---

## 10. Repository Boundary

Sandbox must start from an explicit Git baseline:
- repository identity
- branch/context
- exact commit
- clean/known worktree state

Stage 08:
- changed paths independently inspected
- protected paths enforced
- unexpected diff stops checkpoint
- checkpoint bound to exact commit

Sandbox filesystem state alone is not recovery evidence.

---

## 11. File Upload / User Artifact Boundary

Uploaded files must be scoped to the project/run that owns them.

Requirements:
- no cross-project visibility
- filename/path sanitization
- size/type limits
- extraction/archive traversal protection
- no automatic execution of uploaded binaries/scripts
- uploaded content does not become authority merely by existence

Untrusted files are data until explicitly promoted through applicable Stage authority.

---

## 12. Tool Execution Boundary

Every tool capability should be classified:

- READ
- WORKSPACE_WRITE
- NETWORK_READ
- NETWORK_WRITE
- PROCESS_EXECUTION
- CREDENTIAL_USE
- PROTECTED_EXTERNAL_ACTION

Agent can only receive tools required by the current execution envelope.

No "all tools available just in case" default.

---

## 13. Process / Resource Limits

Every sandbox must have bounded resources.

At minimum:
- wall-clock timeout
- CPU quota or runtime limit
- memory limit
- disk limit
- process count limit
- output/log size limits
- network request limits where supported

Resource exhaustion must result in normalized failure/evidence, not uncontrolled continuation.

---

## 14. Kill Switch

Control Plane must be able to:
- stop current sandbox
- prevent new dispatch
- revoke credentials
- mark project execution blocked
- preserve available evidence

Kill switch must not depend on the Agent cooperating.

---

## 15. Audit / Evidence

At minimum record:
- sandbox/run identity
- project/repo identity
- baseline commit
- adapter/provider identity
- sandbox class
- granted capabilities
- network policy
- credential class/reference (never secret value)
- start/end/outcome
- changed paths
- verification results
- external protected actions
- approval/pre-authorization reference
- resulting checkpoint/snapshot identity

Audit evidence must survive sandbox destruction.

---

## 16. Multi-Tenant / Multi-Project Isolation

If SDD becomes multi-user:

MUST:
- namespace projects and artifacts
- isolate workspaces
- isolate credentials
- isolate logs/evidence
- authorize every project access at Control Plane
- prevent one sandbox from discovering another tenant's filesystem/processes/secrets

A provider session authenticated for one user/project must not be silently reused across tenants unless the authentication system explicitly provides safe tenant isolation.

---

## 17. Provider Session Boundary

Ephemeral provider sessions are the safe default.

Persistent provider sessions may be introduced only when:
- identity binding is explicit
- project/tenant separation is proven
- context leakage is prevented
- stale authority/session state cannot authorize execution
- logout/revocation semantics exist

Provider memory/session state is not SDD execution state.

---

## 18. Environment Separation

At minimum distinguish:
- development
- test
- staging
- production

Credentials, network targets, approval classes and action runners must respect environment.

A staging sandbox cannot promote itself to production.

Environment identity must be machine-checkable.

---

## 19. Protected Production Actions

Prefer dedicated narrow action runners rather than a general coding Agent for:
- production deploy
- destructive migration
- production data deletion
- IAM/security change
- credential rotation
- rollback with data impact

Protected action runner receives:
- exact target
- exact release/snapshot identity
- exact command/action contract
- exact approval token/reference
- minimum credential
- timeout
- rollback/evidence requirements

---

## 20. Secret Redaction

Logs/output must redact known secrets and credential-bearing fields.

Do not assume hash-only storage makes low-entropy secrets safe.

On suspected secret exposure:
- stop affected flow
- mark incident
- revoke/rotate as applicable
- preserve redacted evidence

---

## 21. Sandbox Failure Semantics

Normalize failures:
- SANDBOX_ALLOCATION_FAILED
- SANDBOX_POLICY_DENIED
- RESOURCE_LIMIT_EXCEEDED
- NETWORK_POLICY_DENIED
- CREDENTIAL_UNAVAILABLE
- CREDENTIAL_SCOPE_MISMATCH
- WORKSPACE_BASELINE_MISMATCH
- PROTECTED_PATH_VIOLATION
- EXTERNAL_ACTION_DENIED
- SANDBOX_TIMEOUT
- SANDBOX_TERMINATED

Failure must fail closed.

---

## 22. Zero-DevEnv UX Rule

The user should not need to manage:
- Docker
- Python/Node installation
- Git commands
- env vars
- dependency installation
- sandbox lifecycle

But hidden infrastructure must remain observable through high-level status:
- Preparing environment
- Running task
- Verifying
- Saved Snapshot
- Waiting for approval
- Blocked
- Restored
- Released

Simplicity must not hide security state.

---

## 23. No Authority Through Infrastructure

Forbidden:
- sandbox admin privilege implies SDD authority
- cloud provider IAM implies product/technical approval
- repository write access implies Stage 08 authorization
- production credential existence implies deployment approval
- Agent network access implies permission to contact arbitrary services

Infrastructure capability is not governance authority.

---

## 24. Minimum Acceptance Tests

1. Read-only sandbox cannot modify repo.
2. Stage 08 sandbox cannot write protected authority artifacts.
3. Sandbox cannot access another project workspace.
4. Sandbox cannot read another project's credentials.
5. General Stage 08 sandbox receives no production-write credential.
6. Network default denies unapproved endpoint.
7. Allowed endpoint access succeeds only within declared policy.
8. Expired/revoked credential fails closed.
9. Dirty/baseline mismatch prevents governed execution.
10. Resource timeout terminates execution.
11. Kill switch stops execution without Agent cooperation.
12. Sandbox destruction leaves required Git/evidence externally recoverable.
13. Uploaded archive path traversal is rejected.
14. Uploaded executable is not auto-run.
15. Staging credential cannot access production target.
16. Protected production action requires valid A2/A3/pre-authorization.
17. Exact protected-action approval cannot be reused for changed target/release.
18. Audit log contains capability/policy identities without secret values.
19. Provider session cannot determine lifecycle authority.
20. Cross-tenant project access is denied.
