from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import (
    Stage08CodexRunner, CodexAdapterError, TaskFileParser, VerificationCommandPolicy
)
from sdd_orchestrator.system_controller import FullSystemController
from sdd_orchestrator.evidence_writer import (
    EvidencePersistenceError,
    EvidenceRecord,
    EvidenceRegistry,
    InvalidEvidence,
    qualification_inputs,
)

SOURCE = Path(__file__).resolve().parents[1]


def run_git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


class FakeCodex:
    def __init__(self, callback):
        self.callback = callback

    def execute(self, repo_root: Path, prompt: str):
        return self.callback(repo_root, prompt)


class V1118Stage08Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE / ".sdd", self.repo / ".sdd")
        (self.repo / ".sdd/evidence/.stage08-pending-evidence-write.yaml").unlink(
            missing_ok=True
        )
        for evidence_file in (self.repo / ".sdd/evidence").glob("*.json"):
            evidence_file.unlink()
        for rel, text in {
            "AGENTS.md": "# AGENTS\n",
            "docs/PRD.md": "# PRD\nFR-001\n",
            "docs/spec.md": "# Spec\nSPEC-001\n",
            "docs/Design.md": "# Design\nDES-001\n",
        }.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        run_git(self.repo, "init")
        run_git(self.repo, "config", "user.email", "test@example.com")
        run_git(self.repo, "config", "user.name", "Test")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "initial")
        state_path = self.repo / ".sdd/state/project-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["stages"]["07"]["status"] = "DONE"
        state["stages"]["07"]["result"] = "PASS"
        state["authorizations"]["implementation"] = True
        state["lifecycle"]["current_stage"] = "08"
        state["lifecycle"]["current_stage_name"] = "IMPLEMENTATION_RUNNER"
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_tasks(self, body: str) -> None:
        (self.repo / "tasks.md").write_text(body, encoding="utf-8")
        run_git(self.repo, "add", "tasks.md", ".sdd/state/project-state.yaml")
        run_git(self.repo, "commit", "-m", "authorize stage08")

    def test_t014_exact_evidence_state_paths_are_task_writable_and_checkpointed(self):
        self._write_tasks('''
### T014 — Build Stage 09 evidence index
- **Status:** TODO
- **Allowed evidence files:** `.sdd/state/implementation-state.md`, `.sdd/state/post-implementation-verification.md`
- **Verification Commands:** `python -c "import sys"`
''')

        def callback(repo: Path, prompt: str):
            (repo / ".sdd/state/implementation-state.md").write_text("implementation evidence\n", encoding="utf-8")
            (repo / ".sdd/state/post-implementation-verification.md").write_text("verification evidence\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="done", stderr="")

        runner = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(callback), heartbeat_seconds=0
        )
        result = runner.execute_one("T014")
        self.assertEqual(result.status, "DONE")
        self.assertIn(".sdd/state/implementation-state.md", result.changed_paths)
        self.assertIn(".sdd/state/post-implementation-verification.md", result.changed_paths)
        committed = run_git(self.repo, "show", "--name-only", "--pretty=format:", result.checkpoint_commit)
        self.assertIn(".sdd/state/implementation-state.md", committed)
        self.assertIn(".sdd/state/post-implementation-verification.md", committed)

    def test_other_sdd_state_file_remains_protected(self):
        self._write_tasks('''
### T001 — Illegal runtime state write
- **Status:** TODO
- **Allowed files:** `.sdd/state/project-state.yaml`
- **Verification Commands:** `python -c "import sys"`
''')
        runner = Stage08CodexRunner(Orchestrator(self.repo), heartbeat_seconds=0)
        with self.assertRaisesRegex(CodexAdapterError, "protected authoritative artifacts"):
            runner.preflight(runner.select_task("T001"))

    def test_one_task_limit_returns_explicit_safe_stop_at_checkpoint_boundary(self):
        self._write_tasks('''
### T001 — First task
- **Status:** TODO
- **Allowed files:** `src/one.py`
- **Verification Commands:** `python -c "import sys"`

### T002 — Second task
- **Status:** TODO
- **Allowed files:** `src/two.py`
- **Verification Commands:** `python -c "import sys"`
''')

        def callback(repo: Path, prompt: str):
            (repo / "src").mkdir(exist_ok=True)
            if "T001" in prompt:
                (repo / "src/one.py").write_text("ONE = 1\n", encoding="utf-8")
            else:
                (repo / "src/two.py").write_text("TWO = 2\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="done", stderr="")

        runner = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(callback), heartbeat_seconds=0
        )
        buf = StringIO()
        with redirect_stdout(buf):
            result = runner.run_until_complete(max_tasks=1)
        self.assertEqual(result["status"], "SAFE_STOP")
        self.assertTrue(result["safe_to_stop"])
        self.assertEqual(result["last_completed_task"], "T001")
        self.assertEqual(result["next_task"], "T002")
        self.assertEqual(runner.orchestrator.project_state["lifecycle"]["current_stage"], "08")
        self.assertIn("SAFE TO STOP", buf.getvalue())

    def test_controller_one_step_preserves_completed_transition_for_final_task(self):
        self._write_tasks('''
### T001 ??Only task
- **Status:** TODO
- **Allowed files:** `src/only.py`
- **Verification Commands:** `python -c "import sys"`
''')

        def callback(repo: Path, prompt: str):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "src/only.py").write_text("ONLY = 1\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="done", stderr="")

        orchestrator = Orchestrator(self.repo)
        runner = Stage08CodexRunner(
            orchestrator, codex=FakeCodex(callback), heartbeat_seconds=0
        )
        controller = FullSystemController(orchestrator, SimpleNamespace(), runner)

        result = controller.run(max_steps=1)

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.end_stage, "09")
        self.assertEqual(result.events[0]["status"], "COMPLETED")
        self.assertEqual(result.events[0]["transition"]["next"], "09")
        self.assertNotIn("safe_to_stop", result.events[0])
        self.assertNotIn("next_task", result.events[0])


    def test_t014_read_only_git_verification_commands_are_preserved_and_allowlisted(self):
        text = """
### T014 — Evidence index
- **Status:** TODO
- **Allowed evidence files:** `.sdd/state/implementation-state.md`
- **Verification Commands:**
  1. `python -m pytest tests/unit tests/contract tests/integration tests/e2e -q`
  2. `git status --short`
  3. `git log --oneline --decorate -20`
  4. `git diff --check`
"""
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(len(task.verification_commands), 4)
        for command in task.verification_commands:
            self.assertTrue(VerificationCommandPolicy.argv(command))
        with self.assertRaises(CodexAdapterError):
            VerificationCommandPolicy.argv("git reset --hard")

    def test_exact_repository_venv_launcher_is_narrowly_allowlisted(self):
        command = r".\.venv\Scripts\python.exe -m pytest -q tests/test_app.py"
        argv = VerificationCommandPolicy.argv(command)
        self.assertEqual(argv[0], r".\.venv\Scripts\python.exe")
        self.assertEqual(argv[1:], ["-m", "pytest", "-q", "tests/test_app.py"])

        rejected = (
            r".venv\Scripts\python.exe -m pytest -q tests",
            r"..\.venv\Scripts\python.exe -m pytest -q tests",
            r"C:\repo\.venv\Scripts\python.exe -m pytest -q tests",
            r".\other-venv\Scripts\python.exe -m pytest -q tests",
            r".\.venv\Scripts\other.exe -m pytest -q tests",
            r".\.venv\Scripts\python.exe -c import_os",
            r".\.venv\Scripts\python.exe -m pip install pytest",
            r".\.venv\Scripts\python.exe -m unittest tests",
            r".\.venv\Scripts\python.exe -m pytest",
            r"powershell .\.venv\Scripts\python.exe -m pytest tests",
            r"cmd /c .\.venv\Scripts\python.exe -m pytest tests",
            r".\.venv\Scripts\python.exe -m pytest tests && echo bad",
            r".\.venv\Scripts\python.exe -m pytest tests | more",
            r".\.venv\Scripts\python.exe -m pytest tests > result.txt",
        )
        for candidate in rejected:
            with self.subTest(candidate=candidate), self.assertRaises(CodexAdapterError):
                VerificationCommandPolicy.argv(candidate)

    def test_heartbeat_reports_long_running_operation(self):
        runner = Stage08CodexRunner(Orchestrator(self.repo), heartbeat_seconds=1)
        buf = StringIO()
        with redirect_stdout(buf):
            value = runner._call_with_heartbeat("T999 still running", lambda: (time.sleep(1.1), 42)[1])
        self.assertEqual(value, 42)
        self.assertIn("T999 still running", buf.getvalue())


