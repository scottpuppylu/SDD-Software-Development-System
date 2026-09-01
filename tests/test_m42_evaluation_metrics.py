from dataclasses import dataclass, replace
import unittest

from sdd_orchestrator.context_compiler import (
    ComponentDeltaKind,
    ExactContextComponent,
    build_component_identity,
    build_ephemeral_baseline,
    compare_baseline_to_current,
    content_digest,
    content_kind_and_bytes,
    parse_component_identity,
    reconstruct_exact_context,
)
from sdd_orchestrator.context_evaluation import (
    CODEX_ACTUAL_PROVIDER_USAGE,
    CODEX_CLI_TOKENS_USED_IS_PROVIDER_EVIDENCE,
    ESTIMATED_TOKENS_ARE_PROVIDER_EVIDENCE,
    MACHINE_EVALUATION_METADATA,
    MISSING_VALID_PROVIDER_USAGE,
    PROVIDER_USAGE_SCHEMA,
    EvaluationCaseResult,
    EvaluationStatus,
    ReuseEligibilityReason as Reason,
    measure_evaluation,
    primary_reuse_reason,
    unavailable_provider_usage,
    validate_openai_actual_usage,
)


def component(
    coordinate: str,
    body: bytes,
    *,
    stage: str = "03",
    authority: bool = False,
) -> ExactContextComponent:
    return ExactContextComponent(
        build_component_identity(coordinate, stage),
        body,
        content_digest(body),
        authority,
    )


@dataclass(frozen=True)
class ControlledCase:
    name: str
    expected_outcome: bool
    primary_reason: Reason


