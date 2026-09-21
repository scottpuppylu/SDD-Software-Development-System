from pathlib import Path
from unittest.mock import patch
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.decisions import DecisionGateway, DecisionGatewayError

SOURCE = Path(__file__).resolve().parents[1]


class DecisionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.durable_repo = Path(self.tmp.name) / "durable-repo"
        shutil.copytree(SOURCE / ".sdd", self.durable_repo / ".sdd")
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(self.durable_repo / ".sdd", self.repo / ".sdd")
        shutil.rmtree(self.repo / ".sdd" / "decisions")
        (self.repo / ".sdd" / "decisions").mkdir()
        self.orch = Orchestrator(self.repo)
        self.gateway = DecisionGateway(self.orch)

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, **changes):
        values = dict(decision_type="PRODUCT_DECISION", source_stage="03",
                      authority_domains=["PRODUCT_REQUIREMENT"],
                      question="Should the proposal adopt bounded behavior?",
                      context="A material product choice requires explicit authority.",
                      options=["APPROVE", "REJECT", "REQUEST_REVISION", "WITHDRAW"],
                      affected_artifacts=["feature:bounded-behavior"], target_version="prd-v3")
        values.update(changes)
        return self.gateway.create(**values)

    def decide(self, req, result, **changes):
        values = dict(actor="02", reference="human-review:42",
                      expected_version=req.record_version,
                      expected_target_version=req.target_version)
        values.update(changes)
        return self.gateway.resolve(req.decision_id, resolution=result, **values)

    def test_pending_record_has_stable_identity_and_understandable_scoped_effect(self):
        req = self.create(independent_scope=["docs-only"])
        self.assertTrue(req.decision_id.startswith("HD-"))
        self.assertEqual(req.status, "PENDING")
        self.assertTrue(self.orch.project_state["blocking"]["is_blocked"])
        self.assertEqual(req.presentation()["needed_from"], ["02"])
        self.assertIn("paused", req.presentation()["effect"])
        self.assertEqual(req.independent_scope, ["docs-only"])
        self.assertEqual(len(req.events), 1)

    def test_identity_collision_and_incomplete_scope_are_rejected(self):
        req = self.create(decision_id="HD-FIXED")
        with self.assertRaises(DecisionGatewayError):
            self.create(decision_id=req.decision_id)
        with self.assertRaises(DecisionGatewayError):
            self.create(affected_artifacts=[])

    def test_identity_is_structurally_bounded_and_cannot_escape_store(self):
        for identity in ("HD-../outside", "HD-A/B", "HD-", "NOT-HD-1"):
            with self.subTest(identity=identity), self.assertRaisesRegex(
                DecisionGatewayError, "invalid identity"
            ):
                self.create(decision_id=identity)
        self.assertEqual(list(self.repo.rglob("outside.yaml")), [])

    def test_independent_scope_must_be_disjoint_from_affected_and_dependents(self):
        for independent, dependencies in (
            (["feature:bounded-behavior"], []),
            (["TASK-9"], ["TASK-9"]),
        ):
            with self.subTest(independent=independent), self.assertRaisesRegex(
                DecisionGatewayError, "Independent scope overlaps"
            ):
                self.create(
                    independent_scope=independent,
                    dependencies=dependencies,
                )
        self.assertEqual(self.gateway.list(), [])
        self.assertFalse(self.orch.project_state["blocking"]["is_blocked"])

    def test_source_repository_a2_decisions_load_truthfully(self):
        gateway = DecisionGateway(Orchestrator(self.durable_repo))
        self.assertEqual(
            {decision.decision_id for decision in gateway.list()},
            {
                "HD-A2-ARCH-IDENTIFIER-RESOLUTION-001",
                "HD-A2-PRD-NAMESPACE-CORRECTION-002",
            },
        )

    def test_all_result_paths_retain_attribution_and_history(self):
        for result, expected in (("APPROVE", "APPROVED"), ("REJECT", "REJECTED"),
                                 ("REQUEST_REVISION", "REVISION_REQUESTED"),
                                 ("WITHDRAW", "WITHDRAWN")):
            req = self.create(dependencies=["TASK-9", "artifact:x"])
            decided = self.decide(req, result)
            self.assertEqual(decided.status, expected)
            self.assertEqual([event.status for event in decided.events], ["PENDING", expected])
            self.assertEqual(decided.events[-1].actor, "02")
            if expected in {"REVISION_REQUESTED", "WITHDRAWN"}:
                self.assertEqual(decided.invalidated_dependents, ["TASK-9", "artifact:x"])
                self.assertEqual(self.orch.project_state["lifecycle"]["next_action"],
                                 "RERUN_AUTHORITATIVE_OWNER")

    def test_approval_satisfies_only_named_condition_not_stage07_authorization(self):
        req = self.create()
        decided = self.decide(req, "APPROVE")
        semantic = self.gateway.semantic_input_for_owner(decided.decision_id)
        self.assertFalse(semantic["IMPLEMENTATION_AUTHORIZATION"])
        self.assertEqual(semantic["AFFECTED_ARTIFACTS"], ["feature:bounded-behavior"])

    def test_approved_decision_can_be_withdrawn_without_erasing_prior_result(self):
        req = self.create(dependencies=["TASK-9"])
        approved = self.decide(req, "APPROVE")
        withdrawn = self.gateway.resolve(
            approved.decision_id, resolution="WITHDRAW", actor="02",
            reference="human-review:withdrawal", expected_version=approved.record_version,
            expected_target_version=approved.target_version)
        self.assertEqual(withdrawn.status, "WITHDRAWN")
        self.assertEqual([event.status for event in withdrawn.events],
                         ["PENDING", "APPROVED", "WITHDRAWN"])
        self.assertEqual(withdrawn.invalidated_dependents, ["TASK-9"])

    def test_rejection_prevents_adoption_and_remains_blocked(self):
        req = self.create()
        self.decide(req, "REJECT")
        self.assertTrue(self.orch.project_state["blocking"]["is_blocked"])
        self.assertEqual(self.orch.project_state["lifecycle"]["next_action"], "STOP_REJECTED")

    def test_unauthorized_actor_stale_target_and_ambiguous_result_preserve_pending(self):
        req = self.create()
        for changes in (
            dict(resolution="APPROVE", actor="03", reference="x", expected_version=1,
                 expected_target_version="prd-v3"),
            dict(resolution="APPROVE", actor="02", reference="x", expected_version=1,
                 expected_target_version="prd-v2"),
            dict(resolution="MAYBE", actor="02", reference="x", expected_version=1,
                 expected_target_version="prd-v3"),
        ):
            with self.assertRaises(DecisionGatewayError):
                self.gateway.resolve(req.decision_id, **changes)
            self.assertEqual(self.gateway.get(req.decision_id).status, "PENDING")

    def test_persistence_failure_keeps_prior_record_and_records_safe_route(self):
        req = self.create()
        with patch("sdd_orchestrator.decisions.os.replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(DecisionGatewayError):
                self.decide(req, "APPROVE")
        retained = self.gateway.get(req.decision_id)
        self.assertEqual(retained.status, "PENDING")
        self.assertEqual(retained.record_version, 1)
        self.assertEqual(self.gateway.failures[-1]["status"], "BLOCKED")
        self.assertNotIn("disk unavailable", str(self.gateway.failures[-1]))

    def test_authority_conflict_routes_to_all_domain_owners(self):
        req = self.gateway.create_authority_conflict(
            source_stage="07", domains=["PRODUCT_REQUIREMENT", "TECHNICAL_CONTRACT"],
            question="Which bounded contract governs?", context="The authorities conflict.",
            affected_artifacts=["feature:retry"])
        self.assertEqual(req.owner_stages, ["02", "03"])
        with self.assertRaises(DecisionGatewayError):
            self.gateway.resolve(req.decision_id, resolution="APPROVE", actor="04", reference="x",
                                 expected_version=1, expected_target_version="UNSPECIFIED")


if __name__ == "__main__":
    unittest.main()
