import subprocess
from pathlib import Path

import yaml

from sdd_orchestrator.developer_entry import (
    bootstrap_global_config,
    detect_binding,
    enable_repo,
    rebind_repo,
    unbind_repo,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("keep\n", encoding="utf-8")
    return repo


def test_global_config_first_create_and_idempotent(tmp_path):
    config = tmp_path / ".sdd" / "config.yaml"
    bootstrap_global_config(config, runtime_path=tmp_path / "runtime")
    first = yaml.safe_load(config.read_text(encoding="utf-8"))
    first["sdd"]["custom"] = "preserve"
    config.write_text(yaml.safe_dump(first, sort_keys=False), encoding="utf-8")
    bootstrap_global_config(config, runtime_path=tmp_path / "other")
    second = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert second["sdd"]["custom"] == "preserve"
    assert second["sdd"]["runtime_path"] == str((tmp_path / "runtime").resolve())
    assert second["sdd"]["default_controller"] == "default"
    assert second["sdd"]["controller_type"] == "local"


def test_enable_detect_reenable_and_unrelated_files_unchanged(tmp_path):
    repo = _repo(tmp_path)
    config = tmp_path / "global.yaml"
    readme_before = (repo / "README.md").read_bytes()
    result = enable_repo(repo, config_path=config)
    assert result["bound"] is True
    assert result["git_status"] == "existing"
    project = repo / ".sdd" / "project.yaml"
    assert yaml.safe_load(project.read_text(encoding="utf-8")) == {
        "sdd": {"enabled": True, "controller": "default", "governance_profile": "auto"}
    }
    enable_repo(repo, config_path=config)
    assert (repo / "README.md").read_bytes() == readme_before
    status = detect_binding(repo, config_path=config)
    assert status["controller"] == "default"
    assert status["governance_profile"] == "auto"


def test_invalid_repo_path(tmp_path):
    try:
        enable_repo(tmp_path / "missing", config_path=tmp_path / "global.yaml")
    except RuntimeError as exc:
        assert "不存在" in str(exc)
    else:
        raise AssertionError("missing repo should fail")


def test_rebind_and_reversible_unbind(tmp_path):
    repo = _repo(tmp_path)
    config = tmp_path / "global.yaml"
    enable_repo(repo, config_path=config)
    rebind = rebind_repo(repo, config_path=config)
    assert rebind["bound"] is True
    unbound = unbind_repo(repo, config_path=config)
    assert unbound["bound"] is False
    raw = yaml.safe_load((repo / ".sdd" / "project.yaml").read_text(encoding="utf-8"))
    assert raw["sdd"]["enabled"] is False
    assert (repo / ".git").exists()
