from pathlib import Path
import os
import shutil
import tempfile
import unittest
import json
from unittest.mock import patch

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StageExecutionRequest, StageExecutionResult
from sdd_orchestrator.pipeline import PipelineController
from sdd_orchestrator.providers import (
    OpenAIResponsesExecutor,
    ProviderPolicyViolationError,
    ProviderUnavailableError,
    ReasoningProviderError,
    ReasoningInvocation,
    ReasoningProviderBoundary,
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

    @staticmethod
    def provider_request():
        return StageExecutionRequest(
            stage_id="03",
            stage_name="Specification",
            stage_type="reasoning",
            core_question="Define the technical contract",
            contract={"outputs": {"files": ["docs/spec.md"]}},
            artifacts={},
        )

    def invocation(self, **overrides):
        values = {
            "attempt_id": "attempt-007-a",
            "operation": "DRAFT_SPECIFICATION",
            "request": self.provider_request(),
            "authoritative_context_refs": ("docs/PRD.md@sha256:abc",),
            "permitted_capabilities": frozenset({"DRAFT", "REASON"}),
            "affected_scope": ("docs/spec.md",),
            "validation_inputs": {"result_vocabulary": ("PASS", "FAIL", "NOT RUN")},
        }
        values.update(overrides)
        return ReasoningInvocation(**values)

    def stage01_orchestrator(self):
        orch = Orchestrator(self.repo)
        orch.project_state["lifecycle"].update(
            {
                "current_stage": "01",
                "current_stage_name": "PROPOSAL",
                "last_completed_stage": None,
                "next_action": "RUN_STAGE",
            }
        )
        for stage_id, state in orch.project_state["stages"].items():
            state["status"] = "IN_PROGRESS" if str(stage_id).zfill(2) == "01" else "TODO"
            state["result"] = None
        orch.project_state["authorizations"]["implementation"] = False
        orch.project_state["blocking"] = {"is_blocked": False, "reasons": []}
        return orch

    def test_replaceable_providers_preserve_non_authoritative_semantics(self):
        class Substitute:
            def __init__(self, provider_name):
                self.provider_name = provider_name

            def execute(self, request):
                return StageExecutionResult(
                    status="COMPLETED",
                    artifacts={"docs/spec.md": "# proposed spec"},
                    metadata={"provider": self.provider_name},
                )

        results = [
            ReasoningProviderBoundary(Substitute(name)).invoke(self.invocation())
            for name in ("provider-a", "provider-b")
        ]
        for result in results:
            self.assertEqual(result.status, "PROPOSED")
            self.assertFalse(result.authoritative)
            self.assertFalse(result.persisted)
            self.assertEqual(
                result.proposed_output.metadata["provider_output_status"],
                "PROPOSED_UNVALIDATED",
            )
        self.assertEqual(results[0].proposed_output.status, results[1].proposed_output.status)
        self.assertEqual(results[0].proposed_output.artifacts, results[1].proposed_output.artifacts)

    def test_failure_classes_preserve_attempt_scope_state_and_routes(self):
        failures = [
            (ProviderUnavailableError("offline"), "UNAVAILABLE"),
            (TimeoutError("deadline"), "TIMEOUT"),
            (ProviderPolicyViolationError("refused"), "POLICY_VIOLATION"),
            (ValueError("bad payload"), "MALFORMED"),
        ]
        for error, category in failures:
            with self.subTest(category=category):
                class FailingProvider:
                    def execute(self, request):
                        raise error

                result = ReasoningProviderBoundary(FailingProvider()).invoke(self.invocation())
                self.assertEqual(result.status, "BLOCKED")
                self.assertEqual(result.failure.category, category)
                self.assertEqual(result.failure.attempt_id, "attempt-007-a")
                self.assertEqual(result.failure.operation, "DRAFT_SPECIFICATION")
                self.assertEqual(result.failure.affected_scope, ("docs/spec.md",))
                self.assertTrue(result.failure.prior_state_preserved)
                self.assertTrue(result.failure.unsafe_continuation_stopped)
                self.assertTrue(result.failure.eligible_routes)

    def test_boundary_rejects_scope_overrun_and_inference_to_approval(self):
        class Substitute:
            def __init__(self, result):
                self.result = result

            def execute(self, request):
                return self.result

        overrun = ReasoningProviderBoundary(
            Substitute(StageExecutionResult(status="COMPLETED", artifacts={"outside.txt": "x"}))
        ).invoke(self.invocation())
        self.assertEqual(overrun.failure.category, "OUT_OF_SCOPE")

        approval = ReasoningProviderBoundary(
            Substitute(StageExecutionResult(status="COMPLETED", metadata={"approval_created": True}))
        ).invoke(self.invocation())
        self.assertEqual(approval.failure.category, "AUTHORITY_CROSSING")

        malformed = ReasoningProviderBoundary(
            Substitute(StageExecutionResult(status="COMPLETED", artifacts=None))
        ).invoke(self.invocation())
        self.assertEqual(malformed.failure.category, "MALFORMED")

    def test_write_capability_without_stage08_envelope_never_invokes_provider(self):
        class MustNotRun:
            called = False

            def execute(self, request):
                self.called = True
                return StageExecutionResult(status="COMPLETED")

        provider = MustNotRun()
        invocation = self.invocation(
            permitted_capabilities=frozenset({"AUTHORIZED_STAGE08_ASSISTANCE"})
        )
        result = ReasoningProviderBoundary(provider).invoke(invocation)
        self.assertEqual(result.failure.category, "NO_AUTHORIZATION")
        self.assertFalse(provider.called)

    def test_missing_authority_reference_and_unknown_capability_fail_closed(self):
        class MustNotRun:
            def execute(self, request):
                self.fail("provider should not run")

        boundary = ReasoningProviderBoundary(MustNotRun())
        no_authority = boundary.invoke(self.invocation(authoritative_context_refs=()))
        self.assertEqual(no_authority.failure.category, "AUTHORITY_CROSSING")
        policy = boundary.invoke(self.invocation(permitted_capabilities=frozenset({"APPROVE"})))
        self.assertEqual(policy.failure.category, "POLICY_VIOLATION")

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
        orch.project_state["stages"]["02"]["status"] = "DONE"
        orch.project_state["stages"]["02"]["result"] = "COMPLETED"
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
        orch = self.stage01_orchestrator()
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
        orch = self.stage01_orchestrator()
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

        orch = self.stage01_orchestrator()
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
