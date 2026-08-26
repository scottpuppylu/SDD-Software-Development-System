# SDD Measurement Contract v1

Status: **FROZEN for M2.2 implementation**
Baseline: `v1.2.0-baseline` / `55092fc1fbfc87be1fe573806125d8b06481ba3c`  
Schema ID: `sdd.measurement.stage_execution`  
Schema version: `1.0.4`

## 1. Purpose and authority boundary

This document is the single naming and serialization contract for Phase 03A measurement implementation. If terminology proposed in Phase 02 Measurement Design or Phase 03 Implementation Planning differs from this document, the exact field names, enum values, nullability, and canonicalization vocabulary in this document win. The minimal consistent names selected here are `event_type`, `component`, `layer`, `availability`, `quality`, `usage_source`, and `outcome_category`; implementations MUST NOT introduce aliases or parallel vocabularies.

Telemetry is observational only. A telemetry event MUST NOT be treated as lifecycle authority, reconstructed into lifecycle authority, or consulted to decide lifecycle behavior.

## 2. Event envelope

Every event is a canonical JSON object with these fields:

| Field | Type | Required | Contract |
|---|---:|:---:|---|
| `schema_id` | string | yes | Always `sdd.measurement.stage_execution`. |
| `schema_version` | string | yes | Always `1.0.4` for this contract. |
| `event_type` | enum | yes | `stage_request`, `provider_call`, or `stage08_task`. |
| `event_id` | string | yes | UUID string generated only for telemetry correlation. |
| `observed_at` | string | yes | UTC RFC 3339 timestamp. It is observational, not an authority timestamp. |
| `stage_id` | string or null | yes | Existing stage identifier when observable; otherwise `null`. |
| `run_id` | string or null | yes | Existing non-authoritative correlation identifier when available; otherwise `null`. MUST NOT be written back into lifecycle state. |
| `outcome_category` | enum or null | yes | `completed`, `blocked`, `failed`, `timeout`, or `null` before an outcome is observable. |
| `metrics` | array of ContentMetric | yes | Empty array when no content metric is observable. |
| `usage` | Usage or null | yes | Provider token-usage observation as defined below. `null` means this event type does not carry provider usage. |
| `metadata` | object | yes | Metadata-only extension object. Values MUST comply with the collection prohibitions in section 10. |

`event_type` is a closed v1 enum:

- `stage_request`: one observation of construction/dispatch of a stage request.
- `provider_call`: one observation of a provider-call boundary. Emitting, retrying, or failing to emit this event MUST NOT create, remove, or change a provider call.
- `stage08_task`: one observation of a Stage 08 task invocation/result boundary.

The required `usage` value is determined by `event_type`:

- `stage_request` MUST use `usage: null`.
- `provider_call` MUST use a Usage object.
- `stage08_task` MUST use `usage: null`; actual Codex process token availability is represented by the associated `provider_call` event.

For `stage_request` and `stage08_task`, `usage: null` means the event type does not carry provider usage. It does not mean unavailable usage or zero usage.

No telemetry event, including the three events above, is lifecycle authority.

## 3. Fixed vocabularies

### 3.1 Component

`component` is exactly one of:

- `governance`
- `stage_instruction`
- `stage_contract`
- `authority_artifacts`
- `operational_state`
- `repo_structure`
- `code`
- `tests`
- `evidence`
- `history`
- `user_input`
- `other`

When `component` is `other`, `classification_reason` MUST be a present, non-empty string. For every other component, `classification_reason` MUST be `null`. An unrecognized component MUST NOT silently be mapped to a known component.

### 3.2 Inclusion/snapshot layer

`layer` is exactly one of:

- `request`
- `system_prompt`
- `user_prompt`
- `rendered`
- `wire`
- `tool_context`

### 3.3 Usage and quality

`availability` is exactly `available` or `unavailable`. `quality` is exactly `actual` or `unavailable`.

`usage_source` is a string vocabulary whose v1 values are:

- `openai_responses_usage`
- `openai_responses_unavailable`
- `codex_cli_unavailable`

Additional sources require a schema-compatible contract revision; implementations MUST NOT invent source spellings locally. Estimates MUST NOT be recorded in any actual usage field or marked with `quality: actual`.

### 3.4 Outcome

`outcome_category` is exactly `completed`, `blocked`, `failed`, or `timeout` when known. It describes an already-determined outcome and never determines that outcome.

