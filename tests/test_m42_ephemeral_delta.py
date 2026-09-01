from dataclasses import FrozenInstanceError, replace
import unittest

from sdd_orchestrator.context_compiler import (
    ComponentDeltaKind, ExactContextComponent, build_ephemeral_baseline,
    compare_baseline_to_current, content_digest, reconstruct_exact_context,
    select_stage_candidates,
)
from sdd_orchestrator.executor import StageExecutionRequest


class EphemeralDeltaTests(unittest.TestCase):
    def request(self, **changes):
        values = dict(
            stage_id="04", stage_name="Manifest", stage_type="build",
            core_question=None, contract={}, artifacts={"docs/spec.md": "spec"},
            semantic_inputs={"empty": [], "null": None},
            runtime_inputs={"GIT_HISTORY": ""}, stage_instructions="",
        )
        values.update(changes)
        return StageExecutionRequest(**values)

    def exact(self, request):
        return select_stage_candidates(request, {})

    def kinds(self, delta):
        return [change.kind for change in delta.changes]

    def test_baseline_is_deterministic_immutable_ordered_and_ephemeral(self):
        scope = object()
        exact = self.exact(self.request())
        first = build_ephemeral_baseline(exact, scope=scope)
        second = build_ephemeral_baseline(exact, scope=scope)
        self.assertEqual(first, second)
        self.assertEqual(first.identity_sequence, tuple(item.identity for item in exact))
        self.assertEqual(first.task_coordinate, "task-absent")
        self.assertFalse(any("path" in name or "time" in name or "cache" in name
                             for name in first.__dataclass_fields__))
        with self.assertRaises(FrozenInstanceError):
            first.version = "other"
        self.assertFalse(compare_baseline_to_current(
            first, exact, scope=object()).exact_reconstruction_eligible)

    def test_coordinate_namespace_version_and_unavailable_current_invalidate(self):
        scope = object()
        exact = self.exact(self.request())
        baseline = build_ephemeral_baseline(exact, scope=scope)
        wrong_stage = self.exact(self.request(stage_id="09"))
        self.assertIn("stage_coordinate_mismatch", compare_baseline_to_current(
            baseline, wrong_stage, scope=scope).invalid_reasons)
        for field in ("namespace", "version"):
            invalid = replace(baseline, **{field: "invalid"})
            self.assertFalse(compare_baseline_to_current(
                invalid, exact, scope=scope).exact_reconstruction_eligible)
        unavailable = compare_baseline_to_current(baseline, None, scope=scope)
        self.assertIn("current_fresh_exact_unavailable", unavailable.invalid_reasons)

    def test_exact_delta_categories_and_direct_reuse_distinction(self):
        scope = object()
        baseline_exact = self.exact(self.request())
        baseline = build_ephemeral_baseline(baseline_exact, scope=scope)
        unchanged = compare_baseline_to_current(baseline, baseline_exact, scope=scope)
        self.assertTrue(unchanged.direct_reuse_eligible)
        self.assertEqual(set(self.kinds(unchanged)), {ComponentDeltaKind.UNCHANGED})

        changed_exact = self.exact(self.request(artifacts={"docs/spec.md": "changed"}))
        changed = compare_baseline_to_current(baseline, changed_exact, scope=scope)
        self.assertIn(ComponentDeltaKind.CHANGED, self.kinds(changed))
        self.assertFalse(changed.direct_reuse_eligible)
        self.assertTrue(changed.exact_reconstruction_eligible)

        added_exact = self.exact(self.request(runtime_inputs={
            "GIT_HISTORY": "", "NEW": {}}))
        self.assertIn(ComponentDeltaKind.ADDED, self.kinds(
            compare_baseline_to_current(baseline, added_exact, scope=scope)))

        removed_exact = self.exact(self.request(runtime_inputs={}))
        removed = compare_baseline_to_current(baseline, removed_exact, scope=scope)
        self.assertIn(ComponentDeltaKind.REMOVED, self.kinds(removed))
        self.assertTrue(removed.exact_reconstruction_eligible)

        reordered_exact = tuple(reversed(baseline_exact))
        reordered = compare_baseline_to_current(baseline, reordered_exact, scope=scope)
        self.assertIn(ComponentDeltaKind.REORDERED, self.kinds(reordered))
        self.assertTrue(reordered.exact_reconstruction_eligible)

    def test_digest_collision_duplicate_and_authority_removal_fail_closed(self):
        scope = object()
        exact = self.exact(self.request())
        baseline = build_ephemeral_baseline(exact, scope=scope)
        original = baseline.components[0]
        collision = replace(original, canonical_bytes=original.canonical_bytes + b"x")
        delta = compare_baseline_to_current(
            baseline, (collision,) + baseline.components[1:], scope=scope)
        self.assertFalse(delta.exact_reconstruction_eligible)
        self.assertIn("digest_canonical_ambiguity", delta.invalid_reasons)
        collision_result = reconstruct_exact_context(baseline, delta, scope=scope)
        self.assertFalse(collision_result.used_fresh_exact)
        self.assertEqual(collision_result.components, ())
        duplicate = compare_baseline_to_current(
            baseline, baseline.components + (baseline.components[0],), scope=scope)
        self.assertIn("duplicate_identity", duplicate.invalid_reasons)
        removed_authority = compare_baseline_to_current(
            baseline, baseline.components[1:], scope=scope)
        self.assertIn("authority_protected_component_removed",
                      removed_authority.invalid_reasons)

    def assert_reconstructs(self, baseline, current, scope):
        delta = compare_baseline_to_current(baseline, current, scope=scope)
        result = reconstruct_exact_context(baseline, delta, scope=scope)
        self.assertTrue(result.reconstructed)
        self.assertTrue(result.exact_match)
        self.assertEqual(tuple(x.identity for x in result.components),
                         tuple(x.identity for x in delta.current_components))
        self.assertEqual(tuple(x.canonical_bytes for x in result.components),
                         tuple(x.canonical_bytes for x in delta.current_components))
        self.assertEqual(result.authority_coverage_percent, 100)
        self.assertEqual(result.authority_byte_mismatch, 0)

    def test_exact_reconstruction_unchanged_changed_added_removed_reordered_mixed(self):
        scope = object()
        base_exact = self.exact(self.request())
        baseline = build_ephemeral_baseline(base_exact, scope=scope)
        cases = [
            base_exact,
            self.exact(self.request(artifacts={"docs/spec.md": "changed"})),
            self.exact(self.request(runtime_inputs={"GIT_HISTORY": "", "NEW": {}})),
            self.exact(self.request(runtime_inputs={})),
            tuple(reversed(base_exact)),
            self.exact(self.request(
                artifacts={"docs/spec.md": "changed", "new.md": []},
                runtime_inputs={},
            )),
        ]
        for current in cases:
            with self.subTest(count=len(current)):
                self.assert_reconstructs(baseline, current, scope)

    def test_invalid_reconstruction_returns_whole_fresh_exact_not_partial(self):
        scope = object()
        base_exact = self.exact(self.request())
        baseline = build_ephemeral_baseline(base_exact, scope=scope)
        current = self.exact(self.request(artifacts={"docs/spec.md": "changed"}))
        delta = compare_baseline_to_current(baseline, current, scope=scope)
        changed = next(x for x in delta.changes if x.kind is ComponentDeltaKind.CHANGED)
        broken_changes = tuple(x for x in delta.changes if x is not changed)
        result = reconstruct_exact_context(
            baseline, replace(delta, changes=broken_changes), scope=scope)
        self.assertFalse(result.reconstructed)
        self.assertTrue(result.used_fresh_exact)
        self.assertTrue(result.fresh_exact_required)
        self.assertEqual(result.components, delta.current_components)

    def test_empty_absent_and_null_canonical_states_remain_distinct(self):
        exact = self.exact(self.request())
        bodies = {item.canonical_bytes for item in exact}
        self.assertTrue({b"", b"{}", b"[]", b"null", b'{"state":"absent"}'}.issubset(bodies))
        self.assertEqual(len({content_digest(body) for body in
                              (b"", b"{}", b"[]", b"null", b'{"state":"absent"}')}), 5)


if __name__ == "__main__":
    unittest.main()
