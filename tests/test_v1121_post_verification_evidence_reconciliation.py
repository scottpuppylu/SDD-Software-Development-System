from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess
import tempfile
import unittest

import yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.codex_adapter import Stage08CodexRunner

SOURCE = Path(__file__).resolve().parents[1]

def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    )
    return (proc.stdout or "").strip()

class FakeCodex:
    def __init__(self, cb): self.cb=cb
    def execute(self, repo_root, prompt): return self.cb(repo_root, prompt)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Path(self.tmp.name)/"repo"
        shutil.copytree(SOURCE/".sdd", self.repo/".sdd")
        for rel,text in {"AGENTS.md":"# A\n","docs/PRD.md":"# P\n","docs/spec.md":"# S\n","docs/Design.md":"# D\n"}.items():
            p=self.repo/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
        git(self.repo,"init"); git(self.repo,"config","user.email","t@e"); git(self.repo,"config","user.name","T")
        git(self.repo,"add","."); git(self.repo,"commit","-m","initial")
        ps=self.repo/".sdd/state/project-state.yaml"; d=yaml.safe_load(ps.read_text(encoding="utf-8")); d["stages"]["07"].update(status="DONE",result="PASS"); d["authorizations"]["implementation"]=True; d["lifecycle"]["current_stage"]="08"; ps.write_text(yaml.safe_dump(d,sort_keys=False),encoding="utf-8")
        (self.repo/"tasks.md").write_text('''### T014 — Evidence\n- **Status:** TODO\n- **Allowed evidence files:** `.sdd/state/implementation-state.md`, `.sdd/state/post-implementation-verification.md`\n- **Verification Commands:** `python -c "import sys"`\n''',encoding="utf-8")
        git(self.repo,"add","."); git(self.repo,"commit","-m","authorize")
    def tearDown(self): self.tmp.cleanup()

    def test_t014_provider_blocked_draft_is_overwritten_by_runtime_pass_before_checkpoint(self):
        def cb(repo,prompt):
            (repo/".sdd/state/implementation-state.md").write_text("T014 BLOCKED python unavailable\n",encoding="utf-8")
            (repo/".sdd/state/post-implementation-verification.md").write_text("INCOMPLETE full suite not run\n",encoding="utf-8")
            return SimpleNamespace(returncode=0,stdout="BLOCKED python unavailable",stderr="")
        r=Stage08CodexRunner(Orchestrator(self.repo),codex=FakeCodex(cb),heartbeat_seconds=0)
        out=r.execute_one("T014")
        self.assertEqual(out.status,"DONE")
        for rel in [".sdd/state/implementation-state.md",".sdd/state/post-implementation-verification.md"]:
            text=(self.repo/rel).read_text(encoding="utf-8")
            self.assertIn("SDD-RUNTIME-FINALIZED:T014",text)
            self.assertIn("PASS",text)
            self.assertNotIn("python unavailable",text)
            committed=git(self.repo,"show",f"{out.checkpoint_commit}:{rel}")
            self.assertIn("SDD-RUNTIME-FINALIZED:T014",committed)

    def test_legacy_completed_t014_is_reconciled_from_pass_json_without_rerunning_codex(self):
        state=self.repo/".sdd/state/implementation-state.yaml"
        state.write_text(yaml.safe_dump({"last_completed_task":"T014","current_task":None,"next_task":None,"last_verified_commit":git(self.repo,"rev-parse","HEAD"),"test_status":{"overall":"PASS"},"blocked_status":{"blocked":False}},sort_keys=False),encoding="utf-8")
        a=self.repo/".sdd/state/implementation-state.md"; b=self.repo/".sdd/state/post-implementation-verification.md"
        a.write_text("T014 BLOCKED\n",encoding="utf-8"); b.write_text("INCOMPLETE\n",encoding="utf-8")
        ev=self.repo/".sdd/evidence"; ev.mkdir(exist_ok=True)
        (ev/"20260815T000000Z-T014.json").write_text(json.dumps({"task_id":"T014","status":"PASS","verification":[{"command":"python -c 'import sys'","returncode":0,"stdout":"","stderr":""}]}),encoding="utf-8")
        git(self.repo,"add","."); git(self.repo,"commit","-m","legacy T014 checkpoint")
        # restore live state to point at legacy T014 checkpoint
        d=yaml.safe_load(state.read_text(encoding="utf-8")); d["last_verified_commit"]=git(self.repo,"rev-parse","HEAD"); state.write_text(yaml.safe_dump(d,sort_keys=False),encoding="utf-8")
        r=Stage08CodexRunner(Orchestrator(self.repo),heartbeat_seconds=0)
        res=r.reconcile_completed_t014_evidence()
        self.assertEqual(res["status"],"RECONCILED")
        self.assertIn("SDD-RUNTIME-FINALIZED:T014",a.read_text(encoding="utf-8"))
        d=yaml.safe_load(state.read_text(encoding="utf-8"))
        self.assertEqual(d["last_completed_task"],"T014")
        self.assertEqual(d["last_verified_commit"],res["checkpoint_commit"])
        again=r.reconcile_completed_t014_evidence()
        self.assertEqual(again["status"],"ALREADY_RECONCILED")

if __name__=="__main__": unittest.main()
