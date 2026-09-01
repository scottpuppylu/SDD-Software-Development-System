import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sdd_orchestrator.context_compiler import (
    CompilationMode,
    ContextCompiler,
    OptimizationCompilationError,
)
from sdd_orchestrator.executor import (
    OptimizationPreparationError,
    SharedExecutorPrerequisiteError,
    StageExecutionRequest,
    StageExecutionResult,
)
from sdd_orchestrator.runner import StageRunner


class DispatchFailure(RuntimeError):
    pass


class Recorder:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


class NonAtomicExecutor:
    def __init__(self, result=None):
        self.requests = []
        self.result = result or StageExecutionResult(status="COMPLETED")

    def execute(self, request):
        self.requests.append(request)
        return self.result


class AtomicExecutor:
    def __init__(self, result=None, prepare_errors=(), dispatch_error=None):
        self.result = result or StageExecutionResult(status="COMPLETED")
        self.prepare_errors = list(prepare_errors)
        self.dispatch_error = dispatch_error
        self.prepared = []
        self.dispatched = []

    def prepare(self, request):
        self.prepared.append(request)
        if self.prepare_errors:
            error = self.prepare_errors.pop(0)
            if error is not None:
                raise error
        return request

    def dispatch(self, prepared):
        self.dispatched.append(prepared)
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return self.result


class HarnessRunner(StageRunner):
    def __init__(self, request, **kwargs):
        super().__init__(SimpleNamespace(repo_root=Path(".")), **kwargs)
        self.request = request
        self.lifecycle_calls = []

    def _prepare_explicit_rerun(self, stage_id):
        self.lifecycle_calls.append(("prepare", stage_id))

    def build_request(self, *args, **kwargs):
        return self.request

    def _validate_result(self, request, result):
        self.lifecycle_calls.append(("validate", request, result))

    def _write_outputs_atomically(self, artifacts):
        self.lifecycle_calls.append(("write", artifacts))
        return list(artifacts)

    def _persist_convergence_tasks(self, request, result):
        self.lifecycle_calls.append(("convergence", request, result))
        return []

    def _apply_transition(self, request, result):
        self.lifecycle_calls.append(("transition", request, result))
        return {"next": "05"}

    def _record_run(self, request, result, transition):
        self.lifecycle_calls.append(("record", request, result, transition))

    def _update_artifact_registry(self, written):
        self.lifecycle_calls.append(("registry", written))


def make_request(history_entries=11):
    history = "\n".join(
        f"{number:040x}\tcommit-{number}" for number in range(history_entries)
    )
    return StageExecutionRequest(
        stage_id="04",
        stage_name="DESIGN",
        stage_type="AUTHORING",
        core_question="How?",
        contract={"outputs": {"files": []}},
        artifacts={"docs/spec.md": "# Spec"},
        semantic_inputs={"nested": {"items": ["preserve"]}},
        runtime_inputs={"GIT_HISTORY": history},
        stage_instructions="Design it.",
    )


