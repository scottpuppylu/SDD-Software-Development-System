import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from sdd_orchestrator.core import Orchestrator
from sdd_orchestrator.executor import StageExecutionRequest, StageExecutionResult
from sdd_orchestrator.runner import StageRunner
from sdd_orchestrator.telemetry import measurement
from sdd_orchestrator.telemetry.models import Component, EventType, Layer, MeasurementEvent


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FROZEN_COMPONENTS = {
    "governance",
    "stage_instruction",
    "stage_contract",
    "authority_artifacts",
    "operational_state",
    "repo_structure",
    "code",
    "tests",
    "evidence",
    "history",
    "user_input",
    "other",
}


def _measure(request):
    measure_stage_request = getattr(measurement, "measure_stage_request", None)
    if measure_stage_request is None:
        raise AssertionError(
            "M1.2 requires sdd_orchestrator.telemetry.measurement.measure_stage_request"
        )
    return measure_stage_request(request)


def _request(**overrides):
    values = {
        "stage_id": "09",
        "stage_name": "POST_IMPLEMENTATION_VERIFICATION",
        "stage_type": "GATE",
        "core_question": "Is the implementation verified?",
        "contract": {"name": "POST_IMPLEMENTATION_VERIFICATION", "type": "GATE"},
        "artifacts": {"docs/PRD.md": "authoritative requirements"},
        "semantic_inputs": {"REVIEW_FOCUS": "user supplied focus"},
        "runtime_inputs": {},
        "stage_instructions": "Follow the stage instructions.",
    }
    values.update(overrides)
    return StageExecutionRequest(**values)


