from pathlib import Path
from types import SimpleNamespace
import shutil, subprocess, tempfile, unittest, yaml

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StageExecutionResult
from sdd_orchestrator.runner import StageRunner, StageExecutionValidationError
from sdd_orchestrator.codex_adapter import Stage08CodexRunner
from sdd_orchestrator.system_controller import FullSystemController

SOURCE = Path(__file__).resolve().parents[1]

class QueueExecutor:
    def __init__(self, by_stage):
        self.by_stage={k:list(v) for k,v in by_stage.items()}
    def execute(self, req):
        return self.by_stage[req.stage_id].pop(0)

class FakeCodex:
    def execute(self, repo, prompt):
        # modify path authorized by convergence task or normal task
        p=repo/'src/app.py'; p.parent.mkdir(exist_ok=True); p.write_text('def ok(): return True\n', encoding='utf-8')
        t=repo/'tests/test_app.py'; t.parent.mkdir(exist_ok=True); t.write_text('from src.app import ok\n\ndef test_ok(): assert ok()\n', encoding='utf-8')
        return SimpleNamespace(returncode=0, stdout='fixed', stderr='')

def git(repo,*args):
    return subprocess.run(['git',*args],cwd=repo,text=True,capture_output=True,check=True).stdout.strip()

class M10Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Path(self.tmp.name)/'repo'
        shutil.copytree(SOURCE/'.sdd', self.repo/'.sdd')
        for rel,text in {
            'AGENTS.md':'# AGENTS\n', 'tasks.md':'# Tasks\n',
            'docs/PRD.md':'# PRD\nFR-001\n','docs/spec.md':'# Spec\nSPEC-001\n','docs/Design.md':'# Design\nDES-001\n'
        }.items():
            p=self.repo/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text, encoding="utf-8")
        git(self.repo,'init');git(self.repo,'config','user.email','t@e.com');git(self.repo,'config','user.name','T');git(self.repo,'add','.');git(self.repo,'commit','-m','base')
    def tearDown(self): self.tmp.cleanup()

    def _set_stage09(self):
        p=self.repo/'.sdd/state/project-state.yaml'; d=yaml.safe_load(p.read_text(encoding="utf-8"));d['lifecycle']['current_stage']='09';d['lifecycle']['current_stage_name']='VERIFICATION_AND_CONVERGENCE';d['stages']['09']['status']='IN_PROGRESS';p.write_text(yaml.safe_dump(d,sort_keys=False), encoding='utf-8');git(self.repo,'add','.sdd/state/project-state.yaml');git(self.repo,'commit','-m','stage09')

    def test_stage09_gap_persists_tc_task_and_routes_08(self):
        self._set_stage09(); orch=Orchestrator(self.repo); runner=StageRunner(orch)
        result=StageExecutionResult(status='COMPLETED',artifacts={'docs/handoff/verification-report.md':'FAIL'},result='FAIL',classification='IMPLEMENTATION_GAP',convergence_tasks=[{
            'task_id':'TC001','title':'Fix app gap','objective':'Implement missing path','traceability':['FR-001','SPEC-001','DES-001'],
            'allowed_paths':['src/app.py','tests/test_app.py'],'verification_commands':['python -m pytest -q']
        }])
        class E:
            def execute(self,req): return result
        out=runner.run(E(),'09')
        self.assertEqual(out['transition']['next'],'08')
        self.assertTrue((self.repo/'.sdd/convergence/TC001.yaml').exists())

    def test_authority_conflict_cannot_emit_tc(self):
        self._set_stage09(); orch=Orchestrator(self.repo); runner=StageRunner(orch)
        bad=StageExecutionResult(status='COMPLETED',artifacts={'docs/handoff/verification-report.md':'FAIL'},result='FAIL',classification='AUTHORITY_CONTRACT_CONFLICT',convergence_tasks=[{'task_id':'TC001'}])
        class E:
            def execute(self,req): return bad
        with self.assertRaises(StageExecutionValidationError): runner.run(E(),'09')

    def test_tc_task_can_be_executed_by_stage08(self):
        # stage09 -> TC -> stage08
        self._set_stage09(); orch=Orchestrator(self.repo); runner=StageRunner(orch)
        gap=StageExecutionResult(status='COMPLETED',artifacts={'docs/handoff/verification-report.md':'FAIL'},result='FAIL',classification='IMPLEMENTATION_GAP',convergence_tasks=[{
            'task_id':'TC001','title':'Fix app gap','objective':'Implement','traceability':['FR-001'],'allowed_paths':['src/app.py','tests/test_app.py'],'verification_commands':['python -m pytest -q']
        }])
        class E:
            def execute(self,req): return gap
        runner.run(E(),'09')
        # grant implementation auth remains expected from prior Stage07 in real flow
        p=self.repo/'.sdd/state/project-state.yaml'; d=yaml.safe_load(p.read_text(encoding="utf-8"));d['stages']['07']['result']='PASS';d['authorizations']['implementation']=True;p.write_text(yaml.safe_dump(d,sort_keys=False), encoding='utf-8');git(self.repo,'add','.sdd/state/project-state.yaml','docs/handoff/verification-report.md','.sdd/convergence/TC001.yaml');git(self.repo,'commit','-m','gap')
        orch=Orchestrator(self.repo); c=Stage08CodexRunner(orch,codex=FakeCodex());r=c.execute_one('TC001')
        self.assertEqual(r.status,'DONE'); self.assertTrue(r.checkpoint_commit)
        tc=yaml.safe_load((self.repo/'.sdd/convergence/TC001.yaml').read_text(encoding='utf-8'));self.assertEqual(tc['status'],'DONE')

