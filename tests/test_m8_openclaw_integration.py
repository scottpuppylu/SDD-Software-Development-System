from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpenClawIntegrationTests(unittest.TestCase):
    def test_skill_has_required_frontmatter_and_safe_commands(self):
        text = (ROOT / "integrations/openclaw/skills/sdd-system/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: sdd-system", text)
        self.assertIn("decision-list --status OPEN", text)
        self.assertIn("codex-stage08", text)
        self.assertNotIn("git add -A", text)
        self.assertNotIn("--yolo", text)

    def test_line_guide_keeps_channel_outside_authority(self):
        text = (ROOT / "integrations/openclaw/line/README.md").read_text(encoding="utf-8")
        self.assertIn("human interaction channel", text)
        self.assertIn("decision-resolve", text)
        self.assertIn("must not edit the contract", text)

    def test_stage_07_09_10_instruction_files_exist(self):
        for stage in ("07", "09", "10"):
            path = ROOT / ".sdd/instructions" / f"stage-{stage}.md"
            self.assertTrue(path.exists())
            self.assertGreater(len(path.read_text(encoding="utf-8")), 300)


if __name__ == "__main__":
    unittest.main()
