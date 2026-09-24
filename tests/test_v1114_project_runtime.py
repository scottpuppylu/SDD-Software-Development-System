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
from sdd_orchestrator.governed_state import ImpactRisk, ModificationImpactLedger
from sdd_orchestrator.verification_execution import (
    RegressionEvidence,
    build_regression_coverage_view,
)
from sdd_orchestrator.verification_runtime import evaluate_regression_completion

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
            _activate_sealed_stage08_verification(runner, root, task)
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


class TestRegressionCoverageAndCompletionGuard(unittest.TestCase):
    def _ledger(self, **overrides):
        values = {
            "modification_id": "MOD-014",
            "request_reference": "REQ-014",
            "requested_change": ("new behavior",),
            "authorized_change_scope": ("new behavior",),
            "affected_behavior_data": ("account display", "stored account"),
            "preservation_expectations": ("account identifier",),
            "authority_basis": (),
            "observed_evidence": (),
            "ambiguities": (),
            "risks": (
                ImpactRisk("RISK-DISPLAY", "display may regress", "account display", "Stage09"),
                ImpactRisk("RISK-DATA", "stored data may regress", "stored account", "Stage09", True),
            ),
            "governing_requirements": (),
            "governing_contracts": (),
            "governing_designs": (),
            "governing_tasks": (),
            "links": (),
            "input_version": "v2",
            "current_version": "v2",
        }
        values.update(overrides)
        return ModificationImpactLedger(**values)

    @staticmethod
    def _evidence(identity, result, risks, **overrides):
        values = {
            "identity": identity,
            "result": result,
            "risk_ids": tuple(risks),
            "version": "v2",
            "evidence": f"evidence/{identity}.json",
        }
        values.update(overrides)
        return RegressionEvidence(**values)

    def test_full_current_regression_coverage_restores_only_completion_eligibility(self):
        evidence = (
            self._evidence("EV-DISPLAY", "PASS", ("RISK-DISPLAY",)),
            self._evidence("EV-DATA", "PASS", ("RISK-DATA",)),
        )

        view = build_regression_coverage_view(self._ledger(), evidence)

        self.assertEqual(view.state, "FULL")
        self.assertTrue(view.non_regression_established)
        self.assertTrue(view.completion_eligible_projection)
        self.assertFalse(view.stage09_qualification_created)
        self.assertEqual(evidence[0].result, "PASS")

    def test_partial_and_absent_coverage_name_each_uncovered_risk(self):
        partial = build_regression_coverage_view(
            self._ledger(),
            (self._evidence("EV-DISPLAY", "PASS", ("RISK-DISPLAY",)),),
        )
        absent = build_regression_coverage_view(self._ledger(), ())

        self.assertEqual(partial.state, "PARTIAL")
        self.assertEqual(partial.uncovered_risks, ("RISK-DATA",))
        self.assertFalse(partial.completion_eligible)
        self.assertEqual(absent.state, "ABSENT")
        self.assertEqual(set(absent.uncovered_risks), {"RISK-DISPLAY", "RISK-DATA"})
        self.assertTrue(any("RISK-DATA" in warning for warning in partial.warnings))

    def test_stale_and_irrelevant_evidence_remain_visible_but_do_not_qualify(self):
        stale = self._evidence("EV-OLD", "PASS", ("RISK-DISPLAY",), version="v1")
        irrelevant = self._evidence(
            "EV-IRRELEVANT", "PASS", ("RISK-DATA",), relevant=False
        )

        view = build_regression_coverage_view(self._ledger(), (stale, irrelevant))

        self.assertEqual(
            tuple(item.state for item in view.risk_coverage), ("STALE", "IRRELEVANT")
        )
        self.assertEqual(view.state, "PARTIAL")
        self.assertFalse(view.completion_eligible)
        self.assertEqual(view.risk_coverage[0].nonqualifying_evidence, (stale,))
        self.assertEqual(view.risk_coverage[1].nonqualifying_evidence, (irrelevant,))

    def test_failed_and_not_run_results_preserve_gaps_and_withhold_completion(self):
        failed = self._evidence("EV-FAIL", "FAIL", ("RISK-DISPLAY",))
        not_run = self._evidence(
            "EV-NOT-RUN", "NOT RUN", ("RISK-DATA",), gap="database fixture unavailable"
        )

        view = build_regression_coverage_view(self._ledger(), (failed, not_run))

        self.assertEqual(view.state, "PARTIAL")
        self.assertFalse(view.completion_eligible)
        self.assertIn("EV-FAIL result is FAIL", view.risk_coverage[0].gaps)
        self.assertIn("database fixture unavailable", view.risk_coverage[1].gaps)
        self.assertEqual(failed.result, "FAIL")
        self.assertEqual(not_run.result, "NOT RUN")

    def test_new_feature_only_pass_is_separate_and_cannot_mask_regression(self):
        feature = self._evidence(
            "EV-FEATURE", "PASS", ("RISK-DISPLAY", "RISK-DATA"), purpose="NEW_BEHAVIOR"
        )

        view = build_regression_coverage_view(self._ledger(), (feature,))

        self.assertEqual(view.state, "NEW_FEATURE_ONLY")
        self.assertEqual(view.new_behavior_evidence, (feature,))
        self.assertFalse(view.non_regression_established)
        self.assertFalse(view.completion_eligible)
        self.assertTrue(any("does not establish non-regression" in item for item in view.warnings))

    def test_stale_impact_ledger_withholds_otherwise_full_coverage(self):
        ledger = self._ledger(input_version="v1")
        evidence = (
            self._evidence("EV-DISPLAY", "PASS", ("RISK-DISPLAY",)),
            self._evidence("EV-DATA", "PASS", ("RISK-DATA",)),
        )

        view = build_regression_coverage_view(ledger, evidence)

        self.assertEqual(view.state, "STALE")
        self.assertFalse(view.non_regression_established)
        self.assertFalse(view.completion_eligible)
        self.assertEqual(set(view.uncovered_risks), {"RISK-DISPLAY", "RISK-DATA"})
        self.assertTrue(any("impact ledger is stale" in item for item in view.warnings))

    def test_missing_risk_link_and_computation_failure_fail_closed(self):
        unknown = self._evidence("EV-UNKNOWN", "PASS", ("RISK-UNKNOWN",))
        missing_link = build_regression_coverage_view(self._ledger(), (unknown,))
        malformed = self._evidence("EV-BAD", "UNKNOWN", ("RISK-DISPLAY",))
        failed = evaluate_regression_completion(self._ledger(), (malformed,))

        self.assertFalse(missing_link.completion_eligible)
        self.assertTrue(any("missing affected-risk links" in item for item in missing_link.warnings))
        self.assertEqual(failed.state, "ABSENT")
        self.assertFalse(failed.completion_eligible)
        self.assertTrue(any("computation failed" in item for item in failed.warnings))

    def test_unrelated_valid_evidence_is_preserved_when_another_result_fails(self):
        passing = self._evidence("EV-PASS", "PASS", ("RISK-DISPLAY",))
        unrelated = self._evidence(
            "EV-OTHER", "PASS", ("RISK-DISPLAY",), purpose="NEW_BEHAVIOR"
        )
        failing = self._evidence("EV-FAIL", "FAIL", ("RISK-DATA",))

        view = build_regression_coverage_view(self._ledger(), (passing, unrelated, failing))

        self.assertEqual(view.risk_coverage[0].applicable_evidence, (passing,))
        self.assertEqual(view.risk_coverage[0].nonqualifying_evidence, (unrelated,))
        self.assertEqual(view.new_behavior_evidence, (unrelated,))
        self.assertFalse(view.completion_eligible)


if __name__ == '__main__':
    unittest.main()
