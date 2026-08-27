from dataclasses import FrozenInstanceError
import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from sdd_orchestrator.executor import (
    AtomicStageExecutor,
    ExternalCommandExecutor,
    StageExecutionRequest,
    StageExecutionResult,
    StaticExecutor,
)
from sdd_orchestrator.providers import (
    CodexExecReasoningExecutor,
    OpenAIResponsesExecutor,
    ReasoningProviderError,
    _provider_system_instructions,
    _provider_user_input,
)


class FakeProc:
    returncode = 0
    stdout = '{"status":"COMPLETED","artifacts":{}}'
    stderr = ""


class AtomicExecutorTests(unittest.TestCase):
    def request(self):
        return StageExecutionRequest(
            stage_id="03",
            stage_name="TECHNICAL_SPECIFICATION",
            stage_type="AUTHORING",
            core_question="What must the system technically guarantee?",
            contract={"outputs": {"files": ["docs/spec.md"]}},
            artifacts={"docs/PRD.md": "# PRD"},
            semantic_inputs={"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"},
            runtime_inputs={},
            stage_instructions="Only Technical Contract authority.",
        )

    def test_capability_detection_is_structural_without_execute(self):
        class BaselineOnly:
            def execute(self, request):
                raise AssertionError("must not be called for detection")

        self.assertNotIsInstance(BaselineOnly(), AtomicStageExecutor)
        for executor in (
            StaticExecutor(StageExecutionResult(status="COMPLETED")),
            ExternalCommandExecutor(["executor"]),
            CodexExecReasoningExecutor(),
            OpenAIResponsesExecutor(api_key="secret"),
        ):
            self.assertIsInstance(executor, AtomicStageExecutor)

    @patch("sdd_orchestrator.providers.urllib.request.urlopen")
    def test_openai_prepare_is_immutable_exact_and_does_not_dispatch(self, urlopen):
        request = self.request()
        original = copy.deepcopy(request.to_dict())
        executor = OpenAIResponsesExecutor(api_key="secret", model="test-model")

        prepared = executor.prepare(request)

        urlopen.assert_not_called()
        body = json.loads(prepared.wire.decode("utf-8"))
        self.assertEqual(body["instructions"], _provider_system_instructions(request))
        self.assertEqual(body["input"], _provider_user_input(request))
        self.assertEqual(request.to_dict(), original)
        with self.assertRaises(FrozenInstanceError):
            prepared.wire = b"changed"

    @patch("sdd_orchestrator.providers.shutil.which", return_value="/bin/codex")
    @patch("sdd_orchestrator.providers.subprocess.run")
    def test_codex_prepare_renders_exact_prompt_without_subprocess(self, run, _which):
        request = self.request()
        original = copy.deepcopy(request.to_dict())
        executor = CodexExecReasoningExecutor(repo_root=Path.cwd())

        prepared = executor.prepare(request)

        run.assert_not_called()
        self.assertEqual(prepared.prompt, executor.build_prompt(request))
        self.assertEqual(request.to_dict(), original)
        with self.assertRaises(FrozenInstanceError):
            prepared.prompt = "changed"

    @patch("sdd_orchestrator.executor.subprocess.run")
    def test_external_prepare_exact_stdin_and_dispatch_once(self, run):
        request = self.request()
        original = copy.deepcopy(request.to_dict())
        executor = ExternalCommandExecutor(["executor", "--json"], timeout_seconds=7)

        prepared = executor.prepare(request)

        run.assert_not_called()
        self.assertEqual(
            prepared.stdin,
            json.dumps(request.to_dict(), ensure_ascii=False),
        )
        self.assertEqual(request.to_dict(), original)
        run.return_value = FakeProc()
        result = executor.dispatch(prepared)
        self.assertEqual(result.status, "COMPLETED")
        run.assert_called_once_with(
            ["executor", "--json"],
            input=prepared.stdin,
            text=True,
            capture_output=True,
            timeout=7,
        )

    def test_static_prepare_has_no_one_shot_side_effect_and_execute_is_compatible(self):
        request = self.request()
        result = StageExecutionResult(status="COMPLETED", result="PASS")
        executor = StaticExecutor(result)

        prepared = executor.prepare(request)
        self.assertIsNone(executor.last_request)
        self.assertIs(executor.dispatch(prepared), result)
        self.assertIs(executor.last_request, request)

        executor.last_request = None
        self.assertIs(executor.execute(request), result)
        self.assertIs(executor.last_request, request)

    @patch("sdd_orchestrator.providers.urllib.request.urlopen")
    def test_openai_dispatch_uses_prepared_wire_once_and_parses_result(self, urlopen):
        payload = {
            "id": "resp_test",
            "output_text": json.dumps({
                "status": "COMPLETED",
                "artifacts": [{"path": "docs/spec.md", "content": "# Spec"}],
                "result": None,
                "classification": None,
                "remediation_reasons": [],
                "provider_notes": None,
            }),
        }

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        urlopen.return_value = Response()
        executor = OpenAIResponsesExecutor(api_key="secret")
        prepared = executor.prepare(self.request())
        result = executor.dispatch(prepared)
        self.assertEqual(result.artifacts, {"docs/spec.md": "# Spec"})
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(urlopen.call_args.args[0].data, prepared.wire)

    @patch("sdd_orchestrator.providers.shutil.which", return_value="/bin/codex")
    @patch("sdd_orchestrator.providers.subprocess.run")
    def test_codex_dispatch_uses_prepared_prompt_once_and_preserves_failure(self, run, _which):
        executor = CodexExecReasoningExecutor(repo_root=Path.cwd())
        prepared = executor.prepare(self.request())

        def fail(_command, **kwargs):
            self.assertEqual(kwargs["input"], prepared.prompt)
            return subprocess.CompletedProcess([], 9, stdout="", stderr="failed")

        run.side_effect = fail
        with self.assertRaisesRegex(ReasoningProviderError, "failed"):
            executor.dispatch(prepared)
        self.assertEqual(run.call_count, 1)

    @patch("sdd_orchestrator.executor.subprocess.run", return_value=FakeProc())
    def test_external_public_execute_remains_prepare_then_dispatch(self, run):
        request = self.request()
        result = ExternalCommandExecutor(["executor"]).execute(request)
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
