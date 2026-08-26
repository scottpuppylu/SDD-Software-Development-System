import inspect
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from sdd_orchestrator.codex_adapter import CodexAdapterError, Stage08CodexRunner
from sdd_orchestrator.codex_results import CodexTaskRunResult, VerificationResult
from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.telemetry import measurement
from sdd_orchestrator.telemetry.models import Component, EventType, Layer


class Stage08TaskMeasurementContractTests(unittest.TestCase):
    def _result(self, status="DONE", *, changed_paths=None, verification=None, checkpoint=None):
        return CodexTaskRunResult(
            task_id="T007",
            title="Secret title must not be persisted",
            codex_returncode=0,
            codex_stdout="secret stdout",
            codex_stderr="secret stderr",
            changed_paths=list(changed_paths or []),
            verification=list(verification or []),
            checkpoint_commit=checkpoint,
            next_task="T008",
            status=status,
            evidence_file=".sdd/evidence/private.json",
        )

    def _measure(self, result):
        builder = getattr(measurement, "measure_stage08_task", None)
        self.assertIsNotNone(
            builder,
            "M2.2 requires telemetry.measurement.measure_stage08_task",
        )
        return builder(task_id=result.task_id, task_contract=None, result=result, run_id=None)

    def test_returned_status_mapping_and_exact_terminal_metadata(self):
        verification = [VerificationResult("private command", 0, "out", "err")]
        expected = {
            "DONE": "completed",
            "CODEX_FAILED": "failed",
            "NO_CHANGES": "failed",
            "VERIFICATION_FAILED": "failed",
        }
        for status, outcome in expected.items():
            with self.subTest(status=status):
                event = self._measure(self._result(
                    status,
                    changed_paths=["private/a.py", "private/b.py"],
                    verification=verification,
                    checkpoint="private-checkpoint-id" if status == "DONE" else None,
                ))
                self.assertEqual(event.event_type, EventType.STAGE08_TASK)
                self.assertEqual(event.stage_id, "08")
                self.assertIsNone(event.run_id)
                self.assertIsNone(event.usage)
                self.assertEqual(event.outcome_category.value, outcome)
                self.assertEqual(event.metadata, {
                    "task_id": "T007",
                    "terminal_status": status,
                    "verification_count": 1,
                    "changed_path_count": 2,
                    "checkpoint_created": status == "DONE",
                })

    def test_task_contract_metric_is_metadata_only_and_does_not_disclose_payloads(self):
        body = "contract body API_KEY=top-secret"
        builder = getattr(measurement, "measure_stage08_task", None)
        self.assertIsNotNone(builder, "M2.2 requires measure_stage08_task")
        event = builder(
            task_id="T007",
            task_contract=body,
            result=self._result("DONE", changed_paths=["secret/path.py"]),
            run_id=None,
        )
        self.assertEqual(len(event.metrics), 1)
        metric = event.metrics[0]
        self.assertEqual(metric.classification, Component.STAGE_CONTRACT)
        self.assertEqual(metric.layer, Layer.REQUEST)
        self.assertIsNone(metric.source_paths)
        serialized = repr(event.to_dict())
        for forbidden in (body, "top-secret", "secret/path.py", "secret stdout", "secret stderr"):
            self.assertNotIn(forbidden, serialized)

    def test_unrecognized_returned_status_is_dropped_instead_of_guessed(self):
        builder = getattr(measurement, "measure_stage08_task", None)
        self.assertIsNotNone(builder, "M2.2 requires measure_stage08_task")
        self.assertIsNone(builder(
            task_id="T007",
            task_contract=None,
            result=self._result("NEW_PRIVATE_STATUS"),
            run_id=None,
        ))

    def test_unknown_returned_status_drops_telemetry_without_mutating_result(self):
        changed_paths = ["deterministic/path.py"]
        verification = [VerificationResult("deterministic verify", 0, "", "")]
        result = CodexTaskRunResult(
            task_id="T-UNKNOWN",
            title="Deterministic task",
            codex_returncode=0,
            codex_stdout="",
            codex_stderr="",
            changed_paths=changed_paths,
            verification=verification,
            checkpoint_commit="deterministic-checkpoint",
            next_task=None,
            status="UNKNOWN_STATUS",
            evidence_file=".sdd/evidence/deterministic.json",
        )
        original_result = result
        original_attributes = dict(vars(result))

        event = measurement.measure_stage08_task(
            task_id="T-UNKNOWN",
            task_contract="deterministic task contract",
            result=result,
            run_id="deterministic-run-id",
        )

        self.assertIsNone(event)
        self.assertIs(result, original_result)
        self.assertEqual(result.status, "UNKNOWN_STATUS")
        self.assertEqual(result.task_id, "T-UNKNOWN")
        self.assertEqual(result.changed_paths, changed_paths)
        self.assertEqual(result.verification, verification)
        self.assertEqual(result.checkpoint_commit, "deterministic-checkpoint")
        self.assertEqual(vars(result), original_attributes)

    def test_lifecycle_result_schemas_remain_telemetry_free(self):
        forbidden = {"telemetry", "measurement", "usage", "stage08_task", "event_id"}
        self.assertFalse({field.name for field in fields(CodexTaskRunResult)} & forbidden)
        self.assertFalse({field.name for field in fields(VerificationResult)} & forbidden)


