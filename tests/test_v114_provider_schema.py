import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sdd_orchestrator.executor import StageExecutionRequest
from sdd_orchestrator.providers import CodexExecReasoningExecutor, ReasoningProviderError, _result_schema


class V114ProviderSchemaTests(unittest.TestCase):
    def _request(self, stage_id='02'):
        return StageExecutionRequest(
            stage_id=stage_id,
            stage_name='TEST',
            stage_type='AUTHORING',
            core_question='test',
            contract={'outputs': {'files': ['docs/PRD.md']}},
            artifacts={},
            semantic_inputs={},
            runtime_inputs={},
            stage_instructions='test',
        )

    def test_stage02_schema_has_no_convergence_field(self):
        schema = _result_schema(self._request('02'))
        self.assertNotIn('convergence_tasks', schema['properties'])
        self.assertNotIn('convergence_tasks', schema['required'])
        self.assertFalse(schema['additionalProperties'])

    def test_stage09_schema_has_convergence_field(self):
        schema = _result_schema(self._request('09'))
        self.assertIn('convergence_tasks', schema['properties'])
        self.assertIn('convergence_tasks', schema['required'])

    def test_long_codex_error_keeps_tail(self):
        executor = CodexExecReasoningExecutor(executable='codex', repo_root='.')
        fake_err = 'PROMPT-' + ('x' * 7000) + '-ROOT_CAUSE_AT_END'
        cp = subprocess.CompletedProcess(args=['codex'], returncode=1, stdout='', stderr=fake_err)
        with patch.object(executor, 'resolved_executable', return_value='codex'), patch('subprocess.run', return_value=cp):
            with self.assertRaises(ReasoningProviderError) as ctx:
                executor.execute(self._request('02'))
        msg = str(ctx.exception)
        self.assertIn('ROOT_CAUSE_AT_END', msg)
        self.assertIn('middle truncated', msg)


if __name__ == '__main__':
    unittest.main()