## 4. Canonical text and JSON

The canonicalization identifier is:

`sdd.canonical.utf8-sorted-compact-v1`

Canonical text is the original sequence of Unicode code points. No Unicode normalization (including NFC, NFD, NFKC, or NFKD), newline rewriting, whitespace trimming, case folding, or replacement is performed. `chars` is the number of Unicode code points in the original string. `utf8_bytes` is the byte length of the original string encoded with `encode('utf-8')`. Text `sha256` is the lowercase hexadecimal SHA-256 digest of those exact UTF-8 bytes.

Canonical JSON uses UTF-8, `ensure_ascii=false`, recursively sorted object keys, compact separators `(',', ':')`, and no Unicode normalization. It has no BOM and no trailing newline. JSON SHA-256, where required, is the lowercase hexadecimal digest of these canonical UTF-8 bytes. Numbers MUST be emitted as JSON numbers, booleans as JSON booleans, and null as JSON `null`; stringifying those values before canonicalization is forbidden.

## 5. ContentMetric

Every member of `metrics` has exactly these core fields; compatible optional fields may be added only under section 12:

| Field | Type | Required | Contract |
|---|---:|:---:|---|
| `classification` | string | yes | A value from the `component` vocabulary. The field name is fixed as `classification`. |
| `classification_reason` | string or null | yes | Required non-empty string only when `classification` is `other`; otherwise `null`. |
| `layer` | enum | yes | One fixed inclusion/snapshot layer. |
| `chars` | non-negative integer | yes | Canonical-text character count; `0` means observed empty content. |
| `utf8_bytes` | non-negative integer | yes | Canonical-text UTF-8 byte count; `0` means observed empty content. |
| `sha256` | string | yes | 64 lowercase hexadecimal characters over canonical text bytes. For observed empty content, this is SHA-256 of empty bytes. |
| `canonicalization_id` | string | yes | Always `sdd.canonical.utf8-sorted-compact-v1`. |
| `source_count` | non-negative integer | yes | Number of logical sources represented. `0` means an observed empty source set. |
| `source_paths` | array of string or null | yes | Policy below. |
| `truncated` | boolean | yes | `true` only when the measured source set or text was intentionally bounded before measurement. |
| `omitted_items` | non-negative integer | yes | Known count omitted by truncation; `0` means none. |

`source_paths` policy:

- Default is `null`; metadata-only telemetry does not disclose paths.
- It MAY be an array only when an explicit telemetry policy enables path metadata.
- Array entries MUST be repository-relative POSIX-style paths, never absolute paths, `..` paths, URLs, user-home paths, environment-derived paths, or secret-bearing values.
- Entries MUST be deduplicated and lexicographically sorted by Unicode code point, without Unicode normalization.
- When present, array length MUST equal `source_count`. When absent, `source_count` still reports the logical count.

## 6. Usage

When `usage` is a Usage object, it has these exact fields:

| Field | Type | Required | Contract |
|---|---:|:---:|---|
| `availability` | enum | yes | `available` or `unavailable`. |
| `quality` | enum | yes | `actual` or `unavailable`. |
| `usage_source` | enum | yes | A value defined in section 3.3. |
| `input_tokens` | non-negative integer or null | yes | Provider-reported actual value, else `null`. |
| `output_tokens` | non-negative integer or null | yes | Provider-reported actual value, else `null`. |
| `total_tokens` | non-negative integer or null | yes | Provider-reported actual value, else `null`. |
| `component_tokens` | ComponentTokens or null | yes | Required ComponentTokens object when `availability` is `available`; `null` when `availability` is `unavailable`. |

ComponentTokens is a closed object with exactly these two canonical members; no other component-token member, alias, or `not_applicable` value is permitted:

| Field | Type | Required | Contract |
|---|---:|:---:|---|
| `cached_input_tokens` | non-negative integer or null | yes | Actual provider-reported cached input tokens, or `null` when the detail is not supplied as a valid actual observation. |
| `reasoning_output_tokens` | non-negative integer or null | yes | Actual provider-reported reasoning output tokens, or `null` when the detail is not supplied as a valid actual observation. |

For every token integer in Usage and ComponentTokens, a valid integer is a JSON number with an integral value greater than or equal to zero. A JSON boolean is not an integer. Malformed, negative, boolean, or non-integer values are not actual observations and MUST NOT be accepted, coerced, or estimated.

