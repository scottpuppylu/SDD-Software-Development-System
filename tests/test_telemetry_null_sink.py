import tempfile
import unittest
from pathlib import Path

from sdd_orchestrator.telemetry.recorder import TelemetryRecorder
from sdd_orchestrator.telemetry.sinks import NullTelemetrySink


class _FailingSink:
    def record(self, event):
        raise OSError("telemetry destination unavailable")


class TelemetryNullSinkTests(unittest.TestCase):
    def test_null_sink_creates_no_files_changes_no_state_and_does_not_raise(self):
        sink = NullTelemetrySink()
        event = {"event_type": "stage_request", "usage": None}
        before_sink_state = dict(vars(sink))
        before_event = dict(event)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sink.record(event)
            sink.record(event)
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(vars(sink), before_sink_state)
        self.assertEqual(event, before_event)

    def test_recorder_swallows_sink_failure_for_best_effort_execution(self):
        recorder = TelemetryRecorder(_FailingSink())
        event = {"event_type": "stage_request", "usage": None}
        try:
            result = recorder.record(event)
        except Exception as exc:  # pragma: no cover - this is the forbidden behavior
            self.fail(f"telemetry failure escaped into the execution path: {exc!r}")
        self.assertIsNone(result)
        self.assertEqual(event, {"event_type": "stage_request", "usage": None})


if __name__ == "__main__":
    unittest.main()
