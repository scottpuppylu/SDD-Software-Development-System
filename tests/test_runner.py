from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StaticExecutor, StageExecutionResult
from sdd_orchestrator.result_serialization import project_status_report
from sdd_orchestrator.runner import StageRunner, StageExecutionValidationError

SOURCE_ROOT = Path(__file__).resolve().parents[1]


class StageRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text="x"):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_stage_03_loads_non_linear_required_artifacts_and_advances(self):
        self.write("docs/proposal.md", "proposal-content")
        self.write("docs/PRD.md", "prd-content")
        orch = Orchestrator(self.repo)
        orch.project_state["stages"]["02"]["status"] = "DONE"
        orch.project_state["stages"]["02"]["result"] = "COMPLETED"
        orch._save_yaml(orch.project_state_path, orch.project_state)
        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(
            status="COMPLETED",
            artifacts={"docs/spec.md": "# spec\n"},
        ))
        out = runner.run(
            executor,
            "03",
            semantic_inputs={"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"},
        )
        self.assertEqual(executor.last_request.artifacts["docs/proposal.md"], "proposal-content")
        self.assertEqual(executor.last_request.artifacts["docs/PRD.md"], "prd-content")
        self.assertEqual((self.repo / "docs/spec.md").read_text(), "# spec\n")
        self.assertEqual(out["transition"]["next"], "04")

    def test_declared_output_is_required(self):
        self.write("docs/proposal.md")
        self.write("docs/PRD.md")
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(status="COMPLETED", artifacts={}))
        with self.assertRaises(StageExecutionValidationError):
            runner.run(
                executor,
                "03",
                semantic_inputs={"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"},
            )

    def test_stage_07_executor_pass_writes_report_and_authorizes_08(self):
        for rel in [
            "docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md"
        ]:
            self.write(rel)
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(
            status="COMPLETED",
            result="PASS",
            artifacts={
                "docs/handoff/pre-implementation-gate-report.md": "PASS\n"
            },
        ))
        out = runner.run(
            executor,
            "07",
            semantic_inputs={"REPOSITORY_STRUCTURE": "present", "GIT_READINESS": "ready"},
        )
        self.assertTrue(out["transition"]["implementation_authorization"])
        self.assertEqual(out["transition"]["next"], "08")

    def test_stage_09_fail_requires_classification(self):
        for rel in [
            "docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md",
            ".sdd/state/implementation-state.yaml"
        ]:
            if rel.startswith(".sdd/"):
                continue
            self.write(rel)
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(
            status="COMPLETED",
            result="FAIL",
            artifacts={"docs/handoff/verification-report.md": "FAIL\n"},
        ))
        with self.assertRaises(StageExecutionValidationError):
            runner.run(executor, "09")

    def test_stage_09_implementation_gap_routes_to_08(self):
        for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md"]:
            self.write(rel)
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(
            status="COMPLETED",
            result="FAIL",
            classification="IMPLEMENTATION_GAP",
            artifacts={"docs/handoff/verification-report.md": "gap\n"},
            convergence_tasks=[{
                "task_id": "TC001",
                "title": "Fix implementation gap",
                "objective": "Close verified implementation gap",
                "traceability": ["FR-001"],
                "allowed_paths": ["src/app.py", "tests/test_app.py"],
                "verification_commands": ["python -m pytest -q"],
            }],
        ))
        out = runner.run(executor, "09")
        self.assertEqual(out["transition"]["next"], "08")

    def test_non_stage_08_cannot_write_unauthorized_file(self):
        self.write("docs/proposal.md")
        self.write("docs/PRD.md")
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(
            status="COMPLETED",
            artifacts={
                "docs/spec.md": "ok",
                "src/backdoor.py": "not allowed",
            },
        ))
        with self.assertRaises(StageExecutionValidationError):
            runner.run(
                executor,
                "03",
                semantic_inputs={"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"},
            )

    def test_stage_09_request_contains_source_and_tests(self):
        for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md"]:
            self.write(rel)
        self.write("src/app.py", "VALUE = 1\n")
        self.write("tests/test_app.py", "def test_x(): pass\n")
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        req = runner.build_request("09")
        self.assertIn("src/app.py", req.runtime_inputs["SOURCE_CODE"])
        self.assertIn("tests/test_app.py", req.runtime_inputs["TEST_EVIDENCE"])

    def test_packet_contains_contract_and_artifacts_but_does_not_advance(self):
        self.write("docs/proposal.md", "proposal")
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        entry_stage = orch.project_state["lifecycle"]["current_stage"]
        packet = runner.create_execution_packet(
            "02", semantic_inputs={"APPROVED_PRODUCT_DECISIONS": "yes"}
        )
        self.assertTrue(packet.exists())
        self.assertEqual(orch.project_state["lifecycle"]["current_stage"], entry_stage)
        text = packet.read_text(encoding="utf-8")
        self.assertIn("docs/proposal.md", text)
        self.assertIn("PRODUCT_REQUIREMENTS", text)


