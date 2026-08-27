import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sdd_orchestrator.context_activation import (
    CONTEXT_COMPILATION_MODE_ENV,
    ContextCompilationModeConfigError,
    resolve_context_compilation_mode,
)
from sdd_orchestrator.context_compiler import CompilationMode
from sdd_orchestrator.pipeline import PipelineController
from sdd_orchestrator.runner import StageRunner
from sdd_orchestrator.system_controller import FullSystemController


class ContextActivationGrammarTests(unittest.TestCase):
    def test_unset_and_exact_baseline_resolve_to_baseline(self):
        self.assertIs(resolve_context_compilation_mode({}), CompilationMode.BASELINE)
        self.assertIs(
            resolve_context_compilation_mode(
                {CONTEXT_COMPILATION_MODE_ENV: "BASELINE"}
            ),
            CompilationMode.BASELINE,
        )

    def test_exact_optimized_resolves_to_optimized(self):
        self.assertIs(
            resolve_context_compilation_mode(
                {CONTEXT_COMPILATION_MODE_ENV: "OPTIMIZED"}
            ),
            CompilationMode.OPTIMIZED,
        )

    def test_environment_mutation_after_resolution_does_not_change_mode(self):
        environment = {CONTEXT_COMPILATION_MODE_ENV: "OPTIMIZED"}
        mode = resolve_context_compilation_mode(environment)
        environment[CONTEXT_COMPILATION_MODE_ENV] = "BASELINE"
        self.assertIs(mode, CompilationMode.OPTIMIZED)

    def test_every_other_value_is_invalid_without_trim_or_casefold(self):
        invalid = [
            "", "baseline", "optimized", "Baseline", "Optimized",
            " OPTIMIZED", "OPTIMIZED ", " BASELINE", "BASELINE ",
            "true", "1", "on", "auto",
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ContextCompilationModeConfigError) as raised:
                    resolve_context_compilation_mode(
                        {CONTEXT_COMPILATION_MODE_ENV: value}
                    )
                diagnostic = str(raised.exception)
                self.assertIn(CONTEXT_COMPILATION_MODE_ENV, diagnostic)
                self.assertIn(repr(value), diagnostic)
                self.assertIn("BASELINE", diagnostic)
                self.assertIn("OPTIMIZED", diagnostic)


class ContextActivationCompositionTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = SimpleNamespace(repo_root=Path("activation-repo"))

    def test_direct_runner_default_is_baseline_independent_of_environment(self):
        with patch.dict(os.environ, {CONTEXT_COMPILATION_MODE_ENV: "OPTIMIZED"}):
            runner = StageRunner(self.orchestrator)
        self.assertIs(runner.compilation_mode, CompilationMode.BASELINE)

    def test_direct_runner_accepts_explicit_typed_optimized(self):
        runner = StageRunner(
            self.orchestrator, compilation_mode=CompilationMode.OPTIMIZED
        )
        self.assertIs(runner.compilation_mode, CompilationMode.OPTIMIZED)

    @patch("sdd_orchestrator.pipeline.StageRunner")
    def test_pipeline_reuses_injected_mode_for_its_runner(self, runner_type):
        mode = resolve_context_compilation_mode(
            {CONTEXT_COMPILATION_MODE_ENV: "OPTIMIZED"}
        )
        controller = PipelineController(self.orchestrator, compilation_mode=mode)
        with patch.dict(
            os.environ, {CONTEXT_COMPILATION_MODE_ENV: "BASELINE"}, clear=False
        ):
            self.assertIs(controller.runner, runner_type.return_value)
        runner_type.assert_called_once_with(
            self.orchestrator,
            telemetry_recorder=None,
            compilation_mode=CompilationMode.OPTIMIZED,
        )

    @patch("sdd_orchestrator.system_controller.GitRepository")
    @patch("sdd_orchestrator.system_controller.DecisionGateway")
    @patch("sdd_orchestrator.system_controller.StageRunner")
    def test_full_system_injects_mode_only_into_reasoning_runner(
        self, runner_type, _gateway_type, _git_type
    ):
        codex_runner = Mock(name="stage08_codex_runner")
        FullSystemController(
            self.orchestrator,
            Mock(name="reasoning_executor"),
            codex_runner,
            compilation_mode=CompilationMode.OPTIMIZED,
        )
        runner_type.assert_called_once_with(
            self.orchestrator,
            telemetry_recorder=None,
            compilation_mode=CompilationMode.OPTIMIZED,
        )
        self.assertFalse(codex_runner.called)


