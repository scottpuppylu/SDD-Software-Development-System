from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess
import tempfile
import unittest
import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import (
    TaskFileParser,
    Stage08CodexRunner,
    CodexAdapterError,
    NoExecutableTaskError,
    VerificationCommandPolicy,
)

SOURCE = Path(__file__).resolve().parents[1]


class FakeCodex:
    def __init__(self, callback):
        self.callback = callback
        self.prompts = []

    def execute(self, repo_root: Path, prompt: str):
        self.prompts.append(prompt)
        return self.callback(repo_root, prompt)


def run_git(repo: Path, *args):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


class M6CodexAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE / ".sdd", self.repo / ".sdd")
        for rel, text in {
            "AGENTS.md": "# AGENTS\nDo not modify authoritative contracts.\n",
            "docs/PRD.md": "# PRD\nFR-001 Calculator addition\n",
            "docs/spec.md": "# Spec\nSPEC-001 add(a,b) returns sum\n",
            "docs/Design.md": "# Design\nDES-001 Python calculator module\n",
        }.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        run_git(self.repo, "init")
        run_git(self.repo, "config", "user.email", "test@example.com")
        run_git(self.repo, "config", "user.name", "Test")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "initial")
        self._authorize_stage08()

    def tearDown(self):
        self.tmp.cleanup()

    def _authorize_stage08(self):
        p = self.repo / ".sdd/state/project-state.yaml"
        state = yaml.safe_load(p.read_text(encoding="utf-8"))
        state["stages"]["07"]["status"] = "DONE"
        state["stages"]["07"]["result"] = "PASS"
        state["authorizations"]["implementation"] = True
        state["lifecycle"]["current_stage"] = "08"
        state["lifecycle"]["current_stage_name"] = "IMPLEMENTATION_RUNNER"
        p.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    def _write_tasks(self, body: str):
        (self.repo / "tasks.md").write_text(body, encoding="utf-8")
        run_git(self.repo, "add", "tasks.md", ".sdd/state/project-state.yaml")
        run_git(self.repo, "commit", "-m", "authorize stage08")

    def test_task_parser_extracts_scope_and_verification(self):
        text = '''\n### T001 — Add calculator\n- **Status:** TODO\n- **Traceability:** FR-001 → SPEC-001 → DES-001\n- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`\n- **Implementation Scope:** Implement the calculator task within the declared files.\n- **Verification Commands:** `python -m pytest -q`\n'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(task.task_id, "T001")
        self.assertEqual(task.allowed_paths, ["src/calculator.py", "tests/test_calculator.py"])
        self.assertEqual(task.verification_commands, ["python -m pytest -q"])

    def test_verification_policy_rejects_shell_chaining(self):
        with self.assertRaises(CodexAdapterError):
            VerificationCommandPolicy.argv("pytest && rm -rf .")

    def test_preflight_requires_explicit_scope(self):
        self._write_tasks('''\n### T001 — vague\n- **Status:** TODO\n- **Verification Commands:** `python -m pytest -q`\n''')
        orch = Orchestrator(self.repo)
        runner = Stage08CodexRunner(orch, codex=FakeCodex(lambda *_: None))
        with self.assertRaises(CodexAdapterError):
            runner.preflight(runner.select_task())

    def test_codex_scope_violation_is_rejected(self):
        self._write_tasks('''\n### T001 — Add calculator\n- **Status:** TODO\n- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`\n- **Implementation Scope:** Implement the calculator task within the declared files.\n- **Verification Commands:** `python -m pytest -q`\n''')
        def callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
            (repo / "README.md").write_text("unauthorized\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="done", stderr="")
        orch = Orchestrator(self.repo)
        runner = Stage08CodexRunner(orch, codex=FakeCodex(callback))
        with self.assertRaises(CodexAdapterError):
            runner.execute_one("T001")
        self.assertTrue((self.repo / "README.md").exists())
        self.assertNotIn("README.md", run_git(self.repo, "show", "--name-only", "--pretty=format:", "HEAD"))

    def test_successful_task_verifies_and_checkpoints(self):
        self._write_tasks('''\n### T001 — Add calculator\n- **Status:** TODO\n- **Traceability:** FR-001 → SPEC-001 → DES-001\n- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`\n- **Implementation Scope:** Implement the calculator task within the declared files.\n- **Verification Commands:** `python -m pytest -q`\n''')
        def callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\ndef test_add():\n    assert add(2,3) == 5\n", encoding="utf-8"
            )
            return SimpleNamespace(returncode=0, stdout="implemented", stderr="")
        orch = Orchestrator(self.repo)
        fake = FakeCodex(callback)
        runner = Stage08CodexRunner(orch, codex=fake)
        result = runner.execute_one("T001")
        self.assertEqual(result.status, "DONE")
        self.assertIsNotNone(result.checkpoint_commit)
        self.assertTrue(all(v.passed for v in result.verification))
        subject = run_git(self.repo, "log", "-1", "--pretty=%s")
        self.assertIn("[T001]", subject)
        self.assertIn("do not commit", fake.prompts[0].lower())

    def test_failed_verification_never_commits(self):
        self._write_tasks('''\n### T001 — Broken calculator\n- **Status:** TODO\n- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`\n- **Implementation Scope:** Implement the calculator task within the declared files.\n- **Verification Commands:** `python -m pytest -q`\n''')
        before = run_git(self.repo, "rev-parse", "HEAD")
        def callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text("def add(a,b): return 0\n", encoding="utf-8")
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\ndef test_add():\n    assert add(2,3) == 5\n", encoding="utf-8"
            )
            return SimpleNamespace(returncode=0, stdout="implemented", stderr="")
        orch = Orchestrator(self.repo)
        runner = Stage08CodexRunner(orch, codex=FakeCodex(callback))
        result = runner.execute_one("T001")
        self.assertEqual(result.status, "VERIFICATION_FAILED")
        self.assertIsNone(result.checkpoint_commit)
        self.assertEqual(before, run_git(self.repo, "rev-parse", "HEAD"))

    def test_verification_failed_authorized_dirty_files_can_resume_and_checkpoint(self):
        self._write_tasks('''
### T001 ? Resume failed calculator
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        before = run_git(self.repo, "rev-parse", "HEAD")

        def broken_callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return 0\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(
                returncode=0, stdout="implemented but broken", stderr=""
            )

        runner = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(broken_callback)
        )
        first = runner.execute_one("T001")

        self.assertEqual(first.status, "VERIFICATION_FAILED")
        self.assertIsNone(first.checkpoint_commit)
        self.assertEqual(before, run_git(self.repo, "rev-parse", "HEAD"))
        self.assertTrue((self.repo / "src/calculator.py").is_file())
        self.assertTrue((self.repo / "tests/test_calculator.py").is_file())
        failed_status = run_git(
            self.repo, "status", "--short", "--untracked-files=all"
        )
        self.assertIn("src/calculator.py", failed_status)
        self.assertIn("tests/test_calculator.py", failed_status)
        failed_head_paths = run_git(
            self.repo, "show", "--name-only", "--pretty=format:", "HEAD"
        )
        self.assertNotIn("src/calculator.py", failed_head_paths)
        self.assertNotIn("tests/test_calculator.py", failed_head_paths)

        def fixed_callback(repo, prompt):
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            return SimpleNamespace(returncode=0, stdout="fixed", stderr="")

        resumed_runner = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(fixed_callback)
        )
        second = resumed_runner.execute_one("T001")

        self.assertEqual(second.status, "DONE")
        self.assertIsNotNone(second.checkpoint_commit)
        self.assertTrue(all(v.passed for v in second.verification))
        self.assertNotEqual(before, run_git(self.repo, "rev-parse", "HEAD"))
        checkpoint_paths = run_git(
            self.repo,
            "show",
            "--name-only",
            "--pretty=format:",
            second.checkpoint_commit,
        )
        self.assertIn("src/calculator.py", checkpoint_paths)
        self.assertIn("tests/test_calculator.py", checkpoint_paths)
        final_status = run_git(self.repo, "status", "--short")
        self.assertNotIn("src/calculator.py", final_status)
        self.assertNotIn("tests/test_calculator.py", final_status)

    def test_codex_failure_never_commits_and_records_evidence(self):
        self._write_tasks('''\n### T001 ??Codex failure
- **Status:** TODO
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Implement the calculator task within the declared files.
- **Verification Commands:** `python -m pytest -q`
''')
        before = run_git(self.repo, "rev-parse", "HEAD")
        callback = lambda *_: SimpleNamespace(returncode=1, stdout="", stderr="codex failed")
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=FakeCodex(callback))

        result = runner.execute_one("T001")

        self.assertEqual(result.status, "CODEX_FAILED")
        self.assertIsNone(result.checkpoint_commit)
        self.assertEqual(before, run_git(self.repo, "rev-parse", "HEAD"))
        self.assertIsNotNone(result.evidence_file)
        self.assertTrue((self.repo / result.evidence_file).is_file())
        self.assertEqual(result.verification, [])

    def test_successful_codex_with_no_changes_never_commits_and_records_evidence(self):
        self._write_tasks('''\n### T001 ??No changes
- **Status:** TODO
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Implement the calculator task within the declared files.
- **Verification Commands:** `python -m pytest -q`
''')
        before = run_git(self.repo, "rev-parse", "HEAD")
        callback = lambda *_: SimpleNamespace(returncode=0, stdout="nothing to change", stderr="")
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=FakeCodex(callback))

        result = runner.execute_one("T001")

        self.assertEqual(result.status, "NO_CHANGES")
        self.assertIsNone(result.checkpoint_commit)
        self.assertEqual(before, run_git(self.repo, "rev-parse", "HEAD"))
        self.assertIsNotNone(result.evidence_file)
        self.assertTrue((self.repo / result.evidence_file).is_file())
        self.assertEqual(result.verification, [])

    def test_stage08_completion_transitions_only_to_verification(self):
        self._write_tasks('''\n### T001 — Add calculator\n- **Status:** TODO\n- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`\n- **Implementation Scope:** Implement the calculator task within the declared files.\n- **Verification Commands:** `python -m pytest -q`\n''')
        def callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\ndef test_add():\n    assert add(1,2) == 3\n", encoding="utf-8"
            )
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")
        orch = Orchestrator(self.repo)
        runner = Stage08CodexRunner(orch, codex=FakeCodex(callback))
        result = runner.run_until_complete(max_tasks=2)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["transition"]["next"], "09")
        self.assertEqual(orch.project_state["lifecycle"]["current_stage"], "09")
        self.assertIsNone(orch.project_state["stages"]["09"]["result"])

    def test_run_until_complete_with_no_executable_tasks_transitions_to_stage09(self):
        self._write_tasks('''
### T001 ??Already completed
- **Status:** DONE
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Already completed.
- **Verification Commands:** `python -m pytest -q`
''')
        orch = Orchestrator(self.repo)

        def callback(*_):
            raise AssertionError("Codex must not execute")

        fake = FakeCodex(callback)
        runner = Stage08CodexRunner(orch, codex=fake)

        result = runner.run_until_complete()

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["stage"], "08")
        self.assertEqual(result["tasks"], [])
        self.assertEqual(result["transition"]["next"], "09")
        self.assertEqual(orch.project_state["lifecycle"]["current_stage"], "09")
        self.assertEqual(orch.project_state["stages"]["08"]["status"], "DONE")
        self.assertEqual(orch.project_state["stages"]["08"]["result"], "COMPLETED")
        self.assertEqual(orch.project_state["stages"]["09"]["status"], "IN_PROGRESS")
        self.assertIsNone(orch.project_state["stages"]["09"]["result"])
        self.assertEqual(fake.prompts, [])

    def test_select_task_uses_specific_error_when_no_executable_task_remains(self):
        self._write_tasks('''
### T001 ??Already completed
- **Status:** DONE
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Already completed.
- **Verification Commands:** `python -m pytest -q`
''')
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=FakeCodex(lambda *_: None))

        with self.assertRaises(NoExecutableTaskError) as ctx:
            runner.select_task()

        self.assertEqual(str(ctx.exception), "No executable TODO/IN_PROGRESS task remains")
        self.assertTrue(issubclass(NoExecutableTaskError, CodexAdapterError))


