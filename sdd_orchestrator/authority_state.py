"""Deterministic, non-authoritative authority-state bootstrap (TC019)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Callable
from urllib.parse import urlsplit

import yaml


SCHEMA_VERSION = "1.0"
GENERATOR_ID = "TC019-AUTHORITY-STATE-CLEAN-CLONE-BOOTSTRAP"
FINAL_DECISION_STATUSES = {
    "APPROVED",
    "REJECTED",
    "REVISION_REQUESTED",
    "WITHDRAWN",
}
DECISION_TYPES = {
    "PRODUCT_DECISION",
    "AUTHORITY_CONFLICT",
    "BLOCKING_TBD",
    "HIGH_RISK_OPERATION",
    "RELEASE_DECISION",
}
DECISION_ID = re.compile(r"HD-[A-Z0-9][A-Z0-9_-]*")
EXPECTED_TOP_LEVEL = {
    "schema_version",
    "domain_owners",
    "unresolved_conflicts",
    "blocking_tbds",
    "resolved_human_decisions",
    "bootstrap_provenance",
}


class AuthorityStateBootstrapError(RuntimeError):
    """Raised when repository facts cannot safely produce runtime state."""


class AuthorityStateValidationError(AuthorityStateBootstrapError):
    """Raised when authority-state data violates the canonical schema."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthorityStateValidationError(f"{label} must be a mapping")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise AuthorityStateValidationError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise AuthorityStateValidationError(f"{label} contains duplicate values")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unexpected = sorted(set(value) - expected)
        raise AuthorityStateValidationError(
            f"{label} schema mismatch: missing={missing}, unexpected={unexpected}"
        )


