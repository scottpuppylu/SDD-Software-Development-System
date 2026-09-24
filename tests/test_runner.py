from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StaticExecutor, StageExecutionResult
from sdd_orchestrator.governance_envelope import GovernanceEnvelopeError
from sdd_orchestrator.result_serialization import project_status_report
from sdd_orchestrator.runner import (
    GovernedRepositorySnapshot,
    StageRunner,
    StageExecutionValidationError,
)

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
        with self.assertRaises(GovernanceEnvelopeError) as raised:
            runner.run(
                executor,
                "03",
                semantic_inputs={"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"},
            )
        self.assertEqual(raised.exception.code, "ACTUAL_SCOPE_EFFECT_MISMATCH")
        self.assertEqual(raised.exception.route, "SECURITY_OR_AUTHORITY_OWNER")

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

    def test_governed_snapshot_reloads_repository_state_and_separates_qualifications(self):
        orch = Orchestrator(self.repo)
        runner = StageRunner(orch)
        state = deepcopy(orch.project_state)
        state["lifecycle"]["current_stage"] = "08"
        state["lifecycle"]["next_action"] = "EXECUTE_TASK"
        state["stages"]["07"]["result"] = "PASS"
        state["stages"]["09"]["result"] = None
        state["authorizations"]["implementation"] = True
        state["authorizations"]["release"] = False
        state["blocking"] = {"is_blocked": False, "reasons": []}
        orch._save_yaml(orch.project_state_path, state)

        snapshot = runner.governed_snapshot()

        self.assertIsInstance(snapshot, GovernedRepositorySnapshot)
        self.assertEqual(snapshot.current_stage, "08")
        self.assertTrue(snapshot.stage08_eligible)
        self.assertTrue(snapshot.qualifications["implementation_authorized"])
        self.assertFalse(snapshot.qualifications["verified"])
        self.assertFalse(snapshot.qualifications["release_authorized"])
        self.assertEqual(orch.project_state["lifecycle"]["next_action"], "EXECUTE_TASK")

    def test_governed_snapshot_rejects_contradictory_gate_facts(self):
        orch = Orchestrator(self.repo)
        state = deepcopy(orch.project_state)
        state["lifecycle"]["current_stage"] = "08"
        state["stages"]["07"]["result"] = "FAIL"
        state["authorizations"]["implementation"] = True
        state["blocking"] = {"is_blocked": False, "reasons": []}
        orch._save_yaml(orch.project_state_path, state)

        snapshot = StageRunner(orch).governed_snapshot()

        self.assertIn(
            "IMPLEMENTATION_AUTHORIZATION_WITHOUT_STAGE07_PASS",
            snapshot.contradictions,
        )
        self.assertFalse(snapshot.continuation_eligible)
        self.assertFalse(snapshot.stage08_eligible)


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


# TASK-018 is a repository-native scenario index, not a Stage09 decision.  Each
# row identifies repeatable setup, expected evidence semantics, preservation and
# failure behavior, trace targets, and an executable check that supplies current
# component evidence.  The meta-checks below fail closed on omissions or stale
# evidence instead of turning partial coverage into completion.
P0_SCENARIO_EVIDENCE_SEMANTICS = {
    "PASS": "The named check executed and satisfied its governed criterion.",
    "FAIL": "The named check executed and did not satisfy its governed criterion.",
    "NOT RUN": "No qualifying current execution evidence exists for the named check.",
}

