"""Tests 1-8: an approved production assembles successfully; unapproved
content blocks; a missing production/scene/voice/asset all block; a
stale voice or stale asset blocks rather than silently assembling from
outdated inputs.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.tests.builders import build_minimal_item
from ..src.pipeline import run_video_assembly
from .builders import build_assembly_ready_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ApprovalAndPreconditionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 1: approved production assembles successfully ---
    def test_approved_production_assembles_successfully(self):
        build_assembly_ready_item(self.root)
        result = run_video_assembly(self.root, apply=True)
        self.assertFalse(result.blocked)
        self.assertFalse(result.aborted)
        self.assertTrue(result.produced)
        self.assertEqual(result.assembly_status, "ASSEMBLED")

    # --- Test 2: unapproved content blocks ---
    def test_unapproved_content_blocks(self):
        build_minimal_item(self.root, status="SCRIPT")
        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertFalse(result.produced)

    def test_golden_sample_never_modified(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_video_assembly(GOLDEN_SAMPLE, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertTrue(result.blocked)
        self.assertEqual(before, after)

    # --- Test 3: missing production blocks ---
    def test_missing_production_blocks(self):
        build_assembly_ready_item(self.root)
        (self.root / "PRODUCTION.md").unlink()
        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("PRODUCTION.md", result.abort_reason)
        self.assertFalse(result.produced)

    # --- Test 4: missing scene blocks ---
    def test_missing_scene_blocks(self):
        build_assembly_ready_item(
            self.root,
            beats=["1. A factual beat. — claims: `c1`", "2. Another beat. — claims: `c1`"],
        )
        # Default fixture has 3 scenes (hook + 2 beats); delete the
        # middle one so the remaining Order values (1, 3) have a gap.
        (self.root / "scenes" / "scene-02.md").unlink()
        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("contiguous", result.blocked_reason)
        self.assertFalse(result.produced)

    # --- Test 5: missing voice blocks ---
    def test_missing_voice_blocks(self):
        build_assembly_ready_item(self.root)
        (self.root / "voice" / "voice-01.md").unlink()
        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("voice", result.blocked_reason.lower())
        self.assertFalse(result.produced)

    # --- Test 6: stale voice blocks ---
    def test_stale_voice_blocks(self):
        build_assembly_ready_item(self.root)
        voice_path = self.root / "voice" / "voice-01.md"
        text = voice_path.read_text(encoding="utf-8")
        line = [l for l in text.splitlines() if l.startswith("| Script content hash |")][0]
        text = text.replace(line, "| Script content hash | `0000000000stale` |")
        voice_path.write_text(text, encoding="utf-8")

        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("stale", result.blocked_reason.lower())
        self.assertFalse(result.produced)

    # --- Test 7: missing asset blocks ---
    def test_missing_asset_blocks(self):
        build_assembly_ready_item(self.root)
        (self.root / "assets" / "asset-02.md").unlink()
        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("missing required asset", result.blocked_reason)
        self.assertFalse(result.produced)

    # --- Test 8: stale asset blocks ---
    def test_stale_asset_blocks(self):
        build_assembly_ready_item(self.root)
        asset_path = self.root / "assets" / "asset-02.md"
        text = asset_path.read_text(encoding="utf-8")
        line = [l for l in text.splitlines() if l.startswith("| Scene/visual content hash |")][0]
        text = text.replace(line, "| Scene/visual content hash | `0000000000stale` |")
        asset_path.write_text(text, encoding="utf-8")

        result = run_video_assembly(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("stale", result.blocked_reason.lower())
        self.assertFalse(result.produced)


if __name__ == "__main__":
    unittest.main()