For OpenAI Responses actual usage, the source mapping is exact:

| OpenAI Responses source | Canonical destination |
|---|---|
| `usage.input_tokens_details.cached_tokens` | `component_tokens.cached_input_tokens` |
| `usage.output_tokens_details.reasoning_tokens` | `component_tokens.reasoning_output_tokens` |

The valid provider usage provenance combinations are frozen as follows:

| Provider observation | `availability` | `quality` | `usage_source` | Token fields |
|---|---|---|---|---|
| OpenAI Responses actual usage supplied | `available` | `actual` | `openai_responses_usage` | Provider-reported aggregate values may individually be `null`; `component_tokens` is an object containing both required canonical members. |
| OpenAI Responses usage unavailable | `unavailable` | `unavailable` | `openai_responses_unavailable` | All `null`. |
| Codex CLI usage unavailable | `unavailable` | `unavailable` | `codex_cli_unavailable` | All `null`. |

These are the only valid combinations. OpenAI Responses usage is unavailable when no actual provider usage observation is available, including an HTTP error, timeout, transport failure, or a response that is absent or does not supply actual usage. `unavailable` describes the provider usage observation, not a token count, and MUST NOT be interpreted or serialized as zero.

For `availability: available`, `quality` MUST be `actual`, `usage_source` MUST be `openai_responses_usage`, and supplied token values MUST be provider-reported. For `availability: unavailable`, `quality` MUST be `unavailable`, `usage_source` MUST be the unavailable source corresponding to the provider, and every token field, including `component_tokens`, MUST be `null`.

When actual provider usage exists, `component_tokens` MUST be an object and MUST contain both `cached_input_tokens` and `reasoning_output_tokens`. If either mapped provider detail is absent or is malformed, negative, boolean, or non-integer, the corresponding canonical member MUST be present with value `null`; it MUST NOT be omitted, coerced, or estimated. Component tokens MUST NOT be inferred from aggregate tokens, bytes, or characters, or proportionally allocated. Missing individual aggregate values remain `null`. A provider-reported numeric `0`, including either mapped component detail, is an actual observation and MUST be preserved as `0`.

Codex CLI token telemetry and file-open telemetry are currently `NOT_RELIABLY_OBSERVABLE`. A `provider_call` event for a Codex CLI process therefore uses `availability: unavailable`, `quality: unavailable`, `usage_source: codex_cli_unavailable`, and null token fields unless a future contract revision establishes a reliable source. Its associated `stage08_task` event uses `usage: null`. A missing CLI observation MUST NOT be converted into zero.

Normative Usage examples (shown independently of the enclosing `provider_call` event) are:

```json
{"availability":"available","quality":"actual","usage_source":"openai_responses_usage","input_tokens":10,"output_tokens":5,"total_tokens":15,"component_tokens":{"cached_input_tokens":4,"reasoning_output_tokens":2}}
{"availability":"available","quality":"actual","usage_source":"openai_responses_usage","input_tokens":10,"output_tokens":5,"total_tokens":15,"component_tokens":{"cached_input_tokens":null,"reasoning_output_tokens":null}}
{"availability":"available","quality":"actual","usage_source":"openai_responses_usage","input_tokens":0,"output_tokens":0,"total_tokens":0,"component_tokens":{"cached_input_tokens":0,"reasoning_output_tokens":0}}
{"availability":"unavailable","quality":"unavailable","usage_source":"openai_responses_unavailable","input_tokens":null,"output_tokens":null,"total_tokens":null,"component_tokens":null}
{"availability":"unavailable","quality":"unavailable","usage_source":"codex_cli_unavailable","input_tokens":null,"output_tokens":null,"total_tokens":null,"component_tokens":null}
```

### 6.1 Stage 08 task observation

A `stage08_task` event is one terminal, metadata-only observation of a Stage 08 atomic-task attempt. An attempt begins only after task selection and any pre-attempt checks have completed and `Stage08CodexRunner.execute_one` has entered the execution boundary for that selected task. Each started attempt MUST make exactly one best-effort terminal event-construction attempt after its terminal outcome is known. No start, progress, heartbeat, verification-start, evidence-start, or checkpoint-start event is emitted.

If a started attempt returns a `CodexTaskRunResult`, telemetry MUST derive the terminal observation from that result without modifying it. If a started attempt raises after the attempt boundary, telemetry MUST still make one best-effort terminal `stage08_task` construction attempt using only contract-approved directly observable information. Telemetry MUST NOT fabricate or replace a lifecycle result.

