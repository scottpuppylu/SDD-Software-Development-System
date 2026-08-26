import inspect
import unittest
from dataclasses import fields

from sdd_orchestrator.codex_adapter import Stage08CodexRunner
from sdd_orchestrator.codex_results import CodexTaskRunResult, VerificationResult
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

if __name__ == "__main__":
    unittest.main()
