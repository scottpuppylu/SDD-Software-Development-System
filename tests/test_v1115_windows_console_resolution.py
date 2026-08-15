import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from sdd_orchestrator.codex_adapter import Stage08CodexRunner, AtomicTask
from sdd_orchestrator.core import Orchestrator

SOURCE = Path(__file__).resolve().parents[1]


class TestWindowsConsoleVerificationResolution(unittest.TestCase):
    def _runner(self, root: Path):
        return Stage08CodexRunner(Orchestrator(root), project_python=sys.executable)

    def test_console_script_is_resolved_before_subprocess(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            runner = self._runner(root)
            task = AtomicTask('T001', 'x', 'TODO', '', [], ['pyproject.toml'], ['todo --help'])
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

            with patch('sdd_orchestrator.codex_adapter.shutil.which', return_value=None), \
                 patch('sdd_orchestrator.codex_adapter.subprocess.run', side_effect=FileNotFoundError(2, 'not found')):
                result = runner._run_verification(task)

            self.assertEqual(result[0].returncode, 127)
            self.assertFalse(result[0].passed)
            self.assertIn('verification executable not found', result[0].stderr)


if __name__ == '__main__':
    unittest.main()
