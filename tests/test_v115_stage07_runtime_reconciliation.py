from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess
import tempfile
import unittest
import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import Stage08CodexRunner
from sdd_orchestrator.executor import StageExecutionRequest
from sdd_orchestrator.providers import _result_schema
from sdd_orchestrator.system_controller import FullSystemController

SOURCE = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


class NoopReasoning:
    def execute(self, request):
        raise AssertionError("reasoning should not be called in this unit test")


class V115RuntimeReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE / ".sdd", self.repo / ".sdd")
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test User")
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        self.orch = Orchestrator(self.repo)
        self.controller = FullSystemController(
            self.orch,
            NoopReasoning(),
            Stage08CodexRunner(self.orch, codex=SimpleNamespace()),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_reconcile_stage07_populates_git_and_clears_stale_non_authoritative_blockers(self):
        state = self.orch.project_state
        state["blocking"]["is_blocked"] = True
        state["blocking"]["reasons"] = ["OLD_STAGE02_PRODUCT_QUESTION"]
        state["git"]["branch"] = None
        state["git"]["head_commit"] = None
        self.orch._save_yaml(self.orch.project_state_path, state)

        evidence = self.controller._reconcile_pre_stage07_runtime_state()
        saved = yaml.safe_load(self.orch.project_state_path.read_text(encoding="utf-8"))

        self.assertTrue(evidence["repository_initialized"])
        self.assertTrue(evidence["branch"])
        self.assertTrue(evidence["head_commit"])
        self.assertEqual(saved["git"]["branch"], evidence["branch"])
        self.assertEqual(saved["git"]["head_commit"], evidence["head_commit"])
        self.assertIsNone(saved["git"]["last_verified_commit"])
        self.assertFalse(saved["blocking"]["is_blocked"])
        self.assertEqual(saved["blocking"]["reasons"], [])

    def test_reconcile_preserves_current_authority_blockers(self):
        authority = self.orch.authority_state
        authority["blocking_tbds"] = ["BTBD-123"]
        self.orch._save_yaml(self.orch.authority_state_path, authority)
        self.orch.authority_state = authority

        self.controller._reconcile_pre_stage07_runtime_state()
        saved = yaml.safe_load(self.orch.project_state_path.read_text(encoding="utf-8"))
        self.assertTrue(saved["blocking"]["is_blocked"])
        self.assertIn("BLOCKING_TBD:BTBD-123", saved["blocking"]["reasons"])

    def test_non_stage09_schema_classification_is_null_only(self):
        req = StageExecutionRequest(
            stage_id="07", stage_name="GATE", stage_type="GATE", core_question="gate",
            contract={"outputs": {"files": ["docs/handoff/pre-implementation-gate-report.md"]},
                      "result_vocabulary": ["PASS", "FAIL", "INCOMPLETE"]},
            artifacts={}, semantic_inputs={}, runtime_inputs={}, stage_instructions="test",
        )
        schema = _result_schema(req)
        self.assertEqual(schema["properties"]["classification"]["enum"], [None])

    def test_reasoning_checkpoint_includes_project_state_and_leaves_clean_tree(self):
        artifact = self.repo / "docs" / "Design.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("# Design\n", encoding="utf-8")
        state = self.orch.project_state
        state["lifecycle"]["current_stage"] = "05"
        self.orch._save_yaml(self.orch.project_state_path, state)

        commit = self.controller._checkpoint_reasoning_stage("04", {"written_artifacts": ["docs/Design.md"]})
        self.assertTrue(commit)
        status = git(self.repo, "status", "--short")
        self.assertEqual(status, "")
        names = set(git(self.repo, "show", "--pretty=", "--name-only", commit).splitlines())
        self.assertIn("docs/Design.md", names)
        self.assertIn(".sdd/state/project-state.yaml", names)


if __name__ == "__main__":
    unittest.main()
