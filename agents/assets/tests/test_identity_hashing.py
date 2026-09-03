"""Tests 16-19: asset IDs are stable across identical re-runs; scene IDs
are preserved; the scene/visual content hash is recorded; a scene change
after asset generation produces a STALE result rather than silently
continuing to use an outdated asset.
"""
import re
import tempfile
import unittest
from pathlib import Path

from ..src.hashing import compute_asset_content_hash
from ..src.pipeline import run_asset_generation
from ..src.scene_reader import load_scene_visual_record
from .builders import build_visual_planned_item

_NARRATION_ROW_RE = re.compile(r"^\|\s*Narration text\s*\|.*\|\s*$", re.MULTILINE)


class IdentityHashingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_visual_planned_item(self.root)

    # --- Test 16: asset IDs are stable ---
    def test_asset_ids_are_stable_across_reruns(self):
        first = run_asset_generation(self.root, apply=True)
        ids_first = sorted(p.asset_id for p in first.plans)
        self.assertTrue(ids_first)

        second = run_asset_generation(self.root, apply=True)
        self.assertTrue(second.already_up_to_date_filenames)
        self.assertFalse(second.plans)  # nothing changed -> no new plans this run

        expected_ids = sorted(f"test-item-{fn[:-3]}" for fn in second.already_up_to_date_filenames)
        self.assertEqual(expected_ids, ids_first)

    # --- Test 17: scene IDs are preserved ---
    def test_scene_ids_preserved_on_each_plan(self):
        result = run_asset_generation(self.root, apply=True)
        for plan in result.plans:
            scene_record = load_scene_visual_record(self.root / "scenes" / plan.scene.filename)
            self.assertEqual(plan.scene.scene_id, scene_record.scene_id)
            self.assertTrue(plan.scene.scene_id)

    # --- Test 18: scene/visual hash is recorded ---
    def test_scene_visual_hash_recorded_and_correct(self):
        result = run_asset_generation(self.root, apply=True)
        plan = [p for p in result.plans if p.filename == "asset-02.md"][0]
        scene_record = load_scene_visual_record(self.root / "scenes" / "scene-02.md")
        self.assertEqual(plan.content_hash, compute_asset_content_hash(scene_record))

        asset_text = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8")
        self.assertIn(f"| Scene/visual content hash | `{plan.content_hash}` |", asset_text)

    # --- Test 19: scene change after generation -> STALE result ---
    def test_scene_change_after_generation_makes_asset_stale(self):
        first = run_asset_generation(self.root, apply=True)
        self.assertTrue(first.produced)

        scene_path = self.root / "scenes" / "scene-02.md"
        text = scene_path.read_text(encoding="utf-8")
        text = _NARRATION_ROW_RE.sub(
            "| Narration text | Edited narration text after asset generation. |", text
        )
        scene_path.write_text(text, encoding="utf-8")

        second = run_asset_generation(self.root, apply=True)
        self.assertIn("asset-02.md", second.stale_filenames)
        self.assertFalse(any(p.filename == "asset-02.md" for p in second.plans))


if __name__ == "__main__":
    unittest.main()
