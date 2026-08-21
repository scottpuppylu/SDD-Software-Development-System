import unittest

from sdd_orchestrator.telemetry.models import (
    CANONICALIZATION_ID,
    SCHEMA_ID,
    SCHEMA_VERSION,
    Component,
    ContentMetric,
    EventType,
    Layer,
    MeasurementEvent,
    Usage,
)


class TelemetryModelTests(unittest.TestCase):
    def _metric(self, classification=Component.CODE, classification_reason=None):
        return ContentMetric(
            classification=classification,
            classification_reason=classification_reason,
            layer=Layer.REQUEST,
            chars=3,
            utf8_bytes=3,
            sha256="a" * 64,
            canonicalization_id=CANONICALIZATION_ID,
            source_count=1,
            source_paths=None,
            truncated=False,
            omitted_items=0,
        )

    def _usage(self):
        return Usage(
            availability="available",
            quality="actual",
            usage_source="openai_responses_usage",
            input_tokens=2,
            output_tokens=3,
            total_tokens=5,
            component_tokens=None,
        )

    def _event(self, event_type, usage):
        return MeasurementEvent(
            event_type=event_type,
            event_id="123e4567-e89b-12d3-a456-426614174000",
            observed_at="2026-08-21T07:00:00Z",
            stage_id="03",
            run_id=None,
            outcome_category=None,
            metrics=[],
            usage=usage,
            metadata={},
        )

    def test_schema_identity_is_frozen(self):
        self.assertEqual(SCHEMA_ID, "sdd.measurement.stage_execution")
        self.assertEqual(SCHEMA_VERSION, "1.0.0")
        event = self._event(EventType.STAGE_REQUEST, None)
        self.assertEqual(event.schema_id, SCHEMA_ID)
        self.assertEqual(event.schema_version, SCHEMA_VERSION)

    def test_event_type_vocabulary_is_closed(self):
        self.assertEqual(
            {member.value for member in EventType},
            {"stage_request", "provider_call", "stage08_task"},
        )

    def test_usage_semantics_are_required_by_event_type(self):
        self._event(EventType.STAGE_REQUEST, None)
        self._event(EventType.PROVIDER_CALL, self._usage())
        self._event(EventType.STAGE08_TASK, None)
        with self.assertRaises((TypeError, ValueError)):
            self._event(EventType.STAGE_REQUEST, self._usage())
        with self.assertRaises((TypeError, ValueError)):
            self._event(EventType.PROVIDER_CALL, None)
        with self.assertRaises((TypeError, ValueError)):
            self._event(EventType.STAGE08_TASK, self._usage())

    def test_content_metric_has_exact_frozen_required_fields(self):
        metric = self._metric()
        self.assertEqual(
            set(metric.to_dict()),
            {
                "classification",
                "classification_reason",
                "layer",
                "chars",
                "utf8_bytes",
                "sha256",
                "canonicalization_id",
                "source_count",
                "source_paths",
                "truncated",
                "omitted_items",
            },
        )

    def test_component_and_layer_vocabularies_are_frozen(self):
        self.assertEqual(
            {member.value for member in Component},
            {
                "governance", "stage_instruction", "stage_contract",
                "authority_artifacts", "operational_state", "repo_structure",
                "code", "tests", "evidence", "history", "user_input", "other",
            },
        )
        self.assertEqual(
            {member.value for member in Layer},
            {"request", "system_prompt", "user_prompt", "rendered", "wire", "tool_context"},
        )

    def test_other_component_requires_non_empty_classification_reason(self):
        for reason in (None, "", "   "):
            with self.subTest(reason=reason), self.assertRaises((TypeError, ValueError)):
                self._metric(Component.OTHER, reason)
        self._metric(Component.OTHER, "not covered by the fixed vocabulary")

    def test_known_component_requires_null_classification_reason(self):
        with self.assertRaises((TypeError, ValueError)):
            self._metric(Component.CODE, "unnecessary override")


if __name__ == "__main__":
    unittest.main()