class StatusReportProjectionTests(unittest.TestCase):
    def _snapshot(self):
        return {
            "snapshot_identity": "state-42",
            "snapshot_version": "commit-abc",
            "current_stage": "08",
            "completed_work": ["TASK-008"],
            "current_work": ["TASK-009"],
            "next_work": ["TASK-010"],
            "pending_decisions": [],
            "authority_state": [{"identity": "AUTH-07", "status": "APPROVED_CURRENT_AUTHORITY"}],
            "conditions": [],
            "continuation_eligible": True,
            "affected_scope": ["status reporting"],
            "preserved_work": ["TASK-008"],
            "required_action": "Continue the authorized reporting task.",
            "next_eligible_route": "TASK-009",
            "verification": [
                {"identity": "runner-tests", "outcome": "PASS", "behavior": "status projection"},
                {"identity": "stage09-review", "outcome": "NOT RUN", "gap": "Stage09 has not evaluated the work."},
            ],
            "evidence_gaps": ["Stage09 decision has not been made."],
            "regression_risk": ["Unreviewed adapters may format the report differently."],
            "qualifications": {
                "approved": True,
                "implementation_authorized": True,
                "stage07_result": "PASS",
                "complete": False,
                "verified": False,
                "stage09_result": None,
                "stage10_eligible": False,
                "release_ready": False,
                "released": False,
            },
            "safe_references": ["tasks.md#TASK-009"],
        }

    def test_projection_is_plain_language_first_complete_and_read_only(self):
        snapshot = self._snapshot()
        original = deepcopy(snapshot)

        report = project_status_report(snapshot, observed_snapshot_identity="state-42")

        self.assertEqual(next(iter(report)), "summary")
        self.assertIn("governed journey", report["summary"]["situation"])
        self.assertEqual(report["lifecycle"]["current_stage"], "08")
        self.assertEqual(report["lifecycle"]["completed_work"], ["TASK-008"])
        self.assertEqual(report["lifecycle"]["next_work"], ["TASK-010"])
        self.assertTrue(report["lifecycle"]["continuation_eligible"])
        self.assertEqual(report["evidence"]["verification"][1]["outcome"], "NOT RUN")
        self.assertFalse(report["qualifications"]["complete"])
        self.assertFalse(report["qualifications"]["verified"])
        self.assertEqual(snapshot, original)

    def test_stale_snapshot_withholds_continuation_and_stronger_status(self):
        report = project_status_report(
            self._snapshot(), observed_snapshot_identity="state-43"
        )

        self.assertTrue(report["identifiers"]["stale"])
        self.assertEqual(report["lifecycle"]["status"], "INCOMPLETE")
        self.assertFalse(report["lifecycle"]["continuation_eligible"])
        self.assertEqual(
            report["summary"]["next_eligible_route"], "REFRESH_GOVERNED_SNAPSHOT"
        )

    def test_missing_and_contradictory_facts_stay_unresolved(self):
        snapshot = {
            "continuation_eligible": True,
            "qualifications": {
                "approved": False,
                "implementation_authorized": True,
                "stage07_result": "NOT RUN",
            },
            "verification": [{"identity": "unknown-check"}],
        }

        report = project_status_report(snapshot)

        self.assertEqual(report["identifiers"]["snapshot_identity"], "TBD")
        self.assertEqual(report["lifecycle"]["current_stage"], "TBD")
        self.assertEqual(report["lifecycle"]["status"], "BLOCKED")
        self.assertFalse(report["lifecycle"]["continuation_eligible"])
        self.assertEqual(report["evidence"]["verification"][0]["outcome"], "NOT RUN")
        self.assertTrue(report["reporting_failures"])
        self.assertTrue(report["qualifications"]["implementation_authorized"])

    def test_sensitive_values_are_redacted_but_safe_references_remain(self):
        snapshot = self._snapshot()
        snapshot["conditions"] = [{
            "status": "BLOCKED",
            "scope": "deployment",
            "reason": "Credential resolution is required.",
            "owner": "security owner",
            "api_token": "do-not-display",
            "safe_reference": "SEC-17",
        }]
        snapshot["continuation_eligible"] = True

        report = project_status_report(snapshot)

        condition = report["lifecycle"]["conditions"][0]
        self.assertEqual(condition["api_token"], "[REDACTED]")
        self.assertEqual(condition["safe_reference"], "SEC-17")
        self.assertEqual(report["lifecycle"]["status"], "BLOCKED")
        self.assertFalse(report["lifecycle"]["continuation_eligible"])


if __name__ == "__main__":
    unittest.main()

class StageRerunLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text="x"):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _stage06_inputs(self):
        for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md"]:
            self.write(rel)

    def test_stage06_rerun_invalidates_stale_stage08_progress_and_authorization(self):
        self._stage06_inputs()
        orch = Orchestrator(self.repo)
        orch.project_state["lifecycle"]["current_stage"] = "07"
        orch.project_state["lifecycle"]["current_stage_name"] = "PRE_IMPLEMENTATION_GATE"
        orch.project_state["stages"]["07"] = {"status": "IN_PROGRESS", "result": None}
        orch.project_state["stages"]["08"] = {"status": "IN_PROGRESS", "result": None}
        orch.project_state["authorizations"]["implementation"] = True
        orch.project_state["authorizations"]["release"] = True
        orch.project_state["blocking"] = {"is_blocked": True, "reasons": ["OLD_GATE_FAIL"]}
        orch._save_yaml(orch.project_state_path, orch.project_state)

        runner = StageRunner(orch)
        executor = StaticExecutor(StageExecutionResult(
            status="COMPLETED",
            artifacts={"tasks.md": "# tasks\n"},
        ))
        out = runner.run(
            executor,
            "06",
            semantic_inputs={"REPOSITORY_STRUCTURE": "present"},
        )

        self.assertEqual(out["transition"]["next"], "07")
        state = orch.project_state
        self.assertEqual(state["stages"]["06"]["status"], "DONE")
        self.assertEqual(state["stages"]["07"]["status"], "IN_PROGRESS")
        self.assertEqual(state["stages"]["08"]["status"], "TODO")
        self.assertIsNone(state["stages"]["08"]["result"])
        self.assertFalse(state["authorizations"]["implementation"])
        self.assertFalse(state["authorizations"]["release"])
        self.assertFalse(state["blocking"]["is_blocked"])

    def test_stage06_rerun_preserves_history_files_while_resetting_projection(self):
        self._stage06_inputs()
        history = self.repo / ".sdd" / "runs" / "old-stage-08.json"
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_text('{"stage":"08","status":"FAILED"}', encoding="utf-8")
        orch = Orchestrator(self.repo)
        orch.project_state["lifecycle"]["current_stage"] = "08"
        orch.project_state["stages"]["08"] = {"status": "IN_PROGRESS", "result": None}
        orch._save_yaml(orch.project_state_path, orch.project_state)

        runner = StageRunner(orch)
        runner.run(
            StaticExecutor(StageExecutionResult(status="COMPLETED", artifacts={"tasks.md": "# tasks\n"})),
            "06",
            semantic_inputs={"REPOSITORY_STRUCTURE": "present"},
        )
        self.assertTrue(history.exists())
        self.assertIn('"FAILED"', history.read_text(encoding="utf-8"))

    def test_stage10_blocked_rerun_revokes_stale_release_authorization(self):
        self.write("docs/handoff/verification-report.md", "PASS\n")
        orch = Orchestrator(self.repo)
        orch.project_state["lifecycle"]["current_stage"] = "10"
        orch.project_state["lifecycle"]["current_stage_name"] = "HANDOFF_AND_RELEASE"
        orch.project_state["stages"]["09"] = {"status": "DONE", "result": "PASS"}
        orch.project_state["stages"]["10"] = {"status": "IN_PROGRESS", "result": None}
        orch._save_yaml(orch.project_state_path, orch.project_state)
        runner = StageRunner(orch)
        semantics = {
            "RELEASE_IDENTITY": "v1",
            "TARGET_ENVIRONMENT": "production",
            "DEPLOYMENT_TARGET": "production service",
            "BUILD_CI_EVIDENCE": "passing",
            "SECURITY_EVIDENCE": "clear",
            "DOCUMENTATION_READINESS": "ready",
            "MIGRATION_READINESS_IF_APPLICABLE": "not applicable",
            "DEPLOYMENT_READINESS": "ready",
            "ROLLBACK_RECOVERY_READINESS": "ready",
        }

        ready = runner.run(
            StaticExecutor(StageExecutionResult(
                status="COMPLETED",
                result="READY",
                artifacts={"docs/handoff/handoff-report.md": "READY\n"},
            )),
            "10",
            semantic_inputs=semantics,
        )
        self.assertEqual(ready["transition"]["next"], "DEPLOY")
        self.assertTrue(orch.project_state["authorizations"]["release"])

        blocked = runner.run(
            StaticExecutor(StageExecutionResult(
                status="BLOCKED",
                result="BLOCKED",
                remediation_reasons=["RELEASE_EVIDENCE_STALE"],
            )),
            "10",
            semantic_inputs=semantics,
        )

        self.assertEqual(blocked["transition"]["next"], "REMEDIATION_ROUTER")
        self.assertTrue(blocked["transition"]["blocked"])
        self.assertEqual(orch.project_state["stages"]["10"]["status"], "BLOCKED")
        self.assertFalse(orch.project_state["authorizations"].get("release", False))
        self.assertNotEqual(orch.project_state["lifecycle"]["next_action"], "DEPLOY")
