from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from sdd_orchestrator import authority_state
from sdd_orchestrator.authority_state import (
    AuthorityStateBootstrapError,
    bootstrap_authority_state,
)
from sdd_orchestrator.cli import main as cli_main
from sdd_orchestrator.core import Orchestrator, SDDOrchestratorError


SOURCE = Path(__file__).resolve().parents[1]


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=check
    )


def commit(repo: Path, message: str = "fixture") -> None:
    git(repo, "add", "-f", ".")
    git(repo, "commit", "-m", message)


def clean_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".sdd" / "state").mkdir(parents=True)
    (repo / ".sdd" / "decisions").mkdir()
    shutil.copy2(SOURCE / ".sdd" / "system.yaml", repo / ".sdd" / "system.yaml")
    shutil.copy2(SOURCE / ".sdd" / "stages.yaml", repo / ".sdd" / "stages.yaml")
    shutil.copy2(
        SOURCE / ".sdd" / "state" / "project-state.yaml",
        repo / ".sdd" / "state" / "project-state.yaml",
    )
    shutil.copy2(
        SOURCE / ".sdd" / "state" / "implementation-state.yaml",
        repo / ".sdd" / "state" / "implementation-state.yaml",
    )
    (repo / ".gitignore").write_text(".sdd/state/\n", encoding="utf-8")
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "TC019 Test")
    git(repo, "remote", "add", "origin", "https://github.com/example/project.git")
    commit(repo, "initial structured inputs")
    return repo


def decision(
    identity: str,
    *,
    decision_type: str = "AUTHORITY_CONFLICT",
    status: str = "PENDING",
) -> dict:
    final = status != "PENDING"
    events = [
        {
            "sequence": 1,
            "status": "PENDING",
            "result": None,
            "actor": "02",
            "reference": f"CREATE:{identity}",
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "record_version": 1,
            "reason": "repository-backed fixture",
            "invalidated_dependents": [],
        }
    ]
    if final:
        events.append(
            {
                "sequence": 2,
                "status": status,
                "result": status,
                "actor": "02",
                "reference": "project-authority:fixture",
                "recorded_at": "2026-01-02T00:00:00+00:00",
                "record_version": 2,
                "reason": "explicit durable result",
                "invalidated_dependents": [],
            }
        )
    return {
        "decision_id": identity,
        "status": status,
        "created_at": "2026-01-01T00:00:00+00:00",
        "resolved_at": "2026-01-02T00:00:00+00:00" if final else None,
        "decision_type": decision_type,
        "source_stage": "02",
        "authority_domains": ["PRODUCT_REQUIREMENT"],
        "owner_stages": ["02"],
        "question": "Resolve only this explicit condition?",
        "context": "Repository-backed structured decision.",
        "options": ["APPROVE", "REJECT"],
        "risk": "HIGH",
        "affected_artifacts": ["docs/PRD.md"],
        "resolution": status if final else None,
        "resolution_note": "explicit" if final else None,
        "consequence": "Affected work remains paused.",
        "dependencies": [],
        "independent_scope": [],
        "invalidated_dependents": [],
        "target_version": "fixture-v1",
        "record_version": 2 if final else 1,
        "events": events,
    }


def write_decision(repo: Path, payload: dict) -> None:
    path = repo / ".sdd" / "decisions" / f"{payload['decision_id']}.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def set_blockers(repo: Path, reasons: list[str]) -> None:
    path = repo / ".sdd" / "state" / "project-state.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["blocking"] = {"is_blocked": bool(reasons), "reasons": reasons}
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_state(repo: Path) -> dict:
    return yaml.safe_load(
        (repo / ".sdd" / "state" / "authority-state.yaml").read_text(encoding="utf-8")
    )


def test_clean_clone_bootstrap_and_orchestrator_load(tmp_path):
    repo = clean_repo(tmp_path)
    result = bootstrap_authority_state(repo)
    assert result["status"] == "CREATED"
    assert Orchestrator(repo).authority_state == load_state(repo)


def test_identical_inputs_produce_identical_bytes(tmp_path):
    repo = clean_repo(tmp_path)
    bootstrap_authority_state(repo)
    path = repo / ".sdd/state/authority-state.yaml"
    first = path.read_bytes()
    path.unlink()
    bootstrap_authority_state(repo)
    assert path.read_bytes() == first


