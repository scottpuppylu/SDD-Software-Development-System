from pathlib import Path
from dataclasses import replace as dataclass_replace
from contextlib import redirect_stdout
import io
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

from sdd_orchestrator.core import (
    AUTHORITY_STATUSES,
    PROTECTED_AUTHORITY_ARTIFACTS,
    AuthorityEntry,
    AuthorityRegistry,
    LifecycleAggregate,
    LifecycleGovernor,
    LifecycleInvariantError,
    LifecycleTransition,
    Orchestrator,
    QualificationState,
    ScopedCondition,
)
from sdd_orchestrator.system_controller import (
    APPROVED_INTAKE_FORMS,
    ChannelNeutralOperationPort,
    GovernedOperationRequest,
    LifecycleCommand,
    LifecycleCommandProcessor,
    LifecycleOperationContext,
    LocalMVPAdapter,
)
from sdd_orchestrator.decisions import DecisionGateway
from sdd_orchestrator.cli import main as cli_main


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


class AuthorityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "conflicts.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, status="APPROVED_CURRENT_AUTHORITY", **changes):
        values = dict(domain="PRODUCT_REQUIREMENT", scope=("T005",), source="docs/PRD.md", version="prd-v1", status=status, approved=status == "APPROVED_CURRENT_AUTHORITY")
        values.update(changes)
        return AuthorityEntry(**values)

    def test_all_registry_statuses_are_explicit_and_existence_is_not_authority(self):
        self.assertEqual(AUTHORITY_STATUSES, {"ABSENT", "DRAFT", "APPROVED_CURRENT_AUTHORITY", "STALE_AFFECTED", "CONFLICTING"})
        for status in AUTHORITY_STATUSES - {"APPROVED_CURRENT_AUTHORITY"}:
            with self.subTest(status=status):
                result = AuthorityRegistry((self.entry(status, version=None if status == "ABSENT" else "v1"),)).resolve("PRODUCT_REQUIREMENT", ("T005",))
                self.assertFalse(result.approved)
                self.assertEqual(result.affected_scope, ("T005",))
                self.assertTrue(result.permitted_route.startswith("ROUTE_TO_STAGE_02"))

    def test_configured_mapping_and_domain_scoped_resolution(self):
        registry = AuthorityRegistry((self.entry(),))
        result = registry.resolve("PRODUCT_REQUIREMENT", ("T005", "T099"))
        self.assertEqual(PROTECTED_AUTHORITY_ARTIFACTS["PRODUCT_REQUIREMENT"], ("02", "docs/PRD.md"))
        self.assertEqual((result.owner_stage, result.source, result.version), ("02", "docs/PRD.md", "prd-v1"))
        self.assertEqual(result.affected_scope, ("T005",))
        self.assertEqual(result.unaffected_scope, ("T099",))

    def test_stale_dependency_blocks_only_proven_affected_scope(self):
        entry = self.entry("STALE_AFFECTED", scope=("T005",), dependencies=("T006",))
        registry = AuthorityRegistry((entry,))
        result = registry.resolve("PRODUCT_REQUIREMENT", ("T005", "T006", "T099"))
        self.assertEqual(result.affected_scope, ("T005", "T006"))
        self.assertEqual(result.unaffected_scope, ("T099",))

    def test_wrong_source_cannot_override_configured_artifact_mapping(self):
        entry = self.entry(source="docs/spec.md")
        result = AuthorityRegistry((entry,)).resolve("PRODUCT_REQUIREMENT", ("T005",))
        self.assertFalse(result.approved)
        self.assertEqual(result.unresolved_condition, "out-of-scope-authority-source")

    def test_missing_and_ambiguous_authority_block_and_persist(self):
        registry = AuthorityRegistry(conflict_store=self.store)
        missing = registry.resolve("TECHNICAL_CONTRACT", ("T005",))
        self.assertEqual(missing.unresolved_condition, "missing-authority")
        ambiguous = AuthorityRegistry((self.entry(), self.entry(version="prd-v2")), conflict_store=self.store).resolve("PRODUCT_REQUIREMENT", ("T005",))
        self.assertEqual(ambiguous.unresolved_condition, "ambiguous-current-version")
        self.assertEqual(len(AuthorityRegistry(conflict_store=self.store).conflicts()), 2)

    def test_explicit_conflict_cannot_be_overridden_by_approved_entry(self):
        approved = self.entry()
        conflicting = self.entry(
            "CONFLICTING",
            approved=False,
            version="prd-v2",
            unresolved_condition="same-domain-contract-conflict",
            scope=("T005", "T099"),
        )
        result = AuthorityRegistry(
            (approved, conflicting), conflict_store=self.store
        ).resolve("PRODUCT_REQUIREMENT", ("T005", "T099", "T100"))

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "CONFLICTING")
        self.assertEqual(result.unresolved_condition, "authority-conflict")
        self.assertEqual(result.affected_scope, ("T005", "T099"))
        self.assertEqual(result.unaffected_scope, ("T100",))
        self.assertEqual(result.permitted_route, "ROUTE_TO_STAGE_02")
        self.assertEqual(
            AuthorityRegistry(conflict_store=self.store).conflicts()[0].protocol,
            ("DETECT", "REPORT", "BLOCK", "ROUTE_TO_AUTHORITATIVE_OWNER"),
        )

    def test_cross_domain_conflict_records_four_steps_and_minimum_disclosure(self):
        registry = AuthorityRegistry(conflict_store=self.store)
        record = registry.record_cross_domain_conflict("AUTH-1", ("PRODUCT_REQUIREMENT", "TECHNICAL_CONTRACT"), ("T005",), condition="contract-mismatch", safe_references=("docs/PRD.md#AC-04", "docs/spec.md#SPEC-004"))
        self.assertEqual(record.protocol, ("DETECT", "REPORT", "BLOCK", "ROUTE_TO_AUTHORITATIVE_OWNER"))
        self.assertEqual(record.owner_stages, ("02", "03"))
        persisted = registry.conflicts()[0]
        self.assertNotIn("secret", repr(persisted))
        with self.assertRaisesRegex(LifecycleInvariantError, "cannot self-clear"):
            registry.record_cross_domain_conflict("AUTH-1", ("PRODUCT_REQUIREMENT", "TECHNICAL_CONTRACT"), ("T005",), condition="resolved", safe_references=("safe",))

    def test_global_precedence_and_gate_substitutions_are_rejected(self):
        with self.assertRaisesRegex(LifecycleInvariantError, "precedence"):
            AuthorityRegistry.reject_global_precedence()
        for result, flag, expected in (("PASS", True, True), ("PASS", False, False), ("FAIL", True, False), (None, True, False)):
            self.assertEqual(AuthorityRegistry.normal_implementation_authorized(stage07_result=result, implementation_authorization=flag), expected)
        for substitute in (
            "HUMAN_DECISION_APPROVED",
            "IMPLEMENTATION_QUALIFIED",
            "VERIFICATION_PASS",
            "STAGE09_PASS",
        ):
            with self.subTest(substitute=substitute):
                self.assertFalse(
                    AuthorityRegistry.normal_implementation_authorized(
                        stage07_result=substitute,
                        implementation_authorization=True,
                    )
                )

    def test_invalid_approval_freshness_and_status_combinations_are_rejected(self):
        invalid = (
            dict(status="DRAFT", approved=True),
            dict(status="APPROVED_CURRENT_AUTHORITY", approved=True, fresh=False),
            dict(status="APPROVED_CURRENT_AUTHORITY", approved=True, version=None),
            dict(status="WITHDRAWN", approved=False),
        )
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(LifecycleInvariantError):
                self.entry(**changes)


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

    def test_work_positions_are_unique_and_mutually_exclusive(self):
        with self.assertRaisesRegex(LifecycleInvariantError, "duplicate current work"):
            lifecycle(current_work=("T002", "T002")).validate()
        with self.assertRaisesRegex(LifecycleInvariantError, "must be disjoint"):
            lifecycle(current_work=("T002",), next_work=("T002",)).validate()

    def test_transition_history_requires_complete_unique_identities(self):
        transition = LifecycleTransition(
            identity="transition-1",
            prior_state_identity="state-0",
            new_state_identity="state-1",
            affected_scope=("T002",),
            reason="task began",
            sources=("TASK-002",),
            next_route="CONTINUE_T002",
        )
        with self.assertRaisesRegex(LifecycleInvariantError, "duplicate transition identity"):
            lifecycle(transitions=(transition, transition)).validate()
        incomplete = dataclass_replace(transition, next_route="")
        with self.assertRaisesRegex(LifecycleInvariantError, "incomplete record"):
            lifecycle(transitions=(incomplete,)).validate()

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