A selection or preflight rejection that occurs before the attempt boundary MUST NOT emit `stage08_task`. An already-completed-task skip, pure historical checkpoint reconciliation, or pure resume/recovery state repair that does not begin a new atomic-task attempt MUST NOT emit `stage08_task`. A retry that actually begins a new attempt MUST emit its own terminal observation. Multiple attempts of the same task are correlated by the same approved `task_id` and distinct `event_id` values; schema 1.0.4 does not add `attempt_id` or `retry_attempt`.

Event construction and sink recording are best-effort. A valid constructed event is passed to the configured sink once. Invalid or failed telemetry construction is dropped without retry at this boundary and MUST NOT alter the underlying task attempt.

For `stage08_task`, the envelope fields are frozen as follows:

- `stage_id` MUST be the string `"08"`.
- `run_id` MUST reuse an already-existing valid Stage 08 execution correlation identifier when one exists. If no such identifier already exists, it MUST be `null`. Telemetry MUST NOT create, persist, or synthesize a parallel run/session identity.
- `usage` MUST be `null` as required by section 2.
- `metrics` MAY contain one metadata-only `ContentMetric` for the current atomic-task instruction/contract text when that text is directly observable at the attempt boundary. That metric MUST use `component: stage_contract` and `layer: request`, MUST use the existing canonical text measurement rules, and MUST contain only approved metadata such as characters, UTF-8 bytes, SHA-256, canonicalization identifier, and existing ContentMetric structural fields; the task body itself MUST NOT be persisted.
- Rendered Codex prompt measurement belongs to the associated `provider_call` event and MUST NOT be duplicated in `stage08_task`.
- Allowed/protected path strings, verification command text, changed-path strings, evidence content, stdout, stderr, and raw Codex response content MUST NOT be persisted in `stage08_task.metrics`.
- `source_paths` MUST NOT be used to encode changed paths, allowed/protected paths, verification commands, or other operational payload.
- `outcome_category` MUST be derived only after the returned `CodexTaskRunResult.status` is known, using the closed mapping below. Telemetry MUST NOT alter or normalize the result status itself.

| `CodexTaskRunResult.status` | `outcome_category` |
|---|---|
| `DONE` | `completed` |
| `CODEX_FAILED` | `failed` |
| `NO_CHANGES` | `failed` |
| `VERIFICATION_FAILED` | `failed` |

For a started attempt that raises instead of returning a `CodexTaskRunResult`, `outcome_category` is mapped only from directly observed execution semantics:

- policy, authority, scope, dirty-tree, or prerequisite rejection after the attempt boundary => `blocked`
- subprocess/process timeout => `timeout`
- evidence-write, checkpoint, or unexpected runtime failure after the attempt boundary => `failed`

Telemetry MUST NOT infer outcome from arbitrary exception text, stdout, stderr, or guessed return-code meaning. It MAY use the actual typed/structured failure path already produced by Stage 08 execution. Telemetry MUST NOT add or change a Stage 08 lifecycle status.

For an unrecognized returned `CodexTaskRunResult.status`, telemetry MUST drop the event rather than guess a mapping, while returning the original result unchanged.

The `metadata` object for `stage08_task` is closed and has exactly these members:

| Field | Type | Contract |
|---|---:|---|
| `task_id` | string | Existing atomic-task identifier; non-empty when directly observable. |
| `terminal_status` | string or null | Existing bounded Stage 08 terminal status when directly observable. For an exception path with no valid existing status value, MUST be `null`; telemetry MUST NOT invent a new status string. |
| `verification_count` | non-negative integer | Number of verification result entries directly available for this attempt; use `0` when none exist. |
| `changed_path_count` | non-negative integer | Number of changed paths directly available for this attempt; path strings themselves MUST NOT be included. |
| `checkpoint_created` | boolean | `true` only when this attempt directly produced a checkpoint; checkpoint identifiers MUST NOT be included. |

The `stage08_task.metadata` object is closed and MUST contain exactly these five members. No other Stage08-specific metadata key is permitted in schema 1.0.4.

The task body, prompt body, raw Markdown, stdout, stderr, raw Codex response, verification command text, allowed/protected path values, changed path values, evidence body/path, checkpoint identifier, commit content, next-task identifier, exception text, secrets, credentials, API keys, or environment dumps MUST NOT be persisted.

