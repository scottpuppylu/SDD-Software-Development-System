from __future__ import annotations

import json
from pathlib import Path
import shutil

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.runner import StageRunner

SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _prepare_stage09_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(SOURCE_ROOT / ".sdd", repo / ".sdd")
    for rel in ["docs/PRD.md", "docs/spec.md", "docs/Design.md", "AGENTS.md", "tasks.md"]:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel + "\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text("def test_x(): pass\n", encoding="utf-8")
    return repo


def test_stage09_evidence_context_omits_verbose_codex_transcript(tmp_path: Path) -> None:
    repo = _prepare_stage09_repo(tmp_path)
    evidence = repo / ".sdd" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    huge = "Z" * 300_000
    payload = {
        "task_id": "T014",
        "status": "PASS",
        "checkpoint_commit": "abc123",
        "verification": {"overall": "PASS", "commands": ["python -m pytest -q"]},
        "provider_output": huge,
        "diff": huge,
        "recorded_at": "20260815T021158Z",
    }
    (evidence / "T014.json").write_text(json.dumps(payload), encoding="utf-8")

    runner = StageRunner(Orchestrator(repo))
    req = runner.build_request("09")
    packed = req.runtime_inputs["BUILD_LINT_TYPECHECK_EVIDENCE_IF_APPLICABLE"][".sdd/evidence/T014.json"]

    assert '"task_id":"T014"' in packed
    assert '"status":"PASS"' in packed
    assert '"checkpoint_commit":"abc123"' in packed
    assert "omitted verbose evidence" in packed
    assert huge[:1000] not in packed
    assert len(packed.encode("utf-8")) < 16_500


def test_stage09_includes_t014_evidence_indexes_when_present(tmp_path: Path) -> None:
    repo = _prepare_stage09_repo(tmp_path)
    state = repo / ".sdd" / "state"
    (state / "post-implementation-verification.md").write_text("# Evidence Index\nT014 PASS\n", encoding="utf-8")
    (state / "implementation-state.md").write_text("# Implementation State\nT001-T014 DONE\n", encoding="utf-8")

    req = StageRunner(Orchestrator(repo)).build_request("09")

    assert req.artifacts[".sdd/state/post-implementation-verification.md"].startswith("# Evidence Index")
    assert req.artifacts[".sdd/state/implementation-state.md"].startswith("# Implementation State")


def test_stage09_evidence_context_has_bounded_total_size(tmp_path: Path) -> None:
    repo = _prepare_stage09_repo(tmp_path)
    evidence = repo / ".sdd" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    for i in range(40):
        payload = {
            "task_id": f"T{i:03d}",
            "status": "PASS",
            "provider_output": "X" * 100_000,
            "verification": {"stdout": "Y" * 100_000, "overall": "PASS"},
        }
        (evidence / f"{i:03d}.json").write_text(json.dumps(payload), encoding="utf-8")

    req = StageRunner(Orchestrator(repo)).build_request("09")
    summary = req.runtime_inputs["BUILD_LINT_TYPECHECK_EVIDENCE_IF_APPLICABLE"]
    total = sum(len(v.encode("utf-8")) for v in summary.values())

    assert total < 210_000
    assert "__context_diet__" in summary
