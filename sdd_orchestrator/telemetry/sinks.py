"""Telemetry sink implementations."""

from typing import Any


class NullTelemetrySink:
    """A telemetry sink that deliberately does nothing."""

    def record(self, event: Any) -> None:
        return None