P0_LIFECYCLE_SCENARIOS = (
    ("SCN-001", "fresh lifecycle snapshot and mutually consistent work positions",
     ("AC-06", "AC-11", "AC-23"), "SPEC-001", "DES-001", ("TASK-001", "TASK-002"),
     "tests/test_orchestrator.py::LifecycleGovernorTests::test_work_positions_are_unique_and_mutually_exclusive",
     "contradictory snapshot", "preserve the last repository-backed state"),
    ("SCN-002", "all five lifecycle actions, invalidation, and independent continuation",
     ("AC-07", "AC-09", "AC-10", "AC-30", "AC-31"), "SPEC-002", "DES-002", ("TASK-003",),
     "tests/test_orchestrator.py::LifecycleCommandProcessorTests::test_pause_and_resume_only_affected_scope",
     "stale or retrospective command", "preserve transition and decision history"),
    ("SCN-003", "all intake forms and seven-dimension requirement readiness",
     ("AC-01", "AC-02", "AC-03", "AC-29"), "SPEC-003", "DES-003", ("TASK-004",),
     "tests/test_orchestrator.py::ChannelNeutralOperationPortTests::test_every_approved_intake_form_starts_plain_language_clarification",
     "material ambiguity", "preserve unresolved product information without guessing"),
    ("SCN-004", "domain authority, decision categories, and conflict routing",
     ("AC-04", "AC-05", "AC-08", "AC-17", "AC-26", "AC-35"), "SPEC-004", "DES-004", ("TASK-005",),
     "tests/test_orchestrator.py::AuthorityRegistryTests::test_cross_domain_conflict_records_four_steps_and_minimum_disclosure",
     "authority conflict", "preserve domain ownership and minimum disclosure"),
    ("SCN-005", "durable Human Decision outcomes and dependent invalidation",
     ("AC-05", "AC-08", "AC-09", "AC-10", "AC-30", "AC-31"), "SPEC-005", "DES-005", ("TASK-006",),
     "tests/test_m7_decision_gateway.py::DecisionGatewayTests::test_all_result_paths_retain_attribution_and_history",
     "unauthorized or ambiguous decision", "preserve prior result and append history"),
    ("SCN-006", "replaceable reasoning provider and non-authoritative AI boundary",
     ("AC-04", "AC-05", "AC-12", "AC-13", "AC-32", "AC-34"), "SPEC-006", "DES-006", ("TASK-007",),
     "tests/test_m4_reasoning_pipeline.py::M4Tests::test_boundary_rejects_scope_overrun_and_inference_to_approval",
     "provider failure or scope overrun", "preserve valid in-scope progress and proposal status"),
    ("SCN-007", "sealed Stage08 scope, Git checkpoint, and cross-session trace",
     ("AC-11", "AC-12", "AC-25"), "SPEC-007", "DES-007", ("TASK-008", "TASK-020"),
     "tests/test_m5_git_recovery.py::M5GitTests::test_checkpoint_commits_only_authorized_paths",
     "unexpected diff or checkpoint failure", "preserve immutable checkpoints and task-indexed qualification"),
    ("SCN-008", "mixed verification outcomes and qualification separation",
     ("AC-14", "AC-15", "AC-23", "AC-33"), "SPEC-008", "DES-009", ("TASK-009",),
     "tests/test_v1118_safe_pause_and_evidence.py::T008EvidenceRegistryTests::test_truthful_three_outcomes_and_metadata",
     "missing, stale, or irrelevant evidence", "preserve every evidence outcome and gap"),
    ("SCN-009", "common failure envelope and safe recovery routes",
     ("AC-13", "AC-16", "AC-24", "AC-34"), "SPEC-009", "DES-012", ("TASK-010",),
     "tests/test_m5_git_recovery.py::M5GitTests::test_failure_journal_preserves_facts_and_filters_routes",
     "tool, command, Git, execution, or persistence failure", "preserve valid work and exact failure history"),
    ("SCN-010", "security, destructive-operation, and authority-conflict interlocks",
     ("AC-08", "AC-17", "AC-26", "AC-35"), "SPEC-010", "DES-013", ("TASK-011",),
     "tests/test_v1118_safe_pause_and_evidence.py::T011SafetyInterlockTests::test_all_protected_risk_classes_fail_closed_and_broad_targets_are_rejected",
     "unresolved safety condition", "preserve least capability and affected-scope isolation"),
    ("SCN-011", "maintenance impact and preservation ledger",
     ("AC-18", "AC-27"), "SPEC-011", "DES-014", ("TASK-013",),
     "tests/test_v1118_safe_pause_and_evidence.py::T016DemonstrationManifestTests::test_complete_manifest_traverses_chain_and_all_six_governing_effects",
     "unknown affected or preserved behavior", "preserve behavior and data outside requested change"),
    ("SCN-012", "regression coverage, gaps, and new-feature-only PASS",
     ("AC-19", "AC-27", "AC-36"), "SPEC-012", "DES-015", ("TASK-014",),
     "tests/test_v1118_safe_pause_and_evidence.py::T008EvidenceRegistryTests::test_stale_irrelevant_partial_and_security_gaps_withhold_inputs",
     "regression evidence gap", "preserve uncovered risks and withhold overall completion"),
    ("SCN-013", "channel-neutral local journey, duplicate delivery, and session loss",
     ("AC-01", "AC-06", "AC-07", "AC-20"), "SPEC-013", "DES-016", ("TASK-015",),
     "tests/test_orchestrator.py::ChannelNeutralOperationPortTests::test_delivery_failure_preserves_committed_command_and_local_resume",
     "channel or delivery failure", "preserve the committed command and repository-backed journey"),
    ("SCN-014", "observable end-to-end governed demonstration",
     ("AC-11", "AC-21"), "SPEC-014", "DES-010", ("TASK-016",),
     "tests/test_v1118_safe_pause_and_evidence.py::T016DemonstrationManifestTests::test_complete_manifest_traverses_chain_and_all_six_governing_effects",
     "broken demonstration link", "preserve source evidence and expose the missing proof"),
    ("SCN-015", "plain-language status, decision, failure, and evidence-gap reporting",
     ("AC-02", "AC-06", "AC-09", "AC-14", "AC-16", "AC-24"), "SPEC-015", "DES-011", ("TASK-017",),
     "tests/test_runner.py::StatusReportProjectionTests::test_projection_is_plain_language_first_complete_and_read_only",
     "opaque or stale report", "preserve snapshot identity and safe references"),
    ("SCN-016", "approval, authorization, completion, verification, and release separation",
     ("AC-08", "AC-12", "AC-14", "AC-15", "AC-23", "AC-26"), "SPEC-016", "DES-008", ("TASK-018",),
     "tests/test_orchestrator.py::LifecycleGovernorTests::test_rejects_every_qualification_substitution",
     "qualification substitution", "preserve distinct gate and evidence provenance"),
    ("SCN-017", "authorized append-only post-checkpoint evidence recovery",
     ("AC-11", "AC-12", "AC-13", "AC-14", "AC-15", "AC-16", "AC-23", "AC-25", "AC-26", "AC-33", "AC-34", "AC-35"),
     "SPEC-017", "DES-017", ("TASK-012", "TASK-019"),
     "tests/test_v1118_safe_pause_and_evidence.py::PostCheckpointEvidenceTests::test_recovery_persistence_is_append_only_and_idempotent",
     "stale, replayed, conflicting, or unauthorized recovery", "preserve historical checkpoint and every attempt"),
)

