from pathlib import Path
import shutil
import tempfile
import unittest
import yaml

from sdd_orchestrator.core import Orchestrator


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text="x"):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_stage_07_missing_design_is_incomplete(self):
        for rel in [
            "docs/PRD.md",
            "docs/spec.md",
            "AGENTS.md",
            "tasks.md",
        ]:
            self.write(rel)
        orch = Orchestrator(self.repo)
        check = orch.check_required_inputs("07")
        self.assertFalse(check.ready)
        self.assertIn("docs/Design.md", check.missing_files)
        self.assertEqual(orch.missing_input_gate_result("07"), "INCOMPLETE")

    def test_stage_07_pass_grants_implementation_and_routes_08(self):
        orch = Orchestrator(self.repo)
        result = orch.record_stage_result("07", "PASS")
        self.assertTrue(result["implementation_authorization"])
        self.assertEqual(result["next"], "08")
        self.assertEqual(orch.project_state["lifecycle"]["current_stage"], "08")

    def test_stage_08_entry_requires_stage_07_and_authorization(self):
        orch = Orchestrator(self.repo)
        check = orch.check_required_inputs("08")
        self.assertIn("stage_07_result == PASS", check.entry_condition_failures)
        self.assertIn(
            "implementation_authorization == true",
            check.entry_condition_failures,
        )

    def test_stage_09_implementation_gap_routes_to_08(self):
        orch = Orchestrator(self.repo)
        result = orch.record_stage_result(
            "09", "FAIL", classification="IMPLEMENTATION_GAP"
        )
        self.assertEqual(result["next"], "08")

    def test_stage_10_ready_grants_release(self):
        orch = Orchestrator(self.repo)
        result = orch.record_stage_result("10", "READY")
        self.assertTrue(result["release_authorization"])
        self.assertEqual(result["next"], "DEPLOY")

    def test_cross_domain_conflict_routes_to_both_authority_owners(self):
        orch = Orchestrator(self.repo)
        route = orch.route_conflict(
            ["PRODUCT_REQUIREMENT", "TECHNICAL_CONTRACT"]
        )
        self.assertEqual(route["owner_stages"], ["02", "03"])
        self.assertTrue(route["human_decision_required"])


if __name__ == "__main__":
    unittest.main()
