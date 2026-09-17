from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import tempfile
import unittest

import yaml

from sdd_orchestrator.codex_results import CodexOutcome, normalize_codex_outcome
from sdd_orchestrator.evidence_writer import write_stage08_evidence
from sdd_orchestrator.git_runtime import GitRepository
from sdd_orchestrator.path_scope_policy import validate_dirty_diff_scope
from sdd_orchestrator.result_serialization import stage08_phase_projection
from sdd_orchestrator.stage08_phase_state import (
    AttemptBinding,
    DiffProvenance,
    EventType,
    InterruptionReason,
    PhaseStateError,
    ResumeContext,
    SCHEMA_VERSION,
    Stage08Phase,
    Stage08PhaseStore,
    VerificationFingerprint,
    allowed_files_sha256,
    canonical_sha256,
    classify_safe_pause,
)
from sdd_orchestrator.task_parser import AtomicTask
from sdd_orchestrator.codex_results import VerificationResult


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


class Stage08PhaseStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.allowed = ["src/a.py", "tests/test_a.py"]
        self.binding = AttemptBinding(
            attempt_id="a" * 64,
            task_id="T027",
            stage07_report_sha256="b" * 64,
            sealed_envelope_id="a" * 64,
            branch="main",
            entry_head="c" * 40,
            authorized_baseline="d" * 40,
            task_contract_sha256="e" * 64,
            authority_sha256="f" * 64,
            allowed_files_sha256=allowed_files_sha256(self.allowed),
            environment_sha256="1" * 64,
        )
        self.store = Stage08PhaseStore(self.repo, self.binding.attempt_id)
        self.store.create(self.binding)

    def tearDown(self):
        self.tmp.cleanup()

    def provenance(self, *, paths=("src/a.py",), digest="2" * 64):
        return DiffProvenance(
            attempt_id=self.binding.attempt_id,
            phase=Stage08Phase.CODEX_PATCH_COMPLETE.value,
            dirty_paths=tuple(paths),
            diff_sha256=digest,
            authorized_scope_sha256=self.binding.allowed_files_sha256,
        )

    def advance_to_patch(self):
        self.store.append(event_type=EventType.PHASE, phase=Stage08Phase.PRECHECK_COMPLETE)
        self.store.append(event_type=EventType.PHASE, phase=Stage08Phase.CONTEXT_READY)
        self.store.append(
            event_type=EventType.PHASE,
            phase=Stage08Phase.CODEX_PATCH_COMPLETE,
            diff_provenance=self.provenance(),
            provider_invocation_id="provider-call-1",
        )

    def context(self, **overrides):
        values = dict(
            binding=self.binding,
            dirty_paths=("src/a.py",),
            diff_sha256="2" * 64,
            diff_attributable=True,
            scope_overrun=False,
        )
        values.update(overrides)
        return ResumeContext(**values)

    def test_atomic_journal_is_versioned_hash_chained_and_reconstructable(self):
        self.advance_to_patch()
        journal = self.store.load()
        self.assertEqual(journal["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(journal["events"]), 3)
        self.assertEqual(
            journal["events"][1]["previous_digest"],
            journal["events"][0]["event_digest"],
        )
        self.assertEqual(
            Stage08PhaseStore.current_phase(
                [self.store._event_from_dict(item) for item in journal["events"]]
            ),
            Stage08Phase.CODEX_PATCH_COMPLETE,
        )
        self.assertFalse(list(self.store.path.parent.glob("*.tmp")))

    def test_corruption_unknown_schema_and_illegal_transition_fail_closed(self):
        self.store.path.write_text("schema_version: '999'\n", encoding="utf-8")
        with self.assertRaises(PhaseStateError):
            self.store.load()

        self.store.path.unlink()
        self.store.create(self.binding)
        with self.assertRaisesRegex(PhaseStateError, "illegal phase transition"):
            self.store.append(
                event_type=EventType.PHASE,
                phase=Stage08Phase.CODEX_PATCH_COMPLETE,
            )

        self.store.path.unlink()
        self.store.create(self.binding)
        self.advance_to_patch()
        raw = yaml.safe_load(self.store.path.read_text(encoding="utf-8"))
        raw["events"][1]["phase"] = Stage08Phase.STAGE8_COMPLETE.value
        self.store.path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        with self.assertRaises(PhaseStateError):
            self.store.load()

    def test_phase_state_never_projects_qualification(self):
        projection = stage08_phase_projection(
            attempt_id=self.binding.attempt_id,
            phase=Stage08Phase.FINAL_VERIFY_COMPLETE.value,
            status="CURRENT",
            resume_eligible=True,
        )
        self.assertFalse(projection["implementation_qualified"])
        self.assertIsNone(projection["stage09_decision"])
        self.assertIsNone(projection["stage10_decision"])

    def test_all_three_interruption_classes_are_safe_only_with_complete_proof(self):
        for reason in InterruptionReason:
            with self.subTest(reason=reason):
                decision = classify_safe_pause(self.context(), reason)
                self.assertEqual(decision.status, "SAFE_PAUSE")
                self.assertIn(reason.value, decision.reasons)

        unsafe = (
            self.context(scope_overrun=True),
            self.context(diff_attributable=False),
            self.context(unexpected_untracked=("outside.txt",)),
            self.context(stage07_valid=False),
            self.context(envelope_valid=False),
            self.context(security_valid=False),
            self.context(unknown_side_effects=True),
        )
        for context in unsafe:
            self.assertEqual(
                classify_safe_pause(context, InterruptionReason.CODEX_TIMEOUT).status,
                "BLOCK",
            )

    def test_resume_revalidates_every_binding_and_skips_completed_codex(self):
        self.advance_to_patch()
        decision = self.store.revalidate_resume(self.context())
        self.assertEqual(decision.status, "RESUME_ALLOWED")
        self.assertTrue(decision.skip_codex)
        mismatched = replace(self.binding, sealed_envelope_id="9" * 64)
        blocked = self.store.revalidate_resume(self.context(binding=mismatched))
        self.assertEqual(blocked.status, "BLOCK")
        self.assertIn("AUTHORITY_OR_ATTEMPT_BINDING_MISMATCH", blocked.reasons)

    def test_successful_verification_is_reused_only_for_identical_fingerprint(self):
        self.advance_to_patch()
        fingerprint = VerificationFingerprint(
            level="TARGET",
            command_sha256="3" * 64,
            input_sha256="4" * 64,
            environment_sha256=self.binding.environment_sha256,
            diff_sha256="2" * 64,
            authority_sha256=self.binding.authority_sha256,
            envelope_id=self.binding.sealed_envelope_id,
            outcome="PASS",
        )
        self.store.append(
            event_type=EventType.PHASE,
            phase=Stage08Phase.FAST_VERIFY_COMPLETE,
            diff_provenance=self.provenance(),
        )
        self.store.append(
            event_type=EventType.PHASE,
            phase=Stage08Phase.TARGET_VERIFY_COMPLETE,
            diff_provenance=self.provenance(),
            verification=(fingerprint,),
        )
        valid = self.store.revalidate_resume(
            self.context(), expected_verification=(fingerprint,)
        )
        self.assertEqual(valid.reusable_verification_levels, ("TARGET",))
        changed = replace(fingerprint, diff_sha256="5" * 64)
        invalid = self.store.revalidate_resume(
            self.context(), expected_verification=(changed,)
        )
        self.assertEqual(invalid.reusable_verification_levels, ())

    def test_remediation_resume_is_bounded_and_auditable(self):
        self.advance_to_patch()
        self.store.append(event_type=EventType.PHASE, phase=Stage08Phase.FAST_VERIFY_COMPLETE)
        self.store.append(event_type=EventType.PHASE, phase=Stage08Phase.TARGET_VERIFY_COMPLETE)
        self.store.append(event_type=EventType.PHASE, phase=Stage08Phase.REMEDIATION_REQUIRED)
        self.store.append(
            event_type=EventType.RESUME,
            details={"package_kind": "REMEDIATION_PACKAGE", "full_context": False},
        )
        self.store.append(
            event_type=EventType.PHASE,
            phase=Stage08Phase.CODEX_PATCH_COMPLETE,
            diff_provenance=self.provenance(),
            provider_invocation_id="provider-call-remediation-1",
        )
        binding = self.store.evidence_binding()
        self.assertEqual(binding["resume_count"], 1)
        self.assertEqual(binding["current_phase"], "CODEX_PATCH_COMPLETE")

    def test_dirty_scope_requires_authorization_and_attempt_attribution(self):
        valid = validate_dirty_diff_scope(
            ("src/a.py",), self.allowed, attributable_paths=("src/a.py",),
            untracked_paths=("src/a.py",),
        )
        self.assertTrue(valid.safe_to_preserve)
        self.assertEqual(
            validate_dirty_diff_scope(
                ("outside.txt",), self.allowed,
                attributable_paths=("outside.txt",), untracked_paths=("outside.txt",),
            ).status,
            "BLOCK",
        )
        self.assertEqual(
            validate_dirty_diff_scope(
                ("src/a.py",), self.allowed, attributable_paths=(),
                untracked_paths=("src/a.py",),
            ).status,
            "BLOCK",
        )

    def test_evidence_adds_phase_binding_without_breaking_legacy_shape(self):
        self.advance_to_patch()
        attempt = self.store.evidence_binding()
        task = AtomicTask(
            "T027", "phase", "TODO", "TASK-027", ["SPEC-019"],
            self.allowed, ["python -m pytest -q tests/test_a.py"], "phase state",
        )
        proc = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        verification = [VerificationResult(task.verification_commands[0], 0, "ok", "")]
        evidence = write_stage08_evidence(
            self.repo, task, proc, ["src/a.py"], verification,
            status="PASS", stage08_attempt=attempt,
        )
        payload = json.loads((self.repo / evidence).read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["stage08_attempt"]["attempt_id"], self.binding.attempt_id)
        self.assertEqual(payload["stage08_attempt"]["journal_sha256"], self.store.content_digest())

        legacy = write_stage08_evidence(
            self.repo, task, proc, ["src/a.py"], verification, status="PASS"
        )
        legacy_payload = json.loads((self.repo / legacy).read_text(encoding="utf-8"))
        self.assertNotIn("stage08_attempt", legacy_payload)

    def test_codex_outcomes_are_normalized_but_not_implicitly_safe(self):
        self.assertEqual(
            normalize_codex_outcome(returncode=1, stderr="quota exhausted"),
            CodexOutcome.CODEX_QUOTA_EXHAUSTED,
        )
        self.assertEqual(
            normalize_codex_outcome(exception=TimeoutError()),
            CodexOutcome.CODEX_TIMEOUT,
        )
        self.assertEqual(
            normalize_codex_outcome(exception=InterruptedError()),
            CodexOutcome.CODEX_INTERRUPTED,
        )


class GitPhaseProvenanceTests(unittest.TestCase):
    def test_working_diff_digest_binds_tracked_and_untracked_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init")
            git(repo, "config", "user.email", "test@example.com")
            git(repo, "config", "user.name", "Test")
            (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
            git(repo, "add", "tracked.txt")
            git(repo, "commit", "-m", "base")
            runtime = GitRepository(repo)
            (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
            (repo / "new.txt").write_text("new\n", encoding="utf-8")
            first = runtime.working_diff_digest(["tracked.txt", "new.txt"])
            self.assertEqual(first, runtime.working_diff_digest(["new.txt", "tracked.txt"]))
            (repo / "new.txt").write_text("changed\n", encoding="utf-8")
            self.assertNotEqual(first, runtime.working_diff_digest(["tracked.txt", "new.txt"]))


if __name__ == "__main__":
    unittest.main()
