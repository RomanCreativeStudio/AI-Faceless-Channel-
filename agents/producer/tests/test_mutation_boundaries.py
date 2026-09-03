"""Tests 11-13: dry-run makes no mutation at all; apply writes only the
Producer's allowed files/fields; protected fields (claims, CONTENT_ITEM.md)
are immutable across a Producer run.
"""
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.pipeline import run_producer
from .builders import build_minimal_item


class MutationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    # --- Test 11: dry-run makes no mutation ---
    def test_dry_run_makes_no_mutation(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_producer(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        self.assertEqual(before, after)
        self.assertFalse(result.produced)
        self.assertEqual(result.production_path, "")
        self.assertFalse((self.root / "PRODUCTION.md").exists())
        self.assertFalse((self.root / "scenes").exists())
        self.assertTrue(result.scenes)  # still computed, just not written

    # --- Test 12: apply writes only allowed fields/files ---
    def test_apply_writes_only_production_and_scene_files(self):
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }

        result = run_producer(self.root, apply=True)

        self.assertTrue((self.root / "PRODUCTION.md").is_file())
        self.assertTrue(result.scene_paths)
        for scene_path in result.scene_paths:
            self.assertTrue(Path(scene_path).is_file())

        self.assertEqual((self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), content_item_before)
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    # --- Test 13: protected fields immutable — mutate.py rejects anything off-whitelist ---
    def test_mutate_rejects_non_whitelisted_scene_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_scene_file(self.root, "not-a-scene.md", "content")

    def test_apply_never_touches_content_item_status(self):
        run_producer(self.root, apply=True)
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)


if __name__ == "__main__":
    unittest.main()
