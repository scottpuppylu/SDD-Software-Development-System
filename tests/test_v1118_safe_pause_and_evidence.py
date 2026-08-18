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

import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import (
    Stage08CodexRunner, CodexAdapterError, TaskFileParser, VerificationCommandPolicy
)
from sdd_orchestrator.system_controller import FullSystemController

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

    def test_heartbeat_reports_long_running_operation(self):
        runner = Stage08CodexRunner(Orchestrator(self.repo), heartbeat_seconds=1)
        buf = StringIO()
        with redirect_stdout(buf):
            value = runner._call_with_heartbeat("T999 still running", lambda: (time.sleep(1.1), 42)[1])
        self.assertEqual(value, 42)
        self.assertIn("T999 still running", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