class RunnerContextIntegrationTests(unittest.TestCase):
    def test_default_and_explicit_baseline_use_original_request_once(self):
        for supplied in (False, True):
            with self.subTest(explicit=supplied):
                request = make_request()
                request.semantic_inputs = {"threshold": 0.5}
                kwargs = ({"compilation_mode": CompilationMode.BASELINE}
                          if supplied else {})
                runner = HarnessRunner(request, **kwargs)
                executor = NonAtomicExecutor()
                with patch(
                    "sdd_orchestrator.runner.ContextCompiler",
                    side_effect=AssertionError("BASELINE must not construct a compiler"),
                ):
                    runner.run(executor)
                self.assertIs(runner.compilation_mode, CompilationMode.BASELINE)
                self.assertEqual(len(executor.requests), 1)
                self.assertIs(executor.requests[0], request)

    def test_constructor_rejects_untyped_mode(self):
        with self.assertRaises(TypeError):
            HarnessRunner(make_request(), compilation_mode="OPTIMIZED")

    def test_stage_request_telemetry_precedes_compilation_and_observes_original_once(self):
        request = make_request()
        recorder = Recorder()
        order = []
        original_measure = __import__(
            "sdd_orchestrator.runner", fromlist=["measure_stage_request"]
        ).measure_stage_request

        def measure(observed):
            order.append(("measure", observed))
            return original_measure(observed)

        original_compile = ContextCompiler.compile_baseline

        def compile_baseline(compiler, observed):
            order.append(("compile", observed))
            return original_compile(compiler, observed)

        with patch("sdd_orchestrator.runner.measure_stage_request", side_effect=measure), \
             patch.object(ContextCompiler, "compile_baseline", new=compile_baseline):
            HarnessRunner(
                request,
                telemetry_recorder=recorder,
                compilation_mode=CompilationMode.OPTIMIZED,
            ).run(NonAtomicExecutor())

        self.assertEqual([item[0] for item in order], ["measure", "compile"])
        self.assertTrue(all(item[1] is request for item in order))
        self.assertEqual(len(recorder.events), 1)

    def test_optimized_reducible_history_dispatches_independent_candidate_once(self):
        request = make_request(11)
        before = copy.deepcopy(request)
        executor = AtomicExecutor()
        HarnessRunner(request, compilation_mode=CompilationMode.OPTIMIZED).run(executor)
        self.assertEqual(len(executor.prepared), 1)
        self.assertEqual(len(executor.dispatched), 1)
        self.assertIsNot(executor.dispatched[0], request)
        self.assertNotEqual(
            executor.dispatched[0].runtime_inputs["GIT_HISTORY"],
            request.runtime_inputs["GIT_HISTORY"],
        )
        self.assertEqual(request, before)
        self.assertIsNot(
            executor.dispatched[0].semantic_inputs["nested"],
            request.semantic_inputs["nested"],
        )

    def test_optimized_unchanged_history_dispatches_original_baseline(self):
        request = make_request(10)
        executor = AtomicExecutor()
        HarnessRunner(request, compilation_mode=CompilationMode.OPTIMIZED).run(executor)
        self.assertEqual(executor.prepared, [request])
        self.assertEqual(executor.dispatched, [request])
        self.assertIs(executor.dispatched[0], request)

    def test_optimized_non_atomic_executes_original_baseline_once(self):
        request = make_request()
        executor = NonAtomicExecutor()
        HarnessRunner(request, compilation_mode=CompilationMode.OPTIMIZED).run(executor)
        self.assertEqual(executor.requests, [request])
        self.assertIs(executor.requests[0], request)

    def test_optimized_compilation_failure_dispatches_original_baseline_once(self):
        request = make_request()
        before = copy.deepcopy(request)
        recorder = Recorder()
        executor = AtomicExecutor()
        with patch.object(
            ContextCompiler,
            "compile_optimized",
            side_effect=OptimizationCompilationError("candidate invalid"),
        ):
            HarnessRunner(
                request,
                telemetry_recorder=recorder,
                compilation_mode=CompilationMode.OPTIMIZED,
            ).run(executor)

        self.assertEqual(executor.prepared, [request])
        self.assertEqual(executor.dispatched, [request])
        self.assertIs(executor.dispatched[0], request)
        self.assertEqual(request, before)
        self.assertEqual(len(recorder.events), 1)

    def test_unrelated_optimized_compilation_error_propagates_without_dispatch(self):
        executor = AtomicExecutor()
        with patch.object(
            ContextCompiler,
            "compile_optimized",
            side_effect=RuntimeError("programming error"),
        ), self.assertRaisesRegex(RuntimeError, "programming error"):
            HarnessRunner(
                make_request(), compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)

        self.assertEqual(executor.prepared, [])
        self.assertEqual(executor.dispatched, [])

    def test_optimized_preparation_fallback_dispatches_baseline_once(self):
        request = make_request()
        executor = AtomicExecutor(
            prepare_errors=[OptimizationPreparationError("optimized"), None]
        )
        HarnessRunner(request, compilation_mode=CompilationMode.OPTIMIZED).run(executor)
        self.assertEqual(len(executor.prepared), 2)
        self.assertIs(executor.prepared[1], request)
        self.assertEqual(executor.dispatched, [request])

    def test_shared_prerequisite_failure_propagates_without_dispatch(self):
        executor = AtomicExecutor(
            prepare_errors=[SharedExecutorPrerequisiteError("shared")]
        )
        with self.assertRaises(SharedExecutorPrerequisiteError):
            HarnessRunner(
                make_request(), compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)
        self.assertEqual(executor.dispatched, [])

    def test_optimized_dispatch_failure_has_no_baseline_retry(self):
        executor = AtomicExecutor(dispatch_error=DispatchFailure("dispatch"))
        with self.assertRaises(DispatchFailure):
            HarnessRunner(
                make_request(), compilation_mode=CompilationMode.OPTIMIZED
            ).run(executor)
        self.assertEqual(len(executor.prepared), 1)
        self.assertEqual(len(executor.dispatched), 1)

    def test_result_metadata_and_existing_lifecycle_referent_are_unchanged(self):
        request = make_request()
        result = StageExecutionResult(status="COMPLETED", metadata={"existing": True})
        runner = HarnessRunner(request, compilation_mode=CompilationMode.OPTIMIZED)
        runner.run(AtomicExecutor(result=result))
        self.assertEqual(result.metadata, {"existing": True})
        referent_calls = [call for call in runner.lifecycle_calls
                          if call[0] in {"validate", "convergence", "transition", "record"}]
        self.assertTrue(referent_calls)
        self.assertTrue(all(call[1] is request for call in referent_calls))


if __name__ == "__main__":
    unittest.main()