The following is a normative example of the complete event shape. The UUID and timestamp values are illustrative, but all keys, nulls, arrays, metadata members, and vocabulary values are exact:

```json
{"schema_id":"sdd.measurement.stage_execution","schema_version":"1.0.4","event_type":"stage08_task","event_id":"00000000-0000-4000-8000-000000000000","observed_at":"2026-01-01T00:00:00Z","stage_id":"08","run_id":null,"outcome_category":"completed","metrics":[],"usage":null,"metadata":{"task_id":"T001","terminal_status":"DONE","verification_count":1,"changed_path_count":2,"checkpoint_created":true}}
```

This example's `metrics: []` means only that this example has no task ContentMetric; it does not require all `stage08_task` events to use an empty metrics array.

For a started task attempt, the timing boundary is defined as the interval from the attempt boundary until the terminal outcome is known. This boundary exists only to define future-compatible or internal non-persistent timing semantics. Schema 1.0.4 `stage08_task` events do not carry or persist task-attempt duration, and duration MUST NOT be added to `stage08_task.metadata`, `metrics`, or any other existing schema field. `observed_at` is captured when the terminal observation is constructed. If an implementation observes elapsed task-attempt timing for internal diagnostic purposes, that observation MUST use a monotonic elapsed clock and MUST remain outside the schema 1.0.4 event. The absence of persisted Stage 08 task-attempt duration in schema 1.0.4 is not an implementation defect. Persisting Stage 08 task-attempt duration requires a future explicit schema-version amendment. Existing `provider_call` duration semantics remain unchanged.

A `stage08_task` observation and Codex `provider_call` observations are independent. `stage08_task.usage` is always `null`. Each actual Codex CLI process invocation is represented by its own `provider_call`; one task attempt may therefore have zero, one, or multiple provider-call observations.

Codex CLI provider usage remains `availability: unavailable`, `quality: unavailable`, `usage_source: codex_cli_unavailable`, with `input_tokens`, `output_tokens`, `total_tokens`, and `component_tokens` all `null`. Producer code MUST NOT parse stdout or stderr to estimate token usage and MUST NOT duplicate provider usage into `stage08_task`.

## 7. Snapshot boundaries

Snapshots are measurements, not stored bodies. They produce ContentMetric metadata only.

### 7.1 `request`

Include the structured, pre-render request content selected for provider dispatch: system instruction inputs, user input, referenced artifact/context selections, and tool-context selections, each classified by component. Exclude renderer-added formatting, provider SDK envelope fields, transport headers, retry metadata, and response content.

### 7.2 `rendered`

Include the exact rendered prompt/message text after deterministic template assembly and immediately before provider-SDK serialization, including renderer-added delimiters and headings. Exclude provider SDK envelope fields, transport framing, HTTP headers, retry metadata, and response content.

### 7.3 `wire`

Include the canonicalized provider request payload at the last observable boundary before transport, including non-secret SDK-added request fields that will be transmitted. Exclude HTTP/TLS framing, transport headers, retry bookkeeping, and response content. If the exact transmitted payload is not observable, the wire snapshot MUST be absent rather than approximated from `rendered`.

For every layer, API keys, authorization headers, cookies, credentials, tokens used as secrets, and environment dumps are always excluded. Their length, hash, presence, or redacted placeholder MUST NOT be captured as content metrics. `system_prompt`, `user_prompt`, and `tool_context` are available for focused sub-snapshots, but MUST use the same exclusions and canonicalization rules.

## 8. Configuration

### 8.1 Configuration authority and enable grammar

V1 configuration is environment-only. The only v1 configuration names are `SDD_TELEMETRY_ENABLED` and `SDD_TELEMETRY_DIR`. Implementations MUST NOT add CLI telemetry flags, telemetry settings to `.sdd/system.yaml`, or other telemetry configuration files. Consequently, v1 has no CLI/config/environment precedence stack. Adding another configuration authority requires a contract and schema amendment.

`SDD_TELEMETRY_ENABLED` defaults to disabled. Its value is parsed by trimming surrounding ASCII whitespace and then comparing case-insensitively. The recognized true values are exactly `1`, `true`, `yes`, and `on`. A missing, empty, invalid, or any other value means disabled. Disabled telemetry MUST NOT produce persistent telemetry side effects.

