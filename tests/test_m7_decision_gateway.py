from pathlib import Path
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.decisions import DecisionGateway, DecisionGatewayError

SOURCE = Path(__file__).resolve().parents[1]


class DecisionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE / ".sdd", self.repo / ".sdd")
        self.orch = Orchestrator(self.repo)
        self.gateway = DecisionGateway(self.orch)

    def tearDown(self):
        self.tmp.cleanup()

    def test_authority_conflict_routes_to_domain_owners_and_blocks(self):
        req = self.gateway.create_authority_conflict(
            source_stage="07",
            domains=["PRODUCT_REQUIREMENT", "TECHNICAL_CONTRACT"],
            question="Can RETRY skip to the next segment?",
            context="PRD denies progression; spec permits skip.",
            affected_artifacts=["docs/PRD.md", "docs/spec.md"],
        )
        self.assertEqual(req.owner_stages, ["02", "03"])
        self.assertEqual(req.status, "OPEN")
        self.assertTrue(self.orch.project_state["blocking"]["is_blocked"])
        self.assertEqual(self.orch.project_state["lifecycle"]["next_action"], "WAIT_FOR_HUMAN_DECISION")

    def test_resolution_is_recorded_but_does_not_self_modify_contracts(self):
        req = self.gateway.create(
            decision_type="PRODUCT_DECISION",
            source_stage="03",
            authority_domains=["PRODUCT_REQUIREMENT"],
            question="Should skip be allowed?",
            context="Blocking product behavior decision.",
            options=["ALLOW", "DISALLOW"],
            affected_artifacts=["docs/PRD.md"],
        )
        resolved = self.gateway.resolve(req.decision_id, resolution="DISALLOW", note="Must pass before progression.")
        self.assertEqual(resolved.status, "RESOLVED")
        self.assertEqual(self.orch.project_state["lifecycle"]["next_action"], "RERUN_AUTHORITATIVE_OWNER")
        self.assertFalse((self.repo / "docs/PRD.md").exists())
        semantic = self.gateway.semantic_input_for_owner(req.decision_id)
        self.assertEqual(semantic["HUMAN_RESOLUTION"], "DISALLOW")

    def test_declared_options_are_enforced(self):
        req = self.gateway.create(
            decision_type="HIGH_RISK_OPERATION",
            source_stage="10",
            authority_domains=["RELEASE_DECISION"],
            question="Approve destructive migration?",
            context="Migration can drop data.",
            options=["APPROVE", "REJECT"],
            risk="CRITICAL",
        )
        with self.assertRaises(DecisionGatewayError):
            self.gateway.resolve(req.decision_id, resolution="MAYBE")

    def test_list_open_and_resolved(self):
        a = self.gateway.create(
            decision_type="BLOCKING_TBD", source_stage="02",
            authority_domains=["PRODUCT_REQUIREMENT"], question="A?", context=""
        )
        b = self.gateway.create(
            decision_type="BLOCKING_TBD", source_stage="03",
            authority_domains=["TECHNICAL_CONTRACT"], question="B?", context=""
        )
        self.gateway.resolve(a.decision_id, resolution="Resolved A")
        self.assertEqual([d.decision_id for d in self.gateway.list(status="OPEN")], [b.decision_id])
        self.assertEqual([d.decision_id for d in self.gateway.list(status="RESOLVED")], [a.decision_id])


if __name__ == "__main__":
    unittest.main()
