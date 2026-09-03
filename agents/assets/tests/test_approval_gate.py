"""Tests 1-3: an approved fixture produces asset records; unapproved
content is blocked with no mutation; the real golden sample (never
APPROVED) is never modified by an Asset agent run.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.tests.builders import build_minimal_item
from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 1: approved fixture produces asset records ---
    def test_approved_fixture_produces_asset_records(self):
        build_visual_planned_item(self.root)
        result = run_asset_generation(self.root, apply=True)
        self.assertFalse(result.blocked)
        self.assertFalse(result.aborted)
        self.assertTrue(result.produced)
        self.assertTrue(result.plans)
        for path in result.asset_paths:
            self.assertTrue(Path(path).is_file())

    # --- Test 2: unapproved content is blocked ---
    def test_unapproved_content_item_status_is_blocked_with_no_mutation(self):
        build_minimal_item(self.root, status="SCRIPT")
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_asset_generation(self.root, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertFalse(result.produced)
        self.assertEqual(before, after)
        self.assertFalse((self.root / "assets").exists())

    # --- Test 3: golden sample untouched ---
    def test_golden_sample_never_modified(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_asset_generation(GOLDEN_SAMPLE, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}

        self.assertTrue(result.blocked)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
