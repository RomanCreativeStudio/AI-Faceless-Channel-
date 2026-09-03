"""Tests 1-3: approved script -> a voice plan can be produced;
unapproved content -> blocked with no mutation; the real golden sample
(never APPROVED) is never modified by a Voice run.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.tests.builders import build_minimal_item
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 1: approved script -> voice plan ---
    def test_approved_status_produces_a_voice_plan(self):
        build_produced_item(self.root)
        result = run_voice_generation(self.root, apply=True)
        self.assertFalse(result.blocked)
        self.assertFalse(result.aborted)
        self.assertTrue(result.produced)
        self.assertTrue(Path(result.voice_path).is_file())
        self.assertTrue(Path(result.audio_path).is_file())

    # --- Test 2: unapproved content -> blocked, no mutation ---
    def test_unapproved_content_item_status_is_blocked_with_no_mutation(self):
        build_minimal_item(self.root, status="SCRIPT")

        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_voice_generation(self.root, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertFalse(result.produced)
        self.assertEqual(before, after)
        self.assertFalse((self.root / "voice").exists())

    # --- Test 3: golden sample (status=SCRIPT, never APPROVED) untouched ---
    def test_golden_sample_never_modified(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_voice_generation(GOLDEN_SAMPLE, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}

        self.assertTrue(result.blocked)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
