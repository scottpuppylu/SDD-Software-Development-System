from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import (
    TaskFileParser,
    Stage08CodexRunner,
    CodexAdapterError,
    NoExecutableTaskError,
    VerificationCommandPolicy,
)
from sdd_orchestrator.git_runtime import GitRuntimeError

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

    def test_checkpoint_failure_does_not_report_task_done_or_advance_recovery_state(self):
        self._write_tasks('''
### T001 ? Checkpoint failure
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        before_head = run_git(self.repo, "rev-parse", "HEAD")
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        before_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))

        def callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(
                returncode=0, stdout="implemented", stderr=""
            )

        fake = FakeCodex(callback)
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)

        with patch.object(
            runner.git,
            "checkpoint",
            side_effect=GitRuntimeError("simulated checkpoint failure"),
        ):
            with self.assertRaisesRegex(
                GitRuntimeError, "simulated checkpoint failure"
            ):
                runner.execute_one("T001")

        self.assertEqual(before_head, run_git(self.repo, "rev-parse", "HEAD"))
        self.assertNotIn(
            "[T001]", run_git(self.repo, "log", "--pretty=%s", f"{before_head}..HEAD")
        )
        status = run_git(
            self.repo, "status", "--short", "--untracked-files=all"
        )
        self.assertIn("src/calculator.py", status)
        self.assertIn("tests/test_calculator.py", status)
        self.assertEqual(len(fake.prompts), 1)

        evidence_files = sorted((self.repo / ".sdd/evidence").glob("*-T001.json"))
        self.assertEqual(len(evidence_files), 1)
        evidence = json.loads(evidence_files[0].read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["verification"])
        self.assertTrue(all(item["passed"] for item in evidence["verification"]))
        self.assertNotIn("checkpoint_commit", evidence)

        after_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        self.assertEqual(after_state, before_state)
        self.assertNotEqual(after_state.get("last_completed_task"), "T001")
        self.assertNotEqual(after_state.get("last_verified_commit"), before_head)

    def test_evidence_write_failure_before_checkpoint_resumes_without_rerunning_codex(self):
        self._write_tasks('''
### T001 ? Evidence write failure
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        before_head = run_git(self.repo, "rev-parse", "HEAD")
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        before_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        convergence_path = self.repo / ".sdd/convergence/T001.yaml"

        calls = 0

        def implement(repo, _prompt):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise AssertionError(
                    "Codex implementation must not rerun after evidence write failure"
                )
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="implemented", stderr="")

        fake = FakeCodex(implement)
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)

        with patch.object(
            runner,
            "_write_evidence",
            side_effect=RuntimeError("simulated evidence write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated evidence write failure"
            ):
                runner.execute_one("T001")

        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), before_head)
        self.assertEqual(
            run_git(self.repo, "log", "--format=%s").count("[T001]"), 0
        )
        dirty = run_git(
            self.repo, "status", "--short", "--untracked-files=all"
        )
        self.assertIn("src/calculator.py", dirty)
        self.assertIn("tests/test_calculator.py", dirty)
        self.assertEqual(TaskFileParser(
            (self.repo / "tasks.md").read_text(encoding="utf-8")
        ).parse()[0].status, "TODO")
        self.assertEqual(
            yaml.safe_load(state_path.read_text(encoding="utf-8")), before_state
        )
        self.assertNotEqual(before_state.get("last_completed_task"), "T001")
        self.assertFalse(convergence_path.exists())
        self.assertEqual(calls, 1)

        result = runner.execute_one("T001")

        self.assertEqual(result.status, "DONE")
        self.assertEqual(calls, 1)

    def test_fresh_runner_recovers_evidence_write_failure_before_checkpoint_without_rerunning_codex(self):
        self._write_tasks('''
### T001 ? Fresh runner evidence recovery
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        before_head = run_git(self.repo, "rev-parse", "HEAD")
        calls = 0

        def implement(repo, _prompt):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise AssertionError(
                    "Codex implementation must not rerun during fresh-runner recovery"
                )
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="implemented", stderr="")

        fake = FakeCodex(implement)
        first = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)

        with patch.object(
            first,
            "_write_evidence",
            side_effect=RuntimeError("simulated evidence write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated evidence write failure"
            ):
                first.execute_one("T001")

        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), before_head)
        self.assertEqual(
            TaskFileParser(
                (self.repo / "tasks.md").read_text(encoding="utf-8")
            ).parse()[0].status,
            "TODO",
        )
        dirty = run_git(
            self.repo, "status", "--short", "--untracked-files=all"
        )
        self.assertIn("src/calculator.py", dirty)
        self.assertIn("tests/test_calculator.py", dirty)
        self.assertEqual(calls, 1)

        first = None
        fresh = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)
        result = fresh.execute_one("T001")

        self.assertEqual(result.status, "DONE")
        self.assertIsNotNone(result.checkpoint_commit)
        self.assertEqual(calls, 1)

    def test_fresh_runner_retry_after_post_write_evidence_failure_does_not_duplicate_pass_evidence(self):
        self._write_tasks('''
### T001 ? Post-write evidence failure
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        before_head = run_git(self.repo, "rev-parse", "HEAD")
        calls = 0

        def implement(repo, _prompt):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise AssertionError(
                    "Codex implementation must not rerun after PASS evidence was written"
                )
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="implemented", stderr="")

        fake = FakeCodex(implement)
        first = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)
        original_write_evidence = first._write_evidence

        def write_then_throw(*args, **kwargs):
            evidence_path = original_write_evidence(*args, **kwargs)
            self.assertTrue((self.repo / evidence_path).is_file())
            raise RuntimeError("simulated post-write evidence failure")

        with patch.object(first, "_write_evidence", side_effect=write_then_throw):
            with self.assertRaisesRegex(
                RuntimeError, "simulated post-write evidence failure"
            ):
                first.execute_one("T001")

        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), before_head)
        self.assertEqual(
            run_git(self.repo, "log", "--format=%s", f"{before_head}..HEAD").count("[T001]"),
            0,
        )
        self.assertEqual(
            TaskFileParser(
                (self.repo / "tasks.md").read_text(encoding="utf-8")
            ).parse()[0].status,
            "TODO",
        )
        first_pass_evidence = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (self.repo / ".sdd/evidence").glob("*-T001.json")
        ]
        self.assertEqual(len(first_pass_evidence), 1)
        self.assertEqual(first_pass_evidence[0]["task_id"], "T001")
        self.assertEqual(first_pass_evidence[0]["status"], "PASS")
        self.assertTrue(first_pass_evidence[0]["verification"])
        self.assertTrue(
            all(item["passed"] for item in first_pass_evidence[0]["verification"])
        )
        self.assertEqual(calls, 1)

        fresh = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)
        result = fresh.execute_one("T001")

        self.assertEqual(result.status, "DONE")
        self.assertIsNotNone(result.checkpoint_commit)
        self.assertEqual(calls, 1)
        pass_evidence = []
        for path in (self.repo / ".sdd/evidence").glob("*-T001.json"):
            evidence = json.loads(path.read_text(encoding="utf-8"))
            if evidence.get("task_id") == "T001" and evidence.get("status") == "PASS":
                pass_evidence.append(evidence)
        self.assertEqual(len(pass_evidence), 1)
        self.assertEqual(
            run_git(self.repo, "log", "--format=%s", f"{before_head}..HEAD").count("[T001]"),
            1,
        )
        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), result.checkpoint_commit)

    def test_recovery_state_failure_after_checkpoint_exposes_split_brain_without_false_done(self):
        self._write_tasks('''
### T001 ? Recovery state failure
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        before_head = run_git(self.repo, "rev-parse", "HEAD")
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        before_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        recovery_fields = (
            "last_completed_task",
            "current_task",
            "next_task",
            "last_verified_commit",
            "test_status",
        )

        def callback(repo, prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(
                returncode=0, stdout="implemented", stderr=""
            )

        fake = FakeCodex(callback)
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)
        result = None

        with patch.object(
            runner.recovery,
            "record_checkpoint",
            side_effect=RuntimeError("simulated recovery state write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated recovery state write failure"
            ):
                result = runner.execute_one("T001")

        self.assertIsNone(result)
        self.assertEqual(len(fake.prompts), 1)

        after_head = run_git(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(after_head, before_head)
        checkpoint_paths = run_git(
            self.repo, "show", "--name-only", "--pretty=format:", "HEAD"
        ).splitlines()
        self.assertIn("src/calculator.py", checkpoint_paths)
        self.assertIn("tests/test_calculator.py", checkpoint_paths)

        evidence_paths = [
            path for path in checkpoint_paths
            if path.startswith(".sdd/evidence/") and path.endswith("-T001.json")
        ]
        self.assertEqual(len(evidence_paths), 1)
        evidence = json.loads(
            (self.repo / evidence_paths[0]).read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(evidence["verification"])
        self.assertTrue(all(item["passed"] for item in evidence["verification"]))

        after_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        for field in recovery_fields:
            self.assertEqual(after_state.get(field), before_state.get(field))
        if before_state.get("last_completed_task") != "T001":
            self.assertNotEqual(after_state.get("last_completed_task"), "T001")
        if before_state.get("last_verified_commit") != after_head:
            self.assertNotEqual(after_state.get("last_verified_commit"), after_head)

        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), after_head)
        self.assertNotEqual(after_state.get("last_verified_commit"), after_head)
        status = run_git(
            self.repo, "status", "--short", "--untracked-files=all"
        )
        self.assertNotIn("src/calculator.py", status)
        self.assertNotIn("tests/test_calculator.py", status)
        self.assertNotIn(evidence_paths[0], status)

    def test_fresh_runner_reconciles_committed_pass_checkpoint_after_recovery_state_failure(self):
        self._write_tasks('''
### T001 ? Recover checkpoint
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        stale_state = state_path.read_text(encoding="utf-8")

        def implement(repo, _prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/calculator.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_calculator.py").write_text(
                "from src.calculator import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="implemented", stderr="")

        first = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(implement)
        )
        with patch.object(
            first.recovery,
            "record_checkpoint",
            side_effect=RuntimeError("simulated recovery state write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated recovery state write failure"
            ):
                first.execute_one("T001")

        recovered_head = run_git(self.repo, "rev-parse", "HEAD")
        checkpoint_paths = run_git(
            self.repo, "show", "--name-only", "--pretty=format:", "HEAD"
        ).splitlines()
        evidence_paths = [
            path for path in checkpoint_paths
            if path.startswith(".sdd/evidence/") and path.endswith("-T001.json")
        ]
        self.assertEqual(len(evidence_paths), 1)
        evidence_path = evidence_paths[0]
        committed_evidence = run_git(
            self.repo, "show", f"{recovered_head}:{evidence_path}"
        )
        self.assertEqual(state_path.read_text(encoding="utf-8"), stale_state)

        def must_not_run(*_):
            raise AssertionError(
                "Codex must not rerun an already checkpointed task during reconciliation"
            )

        fake = FakeCodex(must_not_run)
        fresh = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)
        result = fresh.execute_one("T001")
        state_after_first = state_path.read_text(encoding="utf-8")
        repeated = fresh.execute_one("T001")

        self.assertEqual(result.status, "DONE")
        self.assertEqual(repeated.status, "DONE")
        self.assertEqual(fake.prompts, [])
        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), recovered_head)
        self.assertEqual(
            run_git(self.repo, "log", "--format=%s").count("[T001]"), 1
        )
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["last_completed_task"], "T001")
        self.assertEqual(state["last_verified_commit"], recovered_head)
        self.assertEqual(state["test_status"]["overall"], "PASS")
        self.assertIsNone(state["current_task"])
        self.assertIsNone(state["next_task"])
        self.assertEqual(state_path.read_text(encoding="utf-8"), state_after_first)
        self.assertEqual(
            run_git(self.repo, "show", f"{recovered_head}:{evidence_path}"),
            committed_evidence,
        )
        self.assertEqual(
            len(list((self.repo / ".sdd/evidence").glob("*-T001.json"))), 1
        )
        status = run_git(self.repo, "status", "--short", "--untracked-files=all")
        self.assertNotIn("src/calculator.py", status)
        self.assertNotIn("tests/test_calculator.py", status)
        self.assertNotIn(evidence_path, status)

    def test_fresh_runner_reconciliation_repairs_tc_convergence_after_recovery_state_failure(self):
        self._write_tasks("# Tasks\n")
        convergence_path = self.repo / ".sdd/convergence/TC001.yaml"
        convergence_path.parent.mkdir(parents=True, exist_ok=True)
        convergence_path.write_text(
            yaml.safe_dump(
                {
                    "task_id": "TC001",
                    "title": "Fix app gap",
                    "objective": "Implement missing path",
                    "traceability": ["FR-001", "SPEC-001", "DES-001"],
                    "allowed_paths": ["src/app.py", "tests/test_app.py"],
                    "verification_commands": ["python -m pytest -q"],
                    "status": "TODO",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        run_git(self.repo, "add", ".sdd/convergence/TC001.yaml")
        run_git(self.repo, "commit", "-m", "add TC001 convergence task")

        def implement(repo, _prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/app.py").write_text(
                "def ok():\n    return True\n", encoding="utf-8"
            )
            (repo / "tests/test_app.py").write_text(
                "from src.app import ok\n\n"
                "def test_ok():\n    assert ok()\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="fixed", stderr="")

        first_codex = FakeCodex(implement)
        first = Stage08CodexRunner(Orchestrator(self.repo), codex=first_codex)
        with patch.object(
            first.recovery,
            "record_checkpoint",
            side_effect=RuntimeError("simulated recovery state write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated recovery state write failure"
            ):
                first.execute_one("TC001")

        checkpoint = run_git(self.repo, "rev-parse", "HEAD")
        self.assertIn(
            "[TC001]",
            run_git(self.repo, "show", "-s", "--format=%s", checkpoint),
        )
        evidence_paths = list((self.repo / ".sdd/evidence").glob("*-TC001.json"))
        self.assertEqual(len(evidence_paths), 1)
        evidence = json.loads(evidence_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(all(item["passed"] for item in evidence["verification"]))
        self.assertEqual(
            yaml.safe_load(convergence_path.read_text(encoding="utf-8"))["status"],
            "TODO",
        )
        self.assertEqual(len(first_codex.prompts), 1)

        def must_not_run(*_):
            raise AssertionError(
                "Codex must not rerun a checkpointed TC task during reconciliation"
            )

        fresh_codex = FakeCodex(must_not_run)
        fresh = Stage08CodexRunner(Orchestrator(self.repo), codex=fresh_codex)
        result = fresh.execute_one("TC001")

        self.assertEqual(result.status, "DONE")
        self.assertEqual(result.checkpoint_commit, checkpoint)
        self.assertEqual(fresh_codex.prompts, [])
        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), checkpoint)
        self.assertEqual(
            run_git(self.repo, "log", "--format=%s").count("[TC001]"), 1
        )
        self.assertEqual(
            len(list((self.repo / ".sdd/evidence").glob("*-TC001.json"))), 1
        )
        self.assertEqual(
            yaml.safe_load(convergence_path.read_text(encoding="utf-8"))["status"],
            "DONE",
        )

    def test_fresh_runner_repairs_tc_convergence_after_finalization_failure(self):
        self._write_tasks("# Tasks\n")
        convergence_path = self.repo / ".sdd/convergence/TC001.yaml"
        convergence_path.parent.mkdir(parents=True, exist_ok=True)
        convergence_path.write_text(
            yaml.safe_dump(
                {
                    "task_id": "TC001",
                    "title": "Fix app gap",
                    "objective": "Implement missing path",
                    "traceability": ["FR-001", "SPEC-001", "DES-001"],
                    "allowed_paths": ["src/app.py", "tests/test_app.py"],
                    "verification_commands": ["python -m pytest -q"],
                    "status": "TODO",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        run_git(self.repo, "add", ".sdd/convergence/TC001.yaml")
        run_git(self.repo, "commit", "-m", "add TC001 convergence task")

        def implement(repo, _prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/app.py").write_text(
                "def ok():\n    return True\n", encoding="utf-8"
            )
            (repo / "tests/test_app.py").write_text(
                "from src.app import ok\n\n"
                "def test_ok():\n    assert ok()\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="fixed", stderr="")

        first_codex = FakeCodex(implement)
        first = Stage08CodexRunner(Orchestrator(self.repo), codex=first_codex)
        with patch.object(
            first,
            "_mark_convergence_done",
            side_effect=RuntimeError("simulated convergence finalization failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated convergence finalization failure"
            ):
                first.execute_one("TC001")

        checkpoint = run_git(self.repo, "rev-parse", "HEAD")
        self.assertIn(
            "[TC001]", run_git(self.repo, "show", "-s", "--format=%s", checkpoint)
        )
        evidence_paths = list((self.repo / ".sdd/evidence").glob("*-TC001.json"))
        self.assertEqual(len(evidence_paths), 1)
        evidence = json.loads(evidence_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(all(item["passed"] for item in evidence["verification"]))
        state = yaml.safe_load(
            (self.repo / ".sdd/state/implementation-state.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(state["last_completed_task"], "TC001")
        self.assertEqual(state["last_verified_commit"], checkpoint)
        self.assertEqual(state["test_status"]["overall"], "PASS")
        self.assertIsNone(state["current_task"])
        self.assertEqual(
            yaml.safe_load(convergence_path.read_text(encoding="utf-8"))["status"],
            "TODO",
        )
        self.assertEqual(len(first_codex.prompts), 1)

        def must_not_run(*_):
            raise AssertionError(
                "Codex must not rerun after convergence finalization failure"
            )

        fresh_codex = FakeCodex(must_not_run)
        fresh = Stage08CodexRunner(Orchestrator(self.repo), codex=fresh_codex)
        result = fresh.execute_one("TC001")

        self.assertEqual(result.status, "DONE")
        self.assertEqual(result.checkpoint_commit, checkpoint)
        self.assertEqual(fresh_codex.prompts, [])
        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), checkpoint)
        self.assertEqual(
            run_git(self.repo, "log", "--format=%s").count("[TC001]"), 1
        )
        self.assertEqual(
            len(list((self.repo / ".sdd/evidence").glob("*-TC001.json"))), 1
        )
        self.assertEqual(
            yaml.safe_load(convergence_path.read_text(encoding="utf-8"))["status"],
            "DONE",
        )

    def test_multi_checkpoint_stale_recovery_does_not_rerun_checkpointed_tasks(self):
        self._write_tasks('''
### T001 ? First calculator task
- **Status:** TODO
- **Allowed files:** `src/first.py`, `tests/test_first.py`
- **Implementation Scope:** Implement first task.
- **Verification Commands:** `python -m pytest -q`

### T002 ? Second calculator task
- **Status:** TODO
- **Allowed files:** `src/second.py`, `tests/test_second.py`
- **Implementation Scope:** Implement second task.
- **Verification Commands:** `python -m pytest -q`
''')
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        stale_state = state_path.read_text(encoding="utf-8")
        setup_head = run_git(self.repo, "rev-parse", "HEAD")

        def implement_first(repo, _prompt):
            (repo / "src").mkdir(exist_ok=True)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "src/first.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            (repo / "tests/test_first.py").write_text(
                "from src.first import add\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="implemented T001", stderr="")

        first_codex = FakeCodex(implement_first)
        first = Stage08CodexRunner(Orchestrator(self.repo), codex=first_codex)
        with patch.object(
            first.recovery,
            "record_checkpoint",
            side_effect=RuntimeError("simulated T001 recovery state write failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated T001 recovery state write failure"
            ):
                first.execute_one("T001")

        t001_commit = run_git(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(t001_commit, setup_head)
        self.assertEqual(len(first_codex.prompts), 1)
        self.assertEqual(state_path.read_text(encoding="utf-8"), stale_state)
        self.assertRegex(
            run_git(self.repo, "show", "-s", "--format=%s", t001_commit),
            r"^(?:feat|fix)\(implementation\): \[T001\] .+",
        )

        def implement_second(repo, _prompt):
            (repo / "src/second.py").write_text(
                "def multiply(a, b):\n    return a * b\n", encoding="utf-8"
            )
            (repo / "tests/test_second.py").write_text(
                "from src.second import multiply\n\n"
                "def test_multiply():\n    assert multiply(2, 3) == 6\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="implemented T002", stderr="")

        second_codex = FakeCodex(implement_second)
        second = Stage08CodexRunner(Orchestrator(self.repo), codex=second_codex)
        second_result = second.execute_one("T002")
        t002_commit = second_result.checkpoint_commit
        self.assertIsNotNone(t002_commit)
        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), t002_commit)
        self.assertEqual(run_git(self.repo, "rev-parse", f"{t002_commit}^"), t001_commit)
        self.assertRegex(
            run_git(self.repo, "show", "-s", "--format=%s", t002_commit),
            r"^(?:feat|fix)\(implementation\): \[T002\] .+",
        )
        self.assertEqual(len(second_codex.prompts), 1)

        def committed_pass_evidence(commit, task_id):
            paths = run_git(
                self.repo, "show", "--name-only", "--pretty=format:", commit
            ).splitlines()
            matches = [
                path for path in paths
                if path.startswith(".sdd/evidence/") and path.endswith(f"-{task_id}.json")
            ]
            self.assertEqual(len(matches), 1)
            evidence = json.loads(run_git(self.repo, "show", f"{commit}:{matches[0]}"))
            self.assertEqual(evidence["schema_version"], "1.0")
            self.assertEqual(evidence["stage"], "08")
            self.assertEqual(evidence["task_id"], task_id)
            self.assertEqual(evidence["status"], "PASS")
            self.assertIsInstance(evidence["changed_paths"], list)
            self.assertIsInstance(evidence["codex"], dict)
            self.assertEqual(evidence["codex"]["returncode"], 0)
            self.assertTrue(evidence["verification"])
            self.assertEqual(
                [item["command"] for item in evidence["verification"]],
                ["python -m pytest -q"],
            )
            self.assertTrue(all(
                isinstance(item["command"], str)
                and isinstance(item["returncode"], int)
                and isinstance(item["stdout"], str)
                and isinstance(item["stderr"], str)
                and item["passed"] is True
                and item["returncode"] == 0
                for item in evidence["verification"]
            ))
            return matches[0]

        t001_evidence = committed_pass_evidence(t001_commit, "T001")
        t002_evidence = committed_pass_evidence(t002_commit, "T002")
        state_after_t002 = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state_after_t002["last_completed_task"], "T002")
        self.assertEqual(state_after_t002["last_verified_commit"], t002_commit)

        def must_not_run(*_):
            raise AssertionError(
                "Codex must not rerun already checkpointed tasks during reconciliation"
            )

        fresh_codex = FakeCodex(must_not_run)
        fresh = Stage08CodexRunner(Orchestrator(self.repo), codex=fresh_codex)
        head_before_reconciliation = run_git(self.repo, "rev-parse", "HEAD")
        evidence_count_before = len(list((self.repo / ".sdd/evidence").glob("*.json")))

        t001_result = fresh.execute_one("T001")
        t002_result = fresh.execute_one("T002")
        repeated_t001_result = fresh.execute_one("T001")

        self.assertEqual(t001_result.checkpoint_commit, t001_commit)
        self.assertEqual(t002_result.checkpoint_commit, t002_commit)
        self.assertEqual(repeated_t001_result.status, "DONE")
        self.assertEqual(repeated_t001_result.checkpoint_commit, t001_commit)
        self.assertEqual(fresh_codex.prompts, [])
        self.assertEqual(run_git(self.repo, "rev-parse", "HEAD"), head_before_reconciliation)
        self.assertEqual(len(list((self.repo / ".sdd/evidence").glob("*.json"))), evidence_count_before)
        self.assertEqual(run_git(self.repo, "log", "--format=%s").count("[T001]"), 1)
        self.assertEqual(run_git(self.repo, "log", "--format=%s").count("[T002]"), 1)
        self.assertTrue(run_git(self.repo, "show", f"{t001_commit}:{t001_evidence}"))
        self.assertTrue(run_git(self.repo, "show", f"{t002_commit}:{t002_evidence}"))
        state_after_reconciliation = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state_after_reconciliation["last_completed_task"], "T002")
        self.assertEqual(state_after_reconciliation["last_verified_commit"], t002_commit)
        self.assertEqual(state_after_reconciliation["current_task"], state_after_t002["current_task"])

    def test_historical_reconciliation_does_not_cross_unrelated_commit(self):
        self._write_tasks('''
### T001 ? First task
- **Status:** TODO
- **Allowed files:** `src/first.py`, `tests/test_first.py`
- **Implementation Scope:** Implement first task.
- **Verification Commands:** `python -m pytest -q`

### T002 ? Second task
- **Status:** TODO
- **Allowed files:** `src/second.py`, `tests/test_second.py`
- **Implementation Scope:** Implement second task.
- **Verification Commands:** `python -m pytest -q`
''')

        def implement(task_id, module):
            def callback(repo, _prompt):
                (repo / "src").mkdir(exist_ok=True)
                (repo / "tests").mkdir(exist_ok=True)
                (repo / f"src/{module}.py").write_text("VALUE = 1\n", encoding="utf-8")
                (repo / f"tests/test_{module}.py").write_text(
                    f"from src.{module} import VALUE\n\ndef test_{task_id.lower()}():\n    assert VALUE == 1\n",
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0, stdout=f"implemented {task_id}", stderr="")
            return callback

        first = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(implement("T001", "first"))
        ).execute_one("T001")
        unrelated = self.repo / "README.md"
        unrelated.write_text("unrelated history\n", encoding="utf-8")
        run_git(self.repo, "add", "README.md")
        run_git(self.repo, "commit", "-m", "docs: unrelated history")
        unrelated_commit = run_git(self.repo, "rev-parse", "HEAD")
        second = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(implement("T002", "second"))
        ).execute_one("T002")

        def observed_rerun(_repo, _prompt):
            return SimpleNamespace(returncode=1, stdout="", stderr="not reconciled")

        codex = FakeCodex(observed_rerun)
        result = Stage08CodexRunner(Orchestrator(self.repo), codex=codex).execute_one("T001")

        self.assertEqual(result.status, "CODEX_FAILED")
        self.assertEqual(len(codex.prompts), 1)
        self.assertEqual(run_git(self.repo, "rev-parse", f"{second.checkpoint_commit}^"), unrelated_commit)
        self.assertNotEqual(first.checkpoint_commit, unrelated_commit)
        self.assertEqual(run_git(self.repo, "log", "--format=%s").count("[T001]"), 1)
        self.assertEqual(run_git(self.repo, "log", "--format=%s").count("[T002]"), 1)

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

    def test_resume_with_authorized_and_unrelated_dirty_files_is_blocked_before_codex(self):
        self._write_tasks('''
### T001 ? Resume calculator
- **Status:** TODO
- **Allowed files:** `src/calculator.py`, `tests/test_calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        (self.repo / "src").mkdir(exist_ok=True)
        (self.repo / "src/calculator.py").write_text(
            "def add(a, b):\n    return a + b\n", encoding="utf-8"
        )
        (self.repo / "tests").mkdir(exist_ok=True)
        (self.repo / "tests/test_calculator.py").write_text(
            "from src.calculator import add\n", encoding="utf-8"
        )
        (self.repo / "outside.txt").write_text("unrelated\n", encoding="utf-8")

        def callback(*_):
            raise AssertionError(
                "Codex must not execute when unrelated dirty state exists"
            )

        fake = FakeCodex(callback)
        runner = Stage08CodexRunner(Orchestrator(self.repo), codex=fake)
        before = run_git(self.repo, "rev-parse", "HEAD")

        with self.assertRaisesRegex(
            CodexAdapterError,
            "pre-existing non-runtime dirty files outside the current task scope",
        ):
            runner.execute_one("T001")

        self.assertEqual(fake.prompts, [])
        self.assertEqual(before, run_git(self.repo, "rev-parse", "HEAD"))
        self.assertTrue((self.repo / "src/calculator.py").is_file())
        self.assertTrue((self.repo / "tests/test_calculator.py").is_file())
        self.assertTrue((self.repo / "outside.txt").is_file())

        status = run_git(self.repo, "status", "--short", "--untracked-files=all")
        self.assertIn("src/calculator.py", status)
        self.assertIn("tests/test_calculator.py", status)
        self.assertIn("outside.txt", status)

        head_paths = run_git(
            self.repo, "show", "--name-only", "--pretty=format:", "HEAD"
        )
        self.assertNotIn("src/calculator.py", head_paths)
        self.assertNotIn("tests/test_calculator.py", head_paths)
        self.assertNotIn("outside.txt", head_paths)

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

    def test_run_until_complete_rejects_non_positive_max_tasks_before_execution(self):
        self._write_tasks('''
### T001 ??Pending task
- **Status:** TODO
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        state_path = self.repo / ".sdd/state/project-state.yaml"
        initial_state = state_path.read_text(encoding="utf-8")

        for max_tasks in (0, -1):
            with self.subTest(max_tasks=max_tasks):
                state_path.write_text(initial_state, encoding="utf-8")
                orch = Orchestrator(self.repo)
                fake = FakeCodex(lambda *_: None)
                runner = Stage08CodexRunner(orch, codex=fake)

                with patch.object(runner, "execute_one") as execute_one:
                    with self.assertRaisesRegex(
                        CodexAdapterError,
                        "max_tasks must be a positive integer",
                    ):
                        runner.run_until_complete(max_tasks=max_tasks)

                execute_one.assert_not_called()
                self.assertEqual(fake.prompts, [])
                self.assertEqual(
                    orch.project_state["lifecycle"]["current_stage"], "08"
                )
                self.assertNotEqual(
                    orch.project_state["stages"]["08"]["status"], "DONE"
                )
                self.assertNotEqual(
                    orch.project_state["stages"]["08"]["result"], "COMPLETED"
                )
                self.assertNotEqual(
                    orch.project_state["stages"]["09"]["status"], "IN_PROGRESS"
                )

    def test_run_until_complete_rejects_non_integer_max_tasks_before_execution(self):
        self._write_tasks('''
### T001 ??Pending task
- **Status:** TODO
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Implement calculator addition.
- **Verification Commands:** `python -m pytest -q`
''')
        state_path = self.repo / ".sdd/state/project-state.yaml"
        initial_state = state_path.read_text(encoding="utf-8")

        for max_tasks in (None, True, False, "1", 1.5):
            with self.subTest(max_tasks=max_tasks):
                state_path.write_text(initial_state, encoding="utf-8")
                orch = Orchestrator(self.repo)
                fake = FakeCodex(lambda *_: None)
                runner = Stage08CodexRunner(orch, codex=fake)

                with patch.object(runner, "execute_one") as execute_one:
                    with self.assertRaisesRegex(
                        CodexAdapterError,
                        "max_tasks must be a positive integer",
                    ):
                        runner.run_until_complete(max_tasks=max_tasks)

                execute_one.assert_not_called()
                self.assertEqual(fake.prompts, [])
                self.assertEqual(
                    orch.project_state["lifecycle"]["current_stage"], "08"
                )
                self.assertNotEqual(
                    orch.project_state["stages"]["08"]["status"], "DONE"
                )
                self.assertNotEqual(
                    orch.project_state["stages"]["08"]["result"], "COMPLETED"
                )
                self.assertNotEqual(
                    orch.project_state["stages"]["09"]["status"], "IN_PROGRESS"
                )

    def test_explicit_done_task_without_checkpoint_does_not_rerun_codex(self):
        self._write_tasks('''
### T001 ??Already completed
- **Status:** DONE
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Already completed.
- **Verification Commands:** `python -m pytest -q`
''')

        def must_not_run(*_):
            raise AssertionError("DONE task must not rerun Codex")

        runner = Stage08CodexRunner(
            Orchestrator(self.repo), codex=FakeCodex(must_not_run)
        )

        try:
            result = runner.execute_one("T001")
        except CodexAdapterError:
            pass
        else:
            self.assertEqual(result.status, "DONE")

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

    def test_run_until_complete_with_blocked_task_does_not_complete_stage08(self):
        self._write_tasks('''
### T001 ??Blocked task
- **Status:** BLOCKED
- **Allowed files:** `src/calculator.py`
- **Implementation Scope:** Waiting for an upstream decision.
- **Verification Commands:** `python -m pytest -q`
''')
        orch = Orchestrator(self.repo)
        fake = FakeCodex(
            lambda *_: (_ for _ in ()).throw(
                AssertionError("Codex must not execute")
            )
        )
        runner = Stage08CodexRunner(orch, codex=fake)

        with self.assertRaises(NoExecutableTaskError):
            runner.run_until_complete()

        self.assertEqual(fake.prompts, [])
        self.assertEqual(orch.project_state["lifecycle"]["current_stage"], "08")
        self.assertNotEqual(orch.project_state["stages"]["08"]["status"], "DONE")
        self.assertNotEqual(
            orch.project_state["stages"]["08"]["result"], "COMPLETED"
        )
        self.assertNotEqual(
            orch.project_state["stages"]["09"]["status"], "IN_PROGRESS"
        )

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
