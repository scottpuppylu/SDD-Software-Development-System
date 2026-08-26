import hashlib
import io
import json
import subprocess
import unittest
import urllib.error
from contextlib import ExitStack
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
    Component,
    EventType,
    Layer,
    OutcomeCategory,
    Quality,
    Usage,
    UsageSource,
)
from sdd_orchestrator.telemetry.measurement import measure_provider_call


def _request():
    return StageExecutionRequest(
        stage_id="03",
        stage_name="TECHNICAL_SPECIFICATION",
        stage_type="AUTHORING",
        core_question="What must the system guarantee?",
        contract={"outputs": {"files": ["docs/spec.md"]}},
        artifacts={"docs/PRD.md": "secret-free authoritative input"},
        semantic_inputs={"REVIEW_FOCUS": "Unicode 測試"},
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


def _openai_payload():
    return {
        "id": "resp_test",
        "output_text": json.dumps(_result_data(), ensure_ascii=False),
    }


class _Recorder:
    def __init__(self, *, fail=False):
        self.events = []
        self.fail = fail

    def record(self, event):
        self.events.append(event)
        if self.fail:
            raise OSError("telemetry sink failed")


class _Response:
    def __init__(self, payload=None):
        self.payload = payload or _openai_payload()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def _codex_run_success(cmd, **kwargs):
    output = Path(cmd[cmd.index("--output-last-message") + 1])
    output.write_text(json.dumps(_result_data(), ensure_ascii=False), encoding="utf-8")
    return subprocess.CompletedProcess(cmd, 0, stdout="provider stdout", stderr="")


def _provider_events(recorder):
    return [event for event in recorder.events if event.event_type is EventType.PROVIDER_CALL]


def _metric(event, layer, classification=None):
    matches = [
        item
        for item in event.metrics
        if item.layer is layer
        and (classification is None or item.classification.value == classification)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one {layer.value}/{classification or '*'} metric, got {len(matches)}"
        )
    return matches[0]


class ProviderCallEnvelopeRedTests(unittest.TestCase):
    def _codex(self, recorder=None):
        return CodexExecReasoningExecutor(
            executable="codex",
            model="test-model",
            repo_root=Path.cwd(),
            telemetry_recorder=recorder,
        )

    def _openai(self, recorder=None):
        return OpenAIResponsesExecutor(
            api_key="api-key-must-never-be-measured",
            model="gpt-test",
            telemetry_recorder=recorder,
        )

    def test_codex_invocation_emits_rendered_snapshot_and_omits_unobservable_wire(self):
        recorder = _Recorder()
        executor = self._codex(recorder)
        request = _request()
        captured = {}

        def run(cmd, **kwargs):
            captured.update(kwargs)
            return _codex_run_success(cmd, **kwargs)

        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=run
        ) as invocation:
            executor.execute(request)

        self.assertEqual(invocation.call_count, 1)
        event, = _provider_events(recorder)
        prompt = executor.build_prompt(request)
        rendered = _metric(event, Layer.RENDERED)
        self.assertEqual(captured["input"], prompt)
        self.assertEqual(rendered.chars, len(prompt))
        self.assertEqual(rendered.utf8_bytes, len(prompt.encode("utf-8")))
        self.assertEqual(rendered.sha256, hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        self.assertFalse(
            [metric for metric in event.metrics if metric.layer is Layer.WIRE],
            "Codex stdin is rendered content, not an exact observable transport payload",
        )

    def test_openai_invocation_emits_exactly_one_provider_call_with_split_rendered_and_exact_request_data_wire(self):
        recorder = _Recorder()
        executor = self._openai(recorder)
        captured = {}

        def urlopen(req, timeout):
            captured["request"] = req
            return _Response()

        with patch("sdd_orchestrator.providers.urllib.request.urlopen", side_effect=urlopen) as invocation:
            executor.execute(_request())

        self.assertEqual(invocation.call_count, 1)
        event, = _provider_events(recorder)
        body = json.loads(captured["request"].data.decode("utf-8"))
        system = _metric(event, Layer.RENDERED, "stage_instruction")
        user = _metric(event, Layer.RENDERED, "user_input")
        wire = _metric(event, Layer.WIRE)
        self.assertEqual(system.sha256, hashlib.sha256(body["instructions"].encode("utf-8")).hexdigest())
        self.assertEqual(user.sha256, hashlib.sha256(body["input"].encode("utf-8")).hexdigest())
        self.assertEqual(wire.utf8_bytes, len(captured["request"].data))
        self.assertEqual(wire.sha256, hashlib.sha256(captured["request"].data).hexdigest())
        self.assertNotIn(wire, (system, user))

    def test_m13_usage_is_unavailable_and_never_fabricates_openai_actual_usage(self):
        for factory, boundary in (
            (self._codex, "codex"),
            (self._openai, "openai"),
        ):
            with self.subTest(boundary=boundary):
                recorder = _Recorder()
                executor = factory(recorder)
                if boundary == "codex":
                    context = (
                        patch.object(executor, "resolved_executable", return_value="codex"),
                        patch("sdd_orchestrator.providers.subprocess.run", side_effect=_codex_run_success),
                    )
                else:
                    context = (
                        patch("sdd_orchestrator.providers.urllib.request.urlopen", return_value=_Response()),
                    )
                with context[0]:
                    if len(context) == 2:
                        with context[1]:
                            executor.execute(_request())
                    else:
                        executor.execute(_request())
                event, = _provider_events(recorder)
                self.assertEqual(event.usage.availability, Availability.UNAVAILABLE)
                self.assertEqual(event.usage.quality, Quality.UNAVAILABLE)
                self.assertTrue(all(value is None for value in (
                    event.usage.input_tokens,
                    event.usage.output_tokens,
                    event.usage.total_tokens,
                    event.usage.component_tokens,
                )))
                if boundary == "codex":
                    self.assertEqual(event.usage.usage_source, UsageSource.CODEX_CLI_UNAVAILABLE)
                else:
                    self.assertEqual(
                        event.usage.usage_source,
                        UsageSource.OPENAI_RESPONSES_UNAVAILABLE,
                    )

    def test_openai_provider_observation_rejects_codex_cli_unavailable_provenance(self):
        event = measure_provider_call(
            stage_id="03",
            rendered=[("request", Component.USER_INPUT)],
            wire=b"request",
            outcome_category=OutcomeCategory.COMPLETED,
            metadata={"provider": "openai", "model": "gpt-test"},
        )

        self.assertNotEqual(
            event.usage.usage_source,
            UsageSource.CODEX_CLI_UNAVAILABLE,
        )
        self.assertEqual(
            event.usage.usage_source,
            UsageSource.OPENAI_RESPONSES_UNAVAILABLE,
        )

    def test_provider_call_rejects_cross_provider_usage_provenance(self):
        def unavailable(source):
            return Usage(
                availability=Availability.UNAVAILABLE,
                quality=Quality.UNAVAILABLE,
                usage_source=source,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                component_tokens=None,
            )
        openai_actual = Usage(
            availability=Availability.AVAILABLE,
            quality=Quality.ACTUAL,
            usage_source=UsageSource.OPENAI_RESPONSES_USAGE,
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            component_tokens={
                "cached_input_tokens": None,
                "reasoning_output_tokens": None,
            },
        )
        cases = (
            ("openai", unavailable(UsageSource.CODEX_CLI_UNAVAILABLE)),
            ("codex", unavailable(UsageSource.OPENAI_RESPONSES_UNAVAILABLE)),
            ("codex", openai_actual),
        )
        for provider, usage in cases:
            with self.subTest(provider=provider, source=usage.usage_source):
                with self.assertRaisesRegex(ValueError, "incompatible with provider identity"):
                    measure_provider_call(
                        stage_id="03",
                        rendered=[("request", Component.USER_INPUT)],
                        wire=None,
                        outcome_category=OutcomeCategory.COMPLETED,
                        metadata={"provider": provider, "model": "test"},
                        provider_usage=usage,
                    )

    def test_provenance_construction_failure_is_telemetry_only(self):
        recorder = _Recorder()
        executor = self._openai(recorder)
        with patch(
            "sdd_orchestrator.providers.urllib.request.urlopen", return_value=_Response()
        ) as invocation, patch(
            "sdd_orchestrator.providers.measure_provider_call",
            side_effect=ValueError("usage provenance mismatch"),
        ):
            result = executor.execute(_request())

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(invocation.call_count, 1)

        original = urllib.error.URLError(OSError("original transport failure"))
        with patch(
            "sdd_orchestrator.providers.urllib.request.urlopen", side_effect=original
        ) as invocation, patch(
            "sdd_orchestrator.providers.measure_provider_call",
            side_effect=ValueError("usage provenance mismatch"),
        ):
            with self.assertRaises(ReasoningProviderError) as caught:
                executor.execute(_request())

        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(invocation.call_count, 1)

    def test_duration_uses_monotonic_clock_and_is_non_negative(self):
        recorder = _Recorder()
        executor = self._codex(recorder)
        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=_codex_run_success
        ), patch("sdd_orchestrator.providers.time.monotonic", side_effect=[11.25, 11.75]) as clock:
            executor.execute(_request())

        event, = _provider_events(recorder)
        self.assertGreaterEqual(clock.call_count, 2)
        self.assertGreaterEqual(event.metadata["duration_ms"], 0)
        self.assertEqual(event.metadata["duration_ms"], 500)

    def test_metadata_is_bounded_and_contains_no_bodies_outputs_headers_or_secrets(self):
        recorder = _Recorder()
        executor = self._openai(recorder)
        with patch("sdd_orchestrator.providers.urllib.request.urlopen", return_value=_Response()):
            executor.execute(_request())

        event, = _provider_events(recorder)
        self.assertTrue({"provider", "model", "adapter", "interface"}.issubset(event.metadata))
        serialized = json.dumps(event.to_dict(), ensure_ascii=False)
        for forbidden in (
            "api-key-must-never-be-measured",
            "Authorization",
            "Bearer ",
            "OPENAI_API_KEY",
            "provider stdout",
            "secret-free authoritative input",
            '"output_text"',
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertLess(len(serialized), 20000)

    def test_success_http_error_nonzero_and_timeout_each_emit_one_envelope_without_retry(self):
        cases = (
            ("success", "openai", _Response(), OutcomeCategory.COMPLETED, None),
            (
                "http_error",
                "openai",
                urllib.error.HTTPError("https://example.invalid", 429, "rate limited", {}, io.BytesIO(b"response body")),
                OutcomeCategory.FAILED,
                ReasoningProviderError,
            ),
            ("nonzero", "codex", subprocess.CompletedProcess(["codex"], 7, "out", "err"), OutcomeCategory.FAILED, ReasoningProviderError),
            ("timeout", "codex", subprocess.TimeoutExpired(["codex"], 3), OutcomeCategory.TIMEOUT, subprocess.TimeoutExpired),
        )
        for name, provider, effect, outcome, error in cases:
            with self.subTest(name=name):
                recorder = _Recorder()
                executor = self._openai(recorder) if provider == "openai" else self._codex(recorder)
                with ExitStack() as stack:
                    if provider == "openai":
                        invocation = stack.enter_context(patch(
                            "sdd_orchestrator.providers.urllib.request.urlopen",
                            side_effect=effect if isinstance(effect, Exception) else None,
                            return_value=None if isinstance(effect, Exception) else effect,
                        ))
                    else:
                        stack.enter_context(
                            patch.object(executor, "resolved_executable", return_value="codex")
                        )
                        invocation = stack.enter_context(patch(
                            "sdd_orchestrator.providers.subprocess.run",
                            side_effect=effect if isinstance(effect, Exception) else None,
                            return_value=None if isinstance(effect, Exception) else effect,
                        ))
                    if error:
                        with self.assertRaises(error):
                            executor.execute(_request())
                    else:
                        executor.execute(_request())
                self.assertEqual(invocation.call_count, 1)
                event, = _provider_events(recorder)
                self.assertEqual(event.outcome_category, outcome)

    def test_recorder_failure_preserves_single_call_result_and_original_exceptions(self):
        recorder = _Recorder(fail=True)
        executor = self._codex(recorder)
        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=_codex_run_success
        ) as invocation:
            result = executor.execute(_request())
        self.assertIsInstance(result, StageExecutionResult)
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(invocation.call_count, 1)

        recorder = _Recorder(fail=True)
        executor = self._codex(recorder)
        original = subprocess.TimeoutExpired(["codex"], 13)
        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=original
        ) as invocation:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                executor.execute(_request())
        self.assertIs(caught.exception, original)
        self.assertEqual(str(caught.exception), str(original))
        self.assertEqual(invocation.call_count, 1)

    def test_provider_telemetry_failure_does_not_repeat_provider_execution(self):
        recorder = _Recorder(fail=True)
        executor = self._codex(recorder)
        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=_codex_run_success
        ) as invocation:
            result = executor.execute(_request())

        self.assertEqual(invocation.call_count, 1)
        self.assertIsInstance(result, StageExecutionResult)
        self.assertEqual(result.status, "COMPLETED")

        original = subprocess.TimeoutExpired(["codex"], 13)
        recorder = _Recorder(fail=True)
        executor = self._codex(recorder)
        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=original
        ) as invocation:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                executor.execute(_request())

        self.assertEqual(invocation.call_count, 1)
        self.assertIs(caught.exception, original)

    def test_none_recorder_leaves_provider_behavior_unchanged(self):
        executor = self._codex(None)
        with patch.object(executor, "resolved_executable", return_value="codex"), patch(
            "sdd_orchestrator.providers.subprocess.run", side_effect=_codex_run_success
        ) as invocation:
            result = executor.execute(_request())
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(invocation.call_count, 1)

    def test_stage_execution_result_schema_has_no_telemetry_or_usage_authority_fields(self):
        fields = set(StageExecutionResult.__dataclass_fields__)
        self.assertFalse(fields & {"telemetry", "measurement", "usage", "provider_call"})


if __name__ == "__main__":
    unittest.main()
