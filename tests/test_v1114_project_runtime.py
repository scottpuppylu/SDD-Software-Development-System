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


class TestProjectVerificationRuntime(unittest.TestCase):
    def _runner(self, root: Path, project_python: str | None = None):
        return Stage08CodexRunner(Orchestrator(root), project_python=project_python)

    def test_explicit_project_python_has_priority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            explicit = root / 'python-explicit.exe'
            explicit.write_text('x')
            env_py = root / 'python-env.exe'
            env_py.write_text('x')
            with patch.dict(os.environ, {'SDD_PROJECT_PYTHON': str(env_py)}):
                self.assertEqual(self._runner(root, str(explicit))._resolve_project_python(), str(explicit))

    def test_environment_project_python_is_supported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            env_py = root / 'python-env.exe'
            env_py.write_text('x')
            with patch.dict(os.environ, {'SDD_PROJECT_PYTHON': str(env_py)}):
                self.assertEqual(self._runner(root)._resolve_project_python(), str(env_py))

    def test_python_verification_uses_project_interpreter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            runner = self._runner(root, sys.executable)
            task = AtomicTask('T001', 'x', 'TODO', '', [], ['pyproject.toml'], ['python -c "import sys"'])
            seen = {}

            class Proc:
                returncode = 0
                stdout = 'ok'
                stderr = ''

            def fake_run(argv, **kwargs):
                seen['argv'] = argv
                seen['env'] = kwargs['env']
                return Proc()

            with patch('sdd_orchestrator.codex_adapter.subprocess.run', side_effect=fake_run):
                result = runner._run_verification(task)
            self.assertEqual(seen['argv'][0], sys.executable)
            self.assertEqual(seen['env']['SDD_PROJECT_PYTHON'], sys.executable)
            self.assertTrue(result[0].passed)

    def test_resume_allows_preexisting_dirty_only_inside_task_scope(self):
        # Regression contract is implemented in execute_one: dirty task-owned
        # files are resumable; unrelated files remain blockers. This assertion
        # pins the coverage helper semantics used by that branch.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(SOURCE / '.sdd', root / '.sdd')
            runner = self._runner(root)
            self.assertTrue(runner._covered('src/todo_cli/__main__.py', ['src/todo_cli/__main__.py']))
            self.assertFalse(runner._covered('README.md', ['src/todo_cli/__main__.py']))


if __name__ == '__main__':
    unittest.main()
