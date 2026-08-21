"""Best-effort telemetry recording."""

from typing import Any


class TelemetryRecorder:
    def __init__(self, sink: Any) -> None:
        self._sink = sink

    def record(self, event: Any) -> None:
        try:
            self._sink.record(event)
        except Exception:
            pass
        return None
