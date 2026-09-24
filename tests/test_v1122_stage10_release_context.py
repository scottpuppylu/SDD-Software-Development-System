from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.runner import StageRunner

SOURCE_ROOT = Path(__file__).resolve().parents[1]


STAGE10_SEMANTICS = {
    "RELEASE_IDENTITY": "inspect repository release evidence",
    "TARGET_ENVIRONMENT": "inspect explicit target evidence",
    "DEPLOYMENT_TARGET": "inspect explicit target evidence",
    "BUILD_CI_EVIDENCE": "inspect explicit CI/build evidence",
    "SECURITY_EVIDENCE": "use Stage 09 security evidence",
    "DOCUMENTATION_READINESS": "inspect repository docs",
    "MIGRATION_READINESS_IF_APPLICABLE": "inspect explicit migration applicability",
    "DEPLOYMENT_READINESS": "inspect local installation/deployment evidence",
    "ROLLBACK_RECOVERY_READINESS": "inspect rollback/recovery evidence",
}


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True,
        encoding="utf-8", errors="replace", check=True,
    )
    return (proc.stdout or "").strip()


def _prepare_stage10_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(SOURCE_ROOT / ".sdd", repo / ".sdd")
    for rel in ["docs/handoff/verification-report.md"]:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Stage 09\nPASS\n", encoding="utf-8")
    (repo / "README.md").write_text("# Local CLI\nInstall locally.\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname="todo-cli"\nversion="0.1.0"\n', encoding="utf-8")
    profile = repo / "docs/handoff/release-profile.md"
    profile.write_text(
        "# Release Profile\n"
        "Version: 0.1.0\nBranch: master\nTarget: local CLI\n"
        "CI = N/A\nMigration = N/A\nSecrets = NONE\n"
        "Rollback: restore SQLite backup.\n",
        encoding="utf-8",
    )
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "release evidence")
    Orchestrator(repo).record_stage_result("09", "PASS")
    return repo


def test_stage10_includes_release_profile_readme_and_pyproject(tmp_path: Path) -> None:
    repo = _prepare_stage10_repo(tmp_path)
    req = StageRunner(Orchestrator(repo)).build_request("10", semantic_inputs=STAGE10_SEMANTICS)

    assert "README.md" in req.artifacts
    assert "pyproject.toml" in req.artifacts
    assert "docs/handoff/release-profile.md" in req.artifacts
    assert "CI = N/A" in req.artifacts["docs/handoff/release-profile.md"]
    assert 'version="0.1.0"' in req.artifacts["pyproject.toml"]


def test_stage10_includes_live_git_release_identity(tmp_path: Path) -> None:
    repo = _prepare_stage10_repo(tmp_path)
    req = StageRunner(Orchestrator(repo)).build_request("10", semantic_inputs=STAGE10_SEMANTICS)
    identity = req.runtime_inputs["RELEASE_GIT_IDENTITY"]

    assert identity["branch"] in {"master", "main"}
    assert identity["head_commit"] == _git(repo, "rev-parse", "HEAD")
    assert "release evidence" in identity["recent_commits"]
    assert "STAGE10_CONTEXT_POLICY" in req.runtime_inputs


def test_stage10_release_context_is_bounded(tmp_path: Path) -> None:
    repo = _prepare_stage10_repo(tmp_path)
    (repo / "README.md").write_text("R" * 200_000, encoding="utf-8")
    req = StageRunner(Orchestrator(repo)).build_request("10", semantic_inputs=STAGE10_SEMANTICS)

    packed = req.artifacts["README.md"]
    assert len(packed.encode("utf-8")) < 70_000
    assert "<omitted: Stage 10 file limit>" in packed
