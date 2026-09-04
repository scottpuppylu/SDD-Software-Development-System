from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

from sdd_orchestrator.git_runtime import GitRepository, RecoveryManager, GitRuntimeError
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
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md", ".sdd"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "chore: initial"], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_reports_branch_head_and_dirty_paths(self):
        (self.repo / "README.md").write_text("changed\n", encoding="utf-8")
        snap = GitRepository(self.repo).snapshot()
        self.assertTrue(snap.is_repository)
        self.assertIsNotNone(snap.head_commit)
        self.assertIn("README.md", snap.dirty_paths)

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
        (self.repo / "done.txt").write_text("done\n", encoding="utf-8")
        commit = GitRepository(self.repo).checkpoint(
            task_id="T010", summary="finish task", paths=["done.txt"]
        )
        mgr = RecoveryManager(self.repo)
        mgr.record_checkpoint(
            commit=commit,
            completed_task="T010",
            next_task="T011",
            test_status="PASS",
        )
        state = yaml.safe_load((self.repo / ".sdd/state/implementation-state.yaml").read_text())
        self.assertEqual(state["last_completed_task"], "T010")
        self.assertEqual(state["current_task"], "T011")
        self.assertEqual(state["last_verified_commit"], commit)
        self.assertEqual(state["test_status"]["overall"], "PASS")

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

    def test_authority_failure_cannot_be_marked_safe_or_complete(self):
        with self.assertRaises(FailureEnvelopeError):
            new_failure(
                operation="resolve", step="authority-check", cause_class="AUTHORITY",
                affected_scope=("docs/spec.md",), pre_operation_identity="ghi789",
                owner="Stage03", safe_reference="conflict-1", unsafe_to_continue=False,
            )


if __name__ == "__main__":
    unittest.main()