`SDD_TELEMETRY_DIR` is the output-directory override and is consulted only when telemetry is enabled.

### 8.2 Directory resolution, defaults, and safety

An absolute `SDD_TELEMETRY_DIR` override resolves as an absolute path. A relative override resolves relative to the process current working directory, never relative to the repository root. The path MUST be normalized and resolved before repository-containment checking.

The default external telemetry directory is:

- Windows: `%LOCALAPPDATA%/sdd-orchestrator/telemetry`.
- POSIX when `XDG_STATE_HOME` exists and is non-empty: `$XDG_STATE_HOME/sdd-orchestrator/telemetry`.
- Other POSIX cases: `~/.local/state/sdd-orchestrator/telemetry`.

Both overrides and defaults MUST pass repository-external validation. A resolved path equal to the repository root or within any repository-root descendant is unsafe. Windows containment comparison follows platform case-insensitive path semantics; POSIX containment comparison follows platform path semantics. Symlink, junction, and reparse-point resolution MUST be considered when safely resolvable. If repository-external safety cannot be established reliably, the destination is unsafe; an implementation MUST NOT guess that an ambiguous path is external.

If a default or override cannot be safely resolved, created, or used, the implementation MUST fall back to `NullTelemetrySink`. Persistence is then effectively disabled. It MUST NOT fall back to repository or working-tree storage, abort or alter stage/provider/lifecycle execution, or define a second telemetry-only execution failure mode.

### 8.3 Persistence format and lifecycle

Persistent telemetry uses UTF-8 JSON Lines (JSONL). The filename is exactly `events.jsonl`, directly under the resolved telemetry directory. V1 does not create separate files per run or session; `event_id` and `run_id` remain correlation identifiers only. M2.1 does not implement rotation, retention, compression, or archival, and a producer MUST NOT invent alternate filenames.

Each line is exactly one directly serialized schema object corresponding to `MeasurementEvent.to_dict()`, with no storage envelope, header, or footer. Existing canonical JSON rules apply: `ensure_ascii=false`, recursively sorted keys, compact separators, no BOM, and no Unicode normalization. Records are separated by exactly one LF newline. Persistent records remain subject to all metadata-only and prohibited-content restrictions in section 10; in particular, they MUST NOT store prompt or body content, stdout, stderr, raw provider responses, secrets, API keys, authorization headers, or other prohibited content.

V1 guarantees single-process append semantics only. Each event MUST be fully canonical-serialized before persistence and written as one logical append operation. After a successful record write, the producer MUST flush the language/runtime buffer; `fsync` is not required. V1 does not guarantee multi-process locking or cross-process atomic append, and implementations MUST NOT introduce distributed locks or session managers.

Serialization, write, and flush failures remain best-effort and non-interfering. A producer MUST NOT treat a partial write as a successfully persisted event. If a partial trailing record exists, a consumer may ignore the incomplete final record. M2.1 does not require a reader or recovery subsystem.

## 9. Non-interference requirements

`StageExecutionResult` and `CodexTaskRunResult` MUST NOT gain telemetry authority fields. Telemetry-only correlation or output state belongs outside these lifecycle result contracts.

The best-effort non-interference boundary covers metric construction, metadata/outcome mapping, clock observation, event construction, and `TelemetryRecorder.record`. Any telemetry failure in those steps MUST be contained and MUST NOT change the task result, verification result, evidence, checkpoint behavior, retry/recovery behavior, Git state, provider-call count, or next-task selection.

M2.2 MUST NOT modify `StageExecutionResult`, `CodexTaskRunResult`, or verification result schemas.

A telemetry success, failure, exception, serialization error, directory error, or write error MUST NOT change:

- provider call count;
- stage status or result;
- blocking decisions;
- authorization;
- validation or verification;
- evidence;
- checkpoint state;
- convergence; or
- next-stage selection.

The same list is invariant when telemetry is enabled versus disabled. Telemetry MUST NOT become an authority input. An unsafe or unavailable destination has the sole v1 behavior defined in section 8: use `NullTelemetrySink`, making persistence effectively disabled without changing provider calls, stage/provider/lifecycle behavior, or lifecycle results.

Telemetry MUST NOT write to `.sdd/state`, `.sdd/evidence`, `.sdd/runs`, the artifact registry, or any checkpoint. It MUST NOT create authority artifacts.
Telemetry MUST NOT create fallback telemetry files anywhere inside the repository or working tree.

