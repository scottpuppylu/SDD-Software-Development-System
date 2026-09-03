from pathlib import Path
from types import SimpleNamespace
import json
import shutil
import subprocess
import tempfile
import unittest
import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import Stage08CodexRunner
from sdd_orchestrator.system_controller import FullSystemController

SOURCE = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


class NoopReasoning:
    def execute(self, request):
        raise AssertionError("reasoning should not be called")


class V116Stage07PreflightRerunTests(unittest.TestCase):
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

    def _seed_previous_failed_gate_and_dirty_runs(self):
        state = self.orch.project_state
        state["lifecycle"]["current_stage"] = "07"
        state["lifecycle"]["current_stage_name"] = "PRE_IMPLEMENTATION_GATE"
        state["lifecycle"]["next_action"] = "REMEDIATION_ROUTER"
        state["stages"]["07"]["status"] = "DONE"
        state["stages"]["07"]["result"] = "FAIL"
        state["authorizations"]["implementation"] = False
        state.setdefault("provenance", {})["stage08_authorization_created"] = True
        state["blocking"]["is_blocked"] = False
        state["blocking"]["reasons"] = []
        self.orch._save_yaml(self.orch.project_state_path, state)
        runs = self.repo / ".sdd" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        for sid in ("04", "05", "06", "07"):
            (runs / f"prior-stage-{sid}.json").write_text(json.dumps({"stage": sid}), encoding="utf-8")

    def test_preflight_commits_runtime_bookkeeping_and_resets_gate_attempt(self):
        self._seed_previous_failed_gate_and_dirty_runs()
        evidence = self.controller._reconcile_pre_stage07_runtime_state()
        saved = yaml.safe_load(self.orch.project_state_path.read_text(encoding="utf-8"))

        self.assertEqual(saved["stages"]["07"]["status"], "IN_PROGRESS")
        self.assertIsNone(saved["stages"]["07"]["result"])
        self.assertFalse(saved["authorizations"]["implementation"])
        self.assertFalse(saved["provenance"]["stage08_authorization_created"])
        self.assertTrue(evidence["stage08_provenance_reconciliation"]["changed"])
        self.assertEqual(saved["lifecycle"]["next_action"], "RERUN_STAGE")
        self.assertTrue(evidence["preflight_reconciliation_commit"])
        self.assertTrue(evidence["working_tree_clean"])
        self.assertEqual(evidence["dirty_paths"], [])
        self.assertEqual(git(self.repo, "status", "--short"), "")
        names = set(git(self.repo, "show", "--pretty=", "--name-only", evidence["preflight_reconciliation_commit"]).splitlines())
        self.assertIn(".sdd/state/project-state.yaml", names)
        self.assertTrue(any(name.startswith(".sdd/runs/") for name in names))

    def test_preflight_does_not_hide_unrelated_source_dirtiness(self):
        self._seed_previous_failed_gate_and_dirty_runs()
        src = self.repo / "src" / "todo.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("dirty = True\n", encoding="utf-8")
        evidence = self.controller._reconcile_pre_stage07_runtime_state()
        self.assertFalse(evidence["working_tree_clean"])
        self.assertIn("src/todo.py", evidence["dirty_paths"])
        self.assertIn("src/todo.py", evidence["unrelated_dirty_paths"])
        self.assertTrue(evidence["preflight_reconciliation_commit"])
        self.assertTrue(git(self.repo, "status", "--short").startswith("?? src"))

    def test_reasoning_checkpoint_commits_current_run_record(self):
        artifact = self.repo / "docs" / "Design.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("# Design\n", encoding="utf-8")
        state = self.orch.project_state
        state["lifecycle"]["current_stage"] = "05"
        self.orch._save_yaml(self.orch.project_state_path, state)
        runs = self.repo / ".sdd" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "stage04.json").write_text("{}\n", encoding="utf-8")

        commit = self.controller._checkpoint_reasoning_stage("04", {"written_artifacts": ["docs/Design.md"]})
        self.assertTrue(commit)
        self.assertEqual(git(self.repo, "status", "--short"), "")
        names = set(git(self.repo, "show", "--pretty=", "--name-only", commit).splitlines())
        self.assertIn("docs/Design.md", names)
        self.assertIn(".sdd/state/project-state.yaml", names)
        self.assertIn(".sdd/runs/stage04.json", names)


if __name__ == "__main__":
    unittest.main()