if __name__ == "__main__":
    unittest.main()

class V1111CodexExecInvocationTests(unittest.TestCase):
    def test_stage08_codex_exec_omits_removed_approval_flag(self):
        from sdd_orchestrator.codex_adapter import CodexCLI
        cmd = CodexCLI(executable="codex", sandbox="workspace-write").command("implement T001")
        self.assertEqual(cmd[:4], ["codex", "exec", "--sandbox", "workspace-write"])
        self.assertNotIn("--ask-for-approval", cmd)
        self.assertNotIn("--approval-policy", cmd)
        self.assertIn("--ephemeral", cmd)
        self.assertEqual(cmd[-1], "-")
        self.assertNotIn("implement T001", cmd)

class V1116GeneratedVerificationArtifactTests(M6CodexAdapterTests):
    def test_untracked_egg_info_and_pycache_do_not_block_task_resume(self):
        self._write_tasks('''
### T001 — generated artifacts resume
- **Status:** TODO
- **Allowed files:** `src/app.py`
- **Implementation Scope:** bounded
- **Verification Commands:** `python -c "import sys"`
''')
        (self.repo / "src/pkg.egg-info").mkdir(parents=True)
        (self.repo / "src/pkg.egg-info/PKG-INFO").write_text("generated\n", encoding="utf-8")
        (self.repo / "src/__pycache__").mkdir(parents=True)
        (self.repo / "src/__pycache__/app.cpython-312.pyc").write_bytes(b"generated")
        def callback(repo, prompt):
            (repo / "src/app.py").write_text("value = 1\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="done", stderr="")
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=FakeCodex(callback))
        result = runner.execute_one("T001")
        self.assertEqual(result.status, "DONE")

    def test_other_untracked_file_still_blocks(self):
        self._write_tasks('''
### T001 — generated artifacts resume
- **Status:** TODO
- **Allowed files:** `src/app.py`
- **Implementation Scope:** bounded
- **Verification Commands:** `python -c "import sys"`
''')
        (self.repo / "src/pkg.egg-info").mkdir(parents=True)
        (self.repo / "src/pkg.egg-info/PKG-INFO").write_text("generated\n", encoding="utf-8")
        (self.repo / "outside.txt").write_text("not generated\n", encoding="utf-8")
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=FakeCodex(lambda *_: None))
        with self.assertRaises(CodexAdapterError):
            runner.execute_one("T001")
