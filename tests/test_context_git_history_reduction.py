import copy
import unittest

from sdd_orchestrator.context_compiler import (
    GIT_HISTORY_REDUCTION_POLICY_ID,
    CompilationMode,
    ContextCompiler,
    InclusionDisposition,
    ManifestClassification,
    reduce_git_history,
)
from sdd_orchestrator.executor import StageExecutionRequest


def history(count, *, subject=lambda index: f"subject {index}"):
    return "\n".join(f"{index:040x}\t{subject(index)}" for index in range(1, count + 1))


class GitHistoryReducerTests(unittest.TestCase):
    def assert_exact(self, value):
        result = reduce_git_history(value)
        self.assertIs(result.source_body, value)
        self.assertIs(result.result_body, value)
        self.assertIs(result.disposition, InclusionDisposition.EXACT)
        self.assertIsNone(result.reduction_policy_id)

    def test_valid_exact_boundaries_and_subjects(self):
        for value in (
            "", history(1), history(10),
            "a" * 40 + "\t",
            "b" * 40 + "\t雪 e\u0301",
            "c" * 40 + "\t  \u2003 ",
            "\n".join(["d" * 40 + "\tduplicate"] * 2),
        ):
            with self.subTest(value=value):
                self.assert_exact(value)

    def test_reduces_11_and_20_entries_exactly(self):
        for count in (11, 20):
            source = history(count, subject=lambda i: " duplicate " if i in (2, 9) else f"雪 {i} ")
            result = reduce_git_history(source)
            source_lines = source.split("\n")
            result_lines = result.result_body.split("\n")
            self.assertIs(result.disposition, InclusionDisposition.REDUCED)
            self.assertEqual(result.reduction_policy_id, GIT_HISTORY_REDUCTION_POLICY_ID)
            self.assertEqual(result_lines[:8], source_lines[:8])
            self.assertEqual(result_lines[8], f"[[GIT_HISTORY_OMITTED_ENTRIES:{count - 10}]]")
            self.assertEqual(result_lines[9:], source_lines[-2:])
            self.assertFalse(result.result_body.endswith("\n"))

    def test_malformed_and_outside_grammar_fail_closed(self):
        valid = "a" * 40 + "\tok"
        malformed = (
            "a" * 39 + "\tx", "A" * 40 + "\tx", "g" * 40 + "\tx",
            "a" * 40, "a" * 40 + "\tx\textra", valid + "\r\n" + valid,
            valid + "\r", "\n" + valid, valid + "\n", valid + "\n\n" + valid,
            history(21), None, 7, [valid], valid + "\n" + "bad\tline",
        )
        for value in malformed:
            with self.subTest(value=value):
                self.assert_exact(value)


class OptimizedCompilationTests(unittest.TestCase):
    def request(self, git_history):
        return StageExecutionRequest(
            stage_id="04", stage_name="Manifest", stage_type="build",
            core_question="question", contract={"nested": [1, {"x": 2}]},
            artifacts={"docs/spec.md": "authority", "unknown": {"m": []}},
            semantic_inputs={"semantic": {"items": [1]}},
            runtime_inputs={"OTHER": {"nested": [2]}, "GIT_HISTORY": git_history},
            stage_instructions="instructions",
        )

    def test_reduction_changes_only_git_history_and_does_not_alias(self):
        request = self.request(history(11))
        snapshot = copy.deepcopy(request)
        compiler = ContextCompiler()
        baseline = compiler.compile_baseline(request)
        optimized = compiler.compile_optimized(request)
        self.assertIs(baseline.request, request)
        self.assertIsNot(optimized.request, request)
        self.assertEqual(request, snapshot)
        self.assertEqual(optimized.mode, CompilationMode.OPTIMIZED)
        self.assertEqual(optimized.request.runtime_inputs["GIT_HISTORY"], reduce_git_history(history(11)).result_body)
        for field in ("stage_id", "stage_name", "stage_type", "core_question", "contract",
                      "artifacts", "semantic_inputs", "stage_instructions"):
            self.assertEqual(getattr(optimized.request, field), getattr(request, field))
        self.assertEqual(optimized.request.runtime_inputs["OTHER"], request.runtime_inputs["OTHER"])
        optimized.request.contract["nested"][1]["x"] = 99
        optimized.request.runtime_inputs["OTHER"]["nested"].append(3)
        self.assertEqual(request, snapshot)

    def test_manifest_reduction_and_exact_authority_unknown_entries(self):
        package = ContextCompiler().compile_optimized(self.request(history(20)))
        reduced = [entry for entry in package.entries
                   if entry.manifest_entry.disposition is InclusionDisposition.REDUCED]
        self.assertEqual(len(reduced), 1)
        self.assertIs(reduced[0].manifest_entry.classification,
                      ManifestClassification.APPROVED_REDUCIBLE_OPERATIONAL_HISTORY)
        self.assertEqual(reduced[0].manifest_entry.reduction_policy_id,
                         GIT_HISTORY_REDUCTION_POLICY_ID)
        for entry in package.entries:
            if entry not in reduced:
                self.assertIs(entry.manifest_entry.disposition, InclusionDisposition.EXACT)
                self.assertEqual(entry.source_body, entry.result_body)
        self.assertFalse(any(entry.manifest_entry.disposition is InclusionDisposition.OMITTED
                             for entry in package.entries))

    def test_small_malformed_non_string_and_missing_history_stay_exact(self):
        cases = (
            ("valid small", history(10)),
            ("malformed", "bad\tline"),
            ("too large", history(21)),
            ("non-string", {"commits": []}),
        )
        requests = [(name, self.request(value)) for name, value in cases]
        missing = self.request(history(1))
        del missing.runtime_inputs["GIT_HISTORY"]
        requests.append(("missing", missing))
        for name, request in requests:
            with self.subTest(case=name):
                snapshot = copy.deepcopy(request)
                package = ContextCompiler().compile_optimized(request)
                self.assertIs(package.mode, CompilationMode.OPTIMIZED)
                self.assertIsNot(package.request, request)
                self.assertEqual(package.request, request)
                self.assertIsNot(package.request.contract, request.contract)
                self.assertIsNot(package.request.contract["nested"], request.contract["nested"])
                self.assertIsNot(package.request.artifacts, request.artifacts)
                self.assertIsNot(package.request.semantic_inputs, request.semantic_inputs)
                self.assertIsNot(package.request.runtime_inputs, request.runtime_inputs)
                self.assertIsNot(package.request.runtime_inputs["OTHER"],
                                 request.runtime_inputs["OTHER"])
                package.request.contract["nested"][1]["x"] = 99
                package.request.runtime_inputs["OTHER"]["nested"].append(3)
                self.assertEqual(request, snapshot)
                self.assertTrue(all(entry.manifest_entry.disposition
                                    is InclusionDisposition.EXACT
                                    for entry in package.entries))
                self.assertTrue(all(entry.manifest_entry.reduction_policy_id is None
                                    for entry in package.entries))

    def test_repeated_optimized_compilation_is_deterministic(self):
        request = self.request(history(11))
        first = ContextCompiler().compile_optimized(request)
        second = ContextCompiler().compile_optimized(request)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
