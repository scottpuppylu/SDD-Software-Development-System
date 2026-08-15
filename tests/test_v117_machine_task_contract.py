from pathlib import Path
import unittest

from sdd_orchestrator.codex_adapter import TaskFileParser, VerificationCommandPolicy, CodexAdapterError


class V117MachineTaskContractTests(unittest.TestCase):
    def test_parser_accepts_stage06_allowed_files_field(self):
        text = '''
### T001 — 建立 Python package 與測試骨架
- **Status:** TODO
- **Allowed files:** `pyproject.toml`, `src/todo_cli/__init__.py`, `src/todo_cli/__main__.py`, `tests/fixtures/README.md`。
- **Implementation Scope:** 建立 package metadata、entrypoint 與 test discovery；不得實作產品行為。
- **Verification Commands:**
  - `python -m pytest -q tests`
'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(
            task.allowed_paths,
            [
                "pyproject.toml",
                "src/todo_cli/__init__.py",
                "src/todo_cli/__main__.py",
                "tests/fixtures/README.md",
            ],
        )
        self.assertEqual(task.verification_commands, ["python -m pytest -q tests"])

    def test_parser_merges_bounded_production_test_and_evidence_fields(self):
        text = '''
### T010 — verification only
- **Status:** TODO
- **Allowed production files:** NONE
- **Allowed test files:** `tests/integration/test_persistence_failures.py`, `tests/e2e/test_cli_restart_persistence.py`
- **Allowed evidence files:** `.sdd/state/implementation-state.md`
- **Implementation Scope:** Verify behavior only; production repair is forbidden.
- **Verification Commands:** `python -m pytest -q tests/integration/test_persistence_failures.py tests/e2e/test_cli_restart_persistence.py`
'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(
            task.allowed_paths,
            [
                "tests/integration/test_persistence_failures.py",
                "tests/e2e/test_cli_restart_persistence.py",
                ".sdd/state/implementation-state.md",
            ],
        )
        self.assertEqual(len(task.verification_commands), 1)

    def test_implementation_scope_is_not_path_authority(self):
        text = '''
### T001 — prose only
- **Status:** TODO
- **Implementation Scope:** 建立 `src/app.py` 與 `tests/test_app.py`，但沒有宣告 Allowed files。
- **Verification Commands:** `python -m pytest -q tests/test_app.py`
'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(task.allowed_paths, [])

    def test_natural_language_verification_is_not_machine_command(self):
        text = '''
### T001 — human verification only
- **Status:** TODO
- **Allowed files:** `src/app.py`, `tests/test_app.py`
- **Verification:** 在隔離環境確認 package 可匯入且測試可執行。
'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(task.verification_commands, [])

    def test_executable_looking_verification_is_not_machine_command(self):
        text = '''
### T001 - human verification field
- **Status:** TODO
- **Allowed files:** src/app.py
- **Verification:** python -m pytest -q
'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(task.verification_commands, [])

    def test_stage06_and_stage07_instructions_publish_machine_contract(self):
        root = Path(__file__).resolve().parents[1]
        s06 = (root / '.sdd/instructions/stage-06.md').read_text(encoding='utf-8')
        s07 = (root / '.sdd/instructions/stage-07.md').read_text(encoding='utf-8')
        self.assertIn('Verification Commands', s06)
        self.assertIn('Allowed production files', s06)
        self.assertIn('Implementation Scope', s06)
        self.assertIn('Stage 06 → Stage 08 Machine Contract Readiness', s07)
        self.assertIn('Verification Commands', s07)


if __name__ == '__main__':
    unittest.main()

class V1110VerificationCommandParserTests(unittest.TestCase):
    def test_parser_accepts_numbered_verification_commands_from_real_t001_shape(self):
        text = '''
### T001 — 建立 Python package 與測試骨架
- **Status:** TODO
- **Allowed files:** `pyproject.toml`, `src/todo_cli/__init__.py`, `src/todo_cli/__main__.py`, `tests/fixtures/README.md`。
- **Implementation Scope:** 建立 package metadata、entrypoint 與 test discovery。
- **Verification Commands:**
  1. `python -m pip install -e .`
  2. `python -c "import todo_cli"`
  3. `python -m todo_cli --help`
  4. `todo --help`
  5. `python -m pytest --collect-only -q`
'''
        task = TaskFileParser(text).parse()[0]
        self.assertEqual(
            task.verification_commands,
            [
                "python -m pip install -e .",
                'python -c "import todo_cli"',
                "python -m todo_cli --help",
                "todo --help",
                "python -m pytest --collect-only -q",
            ],
        )
        for command in task.verification_commands:
            VerificationCommandPolicy.argv(command)

    def test_policy_rejects_arbitrary_python_c_and_bare_console_mutation(self):
        with self.assertRaises(CodexAdapterError):
            VerificationCommandPolicy.argv('python -c "import os; os.remove(\\\"x\\\")"')
        with self.assertRaises(CodexAdapterError):
            VerificationCommandPolicy.argv('todo delete 1')
