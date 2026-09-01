from dataclasses import replace
from unittest.mock import patch
import unittest

from sdd_orchestrator.context_compiler import (
    CANONICALIZATION_ID,
    IDENTITY_NAMESPACE,
    IDENTITY_VERSION,
    TASK_COORDINATE,
    ComponentIdentity,
    ComponentTreatment,
    build_baseline_package,
    build_component_identity,
    content_digest,
    content_kind_and_bytes,
    parse_component_identity,
    select_stage_candidates,
    validate_component_selections,
)
from sdd_orchestrator.executor import StageExecutionRequest


class M42IdentityTests(unittest.TestCase):
    def test_frozen_contract_constants(self):
        self.assertEqual(IDENTITY_NAMESPACE, "sdd.context.component")
        self.assertEqual(IDENTITY_VERSION, "m4.2-v1")
        self.assertEqual(TASK_COORDINATE, "task-absent")
        self.assertEqual(CANONICALIZATION_ID, "sdd.canonical.utf8-sorted-compact-v1")

    def test_stage_present_absent_and_present_empty_are_distinct(self):
        coordinate = "request/stage-contract"
        present = build_component_identity(coordinate, "08")
        absent = build_component_identity(coordinate, None)
        empty = build_component_identity(coordinate, "")
        self.assertEqual(
            present.text,
            "sdd.context.component/m4.2-v1/stage-id/3038/task-absent/request/stage-contract",
        )
        self.assertEqual(
            absent.text,
            "sdd.context.component/m4.2-v1/stage-absent/task-absent/request/stage-contract",
        )
        self.assertEqual(
            empty.text,
            "sdd.context.component/m4.2-v1/stage-id//task-absent/request/stage-contract",
        )
        self.assertEqual(len({present, absent, empty}), 3)
        for identity in (present, absent, empty):
            self.assertEqual(parse_component_identity(identity.text), identity)
            self.assertEqual(identity.task_coordinate, "task-absent")

    def test_all_structural_coordinates_and_key_encoding(self):
        coordinates = (
            "request/stage-contract",
            "request/stage-instructions",
            "request/artifacts/41",
            "request/semantic-inputs/c3a9",
            "request/runtime-inputs/",
            "request/metadata/stage-id",
            "request/metadata/stage-name",
            "request/metadata/stage-type",
            "request/metadata/core-question",
        )
        first = [build_component_identity(value, "01") for value in coordinates]
        second = [build_component_identity(value, "01") for value in coordinates]
        self.assertEqual(first, second)
        self.assertEqual(len(set(first)), len(coordinates))

    def test_non_string_key_and_malformed_identity_fail_closed(self):
        request = self.request()
        request.semantic_inputs = {1: "invalid"}
        with self.assertRaises(TypeError):
            select_stage_candidates(request, {"08": {"required_inputs": {}}})
        malformed = (
            "other/m4.2-v1/stage-absent/task-absent/request/stage-contract",
            "sdd.context.component/v2/stage-absent/task-absent/request/stage-contract",
            "sdd.context.component/m4.2-v1/stage-id/0/task-absent/request/stage-contract",
            "sdd.context.component/m4.2-v1/stage-absent/task-x/request/stage-contract",
            "sdd.context.component/m4.2-v1/stage-absent/task-absent/request/artifacts/ZZ",
        )
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_component_identity(value)
        with self.assertRaises(ValueError):
            ComponentIdentity(
                IDENTITY_NAMESPACE, "bad", "stage-absent", TASK_COORDINATE,
                "request/stage-contract",
            )

    def test_digest_and_distinct_content_states(self):
        values = (
            content_kind_and_bytes(None, absent=True)[1],
            content_kind_and_bytes("")[1],
            content_kind_and_bytes({})[1],
            content_kind_and_bytes([])[1],
            content_kind_and_bytes(None)[1],
        )
        self.assertEqual(len(set(values)), 5)
        self.assertEqual(len({content_digest(value) for value in values}), 5)
        self.assertNotEqual(content_digest(b"before"), content_digest(b"after"))

    def test_duplicate_identity_and_digest_collision_simulation_fail_closed(self):
        selections = select_stage_candidates(
            self.request(), {"08": {"required_inputs": {}}}
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_component_selections((selections[0], selections[0]))
        collision = (
            replace(selections[0], content_digest="0" * 64, canonical_bytes=b"a"),
            replace(selections[1], content_digest="0" * 64, canonical_bytes=b"b"),
        )
        with patch(
            "sdd_orchestrator.context_compiler.content_digest", return_value="0" * 64
        ), self.assertRaisesRegex(ValueError, "collision"):
            validate_component_selections(collision)

    @staticmethod
    def request():
        return StageExecutionRequest(
            stage_id="08", stage_name="IMPLEMENTATION_RUNNER", stage_type="EXECUTION",
            core_question=None, contract={}, artifacts={}, semantic_inputs={},
            runtime_inputs={}, stage_instructions=None,
        )


class M42SelectionTests(unittest.TestCase):
    def request(self, *, stage_id="08"):
        return StageExecutionRequest(
            stage_id=stage_id, stage_name="stage", stage_type="type",
            core_question=None, contract={"unchanged": True},
            artifacts={"docs/PRD.md": "authority", "unmapped.md": "mixed"},
            semantic_inputs={"REQUIRED": "known", "UNMAPPED": None},
            runtime_inputs={"GIT_STATUS": "", "GIT_HISTORY": "history", "OTHER": []},
            stage_instructions=None,
        )

    def stages(self):
        return {"08": {"required_inputs": {
            "files": ["docs/PRD.md"],
            "semantic": ["REQUIRED"],
            "runtime": ["GIT_STATUS"],
        }}}

    def test_explicit_stage_candidates_only_and_everything_preserved(self):
        request = self.request()
        first = select_stage_candidates(request, self.stages())
        second = select_stage_candidates(request, self.stages())
        self.assertEqual(first, second)
        by_coordinate = {
            item.identity.component_coordinate: item for item in first
        }
        expected_stage_required = {
            "request/artifacts/646f63732f5052442e6d64",
            "request/semantic-inputs/5245515549524544",
            "request/runtime-inputs/4749545f535441545553",
        }
        self.assertEqual(
            {key for key, item in by_coordinate.items() if item.stage_required},
            expected_stage_required,
        )
        for coordinate in expected_stage_required:
            self.assertIs(
                by_coordinate[coordinate].candidate_treatment,
                ComponentTreatment.STAGE_REQUIRED_CANDIDATE,
            )
            self.assertIs(
                by_coordinate[coordinate].treatment,
                ComponentTreatment.FAIL_CLOSED_EXACT,
            )
        self.assertIs(
            by_coordinate["request/runtime-inputs/4749545f484953544f5259"].treatment,
            ComponentTreatment.DELTA_ONLY_CANDIDATE,
        )
        self.assertTrue(all(item.preserve_exact for item in first))
        self.assertFalse(any(item.task_required for item in first))
        self.assertTrue(all(
            item.treatment is ComponentTreatment.ALWAYS_REQUIRED
            for coordinate, item in by_coordinate.items()
            if coordinate in {
                "request/stage-contract", "request/stage-instructions",
                "request/metadata/stage-id", "request/metadata/stage-name",
                "request/metadata/stage-type", "request/metadata/core-question",
            }
        ))

    def test_unknown_mixed_authority_and_stage_mismatch_fail_closed_exact(self):
        selections = select_stage_candidates(self.request(stage_id="09"), self.stages())
        by_coordinate = {item.identity.component_coordinate: item for item in selections}
        for coordinate in (
            "request/artifacts/756e6d61707065642e6d64",
            "request/semantic-inputs/554e4d4150504544",
            "request/runtime-inputs/4f54484552",
        ):
            item = by_coordinate[coordinate]
            self.assertIs(item.treatment, ComponentTreatment.FAIL_CLOSED_EXACT)
            self.assertTrue(item.authority_protected)
            self.assertTrue(item.preserve_exact)
            self.assertFalse(item.stage_required)
        self.assertFalse(any(item.stage_required for item in selections))

    def test_no_authority_omission_and_baseline_compatibility(self):
        request = self.request()
        baseline = build_baseline_package(request)
        selections = select_stage_candidates(request, self.stages())
        self.assertEqual(
            [item.identity.component_coordinate for item in selections],
            [entry.manifest_entry.component_id for entry in baseline.entries],
        )
        self.assertEqual(
            [item.canonical_bytes for item in selections],
            [
                content_kind_and_bytes(
                    entry.source_body,
                    absent=entry.manifest_entry.content_kind.value == "ABSENT",
                )[1]
                for entry in baseline.entries
            ],
        )
        self.assertTrue(all(
            item.preserve_exact for item in selections if item.authority_protected
        ))

    def test_invalid_or_unmapped_stage_declarations_fail_closed(self):
        request = self.request()
        unmapped = select_stage_candidates(request, {})
        self.assertFalse(any(item.stage_required for item in unmapped))
        for invalid in (
            {"08": []},
            {"08": {"required_inputs": []}},
            {"08": {"required_inputs": {"semantic": "REQUIRED"}}},
            {"08": {"required_inputs": {"semantic": [1]}}},
        ):
            with self.subTest(invalid=invalid), self.assertRaises((TypeError, ValueError)):
                select_stage_candidates(request, invalid)


if __name__ == "__main__":
    unittest.main()
