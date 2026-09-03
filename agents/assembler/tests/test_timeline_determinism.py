"""Tests 9-14: the timeline is deterministic and scene ordering is
stable across runs; scenes never overlap; total duration is the sum of
scene durations; claim references and generated-authenticity metadata
are preserved into the timeline.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_video_assembly
from .builders import build_assembly_ready_item


class TimelineDeterminismTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_assembly_ready_item(
            self.root,
            beats=[
                "1. A factual beat. — claims: `c1`",
                "2. A hypothetical beat. — claims: `c4`",
            ],
            extra_claims=[("c4", "ASSUMPTION")],
        )

    # --- Test 9: timeline is deterministic ---
    def test_timeline_is_deterministic_across_dry_runs(self):
        first = run_video_assembly(self.root, apply=False)
        second = run_video_assembly(self.root, apply=False)
        self.assertEqual(first.assembly_content_hash, second.assembly_content_hash)
        self.assertEqual(
            [(s.scene_id, s.start, s.end) for s in first.scenes],
            [(s.scene_id, s.start, s.end) for s in second.scenes],
        )

    # --- Test 10: scene ordering is deterministic ---
    def test_scene_ordering_is_deterministic(self):
        result = run_video_assembly(self.root, apply=False)
        orders = [s.order for s in result.scenes]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(orders, list(range(1, len(orders) + 1)))

    # --- Test 11: no scene overlap ---
    def test_no_scene_overlap(self):
        result = run_video_assembly(self.root, apply=False)
        for prev, curr in zip(result.scenes, result.scenes[1:]):
            self.assertEqual(prev.end, curr.start)
        self.assertEqual(result.scenes[0].start, 0)

    # --- Test 12: duration totals correctly ---
    def test_total_duration_equals_sum_of_scene_durations(self):
        result = run_video_assembly(self.root, apply=False)
        self.assertEqual(result.total_duration, sum(s.duration_seconds for s in result.scenes))
        self.assertEqual(result.total_duration, result.scenes[-1].end)

    # --- Test 13: claim references preserved ---
    def test_claim_references_preserved_in_timeline(self):
        result = run_video_assembly(self.root, apply=True)
        by_scene = {s.filename: s.claim_ids for s in result.scenes}
        self.assertEqual(by_scene["scene-02.md"], ["c1"])
        self.assertEqual(by_scene["scene-03.md"], ["c4"])

        timeline_text = Path(result.timeline_path).read_text(encoding="utf-8")
        self.assertIn("`c1`", timeline_text)
        self.assertIn("`c4`", timeline_text)

    # --- Test 14: generated authenticity metadata preserved ---
    def test_generated_reconstruction_authenticity_preserved_via_asset_reference(self):
        result = run_video_assembly(self.root, apply=True)
        # The timeline never re-derives authenticity — it references the
        # asset record, which is where the classification lives.
        scene03 = [s for s in result.scenes if s.filename == "scene-03.md"][0]
        self.assertEqual(scene03.visual_reference, "assets/asset-03.md")
        asset_text = (self.root / "assets" / "asset-03.md").read_text(encoding="utf-8")
        self.assertIn("`GENERATED_RECONSTRUCTION`", asset_text)


if __name__ == "__main__":
    unittest.main()
