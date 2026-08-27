from __future__ import annotations

from enum import Enum

from .context_compiler import (
    CompilationMode,
    CompiledContextPackage,
    InclusionDisposition,
    validate_compiled_package,
)
from .executor import (
    AtomicStageExecutor,
    OptimizationPreparationError,
    StageExecutionResult,
)


class CoordinationStatus(str, Enum):
    """Ephemeral outcome of optimized-package coordination."""

    OPTIMIZATION_NOT_APPLICABLE = "OPTIMIZATION_NOT_APPLICABLE"
    OPTIMIZATION_FALLBACK = "OPTIMIZATION_FALLBACK"
    OPTIMIZED_READY = "OPTIMIZED_READY"


class ContextDispatchCoordinator:
    """Select, prepare, and dispatch exactly one compiled request."""

    def __init__(self) -> None:
        self._status: CoordinationStatus | None = None

    @property
    def status(self) -> CoordinationStatus | None:
        return self._status

    def execute(
        self,
        executor: object,
        baseline_package: CompiledContextPackage,
        optimized_package: CompiledContextPackage | None,
    ) -> StageExecutionResult:
        self._status = None
        self._validate_baseline(baseline_package)

        if not isinstance(executor, AtomicStageExecutor):
            self._status = CoordinationStatus.OPTIMIZATION_NOT_APPLICABLE
            return executor.execute(baseline_package.request)  # type: ignore[attr-defined]

        if optimized_package is None:
            self._status = CoordinationStatus.OPTIMIZATION_NOT_APPLICABLE
            return self._prepare_and_dispatch_baseline(executor, baseline_package)

        try:
            applicable = self._optimized_is_applicable(
                baseline_package, optimized_package
            )
        except (AttributeError, TypeError, ValueError):
            self._status = CoordinationStatus.OPTIMIZATION_FALLBACK
            return self._prepare_and_dispatch_baseline(executor, baseline_package)

        if not applicable:
            self._status = CoordinationStatus.OPTIMIZATION_NOT_APPLICABLE
            return self._prepare_and_dispatch_baseline(executor, baseline_package)

        try:
            prepared = executor.prepare(optimized_package.request)
        except OptimizationPreparationError:
            self._status = CoordinationStatus.OPTIMIZATION_FALLBACK
            return self._prepare_and_dispatch_baseline(executor, baseline_package)

        self._status = CoordinationStatus.OPTIMIZED_READY
        return executor.dispatch(prepared)

    @staticmethod
    def _validate_baseline(package: CompiledContextPackage) -> None:
        if package.mode is not CompilationMode.BASELINE:
            raise ValueError("baseline package must use BASELINE mode")
        validate_compiled_package(package)

    @staticmethod
    def _optimized_is_applicable(
        baseline: CompiledContextPackage,
        optimized: CompiledContextPackage,
    ) -> bool:
        if optimized.mode is not CompilationMode.OPTIMIZED:
            raise ValueError("optimized package must use OPTIMIZED mode")
        validate_compiled_package(optimized)

        reduced = tuple(
            entry for entry in optimized.entries
            if entry.manifest_entry.disposition is InclusionDisposition.REDUCED
        )
        if not reduced or optimized.request == baseline.request:
            return False

        baseline_by_id = {
            entry.manifest_entry.component_id: entry for entry in baseline.entries
        }
        if len(optimized.entries) != len(baseline.entries):
            raise ValueError("optimized component count differs from baseline")
        for entry in optimized.entries:
            baseline_entry = baseline_by_id.get(entry.manifest_entry.component_id)
            if baseline_entry is None:
                raise ValueError("optimized component is absent from baseline")
            if entry.manifest_entry.disposition is InclusionDisposition.REDUCED:
                if entry.source_body != baseline_entry.result_body:
                    raise ValueError("reduced source does not match baseline")
            elif entry.result_body != baseline_entry.result_body:
                raise ValueError("optimized exact component differs from baseline")
        return True

    @staticmethod
    def _prepare_and_dispatch_baseline(
        executor: AtomicStageExecutor,
        baseline: CompiledContextPackage,
    ) -> StageExecutionResult:
        prepared = executor.prepare(baseline.request)
        return executor.dispatch(prepared)


def execute_compiled_context(
    executor: object,
    baseline_package: CompiledContextPackage,
    optimized_package: CompiledContextPackage | None,
) -> StageExecutionResult:
    """Convenience entry point when the ephemeral status is not needed."""

    return ContextDispatchCoordinator().execute(
        executor, baseline_package, optimized_package
    )
