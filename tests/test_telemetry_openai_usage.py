import io
import json
import subprocess
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from sdd_orchestrator.executor import StageExecutionRequest, StageExecutionResult
from sdd_orchestrator.providers import (
    CodexExecReasoningExecutor,
    OpenAIResponsesExecutor,
    ReasoningProviderError,
)
from sdd_orchestrator.telemetry.models import (
    Availability,
    EventType,
    Quality,
    UsageSource,
)


def _request():
    return StageExecutionRequest(
        stage_id="03",
        stage_name="TECHNICAL_SPECIFICATION",
        stage_type="AUTHORING",
        core_question="What must the system guarantee?",
        contract={"outputs": {"files": ["docs/spec.md"]}},
        artifacts={"docs/PRD.md": "authority body must not enter metadata"},
        semantic_inputs={"REVIEW_FOCUS": "prompt body must not enter metadata"},
        runtime_inputs={},
        stage_instructions="Only Technical Contract authority.",
    )


def _result_data():
    return {
        "status": "COMPLETED",
        "artifacts": [{"path": "docs/spec.md", "content": "# spec"}],
        "result": None,
        "classification": None,
        "remediation_reasons": [],
        "convergence_tasks": [],
        "provider_notes": "ok",
    }


def _payload(usage_marker=None):
    payload = {
        "id": "resp_usage_test",
        "output_text": json.dumps(_result_data()),
    }
    if usage_marker is not _MISSING:
        payload["usage"] = usage_marker
    return payload


class _Missing:
    pass


_MISSING = _Missing()


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class _Recorder:
    def __init__(self, fail=False):
        self.events = []
        self.fail = fail

    def record(self, event):
        self.events.append(event)
        if self.fail:
            raise OSError("telemetry recorder failed")


def _provider_event(recorder):
    events = [event for event in recorder.events if event.event_type is EventType.PROVIDER_CALL]
    if len(events) != 1:
        raise AssertionError(f"expected one provider_call event, got {len(events)}")
    return events[0]


def _assert_unavailable(testcase, usage, source=UsageSource.OPENAI_RESPONSES_UNAVAILABLE):
    testcase.assertEqual(usage.availability, Availability.UNAVAILABLE)
    testcase.assertEqual(usage.quality, Quality.UNAVAILABLE)
    testcase.assertEqual(usage.usage_source, source)
    testcase.assertIsNone(usage.input_tokens)
    testcase.assertIsNone(usage.output_tokens)
    testcase.assertIsNone(usage.total_tokens)
    testcase.assertIsNone(usage.component_tokens)