def controlled_corpus() -> tuple[ControlledCase, ...]:
    """Deterministic, test-local Slice 3 cases; no runtime fixture is written."""
    return (
        ControlledCase("unchanged same-stage exact", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("changed component", True, Reason.CONTENT_CHANGED),
        ControlledCase("added component", True, Reason.COMPONENT_ADDED),
        ControlledCase("removed component", True, Reason.COMPONENT_REMOVED),
        ControlledCase("reordered component", True, Reason.COMPONENT_REORDERED),
        ControlledCase("stage identity change", True, Reason.BASELINE_INVALID),
        ControlledCase("task identity absent", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("empty string", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("empty mapping", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("empty list", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("explicit null", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("fixed absence", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("UNKNOWN", True, Reason.UNKNOWN),
        ControlledCase("MIXED_AUTHORITY", True, Reason.MIXED_AUTHORITY),
        ControlledCase("duplicate identity", True, Reason.DUPLICATE_IDENTITY),
        ControlledCase("digest collision simulation", True, Reason.IDENTITY_COLLISION),
        ControlledCase("malformed identity/version", True, Reason.IDENTITY_MISMATCH),
        ControlledCase("stale/wrong baseline association", True, Reason.BASELINE_INVALID),
        ControlledCase("reconstruction exact success", True, Reason.EXACT_RECONSTRUCTION_ELIGIBLE),
        ControlledCase("reconstruction invalid/fresh-exact-required", True, Reason.BASELINE_INVALID),
        ControlledCase("provider reuse unsupported", True, Reason.PROVIDER_REUSE_UNSUPPORTED),
        ControlledCase("provider usage unavailable", True, Reason.PROVIDER_REUSE_UNSUPPORTED),
        ControlledCase("valid OpenAI actual usage", True, Reason.SAME_IDENTITY_EXACT_BYTES),
        ControlledCase("safety PASS without provider claim", True, Reason.SAME_IDENTITY_EXACT_BYTES),
    )


class M42EvaluationMetricTests(unittest.TestCase):
    def setUp(self):
        self.base = (
            component("request/stage-contract", b"authority", authority=True),
            component("request/runtime-inputs/61", "café".encode("utf-8")),
            component("request/runtime-inputs/62", b"xyz"),
        )
        self.scope = object()
        self.baseline = build_ephemeral_baseline(self.base, scope=self.scope)

    def measured(self, current=None, **kwargs):
        current = self.base if current is None else current
        delta = compare_baseline_to_current(self.baseline, current, scope=self.scope)
        reconstruction = reconstruct_exact_context(
            self.baseline, delta, scope=self.scope
        )
        return measure_evaluation(
            current, current, delta=delta, reconstruction=reconstruction, **kwargs
        )

    def test_exact_source_selection_authority_and_utf8_measurements(self):
        metrics = self.measured()
        self.assertEqual(metrics.source_component_count, 3)
        self.assertEqual(metrics.selected_component_count, 3)
        self.assertEqual(metrics.source_context_utf8_bytes, 9 + 5 + 3)
        self.assertEqual(metrics.selected_context_utf8_bytes, 17)
        self.assertEqual(metrics.authority_required_component_count, 1)
        self.assertEqual(metrics.authority_present_component_count, 1)
        self.assertEqual(metrics.authority_coverage, 100)
        self.assertEqual(metrics.authority_byte_mismatch_count, 0)
        self.assertEqual(metrics.unchanged_component_count, 3)
        self.assertEqual(metrics.unchanged_utf8_bytes, 17)
        self.assertEqual(metrics.delta_utf8_bytes, 0)
        self.assertTrue(metrics.reconstruction_exact_match)

    def test_authority_structural_coverage_and_byte_mismatch_are_separate(self):
        mismatched = (replace(self.base[0], canonical_bytes=b"different"),) + self.base[1:]
        metrics = measure_evaluation(self.base, mismatched)
        self.assertEqual(metrics.authority_coverage, 100)
        self.assertEqual(metrics.authority_present_component_count, 1)
        self.assertEqual(metrics.authority_byte_mismatch_count, 1)
        missing = measure_evaluation(self.base, self.base[1:])
        self.assertEqual(missing.authority_coverage, 0)
        self.assertEqual(missing.authority_present_component_count, 0)
        two_required = (self.base[0], replace(self.base[1], authority_protected=True))
        partial = measure_evaluation(two_required, two_required[:1])
        self.assertEqual(partial.authority_coverage, 50)

    def test_delta_category_counts_and_bytes(self):
        changed_current = (self.base[0], replace(
            self.base[1], canonical_bytes=b"changed",
            content_digest=content_digest(b"changed")), self.base[2])
        changed = self.measured(changed_current)
        self.assertEqual(changed.changed_component_count, 1)
        self.assertEqual(changed.unchanged_component_count, 2)
        self.assertEqual(changed.delta_utf8_bytes, 7)

        added_component = component("request/runtime-inputs/63", b"{}")
        added = self.measured(self.base + (added_component,))
        self.assertEqual(added.added_component_count, 1)
        self.assertEqual(added.delta_utf8_bytes, 2)

        removed = self.measured(self.base[:-1])
        self.assertEqual(removed.removed_component_count, 1)
        self.assertEqual(removed.delta_utf8_bytes, 0)

        reordered = self.measured(tuple(reversed(self.base)))
        self.assertEqual(reordered.reordered_component_count, 2)
        self.assertEqual(reordered.unchanged_component_count, 1)
        self.assertEqual(reordered.unchanged_utf8_bytes, 5)

    def test_invalid_reconstruction_is_observed_exactly(self):
        current = self.base + (component("request/runtime-inputs/63", b"new"),)
        delta = compare_baseline_to_current(self.baseline, current, scope=self.scope)
        broken = replace(
            delta,
            changes=tuple(
                change for change in delta.changes
                if change.kind is not ComponentDeltaKind.ADDED
            ),
        )
        reconstruction = reconstruct_exact_context(
            self.baseline, broken, scope=self.scope
        )
        metrics = measure_evaluation(current, current, delta=broken,
                                     reconstruction=reconstruction)
        self.assertFalse(metrics.reconstruction_exact_match)
        self.assertTrue(reconstruction.fresh_exact_required)

    def test_provider_bytes_are_unavailable_unless_demonstrable(self):
        metrics = self.measured()
        self.assertFalse(metrics.provider_boundary_reuse_supported)
        self.assertIsNone(metrics.provider_bytes_avoided)
        with self.assertRaisesRegex(ValueError, "not demonstrable"):
            self.measured(provider_bytes_avoided=1)


class M42ReuseReasonTests(unittest.TestCase):
    def test_exact_taxonomy_and_deterministic_precedence(self):
        self.assertEqual(
            {reason.value for reason in Reason},
            {
                "SAME_IDENTITY_EXACT_BYTES", "EXACT_RECONSTRUCTION_ELIGIBLE",
                "ALWAYS_REQUIRED", "AUTHORITY_PROTECTED", "UNKNOWN",
                "MIXED_AUTHORITY", "IDENTITY_MISMATCH", "CONTENT_CHANGED",
                "COMPONENT_ADDED", "COMPONENT_REMOVED", "COMPONENT_REORDERED",
                "DUPLICATE_IDENTITY", "IDENTITY_COLLISION", "BASELINE_INVALID",
                "AUTHORITY_CONFLICT", "PROVIDER_REUSE_UNSUPPORTED",
            },
        )
        applicable = (Reason.SAME_IDENTITY_EXACT_BYTES, Reason.ALWAYS_REQUIRED,
                      Reason.CONTENT_CHANGED, Reason.DUPLICATE_IDENTITY)
        for ordering in (applicable, tuple(reversed(applicable))):
            self.assertIs(primary_reuse_reason(ordering), Reason.DUPLICATE_IDENTITY)
        self.assertIs(primary_reuse_reason(
            (Reason.AUTHORITY_PROTECTED, Reason.UNKNOWN)), Reason.UNKNOWN)
        self.assertIs(primary_reuse_reason(
            (Reason.AUTHORITY_PROTECTED, Reason.MIXED_AUTHORITY)),
            Reason.MIXED_AUTHORITY)

    def test_malformed_identity_version_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_component_identity(
                "sdd.context.component/wrong/stage-absent/task-absent/request/stage-contract"
            )


class M42ProviderUsageTests(unittest.TestCase):
    def test_frozen_provider_validity_and_unavailable_is_not_zero(self):
        self.assertEqual(PROVIDER_USAGE_SCHEMA, "1.0.4")
        self.assertEqual(CODEX_ACTUAL_PROVIDER_USAGE, "UNAVAILABLE")
        self.assertEqual(CODEX_CLI_TOKENS_USED_IS_PROVIDER_EVIDENCE, "NO")
        self.assertEqual(ESTIMATED_TOKENS_ARE_PROVIDER_EVIDENCE, "NO")
        self.assertEqual(MISSING_VALID_PROVIDER_USAGE, "UNAVAILABLE_NOT_ZERO")
        for ignored_value in (0, 123, "tokens used: 123"):
            usage = unavailable_provider_usage()
            self.assertFalse(usage.available, ignored_value)
            self.assertIsNone(usage.total_tokens)

    def test_only_valid_structured_openai_actual_usage_is_accepted(self):
        actual = validate_openai_actual_usage({"usage": {
            "input_tokens": 0, "output_tokens": 4, "total_tokens": None,
        }})
        self.assertTrue(actual.available)
        self.assertTrue(actual.actual)
        self.assertEqual(actual.input_tokens, 0)
        self.assertEqual(actual.output_tokens, 4)
        self.assertIsNone(actual.total_tokens)
        for payload in (
            None, {}, {"usage": None}, {"usage": {}},
            {"usage": {"input_tokens": True, "output_tokens": -1,
                       "total_tokens": "4"}},
        ):
            with self.subTest(payload=payload):
                self.assertFalse(validate_openai_actual_usage(payload).available)


class M42EvaluationStatusAndCorpusTests(unittest.TestCase):
    def metrics(self, **kwargs):
        exact = (component("request/stage-contract", b"x", authority=True),)
        return measure_evaluation(exact, exact, **kwargs)

    def test_safety_pass_does_not_require_provider_usage_or_savings(self):
        result = EvaluationCaseResult(self.metrics(), (True,))
        self.assertIs(result.status, EvaluationStatus.PASS)

    def test_provider_claim_without_valid_usage_is_incomplete(self):
        result = EvaluationCaseResult(
            self.metrics(), (True,), provider_token_claim=True
        )
        self.assertIs(result.status, EvaluationStatus.INCOMPLETE)
        actual = validate_openai_actual_usage({"usage": {"total_tokens": 7}})
        complete = EvaluationCaseResult(
            self.metrics(provider_usage=actual), (True,), provider_token_claim=True
        )
        self.assertIs(complete.status, EvaluationStatus.PASS)

    def test_mandatory_failure_is_fail_and_wins_over_missing_evidence(self):
        failed = EvaluationCaseResult(
            self.metrics(semantic_regression_count=1),
            (None,),
            provider_token_claim=True,
        )
        self.assertIs(failed.status, EvaluationStatus.FAIL)
        mismatch_source = (component(
            "request/stage-contract", b"x", authority=True),)
        mismatch_selected = (replace(
            mismatch_source[0], canonical_bytes=b"y"),)
        authority_failure = EvaluationCaseResult(
            measure_evaluation(mismatch_source, mismatch_selected), (True,)
        )
        self.assertIs(authority_failure.status, EvaluationStatus.FAIL)

    def test_controlled_corpus_is_complete_deterministic_and_non_persistent(self):
        first = controlled_corpus()
        second = controlled_corpus()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 24)
        self.assertTrue(all(case.expected_outcome for case in first))
        self.assertEqual(MACHINE_EVALUATION_METADATA, "NON_PERSISTENT")
        self.assertFalse(any(
            word in field.lower()
            for field in EvaluationCaseResult.__dataclass_fields__
            for word in ("path", "cache", "registry", "persist")
        ))

    def test_controlled_canonical_empty_states_are_distinct(self):
        states = (
            content_kind_and_bytes("")[1],
            content_kind_and_bytes({})[1],
            content_kind_and_bytes([])[1],
            content_kind_and_bytes(None)[1],
            content_kind_and_bytes(None, absent=True)[1],
        )
        self.assertEqual(states, (b"", b"{}", b"[]", b"null", b'{"state":"absent"}'))
        self.assertEqual(len(set(states)), 5)


if __name__ == "__main__":
    unittest.main()
