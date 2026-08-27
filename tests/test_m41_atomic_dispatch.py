import copy
import unittest

from sdd_orchestrator.context_compiler import (
    CompilationMode,
    CompiledContextPackage,
    ContextManifest,
    build_baseline_package,
    build_optimized_package,
)
from sdd_orchestrator.context_dispatch import (
    ContextDispatchCoordinator,
    CoordinationStatus,
)
from sdd_orchestrator.executor import (
    OptimizationPreparationError,
    SharedExecutorPrerequisiteError,
    StageExecutionRequest,
    StageExecutionResult,
)


class DispatchFailure(RuntimeError):
    pass


class FakeAtomicExecutor:
    def __init__(self, *, prepare_error=None, dispatch_error=None):
        self.prepare_error = prepare_error
        self.dispatch_error = dispatch_error
        self.prepared = []
        self.dispatched = []

    def prepare(self, request):
        self.prepared.append(request)
        if self.prepare_error is not None:
            error = self.prepare_error
            self.prepare_error = None
            raise error
        return ("prepared", request)

    def dispatch(self, prepared):
        self.dispatched.append(prepared)
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return StageExecutionResult(status="COMPLETED", result="PASS")


class AtomicDispatchTests(unittest.TestCase):
    def request(self, *, reducible=True):
        history = (
            "\n".join(f"{number:040x}\tcommit-{number}" for number in range(20))
            if reducible else "short"
        )
        return StageExecutionRequest(
            stage_id="04",
            stage_name="IMPLEMENTATION",
            stage_type="AUTHORING",
            core_question="Implement?",
            contract={"outputs": ["code"]},
            artifacts={"docs/spec.md": "# Spec"},
            semantic_inputs={"constraint": "exact"},
            runtime_inputs={"GIT_HISTORY": history},
            stage_instructions="Implement only.",
        )

    def packages(self, *, reducible=True):
        request = self.request(reducible=reducible)
        return build_baseline_package(request), build_optimized_package(request)

    def test_non_atomic_executes_baseline_once_without_probe(self):
        baseline, optimized = self.packages()

        class BaselineOnly:
            def __init__(self):
                self.calls = []

            def execute(self, request):
                self.calls.append(request)
                return StageExecutionResult(status="COMPLETED")

        executor = BaselineOnly()
        coordinator = ContextDispatchCoordinator()
        coordinator.execute(executor, baseline, optimized)
        self.assertEqual(executor.calls, [baseline.request])
        self.assertEqual(
            coordinator.status, CoordinationStatus.OPTIMIZATION_NOT_APPLICABLE
        )

    def test_atomic_without_optimized_package_uses_baseline(self):
        baseline, _ = self.packages()
        executor = FakeAtomicExecutor()
        coordinator = ContextDispatchCoordinator()
        coordinator.execute(executor, baseline, None)
        self.assertEqual(executor.prepared, [baseline.request])
        self.assertEqual(len(executor.dispatched), 1)

    def test_optimized_without_reduced_entry_uses_baseline(self):
        baseline, optimized = self.packages(reducible=False)
        executor = FakeAtomicExecutor()
        coordinator = ContextDispatchCoordinator()
        coordinator.execute(executor, baseline, optimized)
        self.assertEqual(executor.prepared, [baseline.request])
        self.assertEqual(coordinator.status, CoordinationStatus.OPTIMIZATION_NOT_APPLICABLE)

    def test_optimized_prepare_success_dispatches_only_optimized(self):
        baseline, optimized = self.packages()
        executor = FakeAtomicExecutor()
        coordinator = ContextDispatchCoordinator()
        coordinator.execute(executor, baseline, optimized)
        self.assertEqual(executor.prepared, [optimized.request])
        self.assertEqual(executor.dispatched, [("prepared", optimized.request)])
        self.assertEqual(coordinator.status, CoordinationStatus.OPTIMIZED_READY)

    def test_optimization_prepare_error_falls_back_once(self):
        baseline, optimized = self.packages()
        executor = FakeAtomicExecutor(
            prepare_error=OptimizationPreparationError("optimized")
        )
        coordinator = ContextDispatchCoordinator()
        coordinator.execute(executor, baseline, optimized)
        self.assertEqual(executor.prepared, [optimized.request, baseline.request])
        self.assertEqual(executor.dispatched, [("prepared", baseline.request)])
        self.assertEqual(coordinator.status, CoordinationStatus.OPTIMIZATION_FALLBACK)

    def test_shared_prerequisite_error_propagates_without_fallback(self):
        baseline, optimized = self.packages()
        executor = FakeAtomicExecutor(
            prepare_error=SharedExecutorPrerequisiteError("shared")
        )
        with self.assertRaises(SharedExecutorPrerequisiteError):
            ContextDispatchCoordinator().execute(executor, baseline, optimized)
        self.assertEqual(executor.prepared, [optimized.request])
        self.assertEqual(executor.dispatched, [])

    def test_baseline_prepare_failure_propagates_without_dispatch(self):
        baseline, _ = self.packages()
        failure = RuntimeError("baseline")
        executor = FakeAtomicExecutor(prepare_error=failure)
        with self.assertRaisesRegex(RuntimeError, "baseline"):
            ContextDispatchCoordinator().execute(executor, baseline, None)
        self.assertEqual(executor.prepared, [baseline.request])
        self.assertEqual(executor.dispatched, [])

    def test_optimized_dispatch_failure_has_no_baseline_retry(self):
        baseline, optimized = self.packages()
        executor = FakeAtomicExecutor(dispatch_error=DispatchFailure("dispatch"))
        with self.assertRaises(DispatchFailure):
            ContextDispatchCoordinator().execute(executor, baseline, optimized)
        self.assertEqual(executor.prepared, [optimized.request])
        self.assertEqual(len(executor.dispatched), 1)

    def test_baseline_dispatch_failure_is_not_retried(self):
        baseline, _ = self.packages()
        executor = FakeAtomicExecutor(dispatch_error=DispatchFailure("dispatch"))
        with self.assertRaises(DispatchFailure):
            ContextDispatchCoordinator().execute(executor, baseline, None)
        self.assertEqual(executor.prepared, [baseline.request])
        self.assertEqual(len(executor.dispatched), 1)

    def test_packages_requests_and_result_metadata_remain_unmodified(self):
        baseline, optimized = self.packages()
        before = copy.deepcopy((baseline, optimized))
        result = ContextDispatchCoordinator().execute(
            FakeAtomicExecutor(), baseline, optimized
        )
        self.assertEqual((baseline, optimized), before)
        self.assertEqual(result.metadata, {})

    def test_status_taxonomy_is_exact(self):
        self.assertEqual(
            {status.value for status in CoordinationStatus},
            {
                "OPTIMIZATION_NOT_APPLICABLE",
                "OPTIMIZATION_FALLBACK",
                "OPTIMIZED_READY",
            },
        )

    def test_invalid_optimized_package_falls_back_before_prepare(self):
        baseline, optimized = self.packages()
        invalid = CompiledContextPackage(
            CompilationMode.BASELINE,
            optimized.request,
            ContextManifest(
                CompilationMode.BASELINE,
                optimized.manifest.canonicalization_id,
                optimized.manifest.entries,
            ),
            optimized.entries,
        )
        executor = FakeAtomicExecutor()
        coordinator = ContextDispatchCoordinator()
        coordinator.execute(executor, baseline, invalid)
        self.assertEqual(executor.prepared, [baseline.request])
        self.assertEqual(len(executor.dispatched), 1)
        self.assertEqual(coordinator.status, CoordinationStatus.OPTIMIZATION_FALLBACK)


if __name__ == "__main__":
    unittest.main()
