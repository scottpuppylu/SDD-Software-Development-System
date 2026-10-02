"""Minimal Golden Path developer entry: global registration and repo binding."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONTROLLER = "default"
DEFAULT_CONTROLLER_TYPE = "local"
DEFAULT_GOVERNANCE_PROFILE = "auto"
START_MESSAGE = "目前已套用 SDD 進行開發。"


class DeveloperEntryError(RuntimeError):
    """Raised for invalid bootstrap or project-binding operations."""


@dataclass(frozen=True)
class BindingStatus:
    bound: bool
    enabled: bool
    controller: str | None
    governance_profile: str | None
    runtime_path: str | None
    project_yaml: str | None


def global_config_path(config_path: str | Path | None = None) -> Path:
    return Path(config_path).expanduser() if config_path else Path.home() / ".sdd" / "config.yaml"


def resolve_runtime_path(runtime_path: str | Path | None = None) -> Path:
    """Resolve this runtime from its package location, never from a hardcoded path."""
    if runtime_path:
        return Path(runtime_path).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise DeveloperEntryError(f"無法讀取設定：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DeveloperEntryError(f"設定格式必須是 YAML mapping：{path}")
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )


def load_global_config(config_path: str | Path | None = None) -> dict[str, Any]:
    return _read_yaml(global_config_path(config_path))


def bootstrap_global_config(
    config_path: str | Path | None = None,
    runtime_path: str | Path | None = None,
) -> Path:
    """Create or idempotently complete the user-level runtime registry."""
    path = global_config_path(config_path)
    data = _read_yaml(path)
    sdd = data.setdefault("sdd", {})
    if not isinstance(sdd, dict):
        raise DeveloperEntryError("global config 的 sdd 欄位必須是 mapping")
    sdd.setdefault("default_controller", DEFAULT_CONTROLLER)
    sdd.setdefault("controller_type", DEFAULT_CONTROLLER_TYPE)
    sdd.setdefault("runtime_path", str(resolve_runtime_path(runtime_path)))
    _write_yaml(path, data)
    return path


def _repo_path(repo: str | Path) -> Path:
    path = Path(repo).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise DeveloperEntryError(f"target repo 不存在或不是目錄：{path}")
    return path


def project_yaml_path(repo: str | Path) -> Path:
    return _repo_path(repo) / ".sdd" / "project.yaml"


def _project_data(repo: Path) -> dict[str, Any]:
    return _read_yaml(repo / ".sdd" / "project.yaml")


def _ensure_git(repo: Path, initialize_git: bool) -> str:
    git = repo / ".git"
    if git.exists():
        return "existing"
    if not initialize_git:
        return "not_available"
    completed = subprocess.run(
        ["git", "init"], cwd=repo, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise DeveloperEntryError(completed.stderr.strip() or "git init 失敗")
    return "initialized"


def _binding_payload(existing: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    data = dict(existing)
    sdd = data.get("sdd")
    if not isinstance(sdd, dict):
        sdd = {}
    else:
        sdd = dict(sdd)
    sdd.update(
        {
            "enabled": enabled,
            "controller": sdd.get("controller", DEFAULT_CONTROLLER),
            "governance_profile": sdd.get("governance_profile", DEFAULT_GOVERNANCE_PROFILE),
        }
    )
    data["sdd"] = sdd
    return data


def enable_repo(
    repo: str | Path,
    *,
    config_path: str | Path | None = None,
    initialize_git: bool = False,
) -> dict[str, Any]:
    path = _repo_path(repo)
    config = bootstrap_global_config(config_path)
    git_status = _ensure_git(path, initialize_git)
    if git_status == "not_available":
        raise DeveloperEntryError("target repo 尚未有 .git；請明確使用 --init-git 後再啟用 SDD")
    project = path / ".sdd" / "project.yaml"
    existing = _project_data(path)
    _write_yaml(project, _binding_payload(existing, enabled=True))
    status = detect_binding(path, config_path=config)
    return {"config_path": str(config), "project_yaml": str(project), "git_status": git_status, **status}


def rebind_repo(repo: str | Path, *, config_path: str | Path | None = None) -> dict[str, Any]:
    path = _repo_path(repo)
    config = bootstrap_global_config(config_path)
    project = path / ".sdd" / "project.yaml"
    _write_yaml(project, _binding_payload(_project_data(path), enabled=True))
    return {"config_path": str(config), "project_yaml": str(project), **detect_binding(path, config_path=config)}


def unbind_repo(repo: str | Path, *, config_path: str | Path | None = None) -> dict[str, Any]:
    path = _repo_path(repo)
    config = bootstrap_global_config(config_path)
    project = path / ".sdd" / "project.yaml"
    if not project.exists():
        raise DeveloperEntryError("repo 尚未建立 SDD binding")
    _write_yaml(project, _binding_payload(_project_data(path), enabled=False))
    return {"config_path": str(config), "project_yaml": str(project), **detect_binding(path, config_path=config)}


def detect_binding(repo: str | Path, *, config_path: str | Path | None = None) -> dict[str, Any]:
    path = _repo_path(repo)
    project = path / ".sdd" / "project.yaml"
    if not project.exists():
        return {
            "bound": False,
            "enabled": False,
            "sdd_enabled": "NO",
            "binding_status": "UNBOUND",
            "controller": None,
            "governance_profile": None,
            "runtime_path": None,
            "project_yaml": str(project),
        }
    data = _project_data(path)
    sdd = data.get("sdd") if isinstance(data.get("sdd"), dict) else {}
    config = load_global_config(config_path)
    global_sdd = config.get("sdd") if isinstance(config.get("sdd"), dict) else {}
    controller = sdd.get("controller", DEFAULT_CONTROLLER)
    enabled = bool(sdd.get("enabled", False))
    return {
        "bound": enabled,
        "enabled": enabled,
        "sdd_enabled": "YES" if enabled else "NO",
        "binding_status": "BOUND" if enabled else "UNBOUND",
        "controller": controller,
        "governance_profile": sdd.get("governance_profile", DEFAULT_GOVERNANCE_PROFILE),
        "runtime_path": global_sdd.get("runtime_path"),
        "project_yaml": str(project),
    }


def start_message() -> str:
    return START_MESSAGE