class Stage08TaskRecorderBoundaryTests(unittest.TestCase):
    def test_runner_accepts_a_shared_optional_telemetry_recorder(self):
        parameters = inspect.signature(Stage08CodexRunner.__init__).parameters
        self.assertIn("telemetry_recorder", parameters)
        self.assertIsNone(parameters["telemetry_recorder"].default)

    def test_stage08_pre_attempt_rejection_emits_no_terminal_event(self):
        events = []
        runner = Stage08CodexRunner.__new__(Stage08CodexRunner)
        runner.telemetry_recorder = type(
            "Recorder",
            (),
            {"record": lambda _self, event: events.append(event)},
        )()
        rejection = CodexAdapterError("deterministic preflight rejection")

        def deterministic_pre_attempt_rejection(task_id=None):
            self.assertEqual(task_id, "T007")
            self.assertIsNone(runner._telemetry_attempt_task)
            raise rejection

        runner._execute_one = deterministic_pre_attempt_rejection

        with self.assertRaises(CodexAdapterError) as caught:
            runner.execute_one("T007")

        self.assertIs(caught.exception, rejection)
        self.assertEqual(
            [event for event in events if event.event_type == EventType.STAGE08_TASK],
            [],
        )
        self.assertEqual(events, [])
        self.assertIsNone(runner._telemetry_attempt_task)

    def test_stage08_already_completed_skip_emits_no_terminal_event(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory) / "repo"
            shutil.copytree(source / ".sdd", repo / ".sdd")
            for relative_path, text in {
                "AGENTS.md": "# AGENTS\nDo not modify authoritative contracts.\n",
                "docs/PRD.md": "# PRD\nFR-001 deterministic task\n",
                "docs/spec.md": "# Spec\nSPEC-001 deterministic behavior\n",
                "docs/Design.md": "# Design\nDES-001 deterministic design\n",
            }.items():
                path = repo / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            def git(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()

            git("init")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            git("add", ".")
            git("commit", "-m", "initial")
            project_state_path = repo / ".sdd/state/project-state.yaml"
            project_state = yaml.safe_load(project_state_path.read_text(encoding="utf-8"))
            project_state["stages"]["07"]["status"] = "DONE"
            project_state["stages"]["07"]["result"] = "PASS"
            project_state["authorizations"]["implementation"] = True
            project_state["lifecycle"]["current_stage"] = "08"
            project_state["lifecycle"]["current_stage_name"] = "IMPLEMENTATION_RUNNER"
            project_state_path.write_text(
                yaml.safe_dump(project_state, sort_keys=False), encoding="utf-8"
            )
            (repo / "tasks.md").write_text(
                """\
### T007 ? Deterministic completed task
- **Status:** TODO
- **Allowed files:** `src/completed.py`, `tests/test_completed.py`
- **Implementation Scope:** Implement deterministic completed behavior.
- **Verification Commands:** `python -m pytest -q tests/test_completed.py`
""",
                encoding="utf-8",
            )
            git("add", "tasks.md", ".sdd/state/project-state.yaml")
            git("commit", "-m", "authorize stage08")

            provider_calls = []

            class FakeCodex:
                def execute(self, repo_root, prompt):
                    provider_calls.append(prompt)
                    (repo_root / "src").mkdir(exist_ok=True)
                    (repo_root / "tests").mkdir(exist_ok=True)
                    (repo_root / "src/completed.py").write_text(
                        "VALUE = 1\n", encoding="utf-8"
                    )
                    (repo_root / "tests/test_completed.py").write_text(
                        "from src.completed import VALUE\n\n"
                        "def test_completed():\n    assert VALUE == 1\n",
                        encoding="utf-8",
                    )
                    return SimpleNamespace(returncode=0, stdout="done", stderr="")

            initial = Stage08CodexRunner(
                Orchestrator(repo), codex=FakeCodex()
            ).execute_one("T007")
            self.assertEqual(initial.status, "DONE")
            self.assertEqual(len(provider_calls), 1)
            checkpoint = initial.checkpoint_commit
            head_before_skip = git("rev-parse", "HEAD")

            events = []
            runner = Stage08CodexRunner(
                Orchestrator(repo),
                codex=FakeCodex(),
                telemetry_recorder=type(
                    "Recorder",
                    (),
                    {"record": lambda _self, event: events.append(event)},
                )(),
            )
            skipped = runner.execute_one("T007")

            self.assertEqual(skipped.status, "DONE")
            self.assertEqual(skipped.checkpoint_commit, checkpoint)
            self.assertEqual(git("rev-parse", "HEAD"), head_before_skip)
            self.assertEqual(len(provider_calls), 1)
            self.assertIsNone(runner._telemetry_attempt_task)
            self.assertEqual(
                [event for event in events if event.event_type == EventType.STAGE08_TASK],
                [],
            )
            self.assertEqual(events, [])
            for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
                self.assertNotIn(forbidden, repr(events))

    def test_stage08_historical_checkpoint_reconciliation_emits_no_terminal_event(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory) / "repo"
            shutil.copytree(source / ".sdd", repo / ".sdd")
            for relative_path, text in {
                "AGENTS.md": "# AGENTS\nDo not modify authoritative contracts.\n",
                "docs/PRD.md": "# PRD\nFR-001 deterministic task\n",
                "docs/spec.md": "# Spec\nSPEC-001 deterministic behavior\n",
                "docs/Design.md": "# Design\nDES-001 deterministic design\n",
            }.items():
                path = repo / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=repo, text=True, capture_output=True, check=True
                ).stdout.strip()

            git("init")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            git("add", ".")
            git("commit", "-m", "initial")
            project_state_path = repo / ".sdd/state/project-state.yaml"
            project_state = yaml.safe_load(project_state_path.read_text(encoding="utf-8"))
            project_state["stages"]["07"]["status"] = "DONE"
            project_state["stages"]["07"]["result"] = "PASS"
            project_state["authorizations"]["implementation"] = True
            project_state["lifecycle"]["current_stage"] = "08"
            project_state["lifecycle"]["current_stage_name"] = "IMPLEMENTATION_RUNNER"
            project_state_path.write_text(
                yaml.safe_dump(project_state, sort_keys=False), encoding="utf-8"
            )
            (repo / "tasks.md").write_text(
                """\
### T007 ? Deterministic recovery task
- **Status:** TODO
- **Allowed files:** `src/recovered.py`, `tests/test_recovered.py`
- **Implementation Scope:** Implement deterministic recovered behavior.
- **Verification Commands:** `python -m pytest -q tests/test_recovered.py`
""",
                encoding="utf-8",
            )
            git("add", "tasks.md", ".sdd/state/project-state.yaml")
            git("commit", "-m", "authorize stage08")

            provider_calls = []

            class FakeCodex:
                def execute(self, repo_root, prompt):
                    provider_calls.append(prompt)
                    (repo_root / "src").mkdir(exist_ok=True)
                    (repo_root / "tests").mkdir(exist_ok=True)
                    (repo_root / "src/recovered.py").write_text("VALUE = 1\n", encoding="utf-8")
                    (repo_root / "tests/test_recovered.py").write_text(
                        "from src.recovered import VALUE\n\n"
                        "def test_recovered():\n    assert VALUE == 1\n",
                        encoding="utf-8",
                    )
                    return SimpleNamespace(returncode=0, stdout="done", stderr="")

            initial_runner = Stage08CodexRunner(Orchestrator(repo), codex=FakeCodex())
            with patch.object(
                initial_runner.recovery,
                "record_checkpoint",
                side_effect=RuntimeError("simulated recovery state write failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "recovery state write failure"):
                    initial_runner.execute_one("T007")

            historical_checkpoint = git("rev-parse", "HEAD")
            commit_count_before = git("rev-list", "--count", "HEAD")
            implementation_state_path = repo / ".sdd/state/implementation-state.yaml"
            stale_state = yaml.safe_load(implementation_state_path.read_text(encoding="utf-8"))
            self.assertNotEqual(stale_state.get("last_verified_commit"), historical_checkpoint)
            self.assertEqual(len(provider_calls), 1)

            events = []
            runner = Stage08CodexRunner(
                Orchestrator(repo),
                codex=FakeCodex(),
                telemetry_recorder=type(
                    "Recorder", (), {"record": lambda _self, event: events.append(event)}
                )(),
            )
            result = runner.execute_one("T007")

            reconciled_state = yaml.safe_load(
                implementation_state_path.read_text(encoding="utf-8")
            )
            self.assertEqual(result.status, "DONE")
            self.assertEqual(result.checkpoint_commit, historical_checkpoint)
            self.assertEqual(reconciled_state["last_completed_task"], "T007")
            self.assertEqual(reconciled_state["last_verified_commit"], historical_checkpoint)
            self.assertEqual(git("rev-parse", "HEAD"), historical_checkpoint)
            self.assertEqual(git("rev-list", "--count", "HEAD"), commit_count_before)
            self.assertEqual(len(provider_calls), 1)
            self.assertIsNone(runner._telemetry_attempt_task)
            self.assertEqual(
                [event for event in events if event.event_type == EventType.STAGE08_TASK], []
            )
            self.assertEqual(events, [])
            for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
                self.assertNotIn(forbidden, repr(events))

    def test_stage08_lifecycle_done_emits_exactly_one_terminal_event(self):
        events = []
        runner = Stage08CodexRunner.__new__(Stage08CodexRunner)
        runner.telemetry_recorder = type(
            "Recorder",
            (),
            {"record": lambda _self, event: events.append(event)},
        )()
        task = type(
            "Task",
            (),
            {"task_id": "T007", "raw_markdown": "deterministic task contract"},
        )()
        result = CodexTaskRunResult(
            task_id="T007",
            title="Deterministic task",
            codex_returncode=0,
            codex_stdout="",
            codex_stderr="",
            changed_paths=["allowed.py"],
            verification=[VerificationResult("deterministic verify", 0, "", "")],
            checkpoint_commit="checkpoint-id",
            next_task=None,
            status="DONE",
            evidence_file=".sdd/evidence/test.json",
        )

        def deterministic_started_attempt(task_id=None):
            self.assertEqual(task_id, "T007")
            runner._telemetry_attempt_task = task
            return result

        runner._execute_one = deterministic_started_attempt

        self.assertIs(runner.execute_one("T007"), result)
        terminal_events = [event for event in events if event.event_type == EventType.STAGE08_TASK]
        self.assertEqual(len(terminal_events), 1)
        event = terminal_events[0]
        self.assertEqual(event.outcome_category.value, "completed")
        self.assertEqual(event.stage_id, "08")
        self.assertIsNone(event.usage)
        self.assertEqual(set(event.metadata), {
            "task_id",
            "terminal_status",
            "verification_count",
            "changed_path_count",
            "checkpoint_created",
        })
        self.assertEqual(event.metadata["terminal_status"], "DONE")
        for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
            self.assertNotIn(forbidden, event.metadata)

    def test_stage08_lifecycle_codex_failed_emits_exactly_one_terminal_event(self):
        events = []
        runner = Stage08CodexRunner.__new__(Stage08CodexRunner)
        runner.telemetry_recorder = type(
            "Recorder",
            (),
            {"record": lambda _self, event: events.append(event)},
        )()
        task = type(
            "Task",
            (),
            {"task_id": "T007", "raw_markdown": "deterministic task contract"},
        )()
        result = CodexTaskRunResult(
            task_id="T007",
            title="Deterministic task",
            codex_returncode=1,
            codex_stdout="",
            codex_stderr="deterministic failure",
            changed_paths=[],
            verification=[],
            checkpoint_commit=None,
            next_task=None,
            status="CODEX_FAILED",
            evidence_file=".sdd/evidence/test.json",
        )

        def deterministic_started_attempt(task_id=None):
            self.assertEqual(task_id, "T007")
            runner._telemetry_attempt_task = task
            return result

        runner._execute_one = deterministic_started_attempt

        self.assertIs(runner.execute_one("T007"), result)
        terminal_events = [event for event in events if event.event_type == EventType.STAGE08_TASK]
        self.assertEqual(len(terminal_events), 1)
        event = terminal_events[0]
        self.assertEqual(event.outcome_category.value, "failed")
        self.assertEqual(event.stage_id, "08")
        self.assertIsNone(event.usage)
        self.assertEqual(set(event.metadata), {
            "task_id",
            "terminal_status",
            "verification_count",
            "changed_path_count",
            "checkpoint_created",
        })
        self.assertEqual(event.metadata["terminal_status"], "CODEX_FAILED")
        for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
            self.assertNotIn(forbidden, event.metadata)

    def test_stage08_lifecycle_no_changes_emits_exactly_one_terminal_event(self):
        events = []
        runner = Stage08CodexRunner.__new__(Stage08CodexRunner)
        runner.telemetry_recorder = type(
            "Recorder",
            (),
            {"record": lambda _self, event: events.append(event)},
        )()
        task = type(
            "Task",
            (),
            {"task_id": "T007", "raw_markdown": "deterministic task contract"},
        )()
        result = CodexTaskRunResult(
            task_id="T007",
            title="Deterministic task",
            codex_returncode=0,
            codex_stdout="",
            codex_stderr="",
            changed_paths=[],
            verification=[],
            checkpoint_commit=None,
            next_task=None,
            status="NO_CHANGES",
            evidence_file=".sdd/evidence/test.json",
        )

        def deterministic_started_attempt(task_id=None):
            self.assertEqual(task_id, "T007")
            runner._telemetry_attempt_task = task
            return result

        runner._execute_one = deterministic_started_attempt

        self.assertIs(runner.execute_one("T007"), result)
        terminal_events = [event for event in events if event.event_type == EventType.STAGE08_TASK]
        self.assertEqual(len(terminal_events), 1)
        event = terminal_events[0]
        self.assertEqual(event.outcome_category.value, "failed")
        self.assertEqual(event.stage_id, "08")
        self.assertIsNone(event.usage)
        self.assertEqual(set(event.metadata), {
            "task_id",
            "terminal_status",
            "verification_count",
            "changed_path_count",
            "checkpoint_created",
        })
        self.assertEqual(event.metadata["terminal_status"], "NO_CHANGES")
        for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
            self.assertNotIn(forbidden, event.metadata)

    def test_stage08_lifecycle_verification_failed_emits_exactly_one_terminal_event(self):
        events = []
        runner = Stage08CodexRunner.__new__(Stage08CodexRunner)
        runner.telemetry_recorder = type(
            "Recorder",
            (),
            {"record": lambda _self, event: events.append(event)},
        )()
        task = type(
            "Task",
            (),
            {"task_id": "T007", "raw_markdown": "deterministic task contract"},
        )()
        result = CodexTaskRunResult(
            task_id="T007",
            title="Deterministic task",
            codex_returncode=0,
            codex_stdout="",
            codex_stderr="",
            changed_paths=["allowed.py"],
            verification=[VerificationResult("deterministic verify", 1, "", "failure")],
            checkpoint_commit=None,
            next_task=None,
            status="VERIFICATION_FAILED",
            evidence_file=".sdd/evidence/test.json",
        )

        def deterministic_started_attempt(task_id=None):
            self.assertEqual(task_id, "T007")
            runner._telemetry_attempt_task = task
            return result

        runner._execute_one = deterministic_started_attempt

        self.assertIs(runner.execute_one("T007"), result)
        terminal_events = [event for event in events if event.event_type == EventType.STAGE08_TASK]
        self.assertEqual(len(terminal_events), 1)
        event = terminal_events[0]
        self.assertEqual(event.outcome_category.value, "failed")
        self.assertEqual(event.stage_id, "08")
        self.assertIsNone(event.usage)
        self.assertEqual(set(event.metadata), {
            "task_id",
            "terminal_status",
            "verification_count",
            "changed_path_count",
            "checkpoint_created",
        })
        self.assertEqual(event.metadata["terminal_status"], "VERIFICATION_FAILED")
        for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
            self.assertNotIn(forbidden, event.metadata)

    def test_stage08_retry_started_twice_emits_two_terminal_events(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory) / "repo"
            shutil.copytree(source / ".sdd", repo / ".sdd")
            for relative_path, text in {
                "AGENTS.md": "# AGENTS\nDo not modify authoritative contracts.\n",
                "docs/PRD.md": "# PRD\nFR-001 deterministic retry\n",
                "docs/spec.md": "# Spec\nSPEC-001 deterministic retry behavior\n",
                "docs/Design.md": "# Design\nDES-001 deterministic retry design\n",
            }.items():
                path = repo / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=repo, text=True, capture_output=True, check=True
                ).stdout.strip()

            git("init")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            git("add", ".")
            git("commit", "-m", "initial")
            project_state_path = repo / ".sdd/state/project-state.yaml"
            project_state = yaml.safe_load(project_state_path.read_text(encoding="utf-8"))
            project_state["stages"]["07"]["status"] = "DONE"
            project_state["stages"]["07"]["result"] = "PASS"
            project_state["authorizations"]["implementation"] = True
            project_state["lifecycle"]["current_stage"] = "08"
            project_state["lifecycle"]["current_stage_name"] = "IMPLEMENTATION_RUNNER"
            project_state_path.write_text(
                yaml.safe_dump(project_state, sort_keys=False), encoding="utf-8"
            )
            (repo / "tasks.md").write_text(
                """\
### T007 ? Deterministic retry task
- **Status:** TODO
- **Allowed files:** `src/retry.py`, `tests/test_retry.py`
- **Implementation Scope:** Implement deterministic retry behavior.
- **Verification Commands:** `python -m pytest -q tests/test_retry.py`
""",
                encoding="utf-8",
            )
            git("add", "tasks.md", ".sdd/state/project-state.yaml")
            git("commit", "-m", "authorize stage08")

            events = []
            recorder = type(
                "Recorder", (), {"record": lambda _self, event: events.append(event)}
            )()
            provider_calls = []

            class FailingCodex:
                def execute(self, repo_root, prompt):
                    provider_calls.append(prompt)
                    return SimpleNamespace(returncode=1, stdout="", stderr="failed")

            first = Stage08CodexRunner(
                Orchestrator(repo), codex=FailingCodex(), telemetry_recorder=recorder
            ).execute_one("T007")
            self.assertEqual(first.status, "CODEX_FAILED")

            class SuccessfulCodex:
                def execute(self, repo_root, prompt):
                    provider_calls.append(prompt)
                    (repo_root / "src").mkdir(exist_ok=True)
                    (repo_root / "tests").mkdir(exist_ok=True)
                    (repo_root / "src/retry.py").write_text("VALUE = 1\n", encoding="utf-8")
                    (repo_root / "tests/test_retry.py").write_text(
                        "from src.retry import VALUE\n\n"
                        "def test_retry():\n    assert VALUE == 1\n",
                        encoding="utf-8",
                    )
                    return SimpleNamespace(returncode=0, stdout="done", stderr="")

            second = Stage08CodexRunner(
                Orchestrator(repo), codex=SuccessfulCodex(), telemetry_recorder=recorder
            ).execute_one("T007")
            self.assertEqual(second.status, "DONE")
            self.assertEqual(len(provider_calls), 2)

            terminal_events = [
                event for event in events if event.event_type == EventType.STAGE08_TASK
            ]
            self.assertEqual(len(terminal_events), 2)
            self.assertEqual(
                [event.metadata["task_id"] for event in terminal_events], ["T007", "T007"]
            )
            self.assertEqual(len({event.event_id for event in terminal_events}), 2)
            self.assertEqual(
                [event.metadata["terminal_status"] for event in terminal_events],
                ["CODEX_FAILED", "DONE"],
            )
            for event in terminal_events:
                self.assertIn(event.outcome_category.value, {"completed", "failed"})
                for forbidden in ("attempt_id", "retry_attempt", "duration", "duration_ms"):
                    self.assertNotIn(forbidden, event.metadata)

if __name__ == "__main__":
    unittest.main()