P0_CROSS_BOUNDARY_EVIDENCE = {
    "five-lifecycle-actions": (
        "tests/test_orchestrator.py::LifecycleCommandProcessorTests::test_pause_and_resume_only_affected_scope",
        "tests/test_orchestrator.py::LifecycleCommandProcessorTests::test_revision_invalidates_dependents_without_erasing_history",
        "tests/test_orchestrator.py::LifecycleCommandProcessorTests::test_rejection_prevents_adoption",
        "tests/test_orchestrator.py::LifecycleCommandProcessorTests::test_approval_only_clears_named_condition",
    ),
    "decisions-and-invalidation": ("tests/test_m7_decision_gateway.py::DecisionGatewayTests::test_approved_decision_can_be_withdrawn_without_erasing_prior_result",),
    "authority-conflict": ("tests/test_orchestrator.py::AuthorityRegistryTests::test_cross_domain_conflict_records_four_steps_and_minimum_disclosure",),
    "provider-failure": ("tests/test_m4_reasoning_pipeline.py::M4Tests::test_failure_classes_preserve_attempt_scope_state_and_routes",),
    "channel-failure-and-session-loss": ("tests/test_orchestrator.py::ChannelNeutralOperationPortTests::test_delivery_failure_preserves_committed_command_and_local_resume",),
    "missing-component-result": ("tests/test_runner.py::StageRunnerTests::test_declared_output_is_required",),
    "sealed-envelope-overrun": ("tests/test_m5_git_recovery.py::M5GitTests::test_checkpoint_refuses_unrelated_dirty_work",),
    "evidence-qualification-separation": ("tests/test_v1118_safe_pause_and_evidence.py::T008EvidenceRegistryTests::test_stale_irrelevant_partial_and_security_gaps_withhold_inputs",),
    "maintenance-and-regression": ("tests/test_v1118_safe_pause_and_evidence.py::T016DemonstrationManifestTests::test_complete_manifest_traverses_chain_and_all_six_governing_effects",),
    "trace-navigation": ("tests/test_v1118_safe_pause_and_evidence.py::T016DemonstrationManifestTests::test_manifest_rejects_ambiguous_identity_and_missing_navigation",),
    "safe-independent-continuation": ("tests/test_v1118_safe_pause_and_evidence.py::T011SafetyInterlockTests::test_unaffected_scope_requires_explicit_nonoverlapping_dependency_finding",),
    "post-checkpoint-evidence-recovery": ("tests/test_v1118_safe_pause_and_evidence.py::PostCheckpointEvidenceTests::test_recovery_qualification_requires_exact_bindings",),
    "partial-persistence": ("tests/test_m5_git_recovery.py::M5GitTests::test_atomic_state_write_failure_does_not_replace_state",),
}


