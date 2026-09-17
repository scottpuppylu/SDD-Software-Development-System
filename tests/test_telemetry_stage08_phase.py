from __future__ import annotations

from copy import deepcopy

import pytest

from sdd_orchestrator.telemetry.measurement import measure_stage08_phase_events
from sdd_orchestrator.telemetry.models import EventType, STAGE08_PHASE_SCHEMA_VERSION
from sdd_orchestrator.telemetry.recorder import TelemetryRecorder


def _event(sequence, event_type, phase, recorded_at, digest_char, **extra):
    return {
        "sequence": sequence,
        "event_type": event_type,
        "phase": phase,
        "recorded_at": recorded_at,
        "event_digest": digest_char * 64,
        "provider_invocation_id": extra.pop("provider_invocation_id", None),
        "verification": extra.pop("verification", []),
        "details": extra.pop("details", {}),
        **extra,
    }


def _journal():
    return {
        "schema_version": "1.0",
        "binding": {"attempt_id": "attempt-028", "task_id": "T028"},
        "events": [
            _event(1, "PHASE", "PRECHECK_COMPLETE", "2026-09-17T00:00:00Z", "1"),
            _event(2, "PHASE", "CONTEXT_READY", "2026-09-17T00:00:01Z", "2"),
            _event(
                3, "PHASE", "CODEX_PATCH_COMPLETE", "2026-09-17T00:00:04Z", "3",
                provider_invocation_id="attempt-028:codex:initial",
            ),
            _event(4, "PHASE", "FAST_VERIFY_COMPLETE", "2026-09-17T00:00:05Z", "4"),
            _event(5, "PHASE", "TARGET_VERIFY_COMPLETE", "2026-09-17T00:00:07Z", "5"),
            _event(
                6, "PHASE", "FINAL_VERIFY_COMPLETE", "2026-09-17T00:00:08Z", "6",
                verification=[{"level": "TARGET"}],
            ),
            _event(7, "PHASE", "STAGE8_COMPLETE", "2026-09-17T00:00:09Z", "7"),
        ],
    }


def test_phase_events_are_versioned_deterministic_and_metadata_only():
    first = measure_stage08_phase_events(task_id="T028", journal=_journal())
    second = measure_stage08_phase_events(task_id="T028", journal=_journal())
    assert [item.event_id for item in first] == [item.event_id for item in second]
    assert all(item.event_type is EventType.STAGE08_PHASE for item in first)
    assert all(item.usage is None and item.metrics == [] for item in first)
    assert first[-1].metadata["phase_schema_version"] == STAGE08_PHASE_SCHEMA_VERSION
    assert first[-1].metadata["phase"] == "STAGE8_COMPLETE"


def test_all_required_metrics_are_cumulative_and_derivable():
    final = measure_stage08_phase_events(task_id="T028", journal=_journal())[-1].metadata
    assert final["codex_invocation_count"] == 1
    assert final["codex_active_duration_ms"] == 3000
    assert final["fast_verify_duration_ms"] == 1000
    assert final["target_verify_duration_ms"] == 2000
    assert final["full_verify_duration_ms"] == 0
    assert final["local_verification_duration_ms"] == 3000
    assert final["remediation_count"] == 0
    assert final["resume_count"] == 0
    assert final["total_stage8_duration_ms"] == 9000
    assert final["codex_active_time_ratio"] == pytest.approx(1 / 3)


def test_resume_remediation_and_reused_verification_do_not_recount_work():
    journal = _journal()
    journal["events"] = journal["events"][:3] + [
        _event(4, "SAFE_PAUSE", None, "2026-09-17T00:00:05Z", "4"),
        _event(5, "RESUME", None, "2026-09-17T00:00:15Z", "5"),
        _event(6, "PHASE", "REMEDIATION_REQUIRED", "2026-09-17T00:00:16Z", "6"),
        _event(
            7, "PHASE", "CODEX_PATCH_COMPLETE", "2026-09-17T00:00:18Z", "7",
            provider_invocation_id="attempt-028:codex:remediation:1",
        ),
        _event(
            8, "PHASE", "FAST_VERIFY_COMPLETE", "2026-09-17T00:00:19Z", "8",
            details={"reused": True},
        ),
        _event(
            9, "PHASE", "TARGET_VERIFY_COMPLETE", "2026-09-17T00:00:20Z", "9",
            details={"reused": True},
        ),
        _event(
            10, "PHASE", "FINAL_VERIFY_COMPLETE", "2026-09-17T00:00:21Z", "a",
            details={"reused": True}, verification=[{"level": "TARGET"}],
        ),
        _event(11, "PHASE", "STAGE8_COMPLETE", "2026-09-17T00:00:22Z", "b"),
    ]
    final = measure_stage08_phase_events(task_id="T028", journal=journal)[-1].metadata
    assert final["codex_invocation_count"] == 2
    assert final["codex_active_duration_ms"] == 5000
    assert final["remediation_count"] == 1
    assert final["resume_count"] == 1
    assert final["verification_reused"] is True
    assert final["local_verification_duration_ms"] == 0
    assert final["total_stage8_duration_ms"] == 22000


def test_recorder_deduplicates_deterministic_phase_event_ids():
    recorded = []
    recorder = TelemetryRecorder(type("Sink", (), {"record": lambda _self, event: recorded.append(event)})())
    event = measure_stage08_phase_events(task_id="T028", journal=_journal())[0]
    recorder.record(event)
    recorder.record(event)
    assert recorded == [event]


def test_invalid_or_ambiguous_history_fails_closed():
    journal = _journal()
    journal["events"][1]["sequence"] = 9
    with pytest.raises(ValueError, match="contiguous"):
        measure_stage08_phase_events(task_id="T028", journal=journal)
    mismatch = deepcopy(_journal())
    mismatch["binding"]["task_id"] = "T027"
    with pytest.raises(ValueError, match="identity mismatch"):
        measure_stage08_phase_events(task_id="T028", journal=mismatch)
