from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import yaml

from sdd_orchestrator.git_runtime import (
    authority_version_digest,
    GitRepository,
    ProjectAuthorityRecoveryAuthorizationIssuer,
    RecoveryAuthorizationStore,
    RecoveryManager,
    GitRuntimeError,
)
from sdd_orchestrator.evidence_writer import (
    ImplementationQualificationBinding,
    RECOVERY_CAPABILITY,
)
from sdd_orchestrator.task_parser import AtomicTask
from sdd_orchestrator.errors import (
    FailureEnvelopeError, JsonFailureJournal, PartialOutput, RecoveryRoute, new_failure,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class M5GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")
        implementation_path = self.repo / ".sdd/state/implementation-state.yaml"
        implementation = yaml.safe_load(implementation_path.read_text(encoding="utf-8"))
        implementation["schema_version"] = "1.0"
        implementation.pop("task_qualifications", None)
        implementation["last_completed_task"] = None
        implementation["last_verified_commit"] = None
        implementation["current_task"] = None
        implementation["next_task"] = None
        implementation_path.write_text(
            yaml.safe_dump(implementation, sort_keys=False), encoding="utf-8"
        )
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        (self.repo / "tasks.md").write_text(
            """## TASK-010 - Test task\n\n- **Status:** `TODO`\n- **Allowed files:** `done.txt`.\n- **Verification Commands:** `pytest tests/test_example.py`\n\n## TASK-011 - Next\n\n- **Status:** `TODO`\n- **Allowed files:** `next.txt`.\n- **Verification Commands:** `pytest tests/test_example.py`\n""",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "README.md", "tasks.md", ".sdd"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "chore: initial"], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _recovery_grant(self, authorization_id="AUTH-TC008-001", **overrides):
        for rel, text in {
            "AGENTS.md": "# Approved Project Authority\n",
            "sdd_orchestrator/evidence_writer.py": "# runtime evidence writer\n",
            "sdd_orchestrator/git_runtime.py": "# runtime git owner\n",
            "sdd_orchestrator/codex_adapter.py": "# runtime recovery executor\n",
            ".sdd/evidence/original-TC008.json": '{"task_id":"TC008"}\n',
            ".sdd/evidence/runtime-TC014.json": '{"task_id":"TC014","status":"PASS"}\n',
        }.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        subprocess.run(
            ["git", "add", "AGENTS.md", "sdd_orchestrator"],
            cwd=self.repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "add", "-f", ".sdd/evidence/original-TC008.json", ".sdd/evidence/runtime-TC014.json"],
            cwd=self.repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "test: recovery authorization basis"],
            cwd=self.repo, check=True, capture_output=True,
        )
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        now = datetime.now(timezone.utc)
        approval_digest = authority_version_digest(self.repo / "AGENTS.md")
        grant = {
            "authorization_id": authorization_id,
            "attempt_id": f"attempt-{authorization_id}",
            "issuer": "PROJECT_AUTHORITY", "issuer_role": "PROJECT_AUTHORITY",
            "issuer_approval_reference": f"AGENTS.md#sha256:{approval_digest}",
            "purpose": RECOVERY_CAPABILITY, "one_time": True,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "repository": str(self.repo.resolve()), "branch": branch, "baseline": baseline,
            "recovery_operation_id": "RECOVERY-TC008-ORDINARY-EVIDENCE-001",
            "target_task_id": "TC008", "task_contract_digest": "a" * 64,
            "target_checkpoint": baseline,
            "target_original_evidence": ".sdd/evidence/original-TC008.json",
            "verification_command": "python -m pytest -q tests/test_tc008.py",
            "verification_command_source": ".sdd/convergence/TC008.yaml",
            "runtime_checkpoint": baseline,
            "runtime_evidence": ".sdd/evidence/runtime-TC014.json",
            "spec_version": "SPEC-017", "design_version": "DES-017",
            "authority_policy_version": "AGENTS.md#9.1",
            "authority_versions": (("AGENTS.md", approval_digest),),
            "allowed_artifact_paths": (
                f".sdd/authorizations/recovery/{authorization_id}.yaml", ".sdd/evidence/",
            ),
            "prohibited_operations": (
                "IMPLEMENTATION_MUTATION", "HISTORICAL_EVIDENCE_MUTATION",
                "IMPLEMENTATION_STATE_RECONCILIATION",
            ),
            "allow_persistence_only_resume": False,
            "checkpoint_conditions": ("verification_pass", "scope_respected"),
        }
        grant.update(overrides)
        return grant

    def test_repository_backed_recovery_authorization_issue_load_and_consume(self):
        grant = self._recovery_grant()
        issuer = ProjectAuthorityRecoveryAuthorizationIssuer(self.repo)
        authorization, rel, issuance_commit = issuer.issue(grant)
        store = RecoveryAuthorizationStore(self.repo)
        loaded = store.load(authorization_id=authorization.authorization_id)
        self.assertEqual(loaded, authorization)
        self.assertEqual(store.load(
            recovery_operation_id=authorization.recovery_operation_id
        ).authorization_id, authorization.authorization_id)
        self.assertEqual(GitRepository(self.repo).commit_paths(issuance_commit), [rel])
        self.assertEqual(loaded.status, "ACTIVE")
        self.assertEqual(len(loaded.status_events), 1)

        consumed, consumption_commit = store.consume(loaded.authorization_id)
        self.assertEqual(consumed.status, "CONSUMED")
        self.assertEqual(len(consumed.status_events), 2)
        self.assertEqual(
            consumed.status_events[1]["previous_event_digest"],
            consumed.status_events[0]["event_digest"],
        )
        self.assertEqual(GitRepository(self.repo).commit_paths(consumption_commit), [rel])
        with self.assertRaisesRegex(GitRuntimeError, "not active"):
            store.consume(loaded.authorization_id)

    def test_recovery_authorization_rejects_overlap_bad_issuer_and_path_escape(self):
        grant = self._recovery_grant()
        issuer = ProjectAuthorityRecoveryAuthorizationIssuer(self.repo)
        with self.assertRaisesRegex(GitRuntimeError, "only Project Authority"):
            issuer.issue({**grant, "issuer": "RECOVERY_EXECUTOR"})
        issuer.issue(grant)
        current = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        with self.assertRaisesRegex(GitRuntimeError, "overlapping ACTIVE"):
            issuer.issue({
                **grant, "authorization_id": "AUTH-TC008-002",
                "attempt_id": "attempt-2", "baseline": current,
            })
        with self.assertRaisesRegex(GitRuntimeError, "unsafe authorization"):
            RecoveryAuthorizationStore.relative_path("../escape")

    def test_recovery_authorization_runtime_tree_and_approval_fail_closed(self):
        grant = self._recovery_grant()
        issuer = ProjectAuthorityRecoveryAuthorizationIssuer(self.repo)
        with self.assertRaisesRegex(GitRuntimeError, "approval reference"):
            issuer.issue({**grant, "issuer_approval_reference": "AGENTS.md#sha256:" + "0" * 64})

        authorization, _, _ = issuer.issue(grant)
        runtime = self.repo / "sdd_orchestrator/codex_adapter.py"
        runtime.write_text("# mutated runtime\n", encoding="utf-8")
        subprocess.run(["git", "add", str(runtime.relative_to(self.repo))], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test: mutate runtime"],
            cwd=self.repo, check=True, capture_output=True,
        )
        with self.assertRaisesRegex(GitRuntimeError, "runtime code tree"):
            RecoveryAuthorizationStore(self.repo).load(
                authorization_id=authorization.authorization_id
            )

    def test_authority_version_digest_normalizes_newlines_but_not_content(self):
        authority = self.repo / "docs/spec.md"
        authority.parent.mkdir(parents=True, exist_ok=True)
        authority.write_bytes(b"# SPEC-017\nimmutable authority\n")
        subprocess.run(["git", "add", "docs/spec.md"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test: add authority digest fixture"],
            cwd=self.repo, check=True, capture_output=True,
        )
        lf_digest = authority_version_digest(authority)
        grant = self._recovery_grant(authority_versions=(("docs/spec.md", lf_digest),))
        authorization, _, _ = ProjectAuthorityRecoveryAuthorizationIssuer(self.repo).issue(grant)

        authority.write_bytes(b"# SPEC-017\r\nimmutable authority\r\n")
        self.assertEqual(authority_version_digest(authority), lf_digest)
        self.assertEqual(
            RecoveryAuthorizationStore(self.repo).load(
                authorization_id=authorization.authorization_id
            ).authorization_id,
            authorization.authorization_id,
        )

        authority.write_bytes(b"# SPEC-017\nmodified authority\n")
        self.assertNotEqual(authority_version_digest(authority), lf_digest)
        with self.assertRaisesRegex(GitRuntimeError, "authority version mismatch"):
            RecoveryAuthorizationStore(self.repo).load(
                authorization_id=authorization.authorization_id
            )

    def test_snapshot_reports_branch_head_and_dirty_paths(self):
        (self.repo / "README.md").write_text("changed\n", encoding="utf-8")
        snap = GitRepository(self.repo).snapshot()
        self.assertTrue(snap.is_repository)
        self.assertIsNotNone(snap.head_commit)
        self.assertIn("README.md", snap.dirty_paths)

    def test_fixture_repository_does_not_inherit_live_qualification_history(self):
        state = yaml.safe_load(
            (self.repo / ".sdd/state/implementation-state.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(state["schema_version"], "1.0")
        self.assertNotIn("task_qualifications", state)
        self.assertIsNone(state["last_completed_task"])
        self.assertIsNone(GitRepository(self.repo).resolve_commit("07f18d293df68ff36b9c3006414d15cc02c888b3"))

    def test_fixture_repository_missing_checkpoint_remains_fail_closed(self):
        git = GitRepository(self.repo)
        self.assertFalse(
            git.is_first_parent_ancestor("07f18d293df68ff36b9c3006414d15cc02c888b3", "HEAD")
        )

    def test_checkpoint_requires_explicit_paths(self):
        with self.assertRaises(GitRuntimeError):
            GitRepository(self.repo).checkpoint(
                task_id="T001", summary="test", paths=[]
            )

    def test_checkpoint_refuses_unrelated_dirty_work(self):
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        (self.repo / "b.txt").write_text("b\n", encoding="utf-8")
        with self.assertRaises(GitRuntimeError):
            GitRepository(self.repo).checkpoint(
                task_id="T001", summary="add a", paths=["a.txt"]
            )

    def test_checkpoint_commits_only_authorized_paths(self):
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        commit = GitRepository(self.repo).checkpoint(
            task_id="T001",
            summary="add a",
            paths=["a.txt"],
            commit_type="feat",
            scope="core",
        )
        subject = subprocess.run(
            ["git", "show", "-s", "--format=%s", commit],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(subject, "feat(core): [T001] add a")

    def test_historical_checkpoint_integrity_and_isolated_worktree(self):
        (self.repo / "README.md").write_text("implementation\n", encoding="utf-8")
        run = lambda *args: subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout.strip()
        run("add", "README.md")
        run("commit", "-m", "feat(implementation): [T001] implementation")
        checkpoint = run("rev-parse", "HEAD")
        git = GitRepository(self.repo)
        self.assertEqual(git.resolve_commit(checkpoint), checkpoint)
        self.assertTrue(git.is_ancestor(checkpoint))
        self.assertRegex(git.tree_identity(checkpoint), r"^[0-9a-f]{40}$")
        self.assertRegex(git.commit_diff_digest(checkpoint), r"^[0-9a-f]{64}$")
        with git.isolated_worktree(checkpoint) as isolated:
            self.assertEqual((isolated / "README.md").read_text(), "implementation\n")
            (isolated / "README.md").write_text("temporary\n", encoding="utf-8")
        self.assertEqual((self.repo / "README.md").read_text(), "implementation\n")
        self.assertFalse(GitRepository(self.repo).snapshot().dirty_paths)

    def test_checkpoint_force_add_is_bounded_to_exact_state_and_evidence_files(self):
        (self.repo / ".gitignore").write_text(
            ".sdd/state/\n.sdd/evidence/\nignored/\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test: ignore runtime files"],
            cwd=self.repo,
            check=True,
            capture_output=True,
        )
        state_path = self.repo / ".sdd/state/project-state.yaml"
        evidence_path = self.repo / ".sdd/evidence/20260903T032342.613245Z-T001.json"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["git"]["last_verified_commit"] = "1" * 40
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
        evidence_path.write_text("{}\n", encoding="utf-8")

        commit = GitRepository(self.repo).checkpoint(
            task_id="T001",
            summary="runtime checkpoint",
            paths=[
                ".sdd/state/project-state.yaml",
                ".sdd/evidence/20260903T032342.613245Z-T001.json",
            ],
        )
        committed = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", commit],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(
            set(committed),
            {".sdd/state/project-state.yaml", ".sdd/evidence/20260903T032342.613245Z-T001.json"},
        )
        self.assertTrue(state_path.is_file())

        ignored_file = self.repo / "ignored/arbitrary.txt"
        ignored_file.parent.mkdir(parents=True, exist_ok=True)
        ignored_file.write_text("ignored\n", encoding="utf-8")
        git_repo = GitRepository(self.repo)
        with self.assertRaises(GitRuntimeError):
            git_repo.checkpoint(
                task_id="T002", summary="reject ignored file", paths=["ignored/arbitrary.txt"]
            )
        with self.assertRaises(GitRuntimeError):
            git_repo.checkpoint(
                task_id="T002", summary="reject ignored directory", paths=["ignored"]
            )
        tracked = subprocess.run(
            ["git", "ls-files", "--", "ignored/arbitrary.txt"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(tracked, "")

    def test_recovery_detects_dirty_tree_and_state(self):
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["current_task"] = "T002"
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
        (self.repo / "work.txt").write_text("partial\n", encoding="utf-8")
        recovery = RecoveryManager(self.repo).snapshot()
        self.assertEqual(recovery.inferred["current_task"], "T002")
        self.assertEqual(recovery.inferred["recommended_action"], "INSPECT_DIRTY_WORKTREE")
        self.assertTrue(recovery.warnings)

    def test_record_checkpoint_updates_restart_contract(self):
        state_path = self.repo / ".sdd/state/implementation-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["last_completed_task"] = None
        state["last_verified_commit"] = None
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
        (self.repo / "done.txt").write_text("done\n", encoding="utf-8")
        evidence_rel = ".sdd/evidence/20260907T030000.000000Z-T010.json"
        evidence = {
            "schema_version": "1.0", "stage": "08", "task_id": "T010",
            "status": "PASS", "recorded_at": "2026-09-07T03:00:00Z",
            "verification": [{"returncode": 0, "passed": True}],
            "codex": {"returncode": 0},
        }
        (self.repo / evidence_rel).write_text(json.dumps(evidence), encoding="utf-8")
        commit = GitRepository(self.repo).checkpoint(
            task_id="T010", summary="finish task", paths=["done.txt", evidence_rel]
        )
        mgr = RecoveryManager(self.repo)
        mgr.record_checkpoint(
            commit=commit,
            completed_task="T010",
            next_task="T011",
            test_status="PASS",
            evidence_path=evidence_rel,
        )
        state = yaml.safe_load((self.repo / ".sdd/state/implementation-state.yaml").read_text())
        self.assertEqual(state["schema_version"], "2.0")
        self.assertEqual(state["task_qualifications"]["T010"]["implementation_checkpoint"], commit)
        self.assertEqual(state["last_completed_task"], "T010")
        self.assertEqual(state["current_task"], "T011")
        self.assertEqual(state["last_verified_commit"], commit)
        self.assertEqual(state["test_status"]["overall"], "PASS")
        self.assertTrue(mgr.is_implementation_qualified("T010"))
        self.assertFalse(mgr.is_implementation_qualified("T011"))

        before = state_path.read_bytes()
        mgr.record_checkpoint(
            commit=commit, completed_task="T010", next_task="T011",
            test_status="PASS", evidence_path=evidence_rel,
        )
        self.assertEqual(state_path.read_bytes(), before)

    def test_schema2_dependency_lookup_rejects_singleton_only_state(self):
        manager = RecoveryManager(self.repo)
        self.assertFalse(manager.is_implementation_qualified("T019"))

    def test_atomic_state_write_failure_does_not_replace_state(self):
        manager = RecoveryManager(self.repo)
        original = manager.implementation_state_path.read_bytes()
        with mock.patch("sdd_orchestrator.git_runtime.os.replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                manager._write_state({
                    "schema_version": "2.0", "task_qualifications": {},
                    "last_completed_task": None, "last_verified_commit": None,
                })
        self.assertEqual(manager.implementation_state_path.read_bytes(), original)

    def test_duplicate_yaml_task_record_fails_closed(self):
        with self.assertRaises(GitRuntimeError):
            RecoveryManager._strict_yaml(
                "schema_version: '2.0'\ntask_qualifications:\n  T010: {}\n  T010: {}\n"
            )

    def test_task_qualification_serialization_is_numeric_and_insertion_independent(self):
        manager = RecoveryManager(self.repo)
        task_ids = ("T001", "T002", "T010", "T019", "T020", "T100")
        records = {task_id: {"task_id": task_id} for task_id in reversed(task_ids)}
        state = {
            "schema_version": "2.0", "current_task": None, "next_task": None,
            "last_completed_task": "T020", "last_verified_commit": "a" * 40,
            "task_qualifications": records,
        }
        canonical = manager._canonicalize_task_qualifications(state)
        self.assertEqual(list(canonical["task_qualifications"]), list(task_ids))
        self.assertEqual(list(state["task_qualifications"]), list(reversed(task_ids)))
        self.assertEqual(canonical["task_qualifications"], records)
        self.assertEqual(canonical["last_completed_task"], "T020")
        self.assertIsNone(canonical["current_task"])
        first = yaml.safe_dump(canonical, sort_keys=False, allow_unicode=True)
        reordered = dict(state)
        reordered["task_qualifications"] = {
            task_id: records[task_id] for task_id in ("T019", "T001", "T100", "T010", "T020", "T002")
        }
        second = yaml.safe_dump(
            manager._canonicalize_task_qualifications(reordered),
            sort_keys=False, allow_unicode=True,
        )
        round_trip = yaml.safe_dump(
            manager._canonicalize_task_qualifications(yaml.safe_load(first)),
            sort_keys=False, allow_unicode=True,
        )
        self.assertEqual(first, second)
        self.assertEqual(first, round_trip)

    def test_task_qualification_serialization_rejects_malformed_task_id(self):
        manager = RecoveryManager(self.repo)
        with self.assertRaisesRegex(GitRuntimeError, "Malformed task qualification"):
            manager._canonicalize_task_qualifications({
                "schema_version": "2.0",
                "task_qualifications": {"T20": {"task_id": "T20"}},
            })

    def test_out_of_order_t012_reconciliation_preserves_t019(self):
        manager = RecoveryManager(self.repo)
        t019_commit, t012_commit = "9" * 40, "1" * 40
        existing = {
            "schema_version": "2.0", "current_task": None, "next_task": None,
            "last_completed_task": "T019", "last_verified_commit": t019_commit,
            "task_qualifications": {
                "T019": {
                    "status": manager.QUALIFIED, "implementation_checkpoint": t019_commit,
                    "evidence": {"path": ".sdd/evidence/t019.json", "kind": "RECOVERY",
                                 "record_sha256": "a" * 64, "repository_commit": "8" * 40},
                    "verification": {"outcome": "PASS"},
                    "reconciliation": {"id": "r19", "sequence": 1,
                                       "recorded_at": "2026-09-07T01:00:00Z",
                                       "source_head": "8" * 40},
                }
            },
        }
        task = AtomicTask("T012", "old", "TODO", "", [], ["src/a.py"], ["pytest x"])
        binding = ImplementationQualificationBinding(
            "T012", t012_commit, "POST_CHECKPOINT_IMPLEMENTATION_EVIDENCE_RECOVERY",
            "b" * 64, "PASS", "2026-09-07T02:00:00Z",
        )
        published = {}
        with (
            mock.patch.object(manager.git, "resolve_commit", return_value="f" * 40),
            mock.patch.object(manager, "_task", return_value=task),
            mock.patch.object(manager, "_resolve_evidence", return_value=(binding, ".sdd/evidence/t012.json", "7" * 40)),
            mock.patch.object(manager, "_load_state", return_value=existing),
            mock.patch.object(manager, "_migrate", side_effect=lambda state, _: state),
            mock.patch.object(manager.git, "is_first_parent_ancestor", side_effect=lambda older, newer: older == t012_commit and newer == t019_commit),
            mock.patch.object(manager, "_validate_v2"),
            mock.patch.object(manager, "_write_state", side_effect=lambda state: published.update(state)),
        ):
            manager.reconcile_qualification(completed_task="T012", evidence_path=".sdd/evidence/t012.json")
        self.assertEqual(list(published["task_qualifications"]), ["T012", "T019"])
        self.assertEqual(published["last_completed_task"], "T019")
        self.assertIsNone(published["current_task"])

    def test_conflicting_checkpoint_reconciliation_fails_closed(self):
        manager = RecoveryManager(self.repo)
        task = AtomicTask("T010", "task", "TODO", "", [], ["done.txt"], ["pytest x"])
        binding = ImplementationQualificationBinding(
            "T010", "2" * 40, "ORDINARY_STAGE08", "b" * 64, "PASS",
            "2026-09-07T02:00:00Z",
        )
        state = {
            "schema_version": "2.0", "task_qualifications": {
                "T010": {"implementation_checkpoint": "1" * 40,
                         "evidence": {"record_sha256": "a" * 64}}
            }
        }
        with (
            mock.patch.object(manager.git, "resolve_commit", return_value="f" * 40),
            mock.patch.object(manager, "_task", return_value=task),
            mock.patch.object(manager, "_resolve_evidence", return_value=(binding, ".sdd/evidence/t010.json", "3" * 40)),
            mock.patch.object(manager, "_load_state", return_value=state),
            mock.patch.object(manager, "_migrate", side_effect=lambda current, _: current),
        ):
            with self.assertRaisesRegex(GitRuntimeError, "Conflicting qualification"):
                manager.reconcile_qualification(completed_task="T010", evidence_path=".sdd/evidence/t010.json")

    def test_failure_journal_preserves_facts_and_filters_routes(self):
        journal = JsonFailureJournal(self.repo / ".sdd" / "failures.json")
        failure = new_failure(
            operation="git checkpoint", step="commit", cause_class="GIT",
            affected_scope=("TASK-010",), pre_operation_identity="abc123",
            owner="Stage08", safe_reference="git-error-1",
            valid_completed_work=("TASK-005",),
            partial_outputs=(PartialOutput("worktree-diff", "UNVERIFIED"),),
            candidate_routes=(
                RecoveryRoute("RETRY", "Stage08", ("worktree_reviewed",)),
                RecoveryRoute("ESCALATION", "ProjectAuthority"),
            ),
        )
        journal.persist(failure)
        restored = journal.get(failure.failure_id)
        self.assertEqual(restored.pre_operation_identity, "abc123")
        self.assertEqual(restored.valid_completed_work, ("TASK-005",))
        self.assertEqual([r.kind for r in restored.eligible_routes(())], ["ESCALATION"])
        self.assertEqual(
            [r.kind for r in restored.eligible_routes({"worktree_reviewed"})],
            ["RETRY", "ESCALATION"],
        )

    def test_linked_repeated_failure_does_not_rewrite_original(self):
        journal = JsonFailureJournal(self.repo / ".sdd" / "failures.json")
        original = new_failure(
            operation="verify", step="pytest", cause_class="TEST_VERIFICATION",
            affected_scope=("TASK-010",), pre_operation_identity="def456",
            owner="Stage08", safe_reference="pytest-failure",
            candidate_routes=(RecoveryRoute("RETRY", "Stage08"),),
        )
        journal.persist(original)
        repeated = original.linked_attempt("RETRY", status="FAILED", safe_reference="pytest-failure-2")
        journal.persist(repeated)
        restored = journal.get(original.failure_id)
        self.assertEqual(restored.failure_id, original.failure_id)
        self.assertEqual(restored.attempts[0].failure_id, original.failure_id)
        self.assertEqual(restored.attempts[0].status, "FAILED")

        rewritten = new_failure(
            operation="different", step="pytest", cause_class="TEST_VERIFICATION",
            affected_scope=("TASK-010",), pre_operation_identity="def456",
            owner="Stage08", safe_reference="pytest-failure",
        )
        object.__setattr__(rewritten, "failure_id", original.failure_id)
        with self.assertRaises(FailureEnvelopeError):
            journal.persist(rewritten)

    def test_failure_journal_rejects_rewritten_preserved_progress(self):
        journal = JsonFailureJournal(self.repo / ".sdd" / "failures.json")
        original = new_failure(
            operation="execute", step="write", cause_class="EXECUTION",
            affected_scope=("TASK-010",), pre_operation_identity="abc123",
            owner="Stage08", safe_reference="execution-failure",
            valid_completed_work=("TASK-005",),
            partial_outputs=(PartialOutput("bounded-diff", "UNVERIFIED"),),
            candidate_routes=(RecoveryRoute("ESCALATION", "ProjectAuthority"),),
        )
        journal.persist(original)
        rewritten = new_failure(
            operation=original.operation, step=original.step,
            cause_class=original.cause_class, affected_scope=original.affected_scope,
            pre_operation_identity=original.pre_operation_identity,
            owner=original.owner, safe_reference=original.safe_reference,
        )
        object.__setattr__(rewritten, "failure_id", original.failure_id)
        object.__setattr__(rewritten, "occurred_at", original.occurred_at)

        with self.assertRaisesRegex(FailureEnvelopeError, "immutable"):
            journal.persist(rewritten)
        self.assertEqual(journal.get(original.failure_id), original)

    def test_failure_journal_rejects_ambiguous_duplicate_json_keys(self):
        path = self.repo / ".sdd" / "failures.json"
        path.write_text('{"failures": {}, "failures": {}}\n', encoding="utf-8")

        with self.assertRaisesRegex(FailureEnvelopeError, "duplicate JSON key"):
            JsonFailureJournal(path).get("failure-missing")

    def test_authority_failure_cannot_be_marked_safe_or_complete(self):
        with self.assertRaises(FailureEnvelopeError):
            new_failure(
                operation="resolve", step="authority-check", cause_class="AUTHORITY",
                affected_scope=("docs/spec.md",), pre_operation_identity="ghi789",
                owner="Stage03", safe_reference="conflict-1", unsafe_to_continue=False,
            )


if __name__ == "__main__":
    unittest.main()
