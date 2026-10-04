from __future__ import annotations

from dataclasses import dataclass, asdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
import re
import shutil
import subprocess
import tempfile

import yaml

from .evidence_writer import (
    ImplementationQualificationBinding,
    InvalidEvidence,
    RECOVERY_CAPABILITY,
    RecoveryAuthorization,
    assemble_recovery_authorization,
    implementation_qualification_binding,
)
from .task_parser import AtomicTask, TaskFileParser


class GitRuntimeError(RuntimeError):
    pass


def authority_version_digest(path: str | Path) -> str:
    """Digest authority text using the Stage08 envelope's canonical text view.

    ``Path.read_text`` uses universal-newline decoding: CRLF and LF therefore
    bind identically, while BOMs and trailing-newline content remain observable.
    """
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


@dataclass
class GitSnapshot:
    is_repository: bool
    branch: str | None
    head_commit: str | None
    dirty_paths: list[str]
    recent_commits: list[dict[str, str]]


@dataclass
class RecoverySnapshot:
    git: GitSnapshot
    implementation_state: dict[str, Any]
    inferred: dict[str, Any]
    warnings: list[str]


class GitRepository:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if check and proc.returncode != 0:
            raise GitRuntimeError(
                f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        return proc

    def is_repository(self) -> bool:
        proc = self._run(["rev-parse", "--is-inside-work-tree"], check=False)
        return proc.returncode == 0 and proc.stdout.strip() == "true"

    def is_tracked(self, path: str) -> bool:
        """Return True only when path is already tracked by Git."""
        proc = self._run(["ls-files", "--error-unmatch", "--", path], check=False)
        return proc.returncode == 0

    def commit_subject(self, commit: str = "HEAD") -> str:
        return self._run(["show", "-s", "--format=%s", commit]).stdout.strip()

    def commit_paths(self, commit: str = "HEAD") -> list[str]:
        return self._run(
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit]
        ).stdout.splitlines()

    def resolve_commit(self, commit: str) -> str | None:
        proc = self._run(["rev-parse", "--verify", f"{commit}^{{commit}}"], check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None

    def is_ancestor(self, commit: str, descendant: str = "HEAD") -> bool:
        return self._run(
            ["merge-base", "--is-ancestor", commit, descendant], check=False
        ).returncode == 0

    def tree_identity(self, commit: str) -> str:
        return self._run(["show", "-s", "--format=%T", commit]).stdout.strip()

    def commit_diff_digest(self, commit: str) -> str:
        parent = self.first_parent(commit)
        if parent is None:
            raise GitRuntimeError("Recovery checkpoint must have exactly one parent")
        patch = self._run(["diff", "--binary", parent, commit, "--"]).stdout
        return hashlib.sha256(patch.encode("utf-8")).hexdigest()

    def paths_identity(self, commit: str, paths: tuple[str, ...]) -> str:
        """Content identity for an exact bounded set of repository paths."""
        resolved = self.resolve_commit(commit)
        if resolved is None:
            raise GitRuntimeError(f"Checkpoint is unreachable: {commit}")
        records: list[tuple[str, str | None]] = []
        for path in paths:
            records.append((Path(path).as_posix(), self.committed_blob_identity(path, resolved)))
        return hashlib.sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def working_diff_digest(self, paths: list[str], *, baseline: str = "HEAD") -> str:
        """Content-bind tracked and untracked task dirtiness without mutating Git."""
        normalized = sorted(dict.fromkeys(Path(item).as_posix() for item in paths))
        records: list[dict[str, Any]] = []
        for rel in normalized:
            target = (self.repo_root / rel).resolve()
            try:
                target.relative_to(self.repo_root)
            except ValueError as exc:
                raise GitRuntimeError(f"Dirty path escapes repository: {rel}") from exc
            tracked = self.is_tracked(rel)
            patch = self._run(
                ["diff", "--binary", baseline, "--", rel], check=False
            ).stdout if tracked else ""
            records.append({
                "path": rel,
                "tracked": tracked,
                "exists": target.is_file(),
                "content_sha256": (
                    hashlib.sha256(target.read_bytes()).hexdigest()
                    if target.is_file() else None
                ),
                "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
            })
        return hashlib.sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def dirty_diff_provenance(
        self,
        *,
        attempt_id: str,
        phase: str,
        allowed_paths: list[str],
        baseline: str = "HEAD",
    ) -> dict[str, Any]:
        snapshot = self.snapshot(recent_limit=1)
        dirty = sorted(snapshot.dirty_paths)
        unauthorized = [
            path for path in dirty if not self._covered_by_paths(path, allowed_paths)
        ]
        return {
            "attempt_id": attempt_id,
            "phase": phase,
            "dirty_paths": dirty,
            "diff_sha256": self.working_diff_digest(dirty, baseline=baseline),
            "authorized_scope_sha256": hashlib.sha256(
                json.dumps(
                    sorted(dict.fromkeys(Path(item).as_posix() for item in allowed_paths)),
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "scope_overrun": bool(unauthorized),
            "unauthorized_paths": unauthorized,
            "attributable": not bool(unauthorized),
        }

    @contextmanager
    def isolated_worktree(self, commit: str):
        resolved = self.resolve_commit(commit)
        if resolved is None:
            raise GitRuntimeError(f"Checkpoint is unreachable: {commit}")
        temporary = Path(tempfile.mkdtemp(prefix="sdd-recovery-"))
        added = False
        try:
            self._run(["worktree", "add", "--detach", str(temporary), resolved])
            added = True
            yield temporary
        finally:
            if added:
                self._run(["worktree", "remove", "--force", str(temporary)], check=False)
            shutil.rmtree(temporary, ignore_errors=True)

    def commit_added_paths(self, commit: str = "HEAD") -> list[str]:
        return self._run(
            ["diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A", "-r", commit]
        ).stdout.splitlines()

    def commit_parents(self, commit: str) -> list[str]:
        return self._run(["show", "-s", "--format=%P", commit]).stdout.split()

    def read_committed_file(self, path: str, commit: str = "HEAD") -> str:
        normalized = Path(path).as_posix()
        return self._run(["show", f"{commit}:{normalized}"]).stdout

    def latest_commit_for_path(self, path: str) -> str | None:
        proc = self._run(["log", "-1", "--format=%H", "--", Path(path).as_posix()], check=False)
        value = proc.stdout.strip()
        return value or None

    def committed_blob_identity(self, path: str, commit: str = "HEAD") -> str | None:
        proc = self._run(
            ["rev-parse", "--verify", f"{commit}:{Path(path).as_posix()}"], check=False
        )
        return proc.stdout.strip() if proc.returncode == 0 else None

    def working_blob_identity(self, path: str) -> str | None:
        proc = self._run(["hash-object", "--", Path(path).as_posix()], check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None

    def is_first_parent_ancestor(self, commit: str, descendant: str = "HEAD") -> bool:
        return commit in self._run(["rev-list", "--first-parent", descendant]).stdout.splitlines()

    def first_parent_commits(self, head: str, lower_exclusive: str) -> list[str] | None:
        """Return the bounded first-parent range, or None when lower is not on it."""
        ancestry = self._run(["rev-list", "--first-parent", head]).stdout.splitlines()
        if lower_exclusive not in ancestry:
            return None
        return self._run(
            ["rev-list", "--first-parent", "--reverse", f"{lower_exclusive}..{head}"]
        ).stdout.splitlines()

    def first_parent(self, commit: str) -> str | None:
        parents = self.commit_parents(commit)
        return parents[0] if parents else None

    def snapshot(self, *, recent_limit: int = 10) -> GitSnapshot:
        if not self.is_repository():
            return GitSnapshot(False, None, None, [], [])
        branch = self._run(["branch", "--show-current"]).stdout.strip() or None
        head_proc = self._run(["rev-parse", "HEAD"], check=False)
        head = head_proc.stdout.strip() if head_proc.returncode == 0 else None
        status = self._run(["status", "--porcelain=v1", "--untracked-files=all"]).stdout.splitlines()
        dirty = []
        for line in status:
            if not line:
                continue
            path = line[3:] if len(line) > 3 else line
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            dirty.append(path)
        commits: list[dict[str, str]] = []
        if head:
            log = self._run(
                ["log", f"-{recent_limit}", "--pretty=format:%H%x09%s"],
                check=False,
            ).stdout or ""
            for line in log.splitlines():
                if "\t" in line:
                    sha, subject = line.split("\t", 1)
                    commits.append({"commit": sha, "subject": subject})
        return GitSnapshot(True, branch, head, dirty, commits)

    def checkpoint(
        self,
        *,
        task_id: str,
        summary: str,
        paths: list[str],
        commit_type: str = "chore",
        scope: str = "sdd",
        allow_unrelated_dirty: bool = False,
    ) -> str:
        if not self.is_repository():
            raise GitRuntimeError("Repository is not initialized with Git")
        if not task_id.strip():
            raise GitRuntimeError("task_id is required")
        if not summary.strip():
            raise GitRuntimeError("summary is required")
        if not paths:
            raise GitRuntimeError(
                "Explicit checkpoint paths are required; automatic git add -A is intentionally forbidden"
            )

        root = self.repo_root
        normalized: list[str] = []
        force_add_paths: list[str] = []
        for rel in paths:
            target = (root / rel).resolve()
            try:
                resolved_rel = target.relative_to(root)
            except ValueError as exc:
                raise GitRuntimeError(f"Checkpoint path escapes repository: {rel}") from exc
            normalized_rel = Path(rel).as_posix()
            normalized.append(normalized_rel)
            evidence_name = re.fullmatch(
                rf"\d{{8}}T\d{{6}}\.\d{{6}}Z-{re.escape(task_id)}(?:-recovery-[A-Za-z0-9_.-]+)?\.json",
                resolved_rel.name,
            )
            if (
                resolved_rel.parent == Path(".sdd/evidence")
                and evidence_name
                and target.is_file()
            ):
                force_add_paths.append(normalized_rel)
            elif (
                resolved_rel == Path(".sdd/state/project-state.yaml")
                and target.is_file()
            ):
                force_add_paths.append(normalized_rel)
            elif (
                resolved_rel.parent == Path(".sdd/authorizations/recovery")
                and re.fullmatch(r"[A-Za-z0-9_.-]+\.yaml", resolved_rel.name)
                and target.is_file()
            ):
                force_add_paths.append(normalized_rel)

        before = self.snapshot()
        unrelated = [p for p in before.dirty_paths if not self._covered_by_paths(p, normalized)]
        if unrelated and not allow_unrelated_dirty:
            raise GitRuntimeError(
                "Unrelated dirty paths exist; refusing checkpoint: " + ", ".join(unrelated)
            )

        ordinary_paths = [path for path in normalized if path not in force_add_paths]
        if ordinary_paths:
            self._run(["add", "--", *ordinary_paths])
        for force_add_path in force_add_paths:
            self._run(["add", "-f", "--", force_add_path])
        staged = self._run(["diff", "--cached", "--name-only"]).stdout.splitlines()
        if not staged:
            raise GitRuntimeError("No staged changes for checkpoint")

        message = f"{commit_type}({scope}): [{task_id}] {summary}"
        self._run(["commit", "-m", message])
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    @staticmethod
    def _covered_by_paths(dirty_path: str, paths: list[str]) -> bool:
        for rel in paths:
            rel = rel.rstrip("/")
            if dirty_path == rel or dirty_path.startswith(rel + "/"):
                return True
        return False


class RecoveryAuthorizationStore:
    """Repository-owned loader and one-time consumer for SPEC-017 grants."""

    ROOT = Path(".sdd/authorizations/recovery")
    RUNTIME_PATHS = (
        "sdd_orchestrator/evidence_writer.py",
        "sdd_orchestrator/git_runtime.py",
        "sdd_orchestrator/codex_adapter.py",
    )

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.git = GitRepository(self.repo_root)

    @classmethod
    def relative_path(cls, authorization_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", authorization_id):
            raise GitRuntimeError("AUTHORITY_INVALID: unsafe authorization identity")
        return (cls.ROOT / f"{authorization_id}.yaml").as_posix()

    def _read(self, path: Path) -> RecoveryAuthorization:
        if not path.is_file() or path.is_symlink():
            raise GitRuntimeError("AUTHORITY_INVALID: authorization artifact is unavailable")
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise GitRuntimeError("SCHEMA_INVALID: authorization artifact is unreadable") from exc
        if not isinstance(payload, Mapping):
            raise GitRuntimeError("SCHEMA_INVALID: authorization artifact is malformed")
        try:
            return RecoveryAuthorization.from_record(payload)
        except InvalidEvidence as exc:
            raise GitRuntimeError(str(exc)) from exc

    def _approval_reference_valid(self, reference: str) -> bool:
        match = re.fullmatch(r"([^#]+)#sha256:([0-9a-f]{64})", reference)
        if match is None:
            return False
        rel, digest = match.groups()
        target = (self.repo_root / rel).resolve()
        try:
            target.relative_to(self.repo_root)
        except ValueError:
            return False
        return (
            target.is_file()
            and self.git.is_tracked(Path(rel).as_posix())
            and authority_version_digest(target) == digest
        )

    def _active_records(self) -> list[RecoveryAuthorization]:
        root = self.repo_root / self.ROOT
        records: list[RecoveryAuthorization] = []
        if not root.exists():
            return records
        for path in sorted(root.glob("*.yaml")):
            record = self._read(path)
            record.validate(require_active=False)
            if record.status == "ACTIVE":
                records.append(record)
        return records

    def load(
        self,
        *,
        authorization_id: str | None = None,
        recovery_operation_id: str | None = None,
        require_active: bool = True,
    ) -> RecoveryAuthorization:
        if (authorization_id is None) == (recovery_operation_id is None):
            raise GitRuntimeError("AUTHORITY_INVALID: exactly one authorization lookup key is required")
        if authorization_id is not None:
            rel = self.relative_path(authorization_id)
            candidates = [(rel, self._read(self.repo_root / rel))]
        else:
            candidates = [
                (self.relative_path(item.authorization_id), item)
                for item in self._active_records()
                if item.recovery_operation_id == recovery_operation_id
            ]
        if len(candidates) != 1:
            raise GitRuntimeError("AUTHORITY_INVALID: authorization lookup is missing or ambiguous")
        rel, authorization = candidates[0]
        if rel != self.relative_path(authorization.authorization_id):
            raise GitRuntimeError("AUTHORITY_INVALID: authorization path identity mismatch")
        try:
            authorization.validate(require_active=require_active)
        except InvalidEvidence as exc:
            raise GitRuntimeError(str(exc)) from exc
        snapshot = self.git.snapshot(recent_limit=2)
        if (
            not snapshot.is_repository
            or snapshot.branch != authorization.branch
            or str(self.repo_root) != str(Path(authorization.repository).resolve())
            or snapshot.head_commit is None
            or not self.git.is_ancestor(authorization.baseline, snapshot.head_commit)
            or not self.git.is_ancestor(authorization.runtime_checkpoint, snapshot.head_commit)
        ):
            raise GitRuntimeError("AUTHORITY_INVALID: repository/branch/baseline binding mismatch")
        artifact_commit = self.git.latest_commit_for_path(rel)
        if (
            artifact_commit is None
            or not self.git.is_ancestor(artifact_commit, snapshot.head_commit)
            or self.git.committed_blob_identity(rel, artifact_commit)
            != self.git.working_blob_identity(rel)
        ):
            raise GitRuntimeError("AUTHORITY_INVALID: authorization is not repository-backed")
        if self.git.paths_identity(snapshot.head_commit, self.RUNTIME_PATHS) != self.git.paths_identity(
            authorization.runtime_checkpoint, self.RUNTIME_PATHS
        ):
            raise GitRuntimeError("AUTHORITY_INVALID: runtime code tree differs from authorized checkpoint")
        if not self._approval_reference_valid(authorization.issuer_approval_reference):
            raise GitRuntimeError("AUTHORITY_INVALID: issuer approval reference is invalid")
        runtime_evidence = self.repo_root / authorization.runtime_evidence
        original_evidence = self.repo_root / authorization.target_original_evidence
        if (
            not runtime_evidence.is_file()
            or not original_evidence.is_file()
            or not self.git.is_tracked(authorization.runtime_evidence)
            or not self.git.is_tracked(authorization.target_original_evidence)
        ):
            raise GitRuntimeError("EVIDENCE_MISMATCH: bound evidence is unavailable")
        current_authorities = tuple(
            (path, authority_version_digest(self.repo_root / path))
            for path, _ in authorization.authority_versions
        )
        if current_authorities != authorization.authority_versions:
            raise GitRuntimeError("AUTHORITY_INVALID: authority version mismatch")
        overlaps = [
            item for item in self._active_records()
            if item.authorization_id != authorization.authorization_id
            and (
                item.recovery_operation_id == authorization.recovery_operation_id
                or (
                    item.target_task_id == authorization.target_task_id
                    and item.target_checkpoint == authorization.target_checkpoint
                )
            )
        ]
        if overlaps:
            raise GitRuntimeError("AUTHORITY_INVALID: overlapping ACTIVE authorization")
        return authorization

    def _persist(self, authorization: RecoveryAuthorization, *, create: bool) -> str:
        rel = self.relative_path(authorization.authorization_id)
        target = self.repo_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if create and target.exists():
            raise GitRuntimeError("AUTHORITY_INVALID: authorization identity already exists")
        encoded = yaml.safe_dump(
            authorization.to_record(), sort_keys=False, allow_unicode=True
        )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=target.parent, prefix=".tmp-authorization-", suffix=".yaml",
                delete=False, encoding="utf-8", newline="\n",
            ) as handle:
                temporary = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return rel

    def consume(self, authorization_id: str) -> tuple[RecoveryAuthorization, str]:
        authorization = self.load(authorization_id=authorization_id, require_active=True)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        consumed = authorization.append_status_event(
            "CONSUMED", occurred_at=now, actor="RECOVERY_EXECUTOR",
            reason="FRESH_VERIFICATION_DISPATCH",
        )
        rel = self._persist(consumed, create=False)
        commit = self.git.checkpoint(
            task_id=consumed.target_task_id,
            summary=f"consume recovery authorization [{consumed.authorization_id}]",
            paths=[rel],
            commit_type="chore",
            scope="recovery-authorization",
        )
        loaded = self.load(authorization_id=authorization_id, require_active=False)
        if loaded.status != "CONSUMED":
            raise GitRuntimeError("AUTHORITY_INVALID: consumption was not persisted")
        return loaded, commit


class ProjectAuthorityRecoveryAuthorizationIssuer:
    """The only repository-owned creation boundary for RecoveryAuthorization."""

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.store = RecoveryAuthorizationStore(self.repo_root)
        self.git = self.store.git

    def issue(self, grant: Mapping[str, Any]) -> tuple[RecoveryAuthorization, str, str]:
        snapshot = self.git.snapshot(recent_limit=2)
        if not snapshot.is_repository or snapshot.head_commit is None or snapshot.dirty_paths:
            raise GitRuntimeError("AUTHORITY_INVALID: issuance requires a clean repository")
        values = dict(grant)
        if values.get("issuer") != "PROJECT_AUTHORITY" or values.get("issuer_role") != "PROJECT_AUTHORITY":
            raise GitRuntimeError("AUTHORITY_INVALID: only Project Authority may issue")
        if values.get("repository") != str(self.repo_root) or values.get("branch") != snapshot.branch:
            raise GitRuntimeError("AUTHORITY_INVALID: issuance repository binding mismatch")
        if values.get("baseline") != snapshot.head_commit:
            raise GitRuntimeError("AUTHORITY_INVALID: issuance baseline must be current HEAD")
        if values.get("purpose") != RECOVERY_CAPABILITY or values.get("one_time") is not True:
            raise GitRuntimeError("AUTHORITY_INVALID: invalid recovery capability grant")
        authorization_id = str(values.get("authorization_id", ""))
        rel = self.store.relative_path(authorization_id)
        if (self.repo_root / rel).exists():
            raise GitRuntimeError("AUTHORITY_INVALID: authorization identity already exists")
        if any(
            item.recovery_operation_id == values.get("recovery_operation_id")
            or (
                item.target_task_id == values.get("target_task_id")
                and item.target_checkpoint == values.get("target_checkpoint")
            )
            for item in self.store._active_records()
        ):
            raise GitRuntimeError("AUTHORITY_INVALID: overlapping ACTIVE authorization")
        authorization = assemble_recovery_authorization(values)
        try:
            authorization.validate(require_active=True)
        except InvalidEvidence as exc:
            raise GitRuntimeError(str(exc)) from exc
        if not self.store._approval_reference_valid(authorization.issuer_approval_reference):
            raise GitRuntimeError("AUTHORITY_INVALID: issuer approval reference is invalid")
        rel = self.store._persist(authorization, create=True)
        commit = self.git.checkpoint(
            task_id=authorization.target_task_id,
            summary=f"issue recovery authorization [{authorization.authorization_id}]",
            paths=[rel],
            commit_type="chore",
            scope="recovery-authorization",
        )
        return self.store.load(authorization_id=authorization.authorization_id), rel, commit


class RecoveryManager:
    STATE_SCHEMA = "2.0"
    QUALIFIED = "IMPLEMENTATION_QUALIFIED"
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.git = GitRepository(self.repo_root)
        self.implementation_state_path = (
            self.repo_root / ".sdd" / "state" / "implementation-state.yaml"
        )
        self.pending_evidence_path = (
            self.repo_root / ".sdd" / "evidence" / ".stage08-pending-evidence-write.yaml"
        )

    def load_pending_evidence_write(self) -> dict[str, Any] | None:
        if not self.pending_evidence_path.exists():
            return None
        data = yaml.safe_load(self.pending_evidence_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise GitRuntimeError("Invalid pending Stage 08 evidence recovery record; inspect before resuming.")
        return data

    def record_pending_evidence_write(self, record: dict[str, Any]) -> None:
        self.pending_evidence_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_evidence_path.write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def clear_pending_evidence_write(self) -> None:
        if self.pending_evidence_path.exists():
            self.pending_evidence_path.unlink()

    @staticmethod
    def _strict_yaml(text: str) -> Any:
        class UniqueKeyLoader(yaml.SafeLoader):
            pass

        def construct_mapping(loader, node, deep=False):
            mapping = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise GitRuntimeError(f"Duplicate implementation-state key: {key}")
                mapping[key] = loader.construct_object(value_node, deep=deep)
            return mapping

        UniqueKeyLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
        )
        return yaml.load(text, Loader=UniqueKeyLoader)

    def _load_state(self) -> dict[str, Any]:
        if not self.implementation_state_path.exists():
            return {}
        try:
            data = self._strict_yaml(self.implementation_state_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise GitRuntimeError(f"Malformed implementation state: {exc}") from exc
        if not isinstance(data, dict):
            raise GitRuntimeError("Implementation state must be a mapping")
        return data

    def _task(self, task_id: str) -> AtomicTask:
        tasks_path = self.repo_root / "tasks.md"
        if not tasks_path.is_file():
            raise GitRuntimeError("tasks.md is required for task-specific qualification")
        tasks = TaskFileParser(tasks_path.read_text(encoding="utf-8")).parse()
        matches = [task for task in tasks if task.task_id == task_id]
        if not matches and task_id.startswith("TC"):
            convergence = self.repo_root / ".sdd" / "convergence" / f"{task_id}.yaml"
            if convergence.is_file() and not convergence.is_symlink():
                payload = yaml.safe_load(convergence.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("task_id") == task_id:
                    matches = [AtomicTask(
                        task_id=task_id,
                        title=str(payload.get("title", task_id)),
                        status=str(payload.get("status", "TODO")),
                        raw_markdown=yaml.safe_dump(payload, sort_keys=True),
                        traceability=list(payload.get("traceability") or []),
                        allowed_paths=list(payload.get("allowed_paths") or []),
                        verification_commands=list(payload.get("verification_commands") or []),
                        behavior_scope=str(payload.get("objective", "")),
                    )]
        if len(matches) != 1:
            raise GitRuntimeError(f"Expected exactly one task contract for {task_id}")
        return matches[0]

    def _evidence_path(self, value: str) -> tuple[str, Path]:
        rel = Path(value).as_posix()
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise GitRuntimeError("Evidence path must be repository-relative")
        target = (self.repo_root / rel).resolve()
        evidence_root = (self.repo_root / ".sdd" / "evidence").resolve()
        if target.parent != evidence_root or target.suffix != ".json" or target.is_symlink():
            raise GitRuntimeError("Qualification evidence must be an exact .sdd/evidence JSON file")
        return rel, target

    def _resolve_evidence(
        self, task: AtomicTask, evidence_path: str
    ) -> tuple[ImplementationQualificationBinding, str, str]:
        rel, target = self._evidence_path(evidence_path)
        if not target.is_file():
            raise GitRuntimeError(f"Qualification evidence does not exist: {rel}")
        evidence_commit = self.git.latest_commit_for_path(rel)
        if not evidence_commit or not self.git.is_ancestor(evidence_commit):
            raise GitRuntimeError("Qualification evidence is not repository-backed and reachable")
        committed_blob = self.git.committed_blob_identity(rel, evidence_commit)
        if committed_blob != self.git.working_blob_identity(rel):
            raise GitRuntimeError("Working evidence differs from its committed repository record")
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GitRuntimeError(f"Invalid qualification evidence: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise GitRuntimeError("Qualification evidence must be a JSON object")
        ordinary_checkpoint = evidence_commit if payload.get("record_kind") is None else None
        try:
            binding = implementation_qualification_binding(
                payload, task, ordinary_checkpoint=ordinary_checkpoint
            )
        except InvalidEvidence as exc:
            raise GitRuntimeError(str(exc)) from exc
        checkpoint = self.git.resolve_commit(binding.implementation_checkpoint)
        if checkpoint != binding.implementation_checkpoint or not self.git.is_ancestor(checkpoint):
            raise GitRuntimeError("Qualification checkpoint is not reachable")
        if payload.get("record_kind") is not None:
            changed = payload.get("checkpoint_changed_paths")
            if changed != self.git.commit_paths(checkpoint):
                raise GitRuntimeError("Recovery evidence checkpoint content binding is stale")
            if set(changed) - set(task.allowed_paths):
                raise GitRuntimeError("Recovery checkpoint exceeds task allowed paths")
            if payload.get("checkpoint_tree") != self.git.tree_identity(checkpoint):
                raise GitRuntimeError("Recovery checkpoint tree identity mismatch")
            if payload.get("checkpoint_diff_sha256") != self.git.commit_diff_digest(checkpoint):
                raise GitRuntimeError("Recovery checkpoint diff identity mismatch")
        return binding, rel, evidence_commit

    def _record(
        self,
        binding: ImplementationQualificationBinding,
        evidence_path: str,
        evidence_commit: str,
        *,
        reconciliation_id: str,
        sequence: int,
        source_head: str,
    ) -> dict[str, Any]:
        return {
            "status": self.QUALIFIED,
            "implementation_checkpoint": binding.implementation_checkpoint,
            "evidence": {
                "path": evidence_path,
                "kind": binding.evidence_kind,
                "record_sha256": binding.evidence_record_sha256,
                "repository_commit": evidence_commit,
            },
            "verification": {"outcome": binding.verification_outcome},
            "reconciliation": {
                "id": reconciliation_id,
                "sequence": sequence,
                "recorded_at": binding.recorded_at,
                "source_head": source_head,
            },
        }

    def _discover_legacy_binding(
        self, task: AtomicTask, checkpoint: str
    ) -> tuple[ImplementationQualificationBinding, str, str]:
        candidates = []
        evidence_dir = self.repo_root / ".sdd" / "evidence"
        for path in sorted(evidence_dir.glob(f"*-{task.task_id}*.json")):
            try:
                candidate = self._resolve_evidence(task, path.relative_to(self.repo_root).as_posix())
            except GitRuntimeError:
                continue
            if candidate[0].implementation_checkpoint == checkpoint:
                candidates.append(candidate)
        if len(candidates) != 1:
            raise GitRuntimeError(
                f"Legacy {task.task_id} qualification requires exactly one repository-backed proof"
            )
        return candidates[0]

    def _migrate(self, state: dict[str, Any], source_head: str) -> dict[str, Any]:
        version = str(state.get("schema_version", "1.0"))
        if version == self.STATE_SCHEMA:
            return state
        if version != "1.0":
            raise GitRuntimeError(f"Unsupported implementation-state schema: {version}")
        completed = state.get("last_completed_task")
        verified = state.get("last_verified_commit")
        if bool(completed) != bool(verified):
            raise GitRuntimeError("Incomplete legacy qualification projection")
        migrated = dict(state)
        migrated["schema_version"] = self.STATE_SCHEMA
        migrated["task_qualifications"] = {}
        if completed:
            task = self._task(str(completed))
            binding, path, evidence_commit = self._discover_legacy_binding(task, str(verified))
            migrated["task_qualifications"][task.task_id] = self._record(
                binding,
                path,
                evidence_commit,
                reconciliation_id=f"MIGRATE-{task.task_id}-{binding.evidence_record_sha256[:12]}",
                sequence=1,
                source_head=source_head,
            )
        return migrated

    def _projection_task(self, records: Mapping[str, Any]) -> str | None:
        if not records:
            return None
        candidates = list(records)
        latest = []
        for task_id in candidates:
            commit = records[task_id]["implementation_checkpoint"]
            if all(
                other == task_id
                or self.git.is_first_parent_ancestor(records[other]["implementation_checkpoint"], commit)
                for other in candidates
            ):
                latest.append(task_id)
        if len(latest) != 1:
            raise GitRuntimeError("Qualified checkpoints have no unique ancestry-latest projection")
        return latest[0]

    @staticmethod
    def _canonical_task_sort_key(task_id: str) -> tuple[int, int, str]:
        match = re.fullmatch(r"(T|TC)(\d{3})", str(task_id))
        if not match:
            raise GitRuntimeError("Malformed task qualification record")
        prefix, number = match.groups()
        return (0 if prefix == "T" else 1, int(number), str(task_id))

    def _canonicalize_task_qualifications(self, state: dict[str, Any]) -> dict[str, Any]:
        records = state.get("task_qualifications")
        if not isinstance(records, dict):
            raise GitRuntimeError("task_qualifications must be a mapping")
        canonical = dict(state)
        canonical["task_qualifications"] = {
            task_id: records[task_id]
            for task_id in sorted(records, key=self._canonical_task_sort_key)
        }
        return canonical

    def _validate_v2(self, state: dict[str, Any]) -> None:
        if str(state.get("schema_version")) != self.STATE_SCHEMA:
            raise GitRuntimeError("Implementation state is not schema 2.0")
        records = state.get("task_qualifications")
        if not isinstance(records, dict):
            raise GitRuntimeError("task_qualifications must be a mapping")
        sequences = []
        for task_id, record in records.items():
            if not re.fullmatch(r"(?:T|TC)\d{3}", str(task_id)) or not isinstance(record, dict):
                raise GitRuntimeError("Malformed task qualification record")
            if record.get("status") != self.QUALIFIED:
                raise GitRuntimeError(f"{task_id} is not implementation-qualified")
            task = self._task(task_id)
            evidence = record.get("evidence")
            reconciliation = record.get("reconciliation")
            if not isinstance(evidence, dict) or not isinstance(reconciliation, dict):
                raise GitRuntimeError(f"Malformed {task_id} evidence/reconciliation binding")
            binding, path, evidence_commit = self._resolve_evidence(task, str(evidence.get("path", "")))
            expected = (
                binding.implementation_checkpoint,
                binding.evidence_kind,
                binding.evidence_record_sha256,
                evidence_commit,
                binding.verification_outcome,
            )
            actual = (
                record.get("implementation_checkpoint"), evidence.get("kind"),
                evidence.get("record_sha256"), evidence.get("repository_commit"),
                (record.get("verification") or {}).get("outcome"),
            )
            if actual != expected or path != evidence.get("path"):
                raise GitRuntimeError(f"{task_id} qualification binding conflict")
            sequence = reconciliation.get("sequence")
            if not isinstance(sequence, int) or sequence < 1:
                raise GitRuntimeError(f"Invalid {task_id} reconciliation sequence")
            sequences.append(sequence)
        if len(sequences) != len(set(sequences)):
            raise GitRuntimeError("Duplicate reconciliation sequence")
        projected = self._projection_task(records)
        expected_commit = records[projected]["implementation_checkpoint"] if projected else None
        if state.get("last_completed_task") != projected or state.get("last_verified_commit") != expected_commit:
            raise GitRuntimeError("Legacy compatibility projection is stale")

    def _write_state(self, state: dict[str, Any]) -> None:
        state = self._canonicalize_task_qualifications(state)
        self.implementation_state_path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.implementation_state_path.parent,
            prefix=".implementation-state-", suffix=".tmp", delete=False,
        )
        temporary = Path(handle.name)
        try:
            with handle:
                yaml.safe_dump(state, handle, sort_keys=False, allow_unicode=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.implementation_state_path)
            self._validate_v2(self._load_state())
        finally:
            temporary.unlink(missing_ok=True)

    def reconcile_qualification(
        self,
        *,
        completed_task: str,
        evidence_path: str,
        next_task: str | None = None,
        move_cursor: bool = False,
        task_contract: AtomicTask | None = None,
        expected_checkpoint: str | None = None,
    ) -> None:
        head = self.git.resolve_commit("HEAD")
        if not head:
            raise GitRuntimeError("Repository HEAD is unavailable")
        task = task_contract or self._task(completed_task)
        if task.task_id != completed_task:
            raise GitRuntimeError("Task contract does not match completed task")
        binding, path, evidence_commit = self._resolve_evidence(task, evidence_path)
        if expected_checkpoint is not None and binding.implementation_checkpoint != expected_checkpoint:
            raise GitRuntimeError("Evidence does not bind the requested checkpoint commit")
        state = self._migrate(self._load_state(), head)
        records = state["task_qualifications"]
        existing = records.get(task.task_id)
        identity = (binding.implementation_checkpoint, binding.evidence_record_sha256)
        if existing:
            existing_identity = (
                existing.get("implementation_checkpoint"),
                (existing.get("evidence") or {}).get("record_sha256"),
            )
            if existing_identity != identity:
                raise GitRuntimeError(f"Conflicting qualification already exists for {task.task_id}")
        else:
            sequence = max(
                (record["reconciliation"]["sequence"] for record in records.values()), default=0
            ) + 1
            records[task.task_id] = self._record(
                binding, path, evidence_commit,
                reconciliation_id=f"RECONCILE-{task.task_id}-{binding.evidence_record_sha256[:12]}",
                sequence=sequence, source_head=head,
            )
        state = self._canonicalize_task_qualifications(state)
        records = state["task_qualifications"]
        projected = self._projection_task(records)
        state["last_completed_task"] = projected
        state["last_verified_commit"] = (
            records[projected]["implementation_checkpoint"] if projected else None
        )
        if move_cursor:
            state["current_task"] = next_task
            state["next_task"] = None
        state.setdefault("test_status", {})["overall"] = "PASS"
        state.setdefault("blocked_status", {})["blocked"] = False
        self._validate_v2(state)
        self._write_state(state)

    def is_implementation_qualified(self, task_id: str) -> bool:
        state = self._load_state()
        if str(state.get("schema_version")) != self.STATE_SCHEMA:
            return False
        self._validate_v2(state)
        return task_id in state["task_qualifications"]

    def snapshot(self) -> RecoverySnapshot:
        git = self.git.snapshot(recent_limit=20)
        state = self._load_state()
        warnings: list[str] = []

        last_verified = state.get("last_verified_commit")
        if last_verified and git.head_commit and last_verified != git.head_commit:
            warnings.append(
                "Git HEAD differs from implementation-state last_verified_commit; inspect commits before resuming."
            )
        if git.dirty_paths:
            warnings.append("Repository has uncommitted changes; inspect before resuming execution.")
        if not git.is_repository:
            warnings.append("Git repository is unavailable; execution recovery evidence is incomplete.")

        current_task = state.get("current_task")
        next_task = state.get("next_task")
        last_completed = state.get("last_completed_task")
        inferred = {
            "last_completed_task": last_completed,
            "current_task": current_task,
            "next_task": next_task,
            "resume_ready": bool(git.is_repository) and not bool(state.get("blocked_status", {}).get("blocked")),
            "recommended_action": (
                "INSPECT_DIRTY_WORKTREE"
                if git.dirty_paths
                else "RESUME_CURRENT_TASK"
                if current_task
                else "SELECT_NEXT_TASK"
                if next_task
                else "RECONCILE_TASK_STATE"
            ),
        }
        return RecoverySnapshot(git, state, inferred, warnings)

    def record_checkpoint(
        self,
        *,
        commit: str,
        completed_task: str,
        next_task: str | None = None,
        test_status: str = "PASS",
        evidence_path: str | None = None,
        task_contract: AtomicTask | None = None,
    ) -> None:
        if test_status != "PASS" or not evidence_path:
            raise GitRuntimeError("Checkpoint state requires repository-backed PASS evidence")
        if self.git.resolve_commit(commit) != commit:
            raise GitRuntimeError("Checkpoint commit must be a full reachable commit")
        self.reconcile_qualification(
            completed_task=completed_task,
            evidence_path=evidence_path,
            next_task=next_task,
            move_cursor=True,
            task_contract=task_contract,
            expected_checkpoint=commit,
        )
