import hashlib
import json
import unittest

from sdd_orchestrator.telemetry.measurement import (
    canonical_json_bytes,
    canonical_json_sha256,
    measure_text,
)
from sdd_orchestrator.telemetry.models import CANONICALIZATION_ID


class TelemetryMeasurementTests(unittest.TestCase):
    def test_text_chars_count_python_unicode_code_points(self):
        self.assertEqual(measure_text("繁😀e\u0301").chars, 4)

    def test_text_utf8_bytes_use_exact_utf8_encoding(self):
        text = "繁😀e\u0301\r\n"
        self.assertEqual(measure_text(text).utf8_bytes, len(text.encode("utf-8")))

    def test_text_sha256_hashes_exact_utf8_bytes(self):
        text = "繁😀e\u0301\r\n"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        measured = measure_text(text)
        self.assertEqual(measured.sha256, expected)
        self.assertEqual(measured.canonicalization_id, CANONICALIZATION_ID)

    def test_canonical_json_is_utf8_sorted_compact_and_has_no_trailing_newline(self):
        value = {"繁": "字", "a": [True, None, 1], "emoji": "😀"}
        encoded = canonical_json_bytes(value)
        self.assertEqual(encoded, '{"a":[true,null,1],"emoji":"😀","繁":"字"}'.encode("utf-8"))
        self.assertFalse(encoded.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(encoded.endswith(b"\n"))

    def test_canonical_json_does_not_normalize_unicode(self):
        composed = canonical_json_bytes({"text": "é"})
        decomposed = canonical_json_bytes({"text": "e\u0301"})
        self.assertNotEqual(composed, decomposed)
        self.assertIn("é".encode("utf-8"), composed)
        self.assertIn("e\u0301".encode("utf-8"), decomposed)

    def test_canonical_json_sha256_hashes_exact_canonical_utf8_bytes(self):
        value = {"z": "繁😀", "a": {"n": 1, "ok": False}}
        expected = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
        self.assertEqual(canonical_json_sha256(value), expected)

    def test_deterministic_text_vectors(self):
        vectors = [
            ("ASCII", 5, 5),
            ("繁體中文", 4, 12),
            ("😀", 1, 4),
            ("e\u0301", 2, 3),
            ("line1\r\nline2", 12, 12),
            ("line1\nline2", 11, 11),
        ]
        for text, chars, utf8_bytes in vectors:
            with self.subTest(text=repr(text)):
                first = measure_text(text)
                second = measure_text(text)
                self.assertEqual(first.chars, chars)
                self.assertEqual(first.utf8_bytes, utf8_bytes)
                self.assertEqual(first.sha256, hashlib.sha256(text.encode("utf-8")).hexdigest())
                self.assertEqual(first, second)
        self.assertNotEqual(measure_text("line1\r\nline2").sha256, measure_text("line1\nline2").sha256)

    def test_canonical_json_matches_frozen_json_settings(self):
        value = {"繁": "e\u0301", "a": [True, None, 1], "lines": "x\r\ny"}
        expected = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(canonical_json_bytes(value), expected)


if __name__ == "__main__":
    unittest.main()