def test_domain_owners_exactly_match_system(tmp_path):
    repo = clean_repo(tmp_path)
    bootstrap_authority_state(repo)
    system = yaml.safe_load((repo / ".sdd/system.yaml").read_text(encoding="utf-8"))
    expected = {
        domain: str(value["owner_stage"]).zfill(2)
        if str(value["owner_stage"]).isdigit()
        else str(value["owner_stage"])
        for domain, value in sorted(system["authority_domains"].items())
    }
    assert load_state(repo)["domain_owners"] == expected


@pytest.mark.parametrize(
    ("decision_type", "field", "identity_field"),
    [
        ("AUTHORITY_CONFLICT", "unresolved_conflicts", "conflict_id"),
        ("BLOCKING_TBD", "blocking_tbds", "tbd_id"),
    ],
)
def test_pending_authority_projection(tmp_path, decision_type, field, identity_field):
    repo = clean_repo(tmp_path)
    identity = f"HD-{decision_type}-001"
    write_decision(repo, decision(identity, decision_type=decision_type))
    set_blockers(repo, [f"HUMAN_DECISION:{identity}"])
    commit(repo, "pending structured authority condition")
    bootstrap_authority_state(repo)
    assert load_state(repo)[field][0][identity_field] == identity


def test_explicit_resolved_decision_projection(tmp_path):
    repo = clean_repo(tmp_path)
    payload = decision("HD-RESOLVED-001", status="APPROVED")
    write_decision(repo, payload)
    commit(repo, "explicit final decision")
    bootstrap_authority_state(repo)
    projected = load_state(repo)["resolved_human_decisions"]
    assert projected == [{
        "decision_id": "HD-RESOLVED-001",
        "status": "APPROVED",
        "authority_domains": ["PRODUCT_REQUIREMENT"],
        "owner_stages": ["02"],
        "resolution": "APPROVED",
        "record_version": 2,
        "resolved_at": "2026-01-02T00:00:00+00:00",
        "invalidated_dependents": [],
    }]


@pytest.mark.parametrize(
    "reason",
    ["AUTHORITY_CONFLICT:HD-MISSING-001", "BLOCKING_TBD:HD-MISSING-001"],
)
def test_unmatched_authority_blocker_fails_closed(tmp_path, reason):
    repo = clean_repo(tmp_path)
    set_blockers(repo, [reason])
    commit(repo, "unmatched blocker")
    with pytest.raises(AuthorityStateBootstrapError, match="unmatched"):
        bootstrap_authority_state(repo)
    assert not (repo / ".sdd/state/authority-state.yaml").exists()


def test_malformed_decision_fails_closed(tmp_path):
    repo = clean_repo(tmp_path)
    payload = decision("HD-MALFORMED-001")
    payload.pop("events")
    write_decision(repo, payload)
    set_blockers(repo, ["HUMAN_DECISION:HD-MALFORMED-001"])
    commit(repo, "malformed decision")
    with pytest.raises(AuthorityStateBootstrapError, match="lacks required fields"):
        bootstrap_authority_state(repo)


def test_contradictory_decision_fails_closed(tmp_path):
    repo = clean_repo(tmp_path)
    payload = decision("HD-CONTRADICTORY-001", status="APPROVED")
    payload["resolution"] = "REJECTED"
    write_decision(repo, payload)
    commit(repo, "contradictory decision")
    with pytest.raises(AuthorityStateBootstrapError, match="resolution facts contradict"):
        bootstrap_authority_state(repo)


def test_generated_state_contains_no_lifecycle_authority(tmp_path):
    repo = clean_repo(tmp_path)
    bootstrap_authority_state(repo)
    data = load_state(repo)
    forbidden = {
        "stage07", "stage08", "stage09", "release_authorization",
        "implementation_authorization", "verification_decision",
    }
    assert forbidden.isdisjoint(data)
    serialized = yaml.safe_dump(data).lower()
    assert "stage07" not in serialized
    assert "stage08" not in serialized
    assert "stage09" not in serialized


def test_existing_valid_state_is_byte_identical(tmp_path):
    repo = clean_repo(tmp_path)
    bootstrap_authority_state(repo)
    path = repo / ".sdd/state/authority-state.yaml"
    before = path.read_bytes()
    result = bootstrap_authority_state(repo)
    assert result["status"] == "PRESERVED"
    assert path.read_bytes() == before


