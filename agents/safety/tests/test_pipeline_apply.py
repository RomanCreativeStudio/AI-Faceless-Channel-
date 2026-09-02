"""Tests 16-17 from the Phase 6 task: dry-run does not modify content;
apply mode modifies only permitted safety fields."""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_safety_review
from .builders import build_minimal_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ApplyModeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    # --- Test 16: dry-run does not modify content ---
    def test_dry_run_does_not_touch_disk(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_safety_review(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        self.assertEqual(before, after)
        self.assertEqual(result.review_path, "")
        self.assertFalse((self.root / "reviews").exists())

    def test_dry_run_against_real_golden_sample_never_writes(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = (GOLDEN_SAMPLE / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        run_safety_review(GOLDEN_SAMPLE, apply=False)
        after = (GOLDEN_SAMPLE / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertFalse((GOLDEN_SAMPLE / "reviews").exists())

    # --- Test 17: apply mode modifies only permitted safety fields ---
    def test_apply_writes_review_and_only_safety_state(self):
        before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        result = run_safety_review(self.root, apply=True)

        review_path = Path(result.review_path)
        self.assertTrue(review_path.is_file())
        self.assertIn(f"`{result.verdict.value}`", review_path.read_text(encoding="utf-8"))

        after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertNotEqual(before, after)
        self.assertIn(f"| Safety state | `{result.verdict.value}` |", after)
        # Everything else is untouched.
        self.assertIn("| Research state | `COMPLETE` |", after)
        self.assertIn("| Fact-check state | `NOT_STARTED` |", after)
        self.assertIn("| Owner approval state | `NOT_STARTED` |", after)

    def test_apply_never_writes_a_claims_file(self):
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_safety_review(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)


if __name__ == "__main__":
    unittest.main()
