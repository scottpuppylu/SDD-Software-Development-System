import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sdd_orchestrator.pipeline import PipelineController
from sdd_orchestrator.system_controller import FullSystemController


class TelemetryControllerWiringTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path("application-wiring-repo")
        self.orchestrator = SimpleNamespace(repo_root=self.repo)
        self.recorder = Mock(name="telemetry_recorder")

    @patch("sdd_orchestrator.pipeline.StageRunner")
    def test_pipeline_controller_passes_recorder_to_its_stage_runner(self, runner_type):
        PipelineController(self.orchestrator, telemetry_recorder=self.recorder)

        runner_type.assert_called_once_with(
            self.orchestrator, telemetry_recorder=self.recorder
        )

    @patch("sdd_orchestrator.system_controller.GitRepository")
    @patch("sdd_orchestrator.system_controller.DecisionGateway")
    @patch("sdd_orchestrator.system_controller.StageRunner")
    def test_full_system_controller_passes_recorder_to_its_stage_runner(
        self, runner_type, _gateway_type, _git_type
    ):
        FullSystemController(
            self.orchestrator,
            Mock(name="reasoning_executor"),
            Mock(name="codex_runner"),
            telemetry_recorder=self.recorder,
        )

        runner_type.assert_called_once_with(
            self.orchestrator, telemetry_recorder=self.recorder
        )


class TelemetryCliWiringTests(unittest.TestCase):
    def _run_cli(self, arguments):
        from sdd_orchestrator import cli

        recorder_type = getattr(cli, "TelemetryRecorder", None)
        if recorder_type is None:
            self.fail(
                "M2.1 requires the CLI composition root to create a "
                "TelemetryRecorder from the process environment"
            )

        repo = Path("cli-wiring-repo")
        recorder = Mock(name="telemetry_recorder")
        orchestrator = SimpleNamespace(repo_root=repo)
        with (
            patch.object(recorder_type, "from_environment", return_value=recorder) as factory,
            patch.object(cli, "Orchestrator", return_value=orchestrator),
            patch.object(cli, "StageRunner") as runner_type,
            patch.object(cli, "PipelineController") as pipeline_type,
            patch.object(cli, "FullSystemController") as system_type,
            patch.object(cli, "Stage08CodexRunner") as stage08_type,
            patch.object(cli, "CodexCLI"),
            patch.object(cli, "CodexExecReasoningExecutor") as codex_type,
            patch.object(cli, "OpenAIResponsesExecutor") as openai_type,
            patch.object(cli, "_print"),
            patch.object(sys, "argv", ["sdd", "--repo", str(repo), *arguments]),
        ):
            runner_type.return_value.create_execution_packet.return_value = repo / "packet"
            pipeline_type.return_value.run_until.return_value = {}
            system_type.return_value.run.return_value = {}
            cli.main()

        factory.assert_called_once_with(repo)
        return SimpleNamespace(
            recorder=recorder,
            orchestrator=orchestrator,
            runner_type=runner_type,
            pipeline_type=pipeline_type,
            system_type=system_type,
            stage08_type=stage08_type,
            codex_type=codex_type,
            openai_type=openai_type,
        )

    def test_packet_wires_environment_recorder_into_stage_runner(self):
        observed = self._run_cli(["packet", "--stage", "03"])

        observed.runner_type.assert_called_once_with(
            observed.orchestrator, telemetry_recorder=observed.recorder
        )

    def test_openai_run_shares_one_recorder_with_runner_and_provider(self):
        observed = self._run_cli(["run", "--stage", "03", "--openai"])

        observed.runner_type.assert_called_once_with(
            observed.orchestrator, telemetry_recorder=observed.recorder
        )
        observed.openai_type.assert_called_once_with(
            model="gpt-5.6", telemetry_recorder=observed.recorder
        )

    def test_codex_pipeline_shares_one_recorder_with_controller_and_provider(self):
        observed = self._run_cli(["pipeline", "--provider", "codex"])

        observed.codex_type.assert_called_once_with(
            executable="codex",
            model=None,
            repo_root=Path("cli-wiring-repo"),
            telemetry_recorder=observed.recorder,
        )
        observed.pipeline_type.assert_called_once_with(
            observed.orchestrator, telemetry_recorder=observed.recorder
        )

    def test_auto_shares_one_recorder_with_controller_and_reasoning_provider(self):
        observed = self._run_cli(["auto", "--reasoning-provider", "openai"])

        observed.openai_type.assert_called_once_with(
            model="gpt-5.6", telemetry_recorder=observed.recorder
        )
        observed.system_type.assert_called_once_with(
            observed.orchestrator,
            observed.openai_type.return_value,
            observed.stage08_type.return_value,
            telemetry_recorder=observed.recorder,
        )


if __name__ == "__main__":
    unittest.main()