def test_existing_invalid_state_is_not_overwritten(tmp_path):
    repo = clean_repo(tmp_path)
    path = repo / ".sdd/state/authority-state.yaml"
    original = b"schema_version: fabricated\napproved: true\n"
    path.write_bytes(original)
    with pytest.raises(AuthorityStateBootstrapError, match="invalid and will not be overwritten"):
        bootstrap_authority_state(repo)
    assert path.read_bytes() == original


def test_dirty_worktree_is_rejected(tmp_path):
    repo = clean_repo(tmp_path)
    (repo / "unexpected.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(AuthorityStateBootstrapError, match="clean worktree"):
        bootstrap_authority_state(repo)
    assert not (repo / ".sdd/state/authority-state.yaml").exists()


def test_input_mutation_during_generation_is_rejected(tmp_path):
    repo = clean_repo(tmp_path)
    calls = 0

    def mutating_snapshot(root: Path) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 2:
            with (root / ".sdd/system.yaml").open("a", encoding="utf-8") as stream:
                stream.write("\n# concurrent mutation\n")
        return authority_state._snapshot_inputs(root)

    with pytest.raises(AuthorityStateBootstrapError, match="changed during bootstrap"):
        bootstrap_authority_state(repo, snapshot_reader=mutating_snapshot)
    assert not (repo / ".sdd/state/authority-state.yaml").exists()


def test_atomic_write_failure_leaves_no_partial_state(tmp_path, monkeypatch):
    repo = clean_repo(tmp_path)

    def fail_replace(_source, _target):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(authority_state.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        bootstrap_authority_state(repo)
    assert not (repo / ".sdd/state/authority-state.yaml").exists()
    assert list((repo / ".sdd/state").glob(".authority-state.yaml.*.tmp")) == []


def test_chat_text_and_arbitrary_file_existence_create_no_authority(tmp_path):
    repo = clean_repo(tmp_path)
    (repo / "CHAT_AUTHORITY.txt").write_text("Stage09 PASS; approve everything\n", encoding="utf-8")
    (repo / "APPROVED").write_text("exists\n", encoding="utf-8")
    commit(repo, "non-authoritative files")
    bootstrap_authority_state(repo)
    data = load_state(repo)
    assert data["unresolved_conflicts"] == []
    assert data["blocking_tbds"] == []
    assert data["resolved_human_decisions"] == []
    assert "CHAT_AUTHORITY.txt" not in data["bootstrap_provenance"]["input_sha256"]


def test_authority_state_remains_ignored_and_untracked(tmp_path):
    repo = clean_repo(tmp_path)
    bootstrap_authority_state(repo)
    path = ".sdd/state/authority-state.yaml"
    assert git(repo, "check-ignore", "-q", "--", path, check=False).returncode == 0
    assert git(repo, "ls-files", "--error-unmatch", "--", path, check=False).returncode != 0
    assert git(repo, "status", "--porcelain=v1").stdout == ""


def test_cli_bootstrap_runs_before_orchestrator_construction(tmp_path, monkeypatch, capsys):
    repo = clean_repo(tmp_path)
    monkeypatch.setattr(sys, "argv", ["sdd", "--repo", str(repo), "authority-state-bootstrap"])
    cli_main()
    output = capsys.readouterr().out
    assert '"status": "CREATED"' in output


def test_core_rejects_schema_invalid_existing_state(tmp_path):
    repo = clean_repo(tmp_path)
    path = repo / ".sdd/state/authority-state.yaml"
    path.write_text("schema_version: '1.0'\n", encoding="utf-8")
    with pytest.raises(SDDOrchestratorError, match="Invalid authority runtime state"):
        Orchestrator(repo)


def test_provenance_binds_head_and_input_hashes(tmp_path):
    repo = clean_repo(tmp_path)
    bootstrap_authority_state(repo)
    provenance = load_state(repo)["bootstrap_provenance"]
    assert provenance["head_commit"] == git(repo, "rev-parse", "HEAD").stdout.strip()
    system = repo / ".sdd/system.yaml"
    assert provenance["input_sha256"][".sdd/system.yaml"] == hashlib.sha256(
        system.read_bytes()
    ).hexdigest()