class P0LifecycleScenarioCoverageTests(unittest.TestCase):
    APPLICABLE_AC = {
        *(f"AC-{number:02d}" for number in range(1, 22)),
        *(f"AC-{number:02d}" for number in range(23, 28)),
        *(f"AC-{number:02d}" for number in range(29, 37)),
    }

    @staticmethod
    def _test_functions(path: Path) -> set[str]:
        import ast
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return {
            node.name
            for parent in tree.body if isinstance(parent, ast.ClassDef)
            for node in parent.body if isinstance(node, ast.FunctionDef)
        }

    @staticmethod
    def _qualification_gaps(scenarios, *, current=True):
        covered_ac = {ac for row in scenarios for ac in row[2]}
        covered_spec = {row[3] for row in scenarios}
        covered_design = {row[4] for row in scenarios}
        covered_tasks = {task for row in scenarios for task in row[5]}
        gaps = []
        if covered_ac != P0LifecycleScenarioCoverageTests.APPLICABLE_AC:
            gaps.append("acceptance-criterion-coverage")
        if covered_spec != {f"SPEC-{number:03d}" for number in range(1, 18)}:
            gaps.append("spec-coverage")
        if covered_design != {f"DES-{number:03d}" for number in range(1, 18)}:
            gaps.append("design-coverage")
        if covered_tasks != {f"TASK-{number:03d}" for number in range(1, 21)}:
            gaps.append("task-coverage")
        if not current:
            gaps.append("stale-evidence")
        return "PASS" if not gaps else "NOT RUN", gaps

    def test_catalog_covers_every_p0_contract_and_task_bidirectionally(self):
        outcome, gaps = self._qualification_gaps(P0_LIFECYCLE_SCENARIOS)
        self.assertEqual(outcome, "PASS")
        self.assertEqual(gaps, [])
        self.assertEqual(len({row[0] for row in P0_LIFECYCLE_SCENARIOS}), 17)
        for row in P0_LIFECYCLE_SCENARIOS:
            with self.subTest(scenario=row[0]):
                self.assertTrue(row[2])
                self.assertTrue(row[5])
                self.assertIn(row[3], {f"SPEC-{n:03d}" for n in range(1, 18)})
                self.assertIn(row[4], {f"DES-{n:03d}" for n in range(1, 18)})

    def test_each_scenario_is_repeatable_and_links_to_an_executable_check(self):
        allowed = {
            "tests/test_orchestrator.py", "tests/test_runner.py",
            "tests/test_m7_decision_gateway.py", "tests/test_m4_reasoning_pipeline.py",
            "tests/test_m5_git_recovery.py", "tests/test_v1118_safe_pause_and_evidence.py",
        }
        for identity, setup, _acs, _spec, _design, _tasks, evidence, failure, preservation in P0_LIFECYCLE_SCENARIOS:
            with self.subTest(scenario=identity):
                path_text, _class_name, function_name = evidence.split("::")
                self.assertIn(path_text, allowed)
                self.assertIn(function_name, self._test_functions(SOURCE_ROOT / path_text))
                self.assertTrue(setup.strip())
                self.assertTrue(failure.strip())
                self.assertTrue(preservation.strip())

        expected_boundaries = {
            "five-lifecycle-actions", "decisions-and-invalidation", "authority-conflict",
            "provider-failure", "channel-failure-and-session-loss", "missing-component-result",
            "sealed-envelope-overrun", "evidence-qualification-separation",
            "maintenance-and-regression", "trace-navigation", "safe-independent-continuation",
            "post-checkpoint-evidence-recovery", "partial-persistence",
        }
        self.assertEqual(set(P0_CROSS_BOUNDARY_EVIDENCE), expected_boundaries)
        for boundary, references in P0_CROSS_BOUNDARY_EVIDENCE.items():
            with self.subTest(boundary=boundary):
                self.assertTrue(references)
                for reference in references:
                    path_text, _class_name, function_name = reference.split("::")
                    self.assertIn(path_text, allowed)
                    self.assertIn(function_name, self._test_functions(SOURCE_ROOT / path_text))

    def test_deliberate_omission_and_stale_evidence_withhold_completion(self):
        for label, scenarios, current in (
            ("missing-scenario", P0_LIFECYCLE_SCENARIOS[:-1], True),
            ("stale-evidence", P0_LIFECYCLE_SCENARIOS, False),
        ):
            with self.subTest(case=label):
                outcome, gaps = self._qualification_gaps(scenarios, current=current)
                self.assertEqual(outcome, "NOT RUN")
                self.assertTrue(gaps)

    def test_scenario_evidence_never_issues_stage09_qualification(self):
        self.assertEqual(set(P0_SCENARIO_EVIDENCE_SEMANTICS), {"PASS", "FAIL", "NOT RUN"})
        result = {
            "scenario_coverage": "PASS",
            "implementation_complete": False,
            "stage09_decision": "NOT_EVALUATED",
            "release_ready": False,
        }
        self.assertEqual(result["scenario_coverage"], "PASS")
        self.assertFalse(result["implementation_complete"])
        self.assertEqual(result["stage09_decision"], "NOT_EVALUATED")
        self.assertFalse(result["release_ready"])