def validate_authority_state(data: Any) -> dict[str, Any]:
    """Validate structure only; this function grants no authority."""
    root = _mapping(data, "authority state")
    _exact_keys(root, EXPECTED_TOP_LEVEL, "authority state")
    if root["schema_version"] != SCHEMA_VERSION:
        raise AuthorityStateValidationError(
            f"unsupported authority-state schema: {root['schema_version']!r}"
        )

    owners = _mapping(root["domain_owners"], "domain_owners")
    if not owners or any(
        not isinstance(domain, str)
        or not domain
        or not isinstance(owner, str)
        or not owner
        for domain, owner in owners.items()
    ):
        raise AuthorityStateValidationError("domain_owners must contain string mappings")
    if list(owners) != sorted(owners):
        raise AuthorityStateValidationError("domain_owners must be sorted by domain")

    conflict_keys = {
        "conflict_id", "authority_domains", "owner_stages", "affected_artifacts", "status"
    }
    for index, item in enumerate(root["unresolved_conflicts"]):
        record = _mapping(item, f"unresolved_conflicts[{index}]")
        _exact_keys(record, conflict_keys, f"unresolved_conflicts[{index}]")
        if record["status"] != "PENDING" or not DECISION_ID.fullmatch(record["conflict_id"]):
            raise AuthorityStateValidationError("unresolved conflict identity/status is invalid")
        _string_list(record["authority_domains"], "conflict authority_domains")
        _string_list(record["owner_stages"], "conflict owner_stages")
        _string_list(record["affected_artifacts"], "conflict affected_artifacts")

    tbd_keys = {"tbd_id", "authority_domains", "owner_stages", "affected_artifacts", "status"}
    for index, item in enumerate(root["blocking_tbds"]):
        record = _mapping(item, f"blocking_tbds[{index}]")
        _exact_keys(record, tbd_keys, f"blocking_tbds[{index}]")
        if record["status"] != "PENDING" or not DECISION_ID.fullmatch(record["tbd_id"]):
            raise AuthorityStateValidationError("blocking TBD identity/status is invalid")
        _string_list(record["authority_domains"], "TBD authority_domains")
        _string_list(record["owner_stages"], "TBD owner_stages")
        _string_list(record["affected_artifacts"], "TBD affected_artifacts")

    resolved_keys = {
        "decision_id", "status", "authority_domains", "owner_stages", "resolution",
        "record_version", "resolved_at", "invalidated_dependents",
    }
    for index, item in enumerate(root["resolved_human_decisions"]):
        record = _mapping(item, f"resolved_human_decisions[{index}]")
        _exact_keys(record, resolved_keys, f"resolved_human_decisions[{index}]")
        if record["status"] not in FINAL_DECISION_STATUSES:
            raise AuthorityStateValidationError("resolved decision has a non-final status")
        if record["resolution"] != record["status"]:
            raise AuthorityStateValidationError("resolved decision status/resolution disagree")
        if not DECISION_ID.fullmatch(record["decision_id"]):
            raise AuthorityStateValidationError("resolved decision identity is invalid")
        if not isinstance(record["record_version"], int) or record["record_version"] < 2:
            raise AuthorityStateValidationError("resolved decision version is invalid")
        if not isinstance(record["resolved_at"], str) or not record["resolved_at"]:
            raise AuthorityStateValidationError("resolved decision timestamp is missing")
        _string_list(record["authority_domains"], "resolved authority_domains")
        _string_list(record["owner_stages"], "resolved owner_stages")
        _string_list(record["invalidated_dependents"], "resolved invalidated_dependents")

    provenance = _mapping(root["bootstrap_provenance"], "bootstrap_provenance")
    _exact_keys(
        provenance,
        {"generator", "repository", "branch", "head_commit", "input_sha256"},
        "bootstrap_provenance",
    )
    if provenance["generator"] != GENERATOR_ID:
        raise AuthorityStateValidationError("unexpected authority-state generator")
    for field in ("repository", "branch"):
        if not isinstance(provenance[field], str) or not provenance[field]:
            raise AuthorityStateValidationError(f"bootstrap_provenance.{field} is invalid")
    if not isinstance(provenance["head_commit"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", provenance["head_commit"]
    ):
        raise AuthorityStateValidationError("bootstrap_provenance.head_commit is invalid")
    digests = _mapping(provenance["input_sha256"], "bootstrap_provenance.input_sha256")
    if not digests or list(digests) != sorted(digests):
        raise AuthorityStateValidationError("input_sha256 must be non-empty and sorted")
    if any(
        not isinstance(path, str)
        or not path
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        for path, digest in digests.items()
    ):
        raise AuthorityStateValidationError("input_sha256 contains an invalid entry")
    return root


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise AuthorityStateBootstrapError(detail)
    return result


def _normalize_owner(value: Any) -> str:
    owner = str(value).strip()
    if not owner:
        raise AuthorityStateBootstrapError("authority domain owner is empty")
    return owner.zfill(2) if owner.isdigit() else owner


def _repository_identity(remote: str) -> str:
    remote = remote.strip()
    if "://" in remote:
        parsed = urlsplit(remote)
        if not parsed.hostname or not parsed.path.strip("/"):
            raise AuthorityStateBootstrapError("origin remote cannot establish repository identity")
        identity = f"{parsed.hostname.lower()}/{parsed.path.strip('/')}"
    elif re.fullmatch(r"[^@\s]+@[^:\s]+:.+", remote):
        host_path = remote.split("@", 1)[1]
        host, path = host_path.split(":", 1)
        identity = f"{host.lower()}/{path.strip('/')}"
    else:
        raise AuthorityStateBootstrapError("origin remote must be a credential-safe network identity")
    return identity[:-4] if identity.endswith(".git") else identity


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise AuthorityStateBootstrapError(f"required structured input is missing or unsafe: {label}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AuthorityStateBootstrapError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityStateBootstrapError(f"{label} must be a YAML mapping")
    return value


def _input_paths(repo: Path) -> list[Path]:
    decisions = repo / ".sdd" / "decisions"
    if not decisions.is_dir() or decisions.is_symlink():
        raise AuthorityStateBootstrapError("canonical .sdd/decisions store is missing or unsafe")
    return [
        repo / ".sdd" / "system.yaml",
        repo / ".sdd" / "state" / "project-state.yaml",
        *sorted(decisions.glob("HD-*.yaml")),
    ]


def _snapshot_inputs(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in _input_paths(repo):
        resolved = path.resolve()
        if repo != resolved and repo not in resolved.parents:
            raise AuthorityStateBootstrapError(f"structured input escapes repository: {path}")
        if not path.is_file() or path.is_symlink():
            raise AuthorityStateBootstrapError(f"structured input is missing or unsafe: {path}")
        relative = path.relative_to(repo).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(result.items()))


def _validate_git(repo: Path, target: Path) -> dict[str, str]:
    if not repo.is_dir() or repo.is_symlink():
        raise AuthorityStateBootstrapError("repository root is missing or unsafe")
    top = Path(_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != repo:
        raise AuthorityStateBootstrapError("--repo must identify the exact Git root")
    head = _git(repo, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    branch = _git(repo, "branch", "--show-current").stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not branch:
        raise AuthorityStateBootstrapError("bootstrap requires a named branch and valid Git HEAD")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout:
        raise AuthorityStateBootstrapError("bootstrap requires a clean worktree")
    relative_target = target.relative_to(repo).as_posix()
    if _git(repo, "ls-files", "--error-unmatch", "--", relative_target, check=False).returncode == 0:
        raise AuthorityStateBootstrapError("authority-state.yaml must remain untracked")
    if _git(repo, "check-ignore", "-q", "--", relative_target, check=False).returncode != 0:
        raise AuthorityStateBootstrapError("authority-state.yaml must remain protected by .gitignore")
    remote = _git(repo, "remote", "get-url", "origin").stdout.strip()
    return {
        "repository": _repository_identity(remote),
        "branch": branch,
        "head_commit": head,
    }


def _validate_decision(
    path: Path, data: dict[str, Any], owners: dict[str, str]
) -> dict[str, Any]:
    required = {
        "decision_id", "status", "created_at", "resolved_at", "decision_type",
        "source_stage", "authority_domains", "owner_stages", "question", "context",
        "options", "risk", "affected_artifacts", "resolution", "resolution_note",
        "record_version", "events",
    }
    missing = sorted(required - set(data))
    if missing:
        raise AuthorityStateBootstrapError(f"decision {path.name} lacks required fields: {missing}")
    identity = data["decision_id"]
    if not isinstance(identity, str) or not DECISION_ID.fullmatch(identity):
        raise AuthorityStateBootstrapError(f"decision {path.name} has an invalid identity")
    if path.name != f"{identity}.yaml":
        raise AuthorityStateBootstrapError(f"decision filename/identity mismatch: {path.name}")
    status = data["status"]
    if status not in {"PENDING", *FINAL_DECISION_STATUSES}:
        raise AuthorityStateBootstrapError(f"decision {identity} has an invalid status")
    if data["decision_type"] not in DECISION_TYPES:
        raise AuthorityStateBootstrapError(f"decision {identity} has an invalid type")
    domains = _string_list(data["authority_domains"], f"decision {identity} authority_domains")
    owner_stages = _string_list(data["owner_stages"], f"decision {identity} owner_stages")
    expected_owners: list[str] = []
    for domain in domains:
        if domain not in owners:
            raise AuthorityStateBootstrapError(f"decision {identity} names an unknown authority domain")
        expected_owners.append(owners[domain])
    if sorted(owner_stages) != sorted(set(expected_owners)):
        raise AuthorityStateBootstrapError(f"decision {identity} owner stages contradict system.yaml")
    affected = _string_list(data["affected_artifacts"], f"decision {identity} affected_artifacts")
    version = data["record_version"]
    events = data["events"]
    if not isinstance(version, int) or version < 1 or not isinstance(events, list) or not events:
        raise AuthorityStateBootstrapError(f"decision {identity} version/events are invalid")
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict) or event.get("sequence") != index:
            raise AuthorityStateBootstrapError(f"decision {identity} event sequence is invalid")
        if event.get("record_version") != index:
            raise AuthorityStateBootstrapError(f"decision {identity} event version is invalid")
    if version != len(events) or events[-1].get("status") != status:
        raise AuthorityStateBootstrapError(f"decision {identity} record/event state contradicts")
    if status == "PENDING":
        if data["resolution"] is not None or data["resolved_at"] is not None or version != 1:
            raise AuthorityStateBootstrapError(f"pending decision {identity} contains resolution facts")
    else:
        if data["resolution"] != status or not isinstance(data["resolved_at"], str) or not data["resolved_at"]:
            raise AuthorityStateBootstrapError(f"final decision {identity} resolution facts contradict")
    invalidated = data.get("invalidated_dependents", [])
    _string_list(invalidated, f"decision {identity} invalidated_dependents")
    return {
        "decision_id": identity,
        "status": status,
        "decision_type": data["decision_type"],
        "authority_domains": sorted(domains),
        "owner_stages": sorted(owner_stages),
        "affected_artifacts": sorted(affected),
        "resolution": data["resolution"],
        "record_version": version,
        "resolved_at": data["resolved_at"],
        "invalidated_dependents": sorted(invalidated),
    }


def _validate_blocker_consistency(project: dict[str, Any], decisions: list[dict[str, Any]]) -> None:
    blocking = project.get("blocking")
    if not isinstance(blocking, dict):
        raise AuthorityStateBootstrapError("project-state blocking section is missing")
    reasons = blocking.get("reasons")
    if not isinstance(blocking.get("is_blocked"), bool) or not isinstance(reasons, list):
        raise AuthorityStateBootstrapError("project-state blocker facts are malformed")
    if any(not isinstance(reason, str) or not reason for reason in reasons):
        raise AuthorityStateBootstrapError("project-state blocker reason is malformed")
    if blocking["is_blocked"] != bool(reasons):
        raise AuthorityStateBootstrapError("project-state blocker flag/reasons contradict")

    by_id = {item["decision_id"]: item for item in decisions}
    pending = {identity for identity, item in by_id.items() if item["status"] == "PENDING"}
    for identity in pending:
        if f"HUMAN_DECISION:{identity}" not in reasons:
            raise AuthorityStateBootstrapError(f"pending decision lacks project blocker: {identity}")
    for reason in reasons:
        if reason.startswith("HUMAN_DECISION:"):
            identity = reason.split(":", 1)[1]
            if identity not in pending:
                raise AuthorityStateBootstrapError(f"unmatched Human Decision blocker: {identity}")
        elif reason.startswith("AUTHORITY_CONFLICT:"):
            identity = reason.split(":", 1)[1]
            item = by_id.get(identity)
            if not item or item["status"] != "PENDING" or item["decision_type"] != "AUTHORITY_CONFLICT":
                raise AuthorityStateBootstrapError(f"unmatched authority conflict blocker: {identity}")
        elif reason.startswith("BLOCKING_TBD:"):
            identity = reason.split(":", 1)[1]
            item = by_id.get(identity)
            if not item or item["status"] != "PENDING" or item["decision_type"] != "BLOCKING_TBD":
                raise AuthorityStateBootstrapError(f"unmatched blocking TBD: {identity}")


def derive_authority_state(repo: Path, git_identity: dict[str, str], inputs: dict[str, str]) -> dict[str, Any]:
    system = _load_yaml(repo / ".sdd" / "system.yaml", ".sdd/system.yaml")
    configured = system.get("authority_domains")
    if not isinstance(configured, dict) or not configured:
        raise AuthorityStateBootstrapError("system.yaml authority_domains is missing")
    owners: dict[str, str] = {}
    for domain in sorted(configured):
        entry = configured[domain]
        if not isinstance(domain, str) or not domain or not isinstance(entry, dict) or "owner_stage" not in entry:
            raise AuthorityStateBootstrapError("system.yaml contains an invalid authority domain")
        owners[domain] = _normalize_owner(entry["owner_stage"])

    decisions: list[dict[str, Any]] = []
    for path in sorted((repo / ".sdd" / "decisions").glob("HD-*.yaml")):
        decisions.append(_validate_decision(path, _load_yaml(path, path.name), owners))
    project = _load_yaml(
        repo / ".sdd" / "state" / "project-state.yaml", ".sdd/state/project-state.yaml"
    )
    _validate_blocker_consistency(project, decisions)

    unresolved = [
        {
            "conflict_id": item["decision_id"],
            "authority_domains": item["authority_domains"],
            "owner_stages": item["owner_stages"],
            "affected_artifacts": item["affected_artifacts"],
            "status": "PENDING",
        }
        for item in decisions
        if item["status"] == "PENDING" and item["decision_type"] == "AUTHORITY_CONFLICT"
    ]
    tbds = [
        {
            "tbd_id": item["decision_id"],
            "authority_domains": item["authority_domains"],
            "owner_stages": item["owner_stages"],
            "affected_artifacts": item["affected_artifacts"],
            "status": "PENDING",
        }
        for item in decisions
        if item["status"] == "PENDING" and item["decision_type"] == "BLOCKING_TBD"
    ]
    resolved = [
        {
            "decision_id": item["decision_id"],
            "status": item["status"],
            "authority_domains": item["authority_domains"],
            "owner_stages": item["owner_stages"],
            "resolution": item["resolution"],
            "record_version": item["record_version"],
            "resolved_at": item["resolved_at"],
            "invalidated_dependents": item["invalidated_dependents"],
        }
        for item in decisions
        if item["status"] in FINAL_DECISION_STATUSES
    ]
    state = {
        "schema_version": SCHEMA_VERSION,
        "domain_owners": owners,
        "unresolved_conflicts": unresolved,
        "blocking_tbds": tbds,
        "resolved_human_decisions": resolved,
        "bootstrap_provenance": {
            "generator": GENERATOR_ID,
            **git_identity,
            "input_sha256": inputs,
        },
    }
    return validate_authority_state(state)


def _serialize(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def bootstrap_authority_state(
    repo_root: str | Path,
    *,
    snapshot_reader: Callable[[Path], dict[str, str]] = _snapshot_inputs,
) -> dict[str, Any]:
    """Create only the deterministic projection authorized by TC019."""
    repo = Path(repo_root).resolve()
    target = repo / ".sdd" / "state" / "authority-state.yaml"
    git_identity = _validate_git(repo, target)
    before = snapshot_reader(repo)
    state = derive_authority_state(repo, git_identity, before)
    after = snapshot_reader(repo)
    if before != after:
        raise AuthorityStateBootstrapError("structured authority inputs changed during bootstrap")
    if _validate_git(repo, target) != git_identity:
        raise AuthorityStateBootstrapError("repository identity changed during bootstrap")
    payload = _serialize(state)

    if target.exists():
        existing = target.read_bytes()
        try:
            parsed = yaml.safe_load(existing.decode("utf-8"))
            validate_authority_state(parsed)
        except (UnicodeError, yaml.YAMLError, AuthorityStateValidationError) as exc:
            raise AuthorityStateBootstrapError(
                "existing authority-state.yaml is invalid and will not be overwritten"
            ) from exc
        if existing != payload:
            raise AuthorityStateBootstrapError(
                "existing authority-state.yaml does not match current repository inputs"
            )
        return {
            "status": "PRESERVED",
            "path": target.relative_to(repo).as_posix(),
            "head_commit": git_identity["head_commit"],
            "sha256": hashlib.sha256(existing).hexdigest(),
        }

    _atomic_write(target, payload)
    if _git(repo, "ls-files", "--error-unmatch", "--", target.relative_to(repo).as_posix(), check=False).returncode == 0:
        raise AuthorityStateBootstrapError("bootstrap unexpectedly created tracked authority state")
    return {
        "status": "CREATED",
        "path": target.relative_to(repo).as_posix(),
        "head_commit": git_identity["head_commit"],
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
