"""Tests 20-23: dry-run makes no mutation at all; apply writes only the
Asset agent's allowed files/fields; every protected field is untouched;
existing asset history is never silently overwritten.
"""
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item


class MutationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_visual_planned_item(self.root)

    # --- Test 20: dry-run makes no mutation ---
    def test_dry_run_makes_no_mutation(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        before_assets = set((self.root / "assets").glob("*"))
        result = run_asset_generation(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        after_assets = set((self.root / "assets").glob("*"))

        self.assertEqual(before, after)
        self.assertEqual(before_assets, after_assets)
        self.assertFalse(result.produced)
        self.assertEqual(result.production_path, "")
        self.assertTrue(result.plans)  # still computed, just not written

    # --- Test 21: apply writes only asset-owned fields/files ---
    def test_apply_writes_only_asset_files_and_production_rollup(self):
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        scenes_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }

        result = run_asset_generation(self.root, apply=True)

        self.assertTrue(result.asset_paths)
        for path in result.asset_paths:
            self.assertTrue(Path(path).is_file())

        self.assertEqual((self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), content_item_before)
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)
        scenes_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }
        self.assertEqual(scenes_before, scenes_after)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("## Asset references (rollup)", production_text)

    # --- Test 22: protected fields cannot be modified ---
    def test_mutate_rejects_non_whitelisted_asset_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_asset_file(self.root, "not-an-asset.md", "content")

    def test_mutate_rejects_non_whitelisted_artifact_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_generated_artifact(self.root, "not-an-artifact.png", "content")

    def test_apply_never_touches_content_item_status(self):
        run_asset_generation(self.root, apply=True)
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)

    # --- Test 23: existing asset history is not overwritten ---
    def test_stale_asset_is_never_overwritten(self):
        run_asset_generation(self.root, apply=True)
        asset_before = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8")

        import re
        scene_path = self.root / "scenes" / "scene-02.md"
        text = scene_path.read_text(encoding="utf-8")
        text = re.sub(
            r"^\|\s*Narration text\s*\|.*\|\s*$",
            "| Narration text | Edited after asset generation. |",
            text, flags=re.MULTILINE,
        )
        scene_path.write_text(text, encoding="utf-8")

        run_asset_generation(self.root, apply=True)
        asset_after = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8")
        self.assertEqual(asset_before, asset_after)


if __name__ == "__main__":
    unittest.main()
