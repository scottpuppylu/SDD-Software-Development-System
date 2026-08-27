import unittest

from sdd_orchestrator.context_compiler import (
    InclusionDisposition,
    ManifestClassification,
    ContentKind,
    ContextCompiler,
    canonical_json_bytes,
    content_kind_and_bytes,
)
from sdd_orchestrator.executor import StageExecutionRequest
from sdd_orchestrator.providers import (
    _provider_system_instructions,
    _provider_user_input,
)


def synthetic_history(count):
    return "\n".join(
        f"{index:040x}\tsynthetic-entry-{index:02d}" for index in range(count)
    )


def request_with_history(count_or_body):
    history = (
        synthetic_history(count_or_body)
        if isinstance(count_or_body, int)
        else count_or_body
    )
    return StageExecutionRequest(
        stage_id="04",
        stage_name="IMPLEMENTATION",
        stage_type="AUTHORING",
        core_question="Implement the approved design?",
        contract={"outputs": {"files": []}},
        artifacts={
            "docs/spec.md": "known authority Ω\r\nexact",
            "AGENTS.md": "known governance\nexact",
            "notes/review.md": {"mixed": ["authority", "evidence"]},
        },
        semantic_inputs={"UNCLASSIFIED_CONTEXT": {"preserve": "exact"}},
        runtime_inputs={
            "GIT_HISTORY": history,
            "OTHER": {"GIT_HISTORY": synthetic_history(20)},
            "GIT_HISTORY_V2": synthetic_history(20),
        },
        stage_instructions="Implement only the approved scope.",
    )


def rendered_parts(request):
    return (
        _provider_system_instructions(request).encode("utf-8"),
        _provider_user_input(request).encode("utf-8"),
    )


def actual_token_comparison(left, right):
    required = {
        "availability": "available",
        "quality": "actual",
        "usage_source": "openai_responses_usage",
    }
    for usage in (left, right):
        if not isinstance(usage, dict):
            return "UNAVAILABLE"
        if any(usage.get(key) != value for key, value in required.items()):
            return "UNAVAILABLE"
        tokens = usage.get("input_tokens")
        if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
            return "UNAVAILABLE"
    return "AVAILABLE"


def evaluation_status(*, reduction_bytes, authority_mismatches,
                      semantic_regressions, lifecycle_regressions,
                      fallback_regressions, required_suite_passed,
                      deterministic_evidence_complete=True,
                      token_comparison="UNAVAILABLE"):
    del token_comparison  # Actual-token availability is explicitly non-gating.
    if any((
        reduction_bytes <= 0,
        authority_mismatches != 0,
        semantic_regressions != 0,
        lifecycle_regressions != 0,
        fallback_regressions != 0,
        not required_suite_passed,
    )):
        return "FAIL"
    if not deterministic_evidence_complete:
        return "INCOMPLETE"
    return "PASS"


