# GIT_HISTORY Reduction Policy v1

**Status:** APPROVED - BLOCKER 5 RESOLVED

**Phase:** Phase 04 - Manifested Context Optimization

**Milestone:** M4.1 - Deterministic Context Manifest and Conservative Operational Reduction

**Planning authority:** `docs/context/context-optimization-plan-v1.md`

**Manifest contract:** `docs/context/context-manifest-contract-v1.md`

## 1. Scope and policy identifier

This document freezes the approved M4.1 Blocker 5 named `GIT_HISTORY` reduction policy. The policy identifier is exactly:

```text
sdd.git-history.newest8-oldest2-v1
```

This identifier is stable and versioned, identifies one fixed policy, and is not a cache key.

The policy applies only to the exact top-level structural slot:

```text
runtime_inputs["GIT_HISTORY"]
```

No nested, similar, differently cased, or otherwise located key is eligible. No other component is eligible.

This document resolves Blocker 5 only. It does not authorize implementation of the reducer, compiler integration, activation, comparison, or evidence.

## 2. Current producer boundary

The current source producer is:

```text
git log -20 --pretty=format:%H%x09%s
```

It runs with `allow_failure=True`.

The repository object format inspected for this v1 policy is SHA-1. This v1 policy MUST NOT silently generalize to repositories using the SHA-256 Git object format. Supporting another Git object format requires an explicitly approved policy revision.

The producer currently decodes UTF-8 with replacement, uses Python text newline handling, and returns stripped output.

The reducer operates only on the supplied source string. It does not attempt to reconstruct information already altered or lost by the producer.

## 3. Accepted grammar

The complete accepted grammar is:

```text
GIT_HISTORY := ""
             | ENTRY ("\n" ENTRY){0,19}

ENTRY   := HASH "\t" SUBJECT

HASH    := exactly 40 lowercase ASCII hexadecimal characters
           matching [0-9a-f]{40}

SUBJECT := zero or more Unicode code points excluding:
           U+0009 TAB
           U+000A LF
           U+000D CR
```

The following rules are normative:

- The empty string is valid.
- One through 20 entries are valid.
- The entry separator is exactly LF.
- CRLF and bare CR are not accepted reducer input.
- A leading newline is malformed.
- A trailing newline is malformed. In particular, a trailing newline is not ignored.
- Each entry has exactly one structural TAB.
- An empty subject is valid.
- Unicode and permitted whitespace in subjects are preserved.
- An embedded TAB in a subject is malformed.
- Duplicate lines, hashes, or subjects are valid and preserved.
- Commit-message content MUST NOT establish or change authority classification.

The entire input MUST parse successfully before reduction. Partial parse followed by reduction is forbidden. Malformed or ambiguous input MUST NOT be repaired.

## 4. Deterministic algorithm

After structural eligibility is already established, the reducer MUST perform exactly these steps:

1. Require a string input.
2. Canonicalize the complete source under `sdd.canonical.utf8-sorted-compact-v1`.
3. Parse the complete input according to Section 3.
4. For an entry count from zero through 10, return the source unchanged.
5. For an entry count from 11 through 20:
   - retain entries 1 through 8 in their original order;
   - retain the final two entries in their original order;
   - omit every entry between those two retained groups;
   - insert the exact omission marker from Section 5 between entry 8 and the first retained oldest entry;
   - join all output lines using LF; and
   - append no trailing newline.

The current `git log` ordering is newest-first. Entries 1 through 8 are therefore the eight newest visible commits, and the final two entries are the two oldest commits in the bounded source window.

The reducer MUST NOT perform semantic summarization, ranking, authority inference, timezone conversion, LLM processing, telemetry-dependent processing, network access, or a second Git call.

## 5. Exact omission marker

For `K` omitted entries, the marker is exactly:

```text
[[GIT_HISTORY_OMITTED_ENTRIES:K]]
```

`K` is a base-10 integer with no sign, padding, spaces, or grouping separator. The marker occupies its own LF-delimited line. It MUST NOT be treated as a commit.

## 6. Frozen thresholds and outcomes

The frozen thresholds are:

- maximum accepted entries: 20;
- reduction threshold: greater than 10;
- newest retained: 8;
- oldest retained: 2;
- retained commits after reduction: 10; and
- omitted count: `source_entry_count - 10`.

The required behavior is:

| Source entry count | Outcome |
| --- | --- |
| 0 | `EXACT` |
| 1-10 | `EXACT` |
| 11-20 | approved projection |
| greater than 20 | fail closed; no reduction |

No minimum token-saving percentage is part of this policy.

## 7. Preservation requirements

For every retained commit entry, the reducer MUST preserve exactly:

- all 40 hash characters;
- all subject code points;
- Unicode;
- permitted whitespace in the subject;
- original commit ordering; and
- duplicates.

The reducer MUST NOT normalize, trim, case-fold, rewrite, escape beyond the existing string representation, enrich, or summarize retained hash or subject content.

## 8. Source, result, and disposition

The source remains untouched. The reducer produces a separate ephemeral result string.

Source and result bodies remain outside `ContextManifest`. Source and result metadata follow `docs/context/context-manifest-contract-v1.md`.

For `BASELINE`, disposition is always `EXACT`.

For `OPTIMIZED`, disposition may be `REDUCED` only when all of the following are true:

- the structural slot is exactly `runtime_inputs["GIT_HISTORY"]`;
- classification is `APPROVED_REDUCIBLE_OPERATIONAL_HISTORY`;
- the complete grammar parses;
- source entry count is from 11 through 20;
- `reduction_policy_id` is exactly `sdd.git-history.newest8-oldest2-v1`; and
- result canonical bytes differ from source canonical bytes.

If output canonical bytes are identical, disposition remains `EXACT` and `reduction_policy_id` is null.

Fail-closed exact inclusion uses unchanged source and result content with matching metadata.

## 9. Fail-closed behavior

At minimum, the following outcomes are frozen:

| Condition | Required outcome |
| --- | --- |
| Malformed line | No reduction |
| Invalid hash | No reduction |
| Missing TAB | No reduction |
| Extra TAB | No reduction |
| CRLF, bare CR, or structural blank line | No reduction |
| Leading or trailing newline | No reduction |
| More than 20 entries | No reduction |
| Non-string input | Outside approved reduction grammar |
| Partial parse | Forbidden; no reduction |
| Uncertain classification | No reduction |
| Mixed or inseparable authority | `MIXED_AUTHORITY` / `EXACT_REQUIRED` / `EXACT` |
| Canonicalization failure | Optimized work is invalid; retain `BASELINE` |
| Internal reducer exception | Discard incomplete optimized work; retain `BASELINE` |
| Wrong structural slot | Invalid optimized package |
| Commit subject merely claiming authority | Do not infer authority from message content |

None of these outcomes becomes a lifecycle failure.

Exact atomic fallback and dispatch implementation remain Blocker 6.

## 10. Security and data minimization

This policy MUST NOT:

- persist raw Git history;
- persist reduced Git history as lifecycle authority;
- add history or subjects to telemetry metadata;
- inspect commit contents;
- inspect diffs;
- parse or enrich secrets from subjects;
- call Git again;
- access the network; or
- enrich commit identities.

## 11. Compatibility freeze

This policy authorizes no changes to:

- `StageExecutionRequest`;
- `StageExecutionResult`;
- telemetry schema 1.0.4;
- the telemetry measurement contract;
- `.sdd` authority;
- lifecycle, run, or evidence schemas;
- current `BASELINE` provider rendering; or
- default `BASELINE` behavior.

Blocker 6 continues to own compiler insertion, optimized-package validation, atomic fallback, and partial-dispatch prevention. Blocker 7 remains activation. Blocker 8 remains comparison and evidence.

## 12. Resolution and remaining blockers

5. **RESOLVED:** Named `GIT_HISTORY` reduction policy.
6. **BLOCKED:** Compiler integration and atomic fallback.
7. **BLOCKED:** Explicit activation mechanism.
8. **BLOCKED:** Comparison and evidence contract.

This document resolves Blocker 5 only. M4.1 implementation readiness remains **BLOCKED**.