class LifecycleCommandProcessorTests(unittest.TestCase):
    def context(self, actions=("PAUSE", "RESUME", "REQUEST_REVISION", "REJECT_PROPOSAL", "APPROVE_DECISION")):
        return LifecycleOperationContext(
            "human-1", "session-1", actions,
            ("proposal-1", "HD-1"), ("T002", "T003", "T004"),
        )

    def command(self, action, *, identity="cmd-1", expected="state-1", new="state-2", target="proposal-1", scope=("T002",), **changes):
        values = dict(
            identity=identity, action=action, target=target,
            affected_scope=scope, expected_state_identity=expected,
            new_state_identity=new, reason=f"reason for {action}",
            operation_context=self.context(),
        )
        values.update(changes)
        return LifecycleCommand(**values)

    def process(self, state, command):
        store = MemoryLifecycleState(state)
        result = LifecycleCommandProcessor(LifecycleGovernor(store)).process(command)
        return store, result

    def test_pause_and_resume_only_affected_scope(self):
        initial = lifecycle(eligible_scope=("T002", "T004"), independent_scope=("T004",))
        store, paused = self.process(initial, self.command("PAUSE"))
        self.assertEqual(paused.next_route, "WAIT_FOR_RESUME")
        self.assertEqual(store.value.eligible_scope, ("T004",))
        self.assertEqual(store.value.independent_scope, ("T004",))
        resume = self.command("RESUME", identity="cmd-2", expected="state-2", new="state-3")
        store2, resumed = self.process(store.value, resume)
        self.assertEqual(resumed.next_route, "CONTINUE_ELIGIBLE_WORK")
        self.assertEqual(store2.value.eligible_scope, ("T002", "T004"))

    def test_revision_invalidates_dependents_without_erasing_history(self):
        initial = lifecycle(completed_work=("T001", "T002", "T004"), eligible_scope=("T003", "T004"), independent_scope=("T004",))
        command = self.command("REQUEST_REVISION", dependent_scope=("T003",))
        store, _ = self.process(initial, command)
        self.assertEqual(store.value.invalidated_scope, ("T002", "T003"))
        self.assertEqual(store.value.rerun_required, ("T002", "T003"))
        self.assertEqual(store.value.completed_work, ("T001", "T004"))
        self.assertEqual(store.value.independent_scope, ("T004",))
        self.assertEqual(store.value.transitions[0].identity, "cmd-1")

    def test_rejection_prevents_adoption(self):
        store, result = self.process(lifecycle(), self.command("REJECT_PROPOSAL"))
        self.assertEqual(result.next_route, "SUBMIT_NEW_PROPOSAL")
        self.assertNotIn("T002", store.value.eligible_scope)
        self.assertIn("T002", store.value.invalidated_scope)

    def test_approval_only_clears_named_condition(self):
        state = lifecycle(
            eligible_scope=(), pending_decisions=("HD-1",),
            conditions=(
                ScopedCondition("PAUSED", "T002", "decision", "HUMAN_DECISION", ("HD-1",)),
                ScopedCondition("BLOCKED", "T003", "gate", "STAGE07", ("gate",)),
            ),
        )
        command = self.command("APPROVE_DECISION", target="HD-1")
        store, result = self.process(state, command)
        self.assertEqual(result.next_route, "CONTINUE_ELIGIBLE_WORK")
        self.assertEqual(store.value.eligible_scope, ("T002",))
        self.assertEqual(store.value.conditions[0].scope, "T003")

    def test_duplicate_is_idempotent_and_identity_reuse_is_rejected(self):
        store, _ = self.process(lifecycle(), self.command("PAUSE"))
        store.fail_publish = True
        duplicate = LifecycleCommandProcessor(LifecycleGovernor(store)).process(self.command("PAUSE"))
        self.assertTrue(duplicate.duplicate)
        with self.assertRaisesRegex(LifecycleInvariantError, "different content"):
            LifecycleCommandProcessor(LifecycleGovernor(store)).process(
                self.command("PAUSE", reason="different")
            )

    def test_duplicate_result_remains_bound_to_original_transition(self):
        store, original = self.process(lifecycle(), self.command("PAUSE"))
        resumed = self.command(
            "RESUME", identity="cmd-2", expected="state-2", new="state-3"
        )
        store, _ = self.process(store.value, resumed)
        state_after_resume = store.value

        replay = LifecycleCommandProcessor(LifecycleGovernor(store)).process(
            self.command("PAUSE")
        )

        self.assertTrue(replay.duplicate)
        self.assertEqual(replay.state_identity, original.state_identity)
        self.assertEqual(replay.next_route, original.next_route)
        self.assertIs(store.value, state_after_resume)

    def test_invalid_commands_leave_state_unchanged(self):
        cases = (
            self.command("PAUSE", expected="stale"),
            self.command("PAUSE", operation_context=self.context(actions=("RESUME",))),
            self.command("PAUSE", scope=("T999",)),
            self.command("RESUME"),
            self.command("APPROVE_DECISION", target="HD-1"),
            self.command("PAUSE", identity=""),
        )
        for command in cases:
            with self.subTest(command=command):
                state = lifecycle()
                store = MemoryLifecycleState(state)
                with self.assertRaises(LifecycleInvariantError):
                    LifecycleCommandProcessor(LifecycleGovernor(store)).process(command)
                self.assertIs(store.value, state)

    def test_approval_cannot_be_retrospective_or_bypass_prerequisites(self):
        pending = lifecycle(
            eligible_scope=(), pending_decisions=("HD-1",),
            conditions=(ScopedCondition("PAUSED", "T002", "decision", "HUMAN_DECISION", ("HD-1",)),),
        )
        command = self.command(
            "APPROVE_DECISION", target="HD-1", prerequisites_satisfied=False
        )
        store = MemoryLifecycleState(pending)
        with self.assertRaisesRegex(LifecycleInvariantError, "prerequisites"):
            LifecycleCommandProcessor(LifecycleGovernor(store)).process(command)
        self.assertIs(store.value, pending)
        retrospective = lifecycle(
            completed_work=("T001", "T002"), eligible_scope=(),
            pending_decisions=("HD-1",),
            conditions=(ScopedCondition("PAUSED", "T002", "decision", "HUMAN_DECISION", ("HD-1",)),),
        )
        store = MemoryLifecycleState(retrospective)
        with self.assertRaisesRegex(LifecycleInvariantError, "retrospective"):
            LifecycleCommandProcessor(LifecycleGovernor(store)).process(
                self.command("APPROVE_DECISION", target="HD-1")
            )
        self.assertIs(store.value, retrospective)

    def test_persistence_failure_is_retryable_by_stable_identity(self):
        state = lifecycle()
        store = MemoryLifecycleState(state)
        store.fail_publish = True
        command = self.command("PAUSE")
        with self.assertRaisesRegex(OSError, "publication failed"):
            LifecycleCommandProcessor(LifecycleGovernor(store)).process(command)
        self.assertIs(store.value, state)
        store.fail_publish = False
        result = LifecycleCommandProcessor(LifecycleGovernor(store)).process(command)
        self.assertFalse(result.duplicate)


class ChannelNeutralOperationPortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")
        self.orchestrator = Orchestrator(self.repo)
        self.port = ChannelNeutralOperationPort(self.orchestrator)
        self.adapter = LocalMVPAdapter(self.port)

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, operation, *, journey="journey-1", command=None,
                target="request-1", payload=None, expected=None):
        return GovernedOperationRequest(
            journey, command or f"command-{operation.lower()}", operation,
            target, payload or {}, expected,
        )

    def submit(self, *, journey="journey-1", command="command-submit",
               intake="PLAIN_LANGUAGE"):
        return self.adapter.invoke(self.request(
            "SUBMIT_REQUEST", journey=journey, command=command,
            payload={"intake_form": intake, "content": "Build a helpful local tool."},
        ))

    def test_every_approved_intake_form_starts_plain_language_clarification(self):
        for number, intake in enumerate(sorted(APPROVED_INTAKE_FORMS), 1):
            with self.subTest(intake=intake):
                result = self.submit(
                    journey=f"journey-{number}", command=f"submit-{number}", intake=intake
                )
                self.assertTrue(result.accepted)
                self.assertTrue(result.command_committed)
                self.assertEqual(result.next_route, "CLARIFY_REQUIREMENTS")
                self.assertTrue(
                    any("outcome" in item for item in result.data["missing_information"])
                )
                self.assertIn("clarification", result.situation.lower())
                self.assertNotIn("Build a helpful", json.dumps(result.data))

    def test_local_journey_pause_resume_status_failure_and_verification_summary(self):
        self.submit()
        paused = self.adapter.invoke(self.request("PAUSE", command="command-pause"))
        self.assertEqual(paused.next_route, "WAIT_FOR_RESUME")
        inspected = self.adapter.invoke(self.request("INSPECT_STATUS", command="command-status"))
        self.assertEqual(inspected.data["journey"]["status"], "PAUSED")
        status = inspected.data["governed_status"]
        self.assertEqual(
            set(status),
            {"current_stage", "completed_work", "current_work", "next_work",
             "journey_status", "blocked_or_incomplete", "pending_human_decisions",
             "authority", "implementation_authorized", "execution_may_continue",
             "next_action"},
        )
        self.assertFalse(status["execution_may_continue"])
        resumed = self.adapter.invoke(self.request("CONTINUE_OR_RESUME", command="command-resume"))
        self.assertEqual(resumed.situation, "The journey is active.")
        failure = self.adapter.invoke(self.request(
            "RECEIVE_FAILURE_OR_BLOCKER", command="command-failure"
        ))
        self.assertIn("blocking", failure.data)
        summary = self.adapter.invoke(self.request(
            "RECEIVE_VERIFICATION_SUMMARY", command="command-summary",
            payload={"checks": [
                         {"check": "intake", "outcome": "PASS", "behaviors": ["AC-01"]},
                         {"check": "reporting", "outcome": "FAIL", "behaviors": ["AC-24"]},
                         {"check": "later adapter", "outcome": "NOT RUN", "behaviors": []},
                     ],
                     "evidence_gaps": ["AC-24"], "regression_risk": "Known gap"},
        ))
        self.assertEqual(summary.data["outcome"], "FAIL")
        self.assertEqual(summary.data["executed_checks"], ["intake", "reporting"])
        self.assertEqual(summary.data["unexecuted_checks"], ["later adapter"])
        self.assertEqual(summary.data["requirements_with_evidence"], ["AC-01"])
        self.assertEqual(summary.data["qualification"], "NOT_EVALUATED_BY_STAGE09")

    def test_decision_receive_approve_reject_and_revision_use_authoritative_gateway(self):
        self.submit()
        gateway = DecisionGateway(self.orchestrator)
        cases = (
            ("APPROVE", "APPROVED", "HD-APPROVE"),
            ("REJECT", "REJECTED", "HD-REJECT"),
            ("REQUEST_REVISION", "REVISION_REQUESTED", "HD-REVISION"),
        )
        for number, (operation, expected, decision_id) in enumerate(cases, 1):
            decision = gateway.create(
                decision_type="PRODUCT_DECISION", source_stage="02",
                authority_domains=["PRODUCT_REQUIREMENT"], question="Choose the outcome",
                context="The affected product choice needs explicit authority.",
                options=[operation], affected_artifacts=["docs/PRD.md"],
                target_version="v1", decision_id=decision_id,
            )
            if operation == "APPROVE":
                with self.assertRaisesRegex(LifecycleInvariantError, "blockers prevent continuation"):
                    self.adapter.invoke(self.request(
                        "CONTINUE_OR_RESUME", command="continue-before-decision"
                    ))
            received = self.adapter.invoke(self.request(
                "RECEIVE_DECISION", command=f"receive-{number}", target=decision_id
            ))
            self.assertEqual(received.data["decision"]["status"], "PENDING")
            resolved = self.adapter.invoke(self.request(
                operation, command=f"resolve-{number}", target=decision_id,
                payload={"actor": "02", "reference": f"approval-{number}",
                         "expected_version": decision.record_version,
                         "expected_target_version": "v1"},
            ))
            self.assertEqual(resolved.data["decision"]["status"], expected)

    def test_stale_malformed_and_reused_commands_are_rejected_without_rewrite(self):
        original = self.submit()
        restarted = LocalMVPAdapter(ChannelNeutralOperationPort(Orchestrator(self.repo)))
        replay = restarted.invoke(self.request(
            "SUBMIT_REQUEST", command="command-submit",
            payload={"intake_form": "PLAIN_LANGUAGE", "content": "Build a helpful local tool."},
        ))
        self.assertTrue(replay.duplicate)
        self.assertEqual(replay.snapshot_identity, original.snapshot_identity)
        with self.assertRaisesRegex(LifecycleInvariantError, "different content"):
            restarted.invoke(self.request(
                "SUBMIT_REQUEST", command="command-submit",
                payload={"intake_form": "DOCUMENT", "content": "different"},
            ))
        with self.assertRaisesRegex(LifecycleInvariantError, "stale operation snapshot"):
            restarted.invoke(self.request(
                "INSPECT_STATUS", command="stale-command", expected="stale"
            ))
        with self.assertRaisesRegex(LifecycleInvariantError, "unsupported"):
            restarted.invoke(self.request("UNKNOWN", command="unknown-command"))

    def test_delivery_failure_preserves_committed_command_and_local_resume(self):
        delivered = self.adapter.invoke(
            self.request("SUBMIT_REQUEST", command="delivery-command",
                         payload={"intake_form": "PLAIN_LANGUAGE", "content": "idea"}),
            deliver=lambda result: (_ for _ in ()).throw(OSError("channel unavailable")),
        )
        self.assertTrue(delivered.command_committed)
        self.assertFalse(delivered.delivery_succeeded)
        self.assertEqual(delivered.next_route, "RETRY_DELIVERY_OR_INSPECT_STATUS")
        recovered = LocalMVPAdapter(
            ChannelNeutralOperationPort(Orchestrator(self.repo))
        ).invoke(self.request("INSPECT_STATUS", command="recovery-status"))
        self.assertEqual(recovered.data["journey"]["status"], "CLARIFICATION_REQUIRED")

    def test_cli_is_a_viable_json_local_adapter(self):
        stdout = io.StringIO()
        argv = [
            "sdd", "--repo", str(self.repo), "operation",
            "--journey", "cli-journey", "--command-id", "cli-command",
            "--operation", "SUBMIT_REQUEST", "--target", "cli-request",
            "--payload-json", json.dumps({
                "intake_form": "PLAIN_LANGUAGE", "content": "A vague one-line idea"
            }),
        ]
        with patch.object(sys, "argv", argv), redirect_stdout(stdout):
            cli_main()
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["command_committed"])
        self.assertEqual(payload["next_route"], "CLARIFY_REQUIREMENTS")


if __name__ == "__main__":
    unittest.main()