class OpenAIResponsesActualUsageRedTests(unittest.TestCase):
    def _execute_openai(self, payload, recorder=None):
        recorder = recorder or _Recorder()
        executor = OpenAIResponsesExecutor(
            api_key="api-key-must-never-be-recorded",
            model="gpt-test",
            telemetry_recorder=recorder,
        )
        with patch(
            "sdd_orchestrator.providers.urllib.request.urlopen",
            return_value=_Response(payload),
        ) as invocation:
            result = executor.execute(_request())
        self.assertEqual(invocation.call_count, 1)
        return result, _provider_event(recorder), recorder

    def test_response_root_usage_aggregates_are_recorded_verbatim_without_recalculation(self):
        usage = {"input_tokens": 41, "output_tokens": 7, "total_tokens": 99}
        _, event, _ = self._execute_openai(_payload(usage))

        self.assertEqual(event.usage.availability, Availability.AVAILABLE)
        self.assertEqual(event.usage.quality, Quality.ACTUAL)
        self.assertEqual(event.usage.usage_source, UsageSource.OPENAI_RESPONSES_USAGE)
        self.assertEqual(event.usage.input_tokens, 41)
        self.assertEqual(event.usage.output_tokens, 7)
        self.assertEqual(event.usage.total_tokens, 99)

    def test_openai_usage_details_map_to_exact_canonical_component_keys(self):
        usage = {
            "input_tokens": 20,
            "output_tokens": 8,
            "total_tokens": 28,
            "input_tokens_details": {"cached_tokens": 6},
            "output_tokens_details": {"reasoning_tokens": 3},
        }
        _, event, _ = self._execute_openai(_payload(usage))

        self.assertEqual(
            event.usage.component_tokens,
            {"cached_input_tokens": 6, "reasoning_output_tokens": 3},
        )

    def test_missing_optional_details_keep_both_canonical_component_keys_as_none(self):
        _, event, _ = self._execute_openai(
            _payload({"input_tokens": 20, "output_tokens": 8, "total_tokens": 28})
        )

        self.assertEqual(
            event.usage.component_tokens,
            {"cached_input_tokens": None, "reasoning_output_tokens": None},
        )

    def test_missing_usage_object_remains_openai_unavailable_with_all_tokens_none(self):
        _, event, _ = self._execute_openai(_payload(_MISSING))
        _assert_unavailable(self, event.usage)

    def test_provider_reported_zero_aggregates_and_components_are_preserved(self):
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        }
        _, event, _ = self._execute_openai(_payload(usage))

        self.assertEqual(
            (event.usage.input_tokens, event.usage.output_tokens, event.usage.total_tokens),
            (0, 0, 0),
        )
        self.assertEqual(
            event.usage.component_tokens,
            {"cached_input_tokens": 0, "reasoning_output_tokens": 0},
        )

    def test_invalid_aggregate_values_are_not_accepted_as_actual_observations(self):
        invalid_values = (True, -1, 1.5, "12", None, [], {})
        fields = ("input_tokens", "output_tokens", "total_tokens")
        for field in fields:
            for invalid in invalid_values:
                with self.subTest(field=field, invalid=invalid):
                    _, event, _ = self._execute_openai(_payload({field: invalid}))
                    _assert_unavailable(self, event.usage)

    def test_invalid_aggregate_field_becomes_none_without_changing_other_actual_aggregates(self):
        invalid_values = (True, -1, 1.5, "12", [], {})
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                usage = {
                    "input_tokens": invalid,
                    "output_tokens": 7,
                    "total_tokens": 99,
                }
                _, event, _ = self._execute_openai(_payload(usage))
                self.assertEqual(event.usage.availability, Availability.AVAILABLE)
                self.assertEqual(event.usage.quality, Quality.ACTUAL)
                self.assertEqual(
                    event.usage.usage_source, UsageSource.OPENAI_RESPONSES_USAGE
                )
                self.assertIsNone(event.usage.input_tokens)
                self.assertEqual(event.usage.output_tokens, 7)
                self.assertEqual(event.usage.total_tokens, 99)
                self.assertEqual(
                    event.usage.component_tokens,
                    {"cached_input_tokens": None, "reasoning_output_tokens": None},
                )

    def test_invalid_component_detail_only_normalizes_that_component_to_none(self):
        invalid_values = (True, -1, 1.5, "4", [], {})
        cases = (
            ("input_tokens_details", "cached_tokens", "cached_input_tokens", "reasoning_output_tokens", 5),
            ("output_tokens_details", "reasoning_tokens", "reasoning_output_tokens", "cached_input_tokens", 4),
        )
        for container, source_key, invalid_key, valid_key, valid_value in cases:
            for invalid in invalid_values:
                with self.subTest(container=container, invalid=invalid):
                    usage = {
                        "input_tokens": 10,
                        "output_tokens": 6,
                        "total_tokens": 31,
                        "input_tokens_details": {"cached_tokens": 4},
                        "output_tokens_details": {"reasoning_tokens": 5},
                    }
                    usage[container][source_key] = invalid
                    _, event, _ = self._execute_openai(_payload(usage))
                    self.assertEqual(event.usage.input_tokens, 10)
                    self.assertEqual(event.usage.output_tokens, 6)
                    self.assertEqual(event.usage.total_tokens, 31)
                    self.assertIsNone(event.usage.component_tokens[invalid_key])
                    self.assertEqual(event.usage.component_tokens[valid_key], valid_value)

    def test_non_object_or_observation_free_usage_does_not_fabricate_actual_usage(self):
        cases = (None, True, 0, [], "usage", {}, {"input_tokens_details": {"cached_tokens": "bad"}})
        for usage in cases:
            with self.subTest(usage=usage):
                _, event, _ = self._execute_openai(_payload(usage))
                _assert_unavailable(self, event.usage)

    def test_http_timeout_and_transport_failures_remain_openai_unavailable(self):
        failures = (
            urllib.error.HTTPError(
                "https://example.invalid", 429, "rate limited", {}, io.BytesIO(b"raw response body")
            ),
            TimeoutError("timed out"),
            urllib.error.URLError(OSError("transport failed")),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                recorder = _Recorder()
                executor = OpenAIResponsesExecutor(
                    api_key="secret", telemetry_recorder=recorder
                )
                with patch(
                    "sdd_orchestrator.providers.urllib.request.urlopen", side_effect=failure
                ) as invocation:
                    with self.assertRaises((ReasoningProviderError, TimeoutError)):
                        executor.execute(_request())
                self.assertEqual(invocation.call_count, 1)
                _assert_unavailable(self, _provider_event(recorder).usage)

    def test_recorder_failure_preserves_openai_success_exception_and_call_count(self):
        recorder = _Recorder(fail=True)
        result, _, _ = self._execute_openai(
            _payload({"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}), recorder
        )
        self.assertIsInstance(result, StageExecutionResult)
        self.assertEqual(result.status, "COMPLETED")

        recorder = _Recorder(fail=True)
        executor = OpenAIResponsesExecutor(api_key="secret", telemetry_recorder=recorder)
        original = urllib.error.URLError(OSError("original transport failure"))
        with patch(
            "sdd_orchestrator.providers.urllib.request.urlopen", side_effect=original
        ) as invocation:
            with self.assertRaises(ReasoningProviderError) as caught:
                executor.execute(_request())
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(invocation.call_count, 1)
        self.assertEqual(len(recorder.events), 1)

    def test_usage_extraction_does_not_store_response_usage_secrets_headers_or_prompt_in_metadata(self):
        raw_marker = "raw-usage-json-marker"
        usage = {
            "input_tokens": 5,
            "output_tokens": 2,
            "total_tokens": 7,
            "input_tokens_details": {"cached_tokens": 1, "raw": raw_marker},
        }
        _, event, _ = self._execute_openai(_payload(usage))
        metadata = json.dumps(event.metadata, ensure_ascii=False)
        for forbidden in (
            raw_marker,
            "resp_usage_test",
            "output_text",
            "api-key-must-never-be-recorded",
            "Authorization",
            "Bearer ",
            "authority body must not enter metadata",
            "prompt body must not enter metadata",
        ):
            self.assertNotIn(forbidden, metadata)

    def test_stage_execution_result_schema_remains_telemetry_free(self):
        fields = set(StageExecutionResult.__dataclass_fields__)
        self.assertFalse(fields & {"telemetry", "measurement", "usage", "provider_call"})

    def test_codex_provider_remains_codex_cli_unavailable_and_does_not_parse_process_output(self):
        recorder = _Recorder()
        executor = CodexExecReasoningExecutor(
            executable="codex", repo_root=Path.cwd(), telemetry_recorder=recorder
        )

        def run(cmd, **kwargs):
            output = Path(cmd[cmd.index("--output-last-message") + 1])
            output.write_text(json.dumps(_result_data()), encoding="utf-8")
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='{"usage":{"input_tokens":91}}',
                stderr='{"usage":{"output_tokens":37}}',
            )

        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=run
        ) as invocation:
            result = executor.execute(_request())

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(invocation.call_count, 1)
        _assert_unavailable(
            self, _provider_event(recorder).usage, UsageSource.CODEX_CLI_UNAVAILABLE
        )


if __name__ == "__main__":
    unittest.main()
