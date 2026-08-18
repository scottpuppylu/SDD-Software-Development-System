from pathlib import Path
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StageExecutionResult, StaticExecutor
from sdd_orchestrator.runner import StageRunner


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class Stage02ProductConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")
        proposal = self.repo / "docs" / "proposal.md"
        proposal.parent.mkdir(parents=True, exist_ok=True)
        proposal.write_text("# Proposal\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_stage02_blocked_clarification_does_not_advance_to_stage03(self):
        runner = StageRunner(Orchestrator(self.repo))
        result = runner.run(
            StaticExecutor(StageExecutionResult(
                status="BLOCKED",
                artifacts={"docs/PRD.md": "# Draft PRD\n\nBLOCKING_TBD: retry behavior\n"},
                remediation_reasons=["PRODUCT_CLARIFICATION_REQUIRED"],
            )),
            "02",
            semantic_inputs={"APPROVED_PRODUCT_DECISIONS": "none"},
        )
        self.assertTrue((self.repo / "docs/PRD.md").exists())
        self.assertTrue(result["transition"]["blocked"])
        self.assertEqual(result["transition"]["next"], "REMEDIATION_ROUTER")
        self.assertNotEqual(runner.orchestrator.project_state["stages"]["02"].get("result"), "COMPLETED")

    def test_stage03_requires_completed_stage02_contract(self):
        prd = self.repo / "docs" / "PRD.md"
        prd.write_text("# PRD\n", encoding="utf-8")
        orch = Orchestrator(self.repo)
        check = orch.check_required_inputs(
            "03", {"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY"}
        )
        self.assertIn("stage_02_result == COMPLETED", check.entry_condition_failures)

        orch.project_state["stages"]["02"]["status"] = "DONE"
        orch.project_state["stages"]["02"]["result"] = "COMPLETED"
        check = orch.check_required_inputs(
            "03", {"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY"}
        )
        self.assertTrue(check.ready)

    def test_delegation_request_requires_confirmation_before_prd_completion(self):
        stage02 = (self.repo / ".sdd/instructions/stage-02.md").read_text(encoding="utf-8")

        self.assertIn("只是 **delegation request**", stage02)
        self.assertIn("不得立即視為已確認的 Decision Delegation", stage02)
        self.assertIn("Stage 02 必須在產生或完成 PRD 前停止", stage02)
        self.assertIn("只做一件主要事情：詢問使用者是否明確授權", stage02)
        self.assertIn("不得產生 final PRD baseline", stage02)
        self.assertIn("不得宣告 Stage 02 完成", stage02)
        self.assertIn("不得路由到 Stage 03", stage02)

    def test_confirmed_delegation_remains_bounded_and_needs_final_baseline(self):
        stage02 = (self.repo / ".sdd/instructions/stage-02.md").read_text(encoding="utf-8")
        stage03 = (self.repo / ".sdd/instructions/stage-03.md").read_text(encoding="utf-8")

        self.assertIn("作出明確肯定後，Decision Delegation 才啟用", stage02)
        self.assertIn("Delegation 啟用後", stage02)
        self.assertIn("一般 Product ambiguity", stage02)
        self.assertIn("重大或高影響決定仍會回來詢問", stage02)
        self.assertIn("Delegation 不取消 final review", stage02)
        self.assertIn("final baseline authorization", stage02)
        self.assertIn("`status: DONE`、`result: COMPLETED`", stage02)
        self.assertIn("不得使用 `READY_FOR_SPEC`", stage02)
        self.assertIn("不得建立任何平行 completion vocabulary", stage02)
        self.assertIn("Product-level clarification 路由回 Stage 02", stage03)
        self.assertIn("普通 technical implementation 選擇", stage03)


if __name__ == "__main__":
    unittest.main()
