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

    def test_lifecycle_result_schemas_remain_telemetry_free(self):
        forbidden = {"telemetry", "measurement", "usage", "stage08_task", "event_id"}
        self.assertFalse({field.name for field in fields(CodexTaskRunResult)} & forbidden)
        self.assertFalse({field.name for field in fields(VerificationResult)} & forbidden)


class Stage08TaskRecorderBoundaryTests(unittest.TestCase):
    def test_runner_accepts_a_shared_optional_telemetry_recorder(self):
        parameters = inspect.signature(Stage08CodexRunner.__init__).parameters
        self.assertIn("telemetry_recorder", parameters)
        self.assertIsNone(parameters["telemetry_recorder"].default)

if __name__ == "__main__":
    unittest.main()
