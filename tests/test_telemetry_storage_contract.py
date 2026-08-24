import json
import os
from pathlib import Path
import tempfile
import unittest

from sdd_orchestrator.telemetry.measurement import canonical_json_bytes
from sdd_orchestrator.telemetry.models import EventType, MeasurementEvent, SCHEMA_VERSION
from sdd_orchestrator.telemetry.recorder import TelemetryRecorder
from sdd_orchestrator.telemetry import sinks
from sdd_orchestrator.telemetry.sinks import NullTelemetrySink


def _event(event_id="123e4567-e89b-12d3-a456-426614174000", metadata=None):
    return MeasurementEvent(
        event_type=EventType.STAGE_REQUEST,
        event_id=event_id,
        observed_at="2026-08-24T00:00:00Z",
        stage_id="03",
        run_id=None,
        outcome_category=None,
        metrics=[],
        usage=None,
        metadata=metadata or {},
    )


def _from_environment(repo_root, environ):
    factory = getattr(TelemetryRecorder, "from_environment", None)
    if factory is None:
        raise AssertionError(
            "M2.1 requires TelemetryRecorder.from_environment(repo_root, environ=...)"
        )
    return factory(repo_root, environ=environ)


def _jsonl_sink(directory):
    sink_type = getattr(sinks, "JsonlTelemetrySink", None)
    if sink_type is None:
        raise AssertionError("M2.1 requires sdd_orchestrator.telemetry.sinks.JsonlTelemetrySink")
    return sink_type(directory)