## 10. Data minimization and secrets

Telemetry is metadata-only by default. It MUST NOT persist prompt bodies, artifact bodies, file bodies, stdout, stderr, API response bodies, secrets, credentials, API keys, authorization headers, cookies, or environment dumps. Hashes and counts may be persisted only for permitted, non-secret content selected by the snapshot rules. A secret is excluded entirely: hashing or measuring a secret is not an acceptable substitute for exclusion.

`metadata` MUST contain only bounded scalar or bounded-array correlation and diagnostic values approved by this contract's data-minimization rules. It MUST NOT be used as an escape hatch for bodies, arbitrary provider payloads, environment data, or a second schema.

## 11. Observability statement

The following capability status is frozen for v1:

| Capability | Status |
|---|---|
| Provider-reported OpenAI Responses usage | Reliably observable when the response supplies usage; source `openai_responses_usage`. |
| OpenAI Responses cached input tokens | Observable only from `usage.input_tokens_details.cached_tokens`; a missing or invalid detail maps to required `component_tokens.cached_input_tokens: null` when actual usage exists. |
| OpenAI Responses reasoning output tokens | Observable only from `usage.output_tokens_details.reasoning_tokens`; a missing or invalid detail maps to required `component_tokens.reasoning_output_tokens: null` when actual usage exists. |
| OpenAI Responses usage when no actual usage is supplied or observable | Unavailable; source `openai_responses_unavailable`; token fields are `null`, not zero. |
| Codex CLI token usage | `NOT_RELIABLY_OBSERVABLE`. |
| Codex CLI file-open activity | `NOT_RELIABLY_OBSERVABLE`. |
| Component-level actual tokens without a valid mapped provider detail | Not observable; the corresponding required ComponentTokens member MUST be `null` when actual usage exists. |
| Environment enable configuration | Observable only through `SDD_TELEMETRY_ENABLED` using the exact grammar in section 8.1; all non-true values disable persistence. |
| Persistent telemetry destination | External-only when repository-external safety can be established; otherwise `NullTelemetrySink`. |
| Persistent record framing | UTF-8 JSONL containing one canonical `MeasurementEvent.to_dict()` schema object per LF-terminated line in `events.jsonl`. |
| Stage 08 task attempt | Observable as one terminal best-effort `stage08_task` construction attempt for each started atomic-task attempt. Normal returned results use the closed returned-status mapping; started attempts that terminate by approved structured exception paths use the exception outcome mapping in section 6.1. Pre-attempt rejection, already-completed skip, pure historical checkpoint reconciliation, and pure recovery/state repair without a new attempt emit no `stage08_task`. |

## 12. Schema compatibility

- Schema version `1.0.4` preserves the meanings of all existing `1.0.3` fields and vocabulary values; it adds and clarifies Stage 08 task-attempt telemetry and Codex absent-wire observability, including the `stage08_task` event-type value, attempt boundary, closed returned-status and structured-exception mappings, and closed metadata object in section 6.1. M1/M2.1 configuration, storage, and provider semantics remain unchanged and MUST NOT be independently reinterpreted by producers. Existing `component` and `layer` vocabularies remain closed.
- Codex absent-wire observability follows section 7.3: when an exact wire snapshot is not observable, `wire` MUST be absent rather than approximated from rendered content.
- For the required envelope field `usage`, `null` means the event type does not carry provider usage; it is neither unavailable usage nor zero usage. Within a Usage object, a null aggregate token or ComponentTokens member means no valid actual observation was supplied for that known field; `component_tokens: null` is reserved for `availability: unavailable`. `0` means an observed numeric zero or empty measured set/content. These meanings are never interchangeable.
- A missing required field is invalid. Producers MUST emit all required fields, including required nullable fields. A missing optional field means the optional feature was not emitted; it MUST NOT be interpreted as zero, empty, false, or null unless that optional field's later specification explicitly says so.
- The `usage` field is always required: `stage_request` and `stage08_task` require JSON `null`, while `provider_call` requires a Usage object. A missing `usage` field is invalid, and an event-type/value mismatch is invalid.
- A `provider_call` Usage object MUST match one row of the frozen provenance matrix in section 6. In particular, OpenAI Responses failures or responses without actual usage use `openai_responses_unavailable`, while unavailable Codex CLI observations use `codex_cli_unavailable`; unavailable token fields are `null` and MUST NOT be interpreted as zero.
- For an `available` Usage object, `component_tokens` is required as a closed object containing exactly `cached_input_tokens` and `reasoning_output_tokens`, even when one or both values are `null`. For an `unavailable` Usage object it MUST be `null`. Missing canonical members, additional component-token members, aliases, boolean-as-integer values, malformed values, negative values, and non-integer values are invalid telemetry. Invalid or absent provider details normalize only to the corresponding required null member when actual usage otherwise exists; they MUST NOT be estimated or converted to zero.
- Within major version 1, minor or patch revisions MAY add optional fields. Consumers MUST ignore unknown optional fields while continuing to validate known fields. Producers MUST NOT change the meaning or type of an existing field or add enum values without a schema revision.
- Unknown `event_type`, `component`/`classification`, `layer`, `availability`, `quality`, `usage_source`, or `outcome_category` values are not silently coerced. A consumer MAY preserve the raw event as unsupported telemetry, but MUST NOT interpret it as a known value or affect lifecycle behavior.
- A consumer that does not support the schema's major version MUST treat the entire event as unsupported telemetry, skip semantic processing, and continue lifecycle execution unchanged. Future major versions require an explicit reader/adapter; they MUST NOT be parsed as v1 by best effort.
- Invalid telemetry is dropped or quarantined only within the telemetry destination. Its invalidity MUST NOT trigger authority writes or lifecycle changes.

