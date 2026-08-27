import copy
from dataclasses import FrozenInstanceError, fields
import hashlib
import math
import unittest

from sdd_orchestrator.context_compiler import (
    AuthorityTreatment, CANONICALIZATION_ID, CompilationMode, CompiledContextEntry,
    CompiledContextPackage, ContentKind, ContentMetadata, ContextCompiler,
    ContextManifest, ContextManifestEntry, InclusionDisposition,
    ManifestClassification, build_baseline_package, canonical_json_bytes,
    canonical_text_bytes, classify_artifact, content_kind_and_bytes,
    content_metadata, encode_component_key,
)
from sdd_orchestrator.executor import StageExecutionRequest


class ContextManifestTests(unittest.TestCase):
    def request(self):
        return StageExecutionRequest(
            stage_id="04", stage_name="Manifest", stage_type="build",
            core_question=None, contract={"z": [3, {"b": 2, "a": 1}]},
            artifacts={"notes.md": "mixed", "src/main.py": "code"},
            semantic_inputs={"é": {"nested": [1, 2]}, "A": []},
            runtime_inputs={"git_history": "no", "GIT_HISTORY": {"commits": []}},
            stage_instructions="keep\r\nlines\n",
        )

    def test_closed_enums(self):
        self.assertEqual([x.value for x in CompilationMode], ["BASELINE", "OPTIMIZED"])
        self.assertEqual([x.value for x in ManifestClassification], [
            "KNOWN_AUTHORITY", "KNOWN_GOVERNANCE",
            "APPROVED_REDUCIBLE_OPERATIONAL_HISTORY", "UNKNOWN", "MIXED_AUTHORITY"])
        self.assertEqual([x.value for x in AuthorityTreatment], [
            "EXACT_REQUIRED", "APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE"])
        self.assertEqual([x.value for x in InclusionDisposition], ["EXACT", "REDUCED", "OMITTED"])
        self.assertEqual([x.value for x in ContentKind], ["TEXT", "JSON", "ABSENT", "EMPTY_MAPPING", "EMPTY_LIST"])

    def test_models_are_frozen_and_have_only_contract_fields(self):
        model_fields = {
            ContentMetadata: {"chars", "utf8_bytes", "sha256", "canonicalization_id"},
            ContextManifestEntry: {"component_id", "source_role", "classification", "authority_treatment", "disposition", "content_kind", "source_metadata", "result_metadata", "reduction_policy_id"},
            ContextManifest: {"mode", "canonicalization_id", "entries"},
            CompiledContextEntry: {"manifest_entry", "source_body", "result_body"},
            CompiledContextPackage: {"mode", "request", "manifest", "entries"},
        }
        for model, expected in model_fields.items():
            self.assertEqual({field.name for field in fields(model)}, expected)
        package = build_baseline_package(self.request())
        with self.assertRaises(FrozenInstanceError):
            package.mode = CompilationMode.OPTIMIZED

    def test_canonical_text_preserves_unicode_newlines_and_empty(self):
        self.assertEqual(canonical_text_bytes("é\r\ne\u0301\n "), "é\r\ne\u0301\n ".encode())
        self.assertEqual(canonical_text_bytes(""), b"")

    def test_canonical_json_sorting_nested_unicode_and_numbers(self):
        value = {"é": 3, "z": {"β": 2, "a": 1}, "A": [True, None, -7]}
        self.assertEqual(canonical_json_bytes(value), '{"A":[true,null,-7],"z":{"a":1,"β":2},"é":3}'.encode())
        self.assertEqual(canonical_json_bytes(value), canonical_json_bytes(copy.deepcopy(value)))

    def test_canonical_json_rejects_invalid_keys_and_floats(self):
        with self.assertRaises(TypeError):
            canonical_json_bytes({1: "x"})
        for value in (math.nan, math.inf, -math.inf, 1.5):
            with self.assertRaises(TypeError):
                canonical_json_bytes(value)

    def test_content_metadata(self):
        raw = "é\n".encode()
        metadata = content_metadata("é\n")
        self.assertEqual(metadata.chars, 2)
        self.assertEqual(metadata.utf8_bytes, 3)
        self.assertEqual(metadata.sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(metadata.canonicalization_id, CANONICALIZATION_ID)
        self.assertRegex(metadata.sha256, r"^[0-9a-f]{64}$")

    def test_absent_and_empty_kinds_are_distinct(self):
        absent = content_kind_and_bytes(None, absent=True)
        self.assertEqual(absent, (ContentKind.ABSENT, b'{"state":"absent"}'))
        self.assertEqual(content_kind_and_bytes(""), (ContentKind.TEXT, b""))
        self.assertEqual(content_kind_and_bytes({}), (ContentKind.EMPTY_MAPPING, b"{}"))
        self.assertEqual(content_kind_and_bytes([]), (ContentKind.EMPTY_LIST, b"[]"))
        self.assertEqual(content_kind_and_bytes(None), (ContentKind.JSON, b"null"))

    def test_component_key_encoding_and_utf8_order(self):
        self.assertEqual(encode_component_key("A"), "41")
        self.assertEqual(encode_component_key("é"), "c3a9")
        request = self.request()
        request.artifacts = {"é": "3", "a": "1", "Z": "2"}
        ids = [e.component_id for e in build_baseline_package(request).manifest.entries]
        artifact_ids = [x for x in ids if x.startswith("request/artifacts/")]
        self.assertEqual(artifact_ids, [
            "request/artifacts/5a", "request/artifacts/61", "request/artifacts/c3a9"])

    def test_closed_artifact_mapping_and_boundaries(self):
        for key in ("docs/proposal.md", "docs/PRD.md", "docs/spec.md", "docs/Design.md", "tasks.md", "src/a.py", "src/lib/a.py", "tests/a.py", "tests/unit/test_a.py"):
            self.assertEqual(classify_artifact(key)[1], ManifestClassification.KNOWN_AUTHORITY)
        self.assertEqual(classify_artifact("AGENTS.md")[1], ManifestClassification.KNOWN_GOVERNANCE)
        for key in ("x/AGENTS.md", "agents.md", "src", "src/", "srcish/a", "src\\a.py", "src/a\\b.py", "src/lib\\file.py", "src/../a", "tests", "tests\\a.py", "tests/a\\b.py", "tests/unit\\test_a.py", "tests2/a", "/src/a"):
            self.assertEqual(classify_artifact(key)[1], ManifestClassification.MIXED_AUTHORITY)

    def test_only_exact_top_level_git_history_is_eligible(self):
        package = build_baseline_package(self.request())
        runtime = [e for e in package.manifest.entries if e.source_role == "RUNTIME_INPUT"]
        eligible = [e for e in runtime if e.classification is ManifestClassification.APPROVED_REDUCIBLE_OPERATIONAL_HISTORY]
        self.assertEqual([e.component_id for e in eligible], ["request/runtime-inputs/4749545f484953544f5259"])
        self.assertIs(eligible[0].authority_treatment, AuthorityTreatment.APPROVED_OPERATIONAL_REDUCTION_ELIGIBLE)
        self.assertIs([e for e in runtime if e.component_id.endswith("6769745f686973746f7279")][0].classification, ManifestClassification.UNKNOWN)
        request = self.request()
        request.runtime_inputs = {"OTHER": {"GIT_HISTORY": []}, "GIT_HISTORY_V2": []}
        self.assertFalse(any(e.classification is ManifestClassification.APPROVED_REDUCIBLE_OPERATIONAL_HISTORY for e in build_baseline_package(request).manifest.entries))

    def test_full_order_and_baseline_invariants(self):
        request = self.request()
        package = ContextCompiler().compile_baseline(request)
        ids = [e.component_id for e in package.manifest.entries]
        self.assertEqual(ids[:2], ["request/stage-contract", "request/stage-instructions"])
        self.assertEqual(ids[-4:], ["request/metadata/stage-id", "request/metadata/stage-name", "request/metadata/stage-type", "request/metadata/core-question"])
        self.assertTrue(all(e.disposition is InclusionDisposition.EXACT for e in package.manifest.entries))
        self.assertTrue(all(e.reduction_policy_id is None for e in package.manifest.entries))
        self.assertFalse(any(e.disposition is InclusionDisposition.OMITTED for e in package.manifest.entries))
        for compiled in package.entries:
            self.assertEqual(compiled.source_body, compiled.result_body)
            self.assertEqual(compiled.manifest_entry.source_metadata, compiled.manifest_entry.result_metadata)
        self.assertIs(package.request, request)

    def test_build_is_deterministic_and_does_not_mutate_request(self):
        request = self.request()
        snapshot = copy.deepcopy(request)
        first = build_baseline_package(request)
        second = build_baseline_package(request)
        self.assertEqual(first, second)
        self.assertEqual(request, snapshot)
        self.assertEqual(request.contract, snapshot.contract)
        self.assertEqual(request.artifacts, snapshot.artifacts)
        self.assertEqual(request.semantic_inputs, snapshot.semantic_inputs)
        self.assertEqual(request.runtime_inputs, snapshot.runtime_inputs)
        self.assertIs(first.request, request)


if __name__ == "__main__":
    unittest.main()