class ContextActivationCliTests(unittest.TestCase):
    def _invoke(self, arguments, resolved_mode):
        from sdd_orchestrator import cli

        repo = Path("activation-cli-repo")
        orchestrator = SimpleNamespace(repo_root=repo)
        recorder = Mock(name="telemetry_recorder")
        with (
            patch.object(cli, "resolve_context_compilation_mode", return_value=resolved_mode) as resolve,
            patch.object(cli, "Orchestrator", return_value=orchestrator),
            patch.object(cli.TelemetryRecorder, "from_environment", return_value=recorder),
            patch.object(cli, "StageRunner") as runner_type,
            patch.object(cli, "PipelineController") as pipeline_type,
            patch.object(cli, "FullSystemController") as system_type,
            patch.object(cli, "Stage08CodexRunner") as stage08_type,
            patch.object(cli, "CodexCLI"),
            patch.object(cli, "CodexExecReasoningExecutor"),
            patch.object(cli, "OpenAIResponsesExecutor") as openai_type,
            patch.object(cli, "_print"),
            patch.object(sys, "argv", ["sdd", "--repo", str(repo), *arguments]),
        ):
            runner_type.return_value.run.return_value = {}
            pipeline_type.return_value.run_until.return_value = {}
            system_type.return_value.run.return_value = {}
            cli.main()
        resolve.assert_called_once_with()
        return SimpleNamespace(
            orchestrator=orchestrator,
            recorder=recorder,
            runner_type=runner_type,
            pipeline_type=pipeline_type,
            system_type=system_type,
            stage08_type=stage08_type,
            openai_type=openai_type,
        )

    def test_direct_run_receives_once_resolved_mode(self):
        observed = self._invoke(
            ["run", "--stage", "03", "--openai"], CompilationMode.OPTIMIZED
        )
        observed.runner_type.assert_called_once_with(
            observed.orchestrator,
            telemetry_recorder=observed.recorder,
            compilation_mode=CompilationMode.OPTIMIZED,
        )

    def test_pipeline_receives_once_resolved_mode(self):
        observed = self._invoke(
            ["pipeline", "--provider", "openai"], CompilationMode.OPTIMIZED
        )
        observed.pipeline_type.assert_called_once_with(
            observed.orchestrator,
            telemetry_recorder=observed.recorder,
            compilation_mode=CompilationMode.OPTIMIZED,
        )

    def test_auto_receives_mode_and_keeps_stage08_on_codex_path(self):
        observed = self._invoke(
            ["auto", "--reasoning-provider", "openai"], CompilationMode.OPTIMIZED
        )
        observed.system_type.assert_called_once_with(
            observed.orchestrator,
            observed.openai_type.return_value,
            observed.stage08_type.return_value,
            telemetry_recorder=observed.recorder,
            compilation_mode=CompilationMode.OPTIMIZED,
        )

    def test_invalid_config_fails_before_orchestrator_runner_or_lifecycle(self):
        from sdd_orchestrator import cli

        with (
            patch.dict(os.environ, {CONTEXT_COMPILATION_MODE_ENV: "optimized"}),
            patch.object(cli, "Orchestrator") as orchestrator_type,
            patch.object(cli, "StageRunner") as runner_type,
            patch.object(sys, "argv", ["sdd", "run", "--stage", "03", "--openai"]),
        ):
            with self.assertRaises(ContextCompilationModeConfigError):
                cli.main()
        orchestrator_type.assert_not_called()
        runner_type.assert_not_called()


if __name__ == "__main__":
    unittest.main()
