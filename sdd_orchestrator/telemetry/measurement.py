"""Exact text and JSON measurement helpers."""

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .models import CANONICALIZATION_ID


@dataclass(frozen=True)
class TextMeasurement:
    chars: int
    utf8_bytes: int
    sha256: str
    canonicalization_id: str = CANONICALIZATION_ID


def measure_text(text: str) -> TextMeasurement:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    encoded = text.encode("utf-8")
    return TextMeasurement(
        chars=len(text),
        utf8_bytes=len(encoded),
        sha256=hashlib.sha256(encoded).hexdigest(),
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