class T008EvidenceRegistryTests(unittest.TestCase):
    def record(self, **changes):
        values = dict(
            check_id="TEST-008", criterion="behavior is satisfied", scope="TASK-008",
            executed=True, outcome="PASS", evidence_reference="pytest://TEST-008",
            evidence_gap=None, coverage_links=("TASK-008", "SPEC-008"),
            evidence_version="abc", current_version="abc", relevant=True,
            regression_risk="No known regression risk", required=True,
        )
        values.update(changes)
        return EvidenceRecord(**values)

    def test_truthful_three_outcomes_and_metadata(self):
        self.assertTrue(self.record().qualifies)
        self.assertFalse(self.record(outcome="FAIL").qualifies)
        not_run = self.record(executed=False, outcome="NOT RUN", evidence_reference=None, evidence_gap="tool unavailable")
        self.assertFalse(not_run.qualifies)
        for changes in (
            {"outcome": "SKIP"},
            {"outcome": "PASS", "executed": False},
            {"outcome": "NOT RUN", "executed": False, "evidence_reference": None, "evidence_gap": None},
            {"coverage_links": ()},
        ):
            with self.subTest(changes=changes), self.assertRaises(InvalidEvidence):
                self.record(**changes)

    def test_stale_irrelevant_partial_and_security_gaps_withhold_inputs(self):
        records = (
            self.record(check_id="pass"),
            self.record(check_id="stale", evidence_version="old", regression_risk="version mismatch"),
            self.record(check_id="irrelevant", relevant=False, regression_risk="scope uncovered"),
            self.record(check_id="security", executed=False, outcome="NOT RUN", evidence_reference=None,
                        evidence_gap="security suite absent", security_related=True, regression_risk="security unknown"),
        )
        result = qualification_inputs(records)
        self.assertFalse(result.evidence_complete)
        self.assertFalse(result.coverage_complete)
        self.assertFalse(result.current_and_relevant)
        self.assertFalse(result.security_evidence_complete)
        self.assertIsNone(result.verification_decision)
        self.assertIsNone(result.release_decision)
        self.assertEqual(len(result.gaps), 3)
        self.assertIn("security unknown", result.regression_risks)

    def test_registry_appends_history_without_overwriting_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = EvidenceRegistry(Path(directory) / "registry.json")
            registry.append(self.record(outcome="FAIL"))
            registry.append(self.record(evidence_reference="pytest://TEST-008/retry"))
            loaded = registry.load()
            self.assertEqual([item.outcome for item in loaded], ["FAIL", "PASS"])
            self.assertEqual(len(loaded), 2)

    def test_registry_failure_is_explicit_and_preserves_prior_state(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = EvidenceRegistry(Path(directory) / "registry.json")
            registry.append(self.record(outcome="FAIL"))
            before = registry.path.read_bytes()
            with patch("pathlib.Path.replace", side_effect=OSError("disk failure")):
                with self.assertRaises(EvidencePersistenceError):
                    registry.append(self.record(evidence_reference="pytest://retry"))
            self.assertEqual(registry.path.read_bytes(), before)

    def test_sensitive_evidence_reference_is_rejected(self):
        with self.assertRaises(InvalidEvidence):
            self.record(evidence_reference="api_key=do-not-store")


if __name__ == "__main__":
    unittest.main()
