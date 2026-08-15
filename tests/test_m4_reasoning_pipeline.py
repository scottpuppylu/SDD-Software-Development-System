from pathlib import Path
import os
import shutil
import tempfile
import unittest
import json
from unittest.mock import patch

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StageExecutionResult
from sdd_orchestrator.pipeline import PipelineController
from sdd_orchestrator.providers import (
    OpenAIResponsesExecutor,
    ReasoningProviderError,
    _result_schema,
)
from sdd_orchestrator.runner import StageRunner


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class StageAwareExecutor:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        outputs = request.contract.get("outputs", {}).get("files", []) or []
        artifacts = {}
        for path in outputs:
            if request.stage_id == "01":
                artifacts[path] = "# Proposal\n\nG-001 — Validate the product intent.\n"
            elif request.stage_id == "02":
                artifacts[path] = "# PRD\n\nFR-001 [P0] — Required behavior.\n"
            elif request.stage_id == "03":
                artifacts[path] = "# Technical Specification\n\nSPEC-001 — Technical guarantee.\n"
            else:
                artifacts[path] = f"# Stage {request.stage_id} Output\n"
        return StageExecutionResult(status="COMPLETED", artifacts=artifacts)


class M4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")

    def tearDown(self):
        self.tmp.cleanup()

    def test_openai_executor_requires_environment_key(self):
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ReasoningProviderError):
                OpenAIResponsesExecutor()
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old

    def test_structured_schema_uses_stage_result_vocabulary(self):
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        # Create the Stage 07 required files so a request can be built.
        for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md"]:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        req = runner.build_request(
            "07",
            semantic_inputs={
                "REPOSITORY_STRUCTURE": "x",
                "GIT_READINESS": "x",
            },
        )
        schema = _result_schema(req)
        values = schema["properties"]["result"]["enum"]
        self.assertIn("PASS", values)
        self.assertIn("FAIL", values)
        self.assertIn("INCOMPLETE", values)


    def test_openai_adapter_builds_structured_response_request_and_parses_result(self):
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        # Prepare Stage 03 prerequisites.
        for rel in ["docs/proposal.md", "docs/PRD.md"]:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# upstream\n", encoding="utf-8")
        req = runner.build_request(
            "03",
            semantic_inputs={"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"},
        )

        fake_payload = {
            "id": "resp_test",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({
                                "status": "COMPLETED",
                                "artifacts": [
                                    {"path": "docs/spec.md", "content": "# Spec\nSPEC-001"}
                                ],
                                "result": None,
                                "classification": None,
                                "remediation_reasons": [],
                                "provider_notes": None,
                            }),
                        }
                    ],
                }
            ],
        }

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps(fake_payload).encode("utf-8")

        captured = {}
        def fake_urlopen(http_request, timeout):
            captured["body"] = json.loads(http_request.data.decode("utf-8"))
            captured["authorization"] = http_request.headers.get("Authorization")
            return FakeResponse()

        executor = OpenAIResponsesExecutor(api_key="test-secret", model="gpt-5.6")
        with patch("urllib.request.urlopen", fake_urlopen):
            result = executor.execute(req)

        self.assertEqual(result.artifacts["docs/spec.md"], "# Spec\nSPEC-001")
        self.assertEqual(result.metadata["response_id"], "resp_test")
        self.assertEqual(captured["body"]["text"]["format"]["type"], "json_schema")
        self.assertTrue(captured["body"]["text"]["format"]["strict"])
        self.assertEqual(captured["authorization"], "Bearer test-secret")
        self.assertNotIn("test-secret", json.dumps(captured["body"]))

    def test_pipeline_01_to_03_without_manual_artifact_handoff(self):
        orch = Orchestrator(self.repo)
        controller = PipelineController(orch)
        executor = StageAwareExecutor()
        result = controller.run_until(
            executor,
            stop_before="04",
            semantic_by_stage={
                "01": {
                    "IDEA_OR_PROBLEM": "Automate a known workflow",
                    "TARGET_USER_OR_USAGE_CONTEXT": "Project owner",
                    "GOALS_OR_DESIRED_OUTCOME": "Produce governed SDD artifacts",
                }
            },
        )
        self.assertEqual(result.stop_reason, "STOP_BEFORE_STAGE")
        self.assertEqual(result.stopped_at_stage, "04")
        self.assertTrue((self.repo / "docs/proposal.md").exists())
        self.assertTrue((self.repo / "docs/PRD.md").exists())
        self.assertTrue((self.repo / "docs/spec.md").exists())
        self.assertEqual([r.stage_id for r in executor.requests], ["01", "02", "03"])
        # Stage 03 request received upstream artifacts automatically.
        stage03 = executor.requests[2]
        self.assertIn("docs/proposal.md", stage03.artifacts)
        self.assertIn("docs/PRD.md", stage03.artifacts)

    def test_pipeline_injects_non_decision_defaults_not_new_authority(self):
        orch = Orchestrator(self.repo)
        controller = PipelineController(orch)
        executor = StageAwareExecutor()
        controller.run_until(
            executor,
            stop_before="03",
            semantic_by_stage={
                "01": {
                    "IDEA_OR_PROBLEM": "x",
                    "TARGET_USER_OR_USAGE_CONTEXT": "y",
                    "GOALS_OR_DESIRED_OUTCOME": "z",
                }
            },
        )
        stage02 = executor.requests[1]
        self.assertIn("APPROVED_PRODUCT_DECISIONS", stage02.semantic_inputs)
        self.assertIn("No additional product decisions", stage02.semantic_inputs["APPROVED_PRODUCT_DECISIONS"])

    def test_pipeline_stops_when_executor_blocks(self):
        class BlockingExecutor:
            def execute(self, request):
                return StageExecutionResult(
                    status="BLOCKED",
                    artifacts={},
                    remediation_reasons=["NEEDS_CLARIFICATION"],
                )

        orch = Orchestrator(self.repo)
        controller = PipelineController(orch)
        result = controller.run_until(
            BlockingExecutor(),
            stop_before="04",
            semantic_by_stage={
                "01": {
                    "IDEA_OR_PROBLEM": "x",
                    "TARGET_USER_OR_USAGE_CONTEXT": "y",
                    "GOALS_OR_DESIRED_OUTCOME": "z",
                }
            },
        )
        self.assertEqual(result.stop_reason, "BLOCKED")
        self.assertEqual(result.stopped_at_stage, "01")
        self.assertTrue(orch.project_state["blocking"]["is_blocked"])


if __name__ == "__main__":
    unittest.main()
