from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

from sdd_orchestrator.executor import StageExecutionRequest
from sdd_orchestrator.providers import CodexExecReasoningExecutor


class FakeProc:
    returncode = 0
    stdout = ""
    stderr = ""


class CodexReasoningTests(unittest.TestCase):
    def request(self):
        return StageExecutionRequest(
            stage_id="03",
            stage_name="TECHNICAL_SPECIFICATION",
            stage_type="AUTHORING",
            core_question="What must the system technically guarantee?",
            contract={
                "outputs": {"files": ["docs/spec.md"]},
            },
            artifacts={"docs/PRD.md": "# PRD"},
            semantic_inputs={},
            runtime_inputs={},
            stage_instructions="Only Technical Contract authority.",
        )

    def test_command_is_read_only_ephemeral_and_structured(self):
        ex = CodexExecReasoningExecutor(executable="codex", model="test-model", repo_root=Path.cwd())
        cmd = ex.command(Path("schema.json"), Path("out.json"))
        self.assertEqual(cmd[:3], ["codex", "exec", "--sandbox"])
        self.assertIn("read-only", cmd)
        self.assertIn("--output-schema", cmd)
        self.assertIn("--output-last-message", cmd)
        self.assertIn("--ephemeral", cmd)
        self.assertEqual(cmd[-1], "-")
        self.assertIn("test-model", cmd)

    @patch("sdd_orchestrator.providers.shutil.which", return_value="/usr/bin/codex")
    @patch("sdd_orchestrator.providers.subprocess.run")
    def test_execute_parses_structured_last_message(self, run, which):
        def fake_run(cmd, **kwargs):
            out = Path(cmd[cmd.index("--output-last-message") + 1])
            out.write_text(json.dumps({
                "status":"COMPLETED",
                "artifacts":[{"path":"docs/spec.md","content":"# spec"}],
                "result":None,
                "classification":None,
                "remediation_reasons":[],
                "convergence_tasks":[],
                "provider_notes":"ok"
            }), encoding="utf-8")
            self.assertEqual(kwargs["cwd"], Path.cwd())
            self.assertIn("Technical Contract", kwargs["input"])
            self.assertEqual(kwargs["encoding"], "utf-8")
            self.assertEqual(kwargs["errors"], "strict")
            return FakeProc()
        run.side_effect = fake_run
        result = CodexExecReasoningExecutor(model=None, repo_root=Path.cwd()).execute(self.request())
        self.assertEqual(result.artifacts["docs/spec.md"], "# spec")
        self.assertEqual(result.metadata["provider"], "codex_exec_reasoning")
        self.assertEqual(result.metadata["sandbox"], "read-only")


    @patch("sdd_orchestrator.providers.shutil.which", return_value=r"C:\\Users\\user\\AppData\\Roaming\\npm\\codex.CMD")
    def test_resolved_executable_uses_path_result(self, which):
        ex = CodexExecReasoningExecutor(executable="codex", repo_root=Path.cwd())
        self.assertTrue(ex.resolved_executable().lower().endswith("codex.cmd"))

    @patch("sdd_orchestrator.providers.shutil.which", return_value=None)
    def test_missing_codex_has_actionable_error(self, which):
        with self.assertRaisesRegex(Exception, "codex login"):
            CodexExecReasoningExecutor().execute(self.request())


if __name__ == "__main__":
    unittest.main()

class CodexConvergenceSchemaTests(unittest.TestCase):
    def test_non_stage09_schema_omits_convergence_tasks(self):
        from sdd_orchestrator.executor import StageExecutionRequest
        from sdd_orchestrator.providers import _result_schema
        request = StageExecutionRequest(
            stage_id="02",
            stage_name="PRODUCT_REQUIREMENTS",
            stage_type="AUTHORING",
            core_question="What should the product do?",
            contract={"outputs": {"files": ["docs/PRD.md"]}},
            artifacts={"docs/proposal.md": "# Proposal"},
        )
        schema = _result_schema(request)
        self.assertNotIn("convergence_tasks", schema["properties"])
        self.assertNotIn("convergence_tasks", schema["required"])

    def test_stage09_schema_allows_convergence_tasks(self):
        from sdd_orchestrator.executor import StageExecutionRequest
        from sdd_orchestrator.providers import _result_schema
        request = StageExecutionRequest(
            stage_id="09",
            stage_name="VERIFICATION_CONVERGENCE",
            stage_type="GATE",
            core_question="Does implementation conform?",
            contract={"outputs": {"files": ["docs/handoff/verification-report.md"]}},
            artifacts={},
        )
        schema = _result_schema(request)
        convergence = schema["properties"]["convergence_tasks"]
        self.assertEqual(convergence["type"], "array")
        self.assertIn("items", convergence)
