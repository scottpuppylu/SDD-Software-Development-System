from pathlib import Path
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StageExecutionResult, StaticExecutor
from sdd_orchestrator.runner import StageRunner
from sdd_orchestrator.pipeline import (
    APPROVED_INTAKE_FORMS,
    READINESS_DIMENSIONS,
    ReadinessDimensionFinding,
    RequirementReadinessError,
    RequirementReadinessEvaluator,
    RequirementReadinessRequest,
)


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
        # The copied repository state records a previously completed Stage02.
        # Establish the pre-completion state for this isolated entry-gate case
        # instead of attributing that inherited completion to this invocation.
        orch.project_state["stages"]["02"]["status"] = "TODO"
        orch.project_state["stages"]["02"]["result"] = None
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


class RequirementReadinessEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = RequirementReadinessEvaluator()

    def finding(self, dimension, result="PASS", **changes):
        values = dict(
            dimension=dimension,
            result=result,
            affected_scope=("PRODUCT_BASELINE",),
            evidence_reference=f"evidence:{dimension}",
            authority_reference="docs/PRD.md#approved-baseline",
            source_kind=(
                "PRODUCT_AUTHORITY"
                if dimension == "product_baseline_approval"
                else "RECORDED_EVIDENCE"
            ),
            explanation=f"Readiness finding for {dimension}.",
            clarification_question=(
                None if result == "PASS" else f"What must be decided for {dimension}?"
            ),
        )
        values.update(changes)
        return ReadinessDimensionFinding(**values)

    def request(self, *, findings=None, intake_form="PLAIN_LANGUAGE", **changes):
        values = dict(
            intake_form=intake_form,
            intake_reference="intake:idea-1",
            proposed_baseline_reference="docs/PRD.md#candidate-1",
            findings=tuple(findings or (self.finding(name) for name in READINESS_DIMENSIONS)),
        )
        values.update(changes)
        return RequirementReadinessRequest(**values)

    def test_all_seven_dimensions_are_required_for_readiness(self):
        decision = self.evaluator.evaluate(self.request())
        self.assertTrue(decision.ready)
        self.assertEqual(decision.result, "PASS")
        self.assertEqual(tuple(item.dimension for item in decision.findings), READINESS_DIMENSIONS)
        self.assertEqual(decision.next_route, "READY_FOR_PRODUCT_BASELINE")

    def test_each_unresolved_dimension_blocks_only_its_affected_scope(self):
        for dimension in READINESS_DIMENSIONS:
            with self.subTest(dimension=dimension):
                findings = [self.finding(name) for name in READINESS_DIMENSIONS]
                index = READINESS_DIMENSIONS.index(dimension)
                findings[index] = self.finding(
                    dimension, "FAIL", affected_scope=(f"scope:{dimension}",)
                )
                decision = self.evaluator.evaluate(self.request(findings=findings))
                self.assertFalse(decision.ready)
                self.assertEqual(decision.result, "FAIL")
                self.assertEqual(decision.blocked_scope, (f"scope:{dimension}",))
                self.assertEqual(len(decision.clarification_questions), 1)

    def test_combined_failures_produce_focused_questions_and_union_scope(self):
        findings = [self.finding(name) for name in READINESS_DIMENSIONS]
        findings[0] = self.finding("problem", "NOT RUN", affected_scope=("PROBLEM",))
        findings[2] = self.finding("mvp_scope", "FAIL", affected_scope=("MVP",))
        decision = self.evaluator.evaluate(self.request(findings=findings))
        self.assertEqual(decision.blocked_scope, ("MVP", "PROBLEM"))
        self.assertEqual(len(decision.clarification_questions), 2)
        self.assertEqual(decision.next_route, "PRODUCT_CLARIFICATION_REQUIRED")

    def test_every_approved_intake_form_is_accepted(self):
        for intake_form in APPROVED_INTAKE_FORMS:
            with self.subTest(intake_form=intake_form):
                decision = self.evaluator.evaluate(self.request(intake_form=intake_form))
                self.assertTrue(decision.ready)
                self.assertEqual(decision.intake_reference, "intake:idea-1")

    def test_noncritical_downstream_detail_does_not_block_product_readiness(self):
        decision = self.evaluator.evaluate(
            self.request(noncritical_downstream_details=("database choice remains open",))
        )
        self.assertTrue(decision.ready)
        self.assertEqual(decision.blocked_scope, ())

    def test_missing_or_duplicate_dimensions_are_rejected(self):
        with self.assertRaisesRegex(RequirementReadinessError, "missing readiness dimensions"):
            self.evaluator.evaluate(self.request(findings=(self.finding("problem"),)))
        findings = [self.finding(name) for name in READINESS_DIMENSIONS]
        findings.append(self.finding("problem"))
        with self.assertRaisesRegex(RequirementReadinessError, "duplicate readiness dimension"):
            self.evaluator.evaluate(self.request(findings=findings))

    def test_unresolved_finding_requires_plain_focused_question(self):
        findings = [self.finding(name) for name in READINESS_DIMENSIONS]
        findings[1] = self.finding("target_user", "FAIL", clarification_question=None)
        with self.assertRaisesRegex(RequirementReadinessError, "focused clarification"):
            self.evaluator.evaluate(self.request(findings=findings))

    def test_inference_ai_proposal_and_silence_cannot_create_readiness(self):
        for source_kind in ("INFERENCE", "AI_PROPOSAL", "SILENCE"):
            with self.subTest(source_kind=source_kind):
                findings = [self.finding(name) for name in READINESS_DIMENSIONS]
                findings[-1] = self.finding(
                    "product_baseline_approval", source_kind=source_kind
                )
                with self.assertRaisesRegex(RequirementReadinessError, "cannot establish"):
                    self.evaluator.evaluate(self.request(findings=findings))

    def test_approval_requires_product_authority_and_repository_reference(self):
        findings = [self.finding(name) for name in READINESS_DIMENSIONS]
        findings[-1] = self.finding(
            "product_baseline_approval", source_kind="RECORDED_EVIDENCE"
        )
        with self.assertRaisesRegex(RequirementReadinessError, "requires Product authority"):
            self.evaluator.evaluate(self.request(findings=findings))
        findings[-1] = self.finding("product_baseline_approval", authority_reference=None)
        with self.assertRaisesRegex(RequirementReadinessError, "requires evidence and authority"):
            self.evaluator.evaluate(self.request(findings=findings))

    def test_malformed_intake_or_result_is_rejected(self):
        with self.assertRaisesRegex(RequirementReadinessError, "unsupported product intake"):
            self.evaluator.evaluate(self.request(intake_form="CHAT_APPROVAL"))
        findings = [self.finding(name) for name in READINESS_DIMENSIONS]
        findings[0] = self.finding("problem", "READY")
        with self.assertRaisesRegex(RequirementReadinessError, "invalid readiness result"):
            self.evaluator.evaluate(self.request(findings=findings))


if __name__ == "__main__":
    unittest.main()
