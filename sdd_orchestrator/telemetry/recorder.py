"""Best-effort telemetry recording."""

import os
from pathlib import Path
from typing import Any

from .sinks import JsonlTelemetrySink, NullTelemetrySink


_TRUE_VALUES = {"1", "true", "yes", "on"}
_ASCII_WHITESPACE = " \t\n\r\v\f"


def _default_directory(environ: Any) -> Path:
    if os.name == "nt":
        local_app_data = environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise ValueError("LOCALAPPDATA is unavailable")
        base = Path(local_app_data)
    else:
        state_home = environ.get("XDG_STATE_HOME")
        if state_home:
            base = Path(state_home)
        else:
            home = environ.get("HOME")
            base = Path(home) if home else Path.home()
            base = base / ".local" / "state"
    return base / "sdd-orchestrator" / "telemetry"


class TelemetryRecorder:
    def __init__(self, sink: Any) -> None:
        self._sink = sink
        self._seen_event_ids: set[str] = set()

    @classmethod
    def from_environment(
        cls, repo_root: str | Path, *, environ: Any = None
    ) -> "TelemetryRecorder":
        environment = os.environ if environ is None else environ
        enabled = environment.get("SDD_TELEMETRY_ENABLED")
        if (
            not isinstance(enabled, str)
            or enabled.strip(_ASCII_WHITESPACE).lower() not in _TRUE_VALUES
        ):
            return cls(NullTelemetrySink())

        try:
            override = environment.get("SDD_TELEMETRY_DIR")
            destination = (
                Path(override)
                if override is not None
                else _default_directory(environment)
            )
            destination = destination.resolve(strict=False)
            repository = Path(repo_root).resolve(strict=False)
            if destination == repository or repository in destination.parents:
                return cls(NullTelemetrySink())
            return cls(JsonlTelemetrySink(destination))
        except (OSError, RuntimeError, TypeError, ValueError):
            return cls(NullTelemetrySink())

    def record(self, event: Any) -> None:
        event_id = getattr(event, "event_id", None)
        if isinstance(event_id, str) and event_id in self._seen_event_ids:
            return None
        try:
            self._sink.record(event)
        except Exception:
            pass
        else:
            if isinstance(event_id, str):
                self._seen_event_ids.add(event_id)
        return None