class M41EvaluationClosureTests(unittest.TestCase):
    def test_optimized_preserves_all_exact_classification_bytes(self):
        package = ContextCompiler().compile_optimized(request_with_history(11))
        required = {
            ManifestClassification.KNOWN_AUTHORITY,
            ManifestClassification.KNOWN_GOVERNANCE,
            ManifestClassification.UNKNOWN,
            ManifestClassification.MIXED_AUTHORITY,
        }
        observed = set()
        mismatches = 0
        for entry in package.entries:
            classification = entry.manifest_entry.classification
            if classification in required:
                observed.add(classification)
                source = entry.manifest_entry.source_metadata
                result = entry.manifest_entry.result_metadata
                absent = entry.manifest_entry.content_kind is ContentKind.ABSENT
                source_bytes = content_kind_and_bytes(
                    entry.source_body, absent=absent
                )[1]
                result_bytes = content_kind_and_bytes(
                    entry.result_body, absent=absent
                )[1]
                mismatches += source_bytes != result_bytes
                self.assertEqual(source_bytes, result_bytes)
                self.assertEqual(source, result)
                self.assertEqual(entry.source_body, entry.result_body)
                self.assertIs(
                    entry.manifest_entry.disposition, InclusionDisposition.EXACT
                )
        self.assertEqual(observed, required)
        self.assertEqual(mismatches, 0)

    def test_controlled_boundaries_and_positive_request_and_rendered_reduction(self):
        for count in (0, 10):
            with self.subTest(entries=count):
                request = request_with_history(count)
                optimized = ContextCompiler().compile_optimized(request)
                self.assertEqual(optimized.request, request)
                self.assertFalse(any(
                    entry.manifest_entry.disposition is InclusionDisposition.REDUCED
                    for entry in optimized.entries
                ))

        for count in (11, 20):
            with self.subTest(entries=count):
                request = request_with_history(count)
                baseline = ContextCompiler().compile_baseline(request)
                optimized = ContextCompiler().compile_optimized(request)
                source_bytes = len(canonical_json_bytes(baseline.request.to_dict()))
                result_bytes = len(canonical_json_bytes(optimized.request.to_dict()))
                self.assertGreater(source_bytes - result_bytes, 0)
                baseline_parts = rendered_parts(baseline.request)
                optimized_parts = rendered_parts(optimized.request)
                self.assertEqual(baseline_parts[0], optimized_parts[0])
                self.assertLess(sum(map(len, optimized_parts)), sum(map(len, baseline_parts)))

    def test_malformed_too_large_and_non_top_level_candidates_are_unchanged(self):
        for body in ("malformed-history", synthetic_history(21)):
            with self.subTest(case=len(body)):
                request = request_with_history(body)
                package = ContextCompiler().compile_optimized(request)
                self.assertEqual(package.request, request)
                self.assertTrue(all(
                    entry.manifest_entry.disposition is InclusionDisposition.EXACT
                    for entry in package.entries
                ))

        package = ContextCompiler().compile_optimized(request_with_history(11))
        other = package.request.runtime_inputs
        self.assertEqual(other["OTHER"]["GIT_HISTORY"], synthetic_history(20))
        self.assertEqual(other["GIT_HISTORY_V2"], synthetic_history(20))

    def test_repeated_compilation_and_canonicalization_are_deterministic(self):
        request = request_with_history(20)
        compiler = ContextCompiler()
        first = compiler.compile_optimized(request)
        second = compiler.compile_optimized(request)
        self.assertEqual(first, second)
        self.assertEqual(
            canonical_json_bytes(first.request.to_dict()),
            canonical_json_bytes(second.request.to_dict()),
        )
        self.assertEqual(rendered_parts(first.request), rendered_parts(second.request))

    def test_m41_never_uses_omitted_disposition(self):
        for count in (0, 10, 11, 20, 21):
            package = ContextCompiler().compile_optimized(request_with_history(count))
            self.assertNotIn(
                InclusionDisposition.OMITTED,
                [entry.manifest_entry.disposition for entry in package.entries],
            )

    def test_actual_tokens_are_unavailable_without_paired_actual_usage(self):
        actual = {
            "availability": "available",
            "quality": "actual",
            "usage_source": "openai_responses_usage",
            "input_tokens": 10,
        }
        self.assertEqual(actual_token_comparison(None, None), "UNAVAILABLE")
        self.assertEqual(actual_token_comparison(actual, None), "UNAVAILABLE")
        self.assertEqual(actual_token_comparison(actual, actual), "AVAILABLE")

    def test_pass_has_no_percentage_threshold_and_tokens_are_non_gating(self):
        arguments = dict(
            reduction_bytes=1,
            authority_mismatches=0,
            semantic_regressions=0,
            lifecycle_regressions=0,
            fallback_regressions=0,
            required_suite_passed=True,
        )
        self.assertEqual(evaluation_status(**arguments), "PASS")
        self.assertEqual(
            evaluation_status(**arguments, token_comparison="UNAVAILABLE"),
            "PASS",
        )


if __name__ == "__main__":
    unittest.main()