class StageRequestMeasurementTests(unittest.TestCase):
    def test_measure_stage_request_produces_stage_request_event_with_null_usage(self):
        event = _measure(_request())

        self.assertIsInstance(event, MeasurementEvent)
        self.assertEqual(event.event_type, EventType.STAGE_REQUEST)
        self.assertEqual(event.stage_id, "09")
        self.assertIsNone(event.usage)
        self.assertTrue(event.metrics)
        self.assertTrue(all(metric.layer is Layer.REQUEST for metric in event.metrics))

    def test_request_level_metrics_use_stable_canonical_chars_bytes_and_hash(self):
        request = _request(
            core_question="Verify 繁😀e\u0301",
            semantic_inputs={"z": 2, "a": "line1\r\nline2"},
        )
        canonical = json.dumps(
            request.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        event = _measure(request)

        self.assertEqual(event.metadata["request_chars"], len(canonical))
        self.assertEqual(event.metadata["request_utf8_bytes"], len(canonical.encode("utf-8")))
        self.assertEqual(
            event.metadata["request_sha256"],
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        )

    def test_component_classification_uses_only_frozen_vocabulary(self):
        event = _measure(_request(runtime_inputs={"UNCLASSIFIED_CONTEXT": "unknown"}))

        self.assertEqual({component.value for component in Component}, FROZEN_COMPONENTS)
        self.assertTrue(
            {metric.classification.value for metric in event.metrics}.issubset(FROZEN_COMPONENTS)
        )
        self.assertNotIn("artifact", FROZEN_COMPONENTS)
        self.assertNotIn("semantic_input", FROZEN_COMPONENTS)
        self.assertNotIn("runtime_input", FROZEN_COMPONENTS)

    def test_real_request_fields_are_classified_by_path_and_role(self):
        request = _request(
            contract={"name": "gate", "required_inputs": {"files": ["docs/PRD.md"]}},
            artifacts={
                "AGENTS.md": "governance rules",
                "docs/PRD.md": "requirements authority",
            },
            semantic_inputs={"REVIEW_FOCUS": "user supplied"},
            runtime_inputs={
                "GIT_STATUS": " M src/app.py",
                "CURRENT_BRANCH": "telemetry-measurement-v2",
                "REPOSITORY_STRUCTURE": ["src/app.py", "tests/test_app.py"],
                "SOURCE_CODE": {"src/app.py": "VALUE = 1\n"},
                "TEST_EVIDENCE": {"tests/test_app.py": "def test_value(): pass\n"},
                "BUILD_LINT_TYPECHECK_EVIDENCE_IF_APPLICABLE": {"pytest": "passed"},
                "GIT_HISTORY": "abc123 implement feature",
                "UNCLASSIFIED_CONTEXT": "fallback",
            },
            stage_instructions="stage-specific instructions",
        )
        event = _measure(request)
        classifications = [metric.classification.value for metric in event.metrics]

        for expected in FROZEN_COMPONENTS:
            self.assertIn(expected, classifications)
        for metric in event.metrics:
            if metric.classification is Component.OTHER:
                self.assertTrue(metric.classification_reason)
            else:
                self.assertIsNone(metric.classification_reason)

    def test_measurement_is_deterministic_across_dict_insertion_order(self):
        first = _request(
            contract={"z": 2, "a": 1},
            artifacts={"docs/spec.md": "same", "docs/PRD.md": "requirements"},
            semantic_inputs={"Z": "last", "A": "first"},
            runtime_inputs={"GIT_STATUS": "clean", "CURRENT_BRANCH": "main"},
        )
        second = _request(
            contract={"a": 1, "z": 2},
            artifacts={"docs/PRD.md": "requirements", "docs/spec.md": "same"},
            semantic_inputs={"A": "first", "Z": "last"},
            runtime_inputs={"CURRENT_BRANCH": "main", "GIT_STATUS": "clean"},
        )

        first_event = _measure(first)
        second_event = _measure(second)
        signature = lambda event: [
            (m.classification, m.classification_reason, m.sha256, m.source_count)
            for m in event.metrics
        ]
        self.assertEqual(first_event.metadata["request_sha256"], second_event.metadata["request_sha256"])
        self.assertEqual(signature(first_event), signature(second_event))

    def test_duplicate_content_is_preserved_as_distinct_component_instances(self):
        duplicate = "identical body\n"
        event = _measure(
            _request(
                artifacts={"docs/PRD.md": duplicate, "docs/spec.md": duplicate},
                runtime_inputs={
                    "SOURCE_CODE": {"src/a.py": duplicate},
                    "TEST_EVIDENCE": {"tests/test_a.py": duplicate},
                },
            )
        )
        digest = hashlib.sha256(duplicate.encode("utf-8")).hexdigest()
        duplicates = [metric for metric in event.metrics if metric.sha256 == digest]

        self.assertEqual(len(duplicates), 4)
        self.assertCountEqual(
            [metric.classification.value for metric in duplicates],
            ["authority_artifacts", "authority_artifacts", "code", "tests"],
        )

    def test_measurement_does_not_read_repo_files(self):
        request = _request(
            artifacts={"docs/PRD.md": "already loaded"},
            runtime_inputs={"SOURCE_CODE": {"src/app.py": "already loaded source"}},
        )
        with patch.object(Path, "read_text", side_effect=AssertionError("unexpected repo read")), patch.object(
            Path, "read_bytes", side_effect=AssertionError("unexpected repo read")
        ):
            event = _measure(request)
        self.assertTrue(event.metrics)


class _RecordingTelemetry:
    def __init__(self, *, fail=False):
        self.events = []
        self.fail = fail

    def record(self, event):
        self.events.append(event)
        if self.fail:
            raise OSError("telemetry failed")


class _CountingExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.requests = []

    def execute(self, request):
        self.calls += 1
        self.requests.append(request)
        return self.result


class StageRunnerStageRequestTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(SOURCE_ROOT / ".sdd", self.repo / ".sdd")
        path = self.repo / "docs" / "proposal.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("proposal", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _result(self):
        return StageExecutionResult(status="COMPLETED", artifacts={"docs/PRD.md": "# PRD\n"})

    def test_run_emits_exactly_one_stage_request_after_build_and_before_execute(self):
        order = []
        recorder = _RecordingTelemetry()
        original_record = recorder.record

        def record(event):
            order.append(("record", event.stage_id))
            original_record(event)

        recorder.record = record
        executor = _CountingExecutor(self._result())
        original_execute = executor.execute

        def execute(request):
            order.append(("execute", request.stage_id))
            return original_execute(request)

        executor.execute = execute
        runner = StageRunner(Orchestrator(self.repo), telemetry_recorder=recorder)
        runner.run(executor, "02", semantic_inputs={"APPROVED_PRODUCT_DECISIONS": "yes"})

        stage_events = [event for event in recorder.events if event.event_type is EventType.STAGE_REQUEST]
        self.assertEqual(len(stage_events), 1)
        self.assertEqual(order, [("record", "02"), ("execute", "02")])

    def test_null_recorder_preserves_executor_call_request_and_outcome(self):
        executor = _CountingExecutor(self._result())
        runner = StageRunner(Orchestrator(self.repo), telemetry_recorder=None)

        outcome = runner.run(
            executor, "02", semantic_inputs={"APPROVED_PRODUCT_DECISIONS": "yes"}
        )

        self.assertEqual(executor.calls, 1)
        self.assertEqual(executor.requests[0].semantic_inputs, {"APPROVED_PRODUCT_DECISIONS": "yes"})
        self.assertEqual(outcome["executor_status"], "COMPLETED")
        self.assertEqual(outcome["transition"]["next"], "03")

    def test_recorder_failure_preserves_single_executor_call_and_result_semantics(self):
        recorder = _RecordingTelemetry(fail=True)
        executor = _CountingExecutor(self._result())
        runner = StageRunner(Orchestrator(self.repo), telemetry_recorder=recorder)

        outcome = runner.run(
            executor, "02", semantic_inputs={"APPROVED_PRODUCT_DECISIONS": "yes"}
        )

        self.assertEqual(executor.calls, 1)
        self.assertEqual(len(recorder.events), 1)
        self.assertEqual(outcome["executor_status"], "COMPLETED")
        self.assertEqual(outcome["transition"]["next"], "03")

    def test_packet_build_never_emits_provider_call_telemetry(self):
        recorder = _RecordingTelemetry()
        runner = StageRunner(Orchestrator(self.repo), telemetry_recorder=recorder)

        packet = runner.create_execution_packet(
            "02", semantic_inputs={"APPROVED_PRODUCT_DECISIONS": "yes"}
        )

        self.assertTrue(packet.exists())
        self.assertFalse(
            any(event.event_type is EventType.PROVIDER_CALL for event in recorder.events)
        )


if __name__ == "__main__":
    unittest.main()
