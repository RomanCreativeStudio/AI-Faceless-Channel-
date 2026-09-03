"""Tests 14, 15: a scene citing a claim with no corresponding claims/*.md
file fails safely (never invents one); claim references are preserved
(traceable from an asset back to the scene's claim references).
"""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item


class ClaimPreservationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 14: missing claim reference fails safely ---
    def test_missing_claim_file_blocks_rather_than_invents_one(self):
        build_visual_planned_item(self.root, beats=["1. A beat citing c1. — claims: `c1`"])
        # Visual Planner already created a skeleton assets/asset-02.md
        # during fixture setup; this run must leave it exactly as-is.
        skeleton_before = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8")
        (self.root / "claims" / "c1.md").unlink()

        result = run_asset_generation(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("c1", result.blocked_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "claims" / "c1.md").exists())
        skeleton_after = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8")
        self.assertEqual(skeleton_before, skeleton_after)
        self.assertNotIn("test-item-c1", skeleton_after)  # never invented a claim reference

    # --- Test 15: claim references are preserved ---
    def test_claim_references_traceable_from_asset_to_scene(self):
        build_visual_planned_item(
            self.root,
            beats=["1. A beat citing two claims. — claims: `c1`, `c4`"],
            extra_claims=[("c4", "ASSUMPTION")],
        )
        result = run_asset_generation(self.root, apply=True)
        plan = [p for p in result.plans if p.filename == "asset-02.md"][0]
        self.assertEqual(plan.scene.claim_ids, ["c1", "c4"])

        scene_text = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")
        self.assertIn("`c1`, `c4`", scene_text)

        asset_text = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8")
        self.assertIn("scenes/scene-02.md", asset_text)


if __name__ == "__main__":
    unittest.main()
