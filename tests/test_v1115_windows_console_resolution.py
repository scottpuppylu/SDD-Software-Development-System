import os
import sys
import tempfile
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from sdd_orchestrator.codex_adapter import Stage08CodexRunner, AtomicTask
from sdd_orchestrator.core import Orchestrator

SOURCE = Path(__file__).resolve().parents[1]


def _activate_sealed_stage08_verification(runner, root: Path, task: AtomicTask):
    for relative in (
        "docs/PRD.md",
        "docs/spec.md",
        "docs/Design.md",
        "docs/handoff/pre-implementation-gate-report.md",
        "AGENTS.md",
        "tasks.md",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / relative, target)
    # Establish the current Stage07 PASS and implementation authorization through
    # the lifecycle owner before sealing the Stage08 verification envelope.
    runner.orchestrator.record_stage_result("07", "PASS")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "TC003 Fixture"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture baseline"], cwd=root, check=True, capture_output=True)
    task.behavior_scope = "verification dispatch fixture compatibility"
    runner._active_stage08_envelope = runner.assemble_execution_envelope(task)


class TestWindowsConsoleVerificationResolution(unittest.TestCase):
    def _runner(self, root: Path):
        return Stage08CodexRunner(Orchestrator(root), project_python=sys.executable)

    def test_console_script_is_resolved_before_subprocess(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            runner = self._runner(root)
            task = AtomicTask('T001', 'x', 'TODO', '', [], ['pyproject.toml'], ['todo --help'])
            _activate_sealed_stage08_verification(runner, root, task)
            seen = {}

            class Proc:
                returncode = 0
                stdout = 'usage'
                stderr = ''

            def fake_which(name, path=None):
                self.assertEqual(name, 'todo')
                self.assertIsNotNone(path)
                return r'D:\\project-python\\Scripts\\todo.exe'

            def fake_run(argv, **kwargs):
                seen['argv'] = argv
                return Proc()

            with patch('sdd_orchestrator.codex_adapter.shutil.which', side_effect=fake_which), \
                 patch('sdd_orchestrator.codex_adapter.subprocess.run', side_effect=fake_run):
                result = runner._run_verification(task)

            self.assertEqual(seen['argv'][0], r'D:\\project-python\\Scripts\\todo.exe')
            self.assertTrue(result[0].passed)

    def test_missing_executable_becomes_verification_failure_not_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            runner = self._runner(root)
            task = AtomicTask('T001', 'x', 'TODO', '', [], ['pyproject.toml'], ['todo --help'])
            _activate_sealed_stage08_verification(runner, root, task)

            with patch('sdd_orchestrator.codex_adapter.shutil.which', return_value=None), \
                 patch('sdd_orchestrator.codex_adapter.subprocess.run', side_effect=FileNotFoundError(2, 'not found')):
                result = runner._run_verification(task)

            self.assertEqual(result[0].returncode, 127)
            self.assertFalse(result[0].passed)
            self.assertIn('verification executable not found', result[0].stderr)


if __name__ == '__main__':
    unittest.main()