if __name__=='__main__': unittest.main()

class FullAutoE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=Path(self.tmp.name)/'repo'
        shutil.copytree(SOURCE/'.sdd', self.repo/'.sdd')
        git(self.repo,'init');git(self.repo,'config','user.email','t@e.com');git(self.repo,'config','user.name','T');git(self.repo,'add','.');git(self.repo,'commit','-m','sdd runtime')
    def tearDown(self): self.tmp.cleanup()

    def test_full_01_to_10_mock_pipeline_reaches_deploy(self):
        by_stage={
            '01':[StageExecutionResult(status='COMPLETED',artifacts={'docs/proposal.md':'# Proposal\nG-001 build app\n'})],
            '02':[StageExecutionResult(status='COMPLETED',artifacts={'docs/PRD.md':'# PRD\nFR-001\nP0\nGiven x When y Then z\n'})],
            '03':[StageExecutionResult(status='COMPLETED',artifacts={'docs/spec.md':'# Spec\nSPEC-001\n'})],
            '04':[StageExecutionResult(status='COMPLETED',artifacts={'docs/Design.md':'# Design\nDES-001\n'})],
            '05':[StageExecutionResult(status='COMPLETED',artifacts={'AGENTS.md':'# AGENTS\nStage 07 PASS required.\n'})],
            '06':[StageExecutionResult(status='COMPLETED',artifacts={'tasks.md':'''# Tasks\n\n### T001 — Implement app\n- **Status:** TODO\n- **Traceability:** FR-001 → SPEC-001 → DES-001\n- **Allowed files:** `src/app.py`, `tests/test_app.py`\n- **Implementation Scope:** Implement the app task within the declared files.\n- **Verification Commands:** `python -m pytest -q`\n'''})],
            '07':[StageExecutionResult(status='COMPLETED',result='PASS',artifacts={'docs/handoff/pre-implementation-gate-report.md':'PASS\n'})],
            '09':[StageExecutionResult(status='COMPLETED',result='PASS',artifacts={'docs/handoff/verification-report.md':'PASS\n'})],
            '10':[StageExecutionResult(status='COMPLETED',result='READY',artifacts={'docs/handoff/handoff-report.md':'READY\n'})],
        }
        reasoning=QueueExecutor(by_stage)
        orch=Orchestrator(self.repo)
        codex=Stage08CodexRunner(orch,codex=FakeCodex())
        controller=FullSystemController(orch,reasoning,codex)
        result=controller.run(max_steps=30,semantic_by_stage={'01':{
            'IDEA_OR_PROBLEM':'Build a tiny app',
            'TARGET_USER_OR_USAGE_CONTEXT':'single user',
            'GOALS_OR_DESIRED_OUTCOME':'verified app',
        }})
        self.assertEqual(result.status,'DEPLOY')
        self.assertEqual(result.end_stage,'10')
        self.assertTrue((self.repo/'docs/handoff/handoff-report.md').exists())
        self.assertTrue((self.repo/'src/app.py').exists())
        self.assertEqual(orch.project_state['stages']['09']['result'],'PASS')
        self.assertTrue(orch.project_state['authorizations']['release'])
