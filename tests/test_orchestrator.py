from pathlib import Path
import shutil
import tempfile
import unittest
import yaml

from sdd_orchestrator.core import (
    LifecycleAggregate,
    LifecycleGovernor,
    LifecycleInvariantError,
    Orchestrator,
    QualificationState,
    ScopedCondition,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class OrchestratorTests(unittest.TestCase):
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

    def test_stage_07_missing_design_is_incomplete(self):
        for rel in [
            "docs/PRD.md",
            "docs/spec.md",
            "AGENTS.md",
            "tasks.md",
        ]:
            self.write(rel)
        orch = Orchestrator(self.repo)
        check = orch.check_required_inputs("07")
        self.assertFalse(check.ready)
        self.assertIn("docs/Design.md", check.missing_files)
        self.assertEqual(orch.missing_input_gate_result("07"), "INCOMPLETE")

    def test_stage_07_pass_grants_implementation_and_routes_08(self):
        orch = Orchestrator(self.repo)
        result = orch.record_stage_result("07", "PASS")
        self.assertTrue(result["implementation_authorization"])
        self.assertEqual(result["next"], "08")
        self.assertEqual(orch.project_state["lifecycle"]["current_stage"], "08")

    def test_stage_08_entry_requires_stage_07_and_authorization(self):
        state_path = self.repo / ".sdd" / "state" / "project-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["stages"]["07"]["result"] = "FAIL"
        state["authorizations"]["implementation"] = False
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

        orch = Orchestrator(self.repo)
        check = orch.check_required_inputs("08")
        self.assertIn("stage_07_result == PASS", check.entry_condition_failures)
        self.assertIn(
            "implementation_authorization == true",
            check.entry_condition_failures,
        )

    def test_stage_09_implementation_gap_routes_to_08(self):
        orch = Orchestrator(self.repo)
        result = orch.record_stage_result(
            "09", "FAIL", classification="IMPLEMENTATION_GAP"
        )
        self.assertEqual(result["next"], "08")

    def test_stage_10_ready_grants_release(self):
        orch = Orchestrator(self.repo)
        result = orch.record_stage_result("10", "READY")
        self.assertTrue(result["release_authorization"])
        self.assertEqual(result["next"], "DEPLOY")

    def test_cross_domain_conflict_routes_to_both_authority_owners(self):
        orch = Orchestrator(self.repo)
        route = orch.route_conflict(
            ["PRODUCT_REQUIREMENT", "TECHNICAL_CONTRACT"]
        )
        self.assertEqual(route["owner_stages"], ["02", "03"])
        self.assertTrue(route["human_decision_required"])


class MemoryLifecycleState:
    def __init__(self, value):
        self.value = value
        self.fail_publish = False
        self.loads = 0

    def load(self):
        self.loads += 1
        return self.value

    def publish(self, state, *, affected_scope):
        if self.fail_publish:
            raise OSError("publication failed")
        self.value = state


def lifecycle(identity="state-1", **changes):
    values = dict(
        identity=identity,
        current_stage="08",
        completed_work=("T001",),
        current_work=("T002",),
        next_work=("T003",),
        eligible_scope=("T002",),
        conditions=(),
        pending_decisions=(),
        authority_summary=("PRD:approved", "SPEC:approved", "DES:approved"),
        qualifications=QualificationState(
            approved=True, implementation_authorized=True, stage07_result="PASS"
        ),
    )
    values.update(changes)
    return LifecycleAggregate(**values)


class LifecycleGovernorTests(unittest.TestCase):
    def transition(self, store, proposed, prior="state-1"):
        return LifecycleGovernor(store).transition(
            proposed,
            expected_prior_identity=prior,
            transition_identity="transition-1",
            affected_scope=("T002",),
            reason="task began",
            sources=("TASK-002", "Stage07-PASS"),
            next_route="CONTINUE_T002",
        )

    def test_records_attributable_transition_from_fresh_snapshot(self):
        store = MemoryLifecycleState(lifecycle())
        accepted = self.transition(store, lifecycle("state-2"))
        self.assertEqual(store.loads, 1)
        self.assertEqual(accepted.transitions[0].prior_state_identity, "state-1")
        self.assertEqual(accepted.transitions[0].affected_scope, ("T002",))
        self.assertEqual(store.value, accepted)

    def test_stale_identity_rejects_without_write(self):
        store = MemoryLifecycleState(lifecycle("newer"))
        with self.assertRaisesRegex(LifecycleInvariantError, "stale prior-state"):
            self.transition(store, lifecycle("state-2"))
        self.assertEqual(store.value.identity, "newer")

    def test_scoped_pause_and_independent_continuation(self):
        paused = lifecycle(
            "state-2",
            current_work=("T004",),
            eligible_scope=("T004",),
            conditions=(ScopedCondition("PAUSED", "T002", "decision needed", "HUMAN_DECISION", ("HD-1",)),),
            pending_decisions=("HD-1",),
            independent_scope=("T004",),
        )
        accepted = self.transition(MemoryLifecycleState(lifecycle()), paused)
        self.assertEqual(accepted.eligible_scope, ("T004",))

    def test_blocked_incomplete_and_invalidated_scope_are_not_eligible(self):
        for status in ("BLOCKED", "INCOMPLETE"):
            with self.subTest(status=status), self.assertRaises(LifecycleInvariantError):
                lifecycle(
                    conditions=(ScopedCondition(status, "T002", "missing fact", "AUTHORITATIVE_OWNER", ("SPEC-001",)),)
                ).validate()
        with self.assertRaisesRegex(LifecycleInvariantError, "cannot be eligible"):
            lifecycle(invalidated_scope=("T002",), rerun_required=("T002",)).validate()

    def test_invalidation_requires_rerun_and_preserves_independent_work(self):
        proposed = lifecycle(
            "state-2",
            completed_work=("T001", "T004"),
            current_work=("T004",),
            eligible_scope=("T004",),
            invalidated_scope=("T002",),
            rerun_required=("T002",),
            independent_scope=("T004",),
        )
        self.transition(MemoryLifecycleState(lifecycle()), proposed)

    def test_persistence_failure_leaves_prior_state_authoritative(self):
        prior = lifecycle()
        store = MemoryLifecycleState(prior)
        store.fail_publish = True
        with self.assertRaisesRegex(OSError, "publication failed"):
            self.transition(store, lifecycle("state-2"))
        self.assertIs(store.value, prior)

    def test_rejects_every_qualification_substitution(self):
        invalid = (
            QualificationState(implementation_authorized=True),
            QualificationState(verified=True),
            QualificationState(complete=True, stage10_eligible=True),
            QualificationState(complete=True, verified=True, release_ready=True),
            QualificationState(complete=True, verified=True, released=True),
            QualificationState(approved=True, recovery_gate_passed=True, stage10_eligible=True),
            QualificationState(approved=True, implementation_authorized=True, stage07_result="FAIL"),
            QualificationState(approved=True, complete=True, verified=True, stage09_result="FAIL"),
        )
        for qualifications in invalid:
            with self.subTest(qualifications=qualifications), self.assertRaises(LifecycleInvariantError):
                lifecycle(qualifications=qualifications).validate()

    def test_completed_snapshot_is_distinct_from_verified_and_released(self):
        completed = lifecycle(
            current_work=(), next_work=(), eligible_scope=(),
            qualifications=QualificationState(
                approved=True, implementation_authorized=True,
                stage07_result="PASS", complete=True
            ),
        )
        completed.validate()
        self.assertFalse(completed.qualifications.verified)
        self.assertFalse(completed.qualifications.release_ready)


if __name__ == "__main__":
    unittest.main()
