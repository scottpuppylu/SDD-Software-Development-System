from pathlib import Path
import shutil
import tempfile
import unittest

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.runner import StageRunner

SOURCE_ROOT = Path(__file__).resolve().parents[1]


class StageRerunExistingOutputTests(unittest.TestCase):
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

    def test_stage_06_rerun_includes_existing_tasks_md(self):
        for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md"]:
            self.write(rel, rel)
        self.write("tasks.md", "# existing tasks\nT001 stable\n")
        runner = StageRunner(Orchestrator(self.repo))
        req = runner.build_request(
            "06", semantic_inputs={"REPOSITORY_STRUCTURE": "existing repo"}
        )
        self.assertEqual(req.artifacts["tasks.md"], "# existing tasks\nT001 stable\n")

    def test_authoring_stages_02_to_05_include_existing_own_output(self):
        cases = [
            ("02", {"docs/proposal.md": "proposal", "docs/PRD.md": "old prd"}, {"APPROVED_PRODUCT_DECISIONS": "none"}, "docs/PRD.md"),
            ("03", {"docs/proposal.md": "proposal", "docs/PRD.md": "prd", "docs/spec.md": "old spec"}, {"KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "none"}, "docs/spec.md"),
            ("04", {"docs/PRD.md": "prd", "docs/spec.md": "spec", "docs/Design.md": "old design"}, {"REPOSITORY_STRUCTURE_IF_EXISTING": "repo", "APPROVED_CONSTRAINTS": "none", "APPROVED_ADRS_IF_ANY": "none"}, "docs/Design.md"),
            ("05", {"docs/PRD.md": "prd", "docs/spec.md": "spec", "docs/Design.md": "design", "AGENTS.md": "old agents"}, {"REPOSITORY_STRUCTURE": "repo"}, "AGENTS.md"),
        ]
        for sid, files, semantics, output in cases:
            with self.subTest(stage=sid):
                repo = Path(self.tmp.name) / f"repo-{sid}"
                shutil.copytree(SOURCE_ROOT / ".sdd", repo / ".sdd")
                for rel, text in files.items():
                    path = repo / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
                req = StageRunner(Orchestrator(repo)).build_request(sid, semantic_inputs=semantics)
                self.assertEqual(req.artifacts[output], files[output])

    def test_gate_rerun_does_not_include_previous_gate_report(self):
        for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md"]:
            self.write(rel, rel)
        self.write("docs/handoff/pre-implementation-gate-report.md", "OLD FAIL")
        runner = StageRunner(Orchestrator(self.repo))
        req = runner.build_request(
            "07", semantic_inputs={"REPOSITORY_STRUCTURE": "repo", "GIT_READINESS": "ready"}
        )
        self.assertNotIn("docs/handoff/pre-implementation-gate-report.md", req.artifacts)


if __name__ == "__main__":
    unittest.main()
