import unittest
from unittest.mock import patch

from test_m41_runner_context_integration import (
    AtomicExecutor,
    DispatchFailure,
    HarnessRunner,
    NonAtomicExecutor,
    make_request,
)
from sdd_orchestrator.context_compiler import (
    CompilationMode,
    ContextCompiler,
    OptimizationCompilationError,
    TASK_COORDINATE,
)
from sdd_orchestrator.executor import SharedExecutorPrerequisiteError


class M42ActivationFallbackTests(unittest.TestCase):
    def test_default_and_explicit_baseline_remain_unchanged(self):
        for kwargs in ({}, {"compilation_mode": CompilationMode.BASELINE}):
            with self.subTest(kwargs=kwargs):
                request = make_request()
                executor = NonAtomicExecutor()
                with patch(
                    "sdd_orchestrator.runner.ContextCompiler",
                    side_effect=AssertionError("BASELINE must not prepare M4.2"),
                ):
                    HarnessRunner(request, **kwargs).run(executor)
                self.assertEqual(executor.requests, [request])

    def test_optimized_proves_complete_candidate_then_dispatches_once(self):
        request = make_request(11)
        executor = AtomicExecutor()
        original = ContextCompiler.validate_m42_candidate
        observed = []

        def validate(compiler, baseline, optimized, stages):
            observed.append((baseline, optimized))
            return original(compiler, baseline, optimized, stages)

        with patch.object(ContextCompiler, "validate_m42_candidate", new=validate):
            HarnessRunner(
                request, compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)

        self.assertEqual(len(observed), 1)
        self.assertEqual(len(executor.prepared), 1)
        self.assertEqual(len(executor.dispatched), 1)
        dispatched = executor.dispatched[0]
        self.assertEqual(dispatched.stage_id, request.stage_id)
        self.assertEqual(dispatched.contract, request.contract)
        self.assertEqual(dispatched.artifacts, request.artifacts)
        self.assertEqual(dispatched.semantic_inputs, request.semantic_inputs)
        self.assertEqual(set(dispatched.runtime_inputs), set(request.runtime_inputs))
        self.assertNotEqual(
            dispatched.runtime_inputs["GIT_HISTORY"],
            request.runtime_inputs["GIT_HISTORY"],
        )

    def test_m42_pre_dispatch_failure_uses_fresh_baseline_once(self):
        request = make_request()
        executor = AtomicExecutor()
        with patch.object(
            ContextCompiler,
            "validate_m42_candidate",
            side_effect=OptimizationCompilationError("M4.2 invalid"),
        ):
            HarnessRunner(
                request, compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)
        self.assertEqual(executor.prepared, [request])
        self.assertEqual(executor.dispatched, [request])

    def test_shared_prerequisite_failure_is_not_m42_fallback(self):
        executor = AtomicExecutor(
            prepare_errors=[SharedExecutorPrerequisiteError("shared")]
        )
        with self.assertRaises(SharedExecutorPrerequisiteError):
            HarnessRunner(
                make_request(), compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)
        self.assertEqual(len(executor.prepared), 1)
        self.assertEqual(executor.dispatched, [])

    def test_post_dispatch_provider_failure_has_no_retry(self):
        executor = AtomicExecutor(dispatch_error=DispatchFailure("provider"))
        with self.assertRaises(DispatchFailure):
            HarnessRunner(
                make_request(), compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)
        self.assertEqual(len(executor.prepared), 1)
        self.assertEqual(len(executor.dispatched), 1)

    def test_post_dispatch_parse_failure_has_no_retry(self):
        request = make_request()
        executor = AtomicExecutor()
        runner = HarnessRunner(request, compilation_mode=CompilationMode.OPTIMIZED)
        runner._validate_result = lambda request, result: (_ for _ in ()).throw(
            ValueError("parse")
        )
        with self.assertRaisesRegex(ValueError, "parse"):
            runner.run(executor)
        self.assertEqual(len(executor.prepared), 1)
        self.assertEqual(len(executor.dispatched), 1)

    def test_exactness_is_complete_and_task_identity_stays_absent(self):
        compiler = ContextCompiler()
        request = make_request(11)
        baseline = compiler.compile_baseline(request)
        optimized = compiler.compile_optimized(request)
        compiler.validate_m42_candidate(baseline, optimized, {})
        self.assertEqual(TASK_COORDINATE, "task-absent")
        self.assertEqual(
            [entry.manifest_entry.component_id for entry in optimized.entries],
            [
                entry.manifest_entry.component_id
                for entry in compiler.compile_baseline(optimized.request).entries
            ],
        )


if __name__ == "__main__":
    unittest.main()