## 13. IMPLEMENTATION ENTRY GATE

**M2.2 MUST use this document as the single Stage 08 telemetry contract, while retaining the naming, configuration, persistence, provider-usage, and non-interference requirements already frozen for M2.1.** Implementation may begin only with `sdd.measurement.stage_execution` version `1.0.4` and the exact names, enum values, and semantics frozen here. Production MUST NOT independently decide or invent `stage08_task` cardinality, the attempt boundary, exception emission, returned-status mapping, structured exception outcome mapping, retry/reconciliation emission, metadata keys, run-ID policy, task metric classification, Codex wire approximation, true-value grammar, relative-path base, unsafe-path fallback, persistence framing, filename, rotation behavior, or append semantics.

The required `usage` field MUST be implemented with the event-type semantics frozen in sections 2, 6, and 12: `null` for `stage_request`, a Usage object for `provider_call`, and `null` for `stage08_task`, with actual Codex process token availability represented by the associated `provider_call`. Each `provider_call` Usage object MUST match the frozen provenance matrix: OpenAI actual usage uses `available`/`actual`/`openai_responses_usage` and a `component_tokens` object containing exactly the required `cached_input_tokens` and `reasoning_output_tokens` members; unavailable OpenAI usage uses `unavailable`/`unavailable`/`openai_responses_unavailable` with null token fields; unavailable Codex CLI usage uses `unavailable`/`unavailable`/`codex_cli_unavailable` with null token fields. OpenAI component details MUST use only the exact source mappings in section 6. A missing or invalid detail under otherwise actual usage MUST produce the corresponding required null member, while a provider-reported zero MUST remain zero. Unavailable provider usage observation MUST NOT be treated as zero. Implementation MUST NOT estimate component tokens, omit either required canonical member, accept invalid detail values as actual observations, fabricate provider usage for an event type that requires `null`, treat that `null` as unavailable or zero, add component-token keys or aliases, add `not_applicable`, create a second schema, use alternate field names or compatibility aliases, invent private enum spellings, or create a parallel canonicalization vocabulary. Any necessary contract change must first revise this document through an explicit schema-version decision; production code is not the place to resolve a naming conflict.

For `stage08_task`, M2.2 MUST make exactly one best-effort terminal construction attempt for every started atomic-task attempt after its terminal outcome is known, including approved structured exception paths, and no observation for pre-attempt rejection, already-completed skip, pure historical checkpoint reconciliation, or pure recovery/state repair without a new attempt. It MUST use `stage_id: "08"`, the existing-correlation-or-null `run_id` policy, `usage: null`, the optional single task-contract metric rule, the exact returned-status and structured-exception outcome mappings, and the exact closed metadata object in section 6.1. It MUST NOT emit progress events, synthesize lifecycle results or statuses, disclose identifiers or content prohibited by section 6.1, inspect authority state to recompute metadata, approximate Codex wire content, change the number of Codex/provider calls, or mutate, replace, delay, or suppress lifecycle behavior because telemetry construction or recording failed.
