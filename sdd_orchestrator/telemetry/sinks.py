"""Telemetry sink implementations."""

from pathlib import Path
from typing import Any

from .measurement import canonical_json_bytes


class NullTelemetrySink:
    """A telemetry sink that deliberately does nothing."""

    def record(self, event: Any) -> None:
        return None


class JsonlTelemetrySink:
    """Append canonical measurement events to the v1 JSONL store."""

    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        if not self._directory.is_dir():
            raise NotADirectoryError(self._directory)
        self._path = self._directory / "events.jsonl"

    def record(self, event: Any) -> None:
        record = canonical_json_bytes(event.to_dict()) + b"\n"
        with self._path.open("ab") as stream:
            if stream.write(record) != len(record):
                raise OSError("partial telemetry record write")
            stream.flush()
