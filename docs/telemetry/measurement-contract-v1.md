# SDD Measurement Contract v1

Status: **FROZEN for M1.1 implementation**  
Baseline: `v1.2.0-baseline` / `55092fc1fbfc87be1fe573806125d8b06481ba3c`  
Schema ID: `sdd.measurement.stage_execution`  
Schema version: `1.0.0`

## 1. Purpose and authority boundary

This document is the single naming and serialization contract for Phase 03A measurement implementation. If terminology proposed in Phase 02 Measurement Design or Phase 03 Implementation Planning differs from this document, the exact field names, enum values, nullability, and canonicalization vocabulary in this document win. The minimal consistent names selected here are `event_type`, `component`, `layer`, `availability`, `quality`, `usage_source`, and `outcome_category`; implementations MUST NOT introduce aliases or parallel vocabularies.

Telemetry is observational only. A telemetry event MUST NOT be treated as lifecycle authority, reconstructed into lifecycle authority, or consulted to decide lifecycle behavior.

## 2. Event envelope

Every event is a canonical JSON object with these fields:

| Field | Type | Required | Contract |
|---|---:|:---:|---|
| `schema_id` | string | yes | Always `sdd.measurement.stage_execution`. |
| `schema_version` | string | yes | Always `1.0.0` for this contract. |
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
| `component_tokens` | object or null | yes | Actual provider-reported component-level token counts, else `null`. |

For `availability: available`, `quality` MUST be `actual`, `usage_source` MUST identify an actual provider usage source, and supplied token values MUST be provider-reported. For `availability: unavailable`, `quality` MUST be `unavailable` and every token field, including `component_tokens`, MUST be `null`.

If a provider reports aggregate tokens but does not report component-level tokens, `component_tokens` MUST be `null`. Component tokens MUST NOT be estimated, inferred from bytes or characters, or proportionally allocated. Missing individual aggregate values remain `null`; `0` is used only when the provider explicitly reports zero.

Codex CLI token telemetry and file-open telemetry are currently `NOT_RELIABLY_OBSERVABLE`. A `provider_call` event for a Codex CLI process therefore uses `availability: unavailable`, `quality: unavailable`, `usage_source: codex_cli_unavailable`, and null token fields unless a future contract revision establishes a reliable source. Its associated `stage08_task` event uses `usage: null`. A missing CLI observation MUST NOT be converted into zero.

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

The only v1 configuration names are:

- `SDD_TELEMETRY_ENABLED`: default disabled. Telemetry is enabled only by an explicitly recognized true value; absence or invalid values resolve to disabled.
- `SDD_TELEMETRY_DIR`: output-directory override. It is consulted only when telemetry is enabled.

The Windows default directory is `C:\Users\user\AppData\Local\SDD Orchestrator\telemetry`. On Windows implementations SHOULD derive the equivalent current-user Local AppData path rather than hard-code the example username. Any `SDD_TELEMETRY_DIR` override MUST resolve outside the repository root. An override resolving to the repository root or any descendant MUST be rejected and telemetry disabled or treated as a telemetry-only failure; it MUST NOT affect execution semantics.

## 9. Non-interference requirements

`StageExecutionResult` and `CodexTaskRunResult` MUST NOT gain telemetry authority fields. Telemetry-only correlation or output state belongs outside these lifecycle result contracts.

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

Telemetry MUST NOT write to `.sdd/state`, `.sdd/evidence`, `.sdd/runs`, the artifact registry, or any checkpoint. It MUST NOT create authority artifacts.

## 10. Data minimization and secrets

Telemetry is metadata-only by default. It MUST NOT persist prompt bodies, artifact bodies, file bodies, stdout, stderr, API response bodies, secrets, credentials, API keys, authorization headers, cookies, or environment dumps. Hashes and counts may be persisted only for permitted, non-secret content selected by the snapshot rules. A secret is excluded entirely: hashing or measuring a secret is not an acceptable substitute for exclusion.

`metadata` MUST contain only bounded scalar or bounded-array correlation and diagnostic values approved by this contract's data-minimization rules. It MUST NOT be used as an escape hatch for bodies, arbitrary provider payloads, environment data, or a second schema.

## 11. Observability statement

The following capability status is frozen for v1:

| Capability | Status |
|---|---|
| Provider-reported OpenAI Responses usage | Reliably observable when the response supplies usage; source `openai_responses_usage`. |
| Codex CLI token usage | `NOT_RELIABLY_OBSERVABLE`. |
| Codex CLI file-open activity | `NOT_RELIABLY_OBSERVABLE`. |
| Component-level actual tokens without provider component data | Not observable; MUST be `null`. |

## 12. Schema compatibility

- For the required envelope field `usage`, `null` means the event type does not carry provider usage; it is neither unavailable usage nor zero usage. Within a Usage object and elsewhere in this schema, `null` means the field is known by this schema but its value is unavailable or inapplicable. `0` means an observed numeric zero or empty measured set/content. These meanings are never interchangeable.
- A missing required field is invalid. Producers MUST emit all required fields, including required nullable fields. A missing optional field means the optional feature was not emitted; it MUST NOT be interpreted as zero, empty, false, or null unless that optional field's later specification explicitly says so.
- The `usage` field is always required: `stage_request` and `stage08_task` require JSON `null`, while `provider_call` requires a Usage object. A missing `usage` field is invalid, and an event-type/value mismatch is invalid.
- Within major version 1, minor or patch revisions MAY add optional fields. Consumers MUST ignore unknown optional fields while continuing to validate known fields. Producers MUST NOT change the meaning or type of an existing field or add enum values without a schema revision.
- Unknown `event_type`, `component`/`classification`, `layer`, `availability`, `quality`, `usage_source`, or `outcome_category` values are not silently coerced. A consumer MAY preserve the raw event as unsupported telemetry, but MUST NOT interpret it as a known value or affect lifecycle behavior.
- A consumer that does not support the schema's major version MUST treat the entire event as unsupported telemetry, skip semantic processing, and continue lifecycle execution unchanged. Future major versions require an explicit reader/adapter; they MUST NOT be parsed as v1 by best effort.
- Invalid telemetry is dropped or quarantined only within the telemetry destination. Its invalidity MUST NOT trigger authority writes or lifecycle changes.

## 13. IMPLEMENTATION ENTRY GATE

**M1.1 MUST use this document as the single naming contract.** Implementation may begin only with `sdd.measurement.stage_execution` version `1.0.0` and the exact names and enum values frozen here. The required `usage` field MUST be implemented with the event-type semantics frozen in sections 2, 6, and 12: `null` for `stage_request`, a Usage object for `provider_call`, and `null` for `stage08_task`, with actual Codex process token availability represented by the associated `provider_call`. Implementation MUST NOT fabricate provider usage for an event type that requires `null`, treat that `null` as unavailable or zero, add `not_applicable`, create a second schema, use alternate field names or compatibility aliases, invent private enum spellings, or create a parallel canonicalization vocabulary. Any necessary contract change must first revise this document through an explicit schema-version decision; production code is not the place to resolve a naming conflict.
