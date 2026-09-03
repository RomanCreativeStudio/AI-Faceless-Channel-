"""Tests 15-18: dry-run creates no output; apply creates only
allowed output; every protected field remains protected; existing
assembly history is never overwritten.
"""
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.pipeline import run_video_assembly
from .builders import build_assembly_ready_item


class MutationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_assembly_ready_item(self.root)

    # --- Test 15: dry-run creates no output ---
    def test_dry_run_creates_no_output(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_video_assembly(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        self.assertEqual(before, after)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "timeline").exists())
        self.assertFalse((self.root / "output").exists())
        self.assertTrue(result.scenes)  # still computed, just not written

    # --- Test 16: apply creates allowed output ---
    def test_apply_creates_only_allowed_output(self):
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        voice_before = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        assets_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "assets").glob("*.md")
        }
        scenes_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }

        result = run_video_assembly(self.root, apply=True)

        self.assertTrue(Path(result.timeline_path).is_file())
        self.assertTrue(Path(result.output_path).is_file())

        self.assertEqual((self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), content_item_before)
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)
        self.assertEqual((self.root / "voice" / "voice-01.md").read_text(encoding="utf-8"), voice_before)
        assets_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "assets").glob("*.md")
        }
        self.assertEqual(assets_before, assets_after)
        scenes_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }
        self.assertEqual(scenes_before, scenes_after)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Assembly status | `ASSEMBLED` |", production_text)
        self.assertIn("| Production status | `CAPTIONS` |", production_text)

    # --- Test 17: protected fields cannot be changed ---
    def test_mutate_rejects_non_whitelisted_timeline_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_timeline_file(self.root, "not-a-timeline.md", "content")

    def test_mutate_rejects_non_whitelisted_output_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_output_artifact(self.root, "not-output.mp4", "content")

    def test_apply_never_touches_claims(self):
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_video_assembly(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    # --- Test 18: existing assembly history isn't overwritten ---
    def test_stale_assembly_is_never_overwritten(self):
        run_video_assembly(self.root, apply=True)
        timeline_before = (self.root / "timeline" / "timeline-01.md").read_text(encoding="utf-8")
        output_before = (self.root / "output" / "video-01.manifest.txt").read_text(encoding="utf-8")

        # Corrupt an asset's hash to simulate an upstream change, forcing staleness.
        asset_path = self.root / "assets" / "asset-02.md"
        text = asset_path.read_text(encoding="utf-8")
        line = [l for l in text.splitlines() if l.startswith("| Scene/visual content hash |")][0]
        text = text.replace(line, "| Scene/visual content hash | `0000000000stale` |")
        asset_path.write_text(text, encoding="utf-8")

        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)  # blocked on the stale-asset precondition, not reached staleness check
        self.assertFalse(result.produced)

        timeline_after = (self.root / "timeline" / "timeline-01.md").read_text(encoding="utf-8")
        output_after = (self.root / "output" / "video-01.manifest.txt").read_text(encoding="utf-8")
        self.assertEqual(timeline_before, timeline_after)
        self.assertEqual(output_before, output_after)


if __name__ == "__main__":
    unittest.main()
