"""Integration tests for apply=True: writes exactly the permitted fields,
respects the two-consecutive-REVISION_REQUIRED cap end-to-end, and never
touches the real fixture (always runs against a temp copy)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.models import ReviewVerdict
from ..src.pipeline import run_fact_check

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_item"


class ApplyModeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(FIXTURE_ROOT, self.root)

    def test_apply_writes_review_file_and_updates_only_permitted_fields(self):
        before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        result = run_fact_check(self.root, apply=True)

        review_path = Path(result.review_path)
        self.assertTrue(review_path.is_file())
        self.assertEqual(review_path.name, "fact_checker-1.md")
        review_text = review_path.read_text(encoding="utf-8")
        self.assertIn(f"`{result.verdict.value}`", review_text)
        self.assertIn(result.content_hash, review_text)

        after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertNotEqual(before, after)
        self.assertIn(f"| Fact-check state | `{result.verdict.value}` |", after)
        # Everything else in CONTENT_ITEM.md besides the one field row and
        # the appended log line is untouched.
        self.assertIn("| Research state | `COMPLETE` |", after)  # unchanged
        self.assertIn("| Content pillar | `what-if` |", after)  # unchanged

    def test_two_consecutive_revision_required_then_blocked(self):
        first = run_fact_check(self.root, apply=True)
        self.assertEqual(first.verdict, ReviewVerdict.REVISION_REQUIRED)
        self.assertFalse(first.blocked)

        second = run_fact_check(self.root, apply=True)
        self.assertEqual(second.verdict, ReviewVerdict.REVISION_REQUIRED)
        self.assertFalse(second.blocked)

        third = run_fact_check(self.root, apply=True)
        self.assertTrue(third.blocked)
        self.assertTrue(third.escalate_to_human)
        self.assertEqual(third.review_path, "")
        # No fact_checker-3.md was written.
        self.assertFalse((self.root / "reviews" / "fact_checker-3.md").is_file())
        self.assertTrue((self.root / "reviews" / "fact_checker-2.md").is_file())

    def test_golden_sample_fixture_untouched_by_this_test_run(self):
        # Sanity check that setUp's copytree isolates us from the real
        # fixture directory tests run against elsewhere.
        self.assertNotEqual(self.root, FIXTURE_ROOT)
        original_review_dir = FIXTURE_ROOT / "reviews"
        self.assertFalse(original_review_dir.exists())


if __name__ == "__main__":
    unittest.main()