class TelemetryConfigurationContractTests(unittest.TestCase):
    def test_m21_uses_amended_schema_version(self):
        self.assertEqual(SCHEMA_VERSION, "1.0.3")

    def test_enable_grammar_accepts_only_frozen_true_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            for value in ("1", "true", "TRUE", " yes ", "\tOn\r\n"):
                output = root / f"enabled-{value.strip().lower()}"
                with self.subTest(value=value):
                    recorder = _from_environment(
                        repo,
                        {"SDD_TELEMETRY_ENABLED": value, "SDD_TELEMETRY_DIR": str(output)},
                    )
                    recorder.record(_event())
                    self.assertTrue((output / "events.jsonl").is_file())

    def test_missing_empty_invalid_and_non_true_values_are_disabled_without_side_effects(self):
        false_values = (
            None,
            "",
            "   ",
            "0",
            "false",
            "no",
            "off",
            "enabled",
            "2",
            "\u00a0true\u00a0",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            for index, value in enumerate(false_values):
                output = root / f"disabled-{index}"
                environ = {"SDD_TELEMETRY_DIR": str(output)}
                if value is not None:
                    environ["SDD_TELEMETRY_ENABLED"] = value
                with self.subTest(value=value):
                    recorder = _from_environment(repo, environ)
                    recorder.record(_event())
                    self.assertIsInstance(recorder._sink, NullTelemetrySink)
                    self.assertFalse(output.exists())

    def test_directory_override_is_not_consulted_when_disabled(self):
        class Environment(dict):
            def get(self, key, default=None):
                if key == "SDD_TELEMETRY_DIR":
                    raise AssertionError("disabled telemetry consulted its directory override")
                return super().get(key, default)

            def __getitem__(self, key):
                if key == "SDD_TELEMETRY_DIR":
                    raise AssertionError("disabled telemetry consulted its directory override")
                return super().__getitem__(key)

        with tempfile.TemporaryDirectory() as directory:
            recorder = _from_environment(
                Path(directory) / "repo",
                Environment(SDD_TELEMETRY_ENABLED="false"),
            )
            self.assertIsInstance(recorder._sink, NullTelemetrySink)

    def test_relative_override_is_resolved_from_process_cwd_not_repository_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            cwd = root / "process-cwd"
            repo.mkdir()
            cwd.mkdir()
            previous = Path.cwd()
            try:
                os.chdir(cwd)
                recorder = _from_environment(
                    repo,
                    {"SDD_TELEMETRY_ENABLED": "true", "SDD_TELEMETRY_DIR": "observations"},
                )
                recorder.record(_event())
            finally:
                os.chdir(previous)
            self.assertTrue((cwd / "observations" / "events.jsonl").is_file())
            self.assertFalse((repo / "observations").exists())

    def test_repository_root_and_descendants_fall_back_to_null_sink(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            for destination in (
                repo,
                repo / "telemetry",
                repo / "outside" / ".." / "telemetry",
                repo / ".sdd" / "state" / "telemetry",
            ):
                with self.subTest(destination=destination):
                    recorder = _from_environment(
                        repo,
                        {
                            "SDD_TELEMETRY_ENABLED": "yes",
                            "SDD_TELEMETRY_DIR": str(destination),
                        },
                    )
                    recorder.record(_event())
                    self.assertIsInstance(recorder._sink, NullTelemetrySink)
                    self.assertFalse((destination / "events.jsonl").exists())

    @unittest.skipUnless(os.name == "nt", "Windows default is platform-specific")
    def test_windows_default_is_under_localappdata_and_external_to_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            local_app_data = root / "local-app-data"
            repo.mkdir()
            recorder = _from_environment(
                repo,
                {"SDD_TELEMETRY_ENABLED": "on", "LOCALAPPDATA": str(local_app_data)},
            )
            recorder.record(_event())
            expected = local_app_data / "sdd-orchestrator" / "telemetry" / "events.jsonl"
            self.assertTrue(expected.is_file())

    def test_unusable_destination_falls_back_without_repository_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            unusable = root / "not-a-directory"
            unusable.write_text("occupied", encoding="utf-8")
            recorder = _from_environment(
                repo,
                {"SDD_TELEMETRY_ENABLED": "1", "SDD_TELEMETRY_DIR": str(unusable)},
            )
            recorder.record(_event())
            self.assertIsInstance(recorder._sink, NullTelemetrySink)
            self.assertEqual(unusable.read_text(encoding="utf-8"), "occupied")
            self.assertEqual(list(repo.iterdir()), [])


class JsonlTelemetryStorageContractTests(unittest.TestCase):
    def test_records_are_direct_canonical_schema_objects_with_one_lf_each(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "telemetry"
            first = _event(metadata={"unicode": "e\u0301", "z": 1})
            second = _event(
                event_id="123e4567-e89b-12d3-a456-426614174001",
                metadata={"message": "測量"},
            )
            sink = _jsonl_sink(output)
            sink.record(first)
            sink.record(second)

            path = output / "events.jsonl"
            expected = canonical_json_bytes(first.to_dict()) + b"\n" + canonical_json_bytes(second.to_dict()) + b"\n"
            self.assertEqual(path.read_bytes(), expected)
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertEqual([item.name for item in output.iterdir()], ["events.jsonl"])
            for line, event in zip(path.read_text(encoding="utf-8").splitlines(), (first, second)):
                self.assertEqual(json.loads(line), event.to_dict())

    def test_sink_serializes_measurement_event_to_dict_not_a_storage_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            event = _event()
            sink = _jsonl_sink(Path(directory))
            sink.record(event)
            stored = json.loads((Path(directory) / "events.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(set(stored), set(event.to_dict()))
            self.assertNotIn("event", stored)
            self.assertNotIn("payload", stored)

    def test_append_serialization_or_flush_failure_is_best_effort_through_recorder(self):
        event = _event()
        for failure in (TypeError("serialization failed"), OSError("write failed")):
            class FailingSink:
                def record(self, observed):
                    self.observed = observed
                    raise failure

            with self.subTest(failure=type(failure).__name__):
                sink = FailingSink()
                recorder = TelemetryRecorder(sink)
                self.assertIsNone(recorder.record(event))
                self.assertIs(sink.observed, event)


if __name__ == "__main__":
    unittest.main()
