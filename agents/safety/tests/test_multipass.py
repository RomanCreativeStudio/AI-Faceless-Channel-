"""Tests 12-14 from the Phase 6 task: existing safety failure cannot be
silently cleared, PASS becomes stale on content change, review attempts
remain immutable/sequential. Reuses agents/researcher/src/multipass's
generic gating functions, same as the pipeline does."""
import tempfile
import unittest
from pathlib import Path

from ...researcher.src.loader import load_content_item
from ...researcher.src.models import ReviewRecord, ReviewVerdict
from ...researcher.src.multipass import can_run_new_attempt, consecutive_autonomous_revision_required
from ..src.hashing import compute_reviewed_content_hash
from ..src.loader import load_safety_bundle
from ..src.pipeline import ROLE_FILE_PREFIX, ROLE_LABEL, run_safety_review
from .builders import build_minimal_item


def _review(attempt, verdict, content_hash="N/A"):
    return ReviewRecord(
        path=Path(f"reviews/{ROLE_FILE_PREFIX}-{attempt}.md"),
        role=ROLE_FILE_PREFIX, attempt=attempt, verdict=verdict, reviewed_content_hash=content_hash,
    )


class SafetyMultipassTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    # --- Test 12: existing failure (REJECT) cannot be silently cleared ---
    def test_reject_blocks_new_attempt_without_human_reopen(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        reviews = [_review(1, ReviewVerdict.REJECT)]
        allowed, reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)
        self.assertFalse(allowed)
        self.assertIn("REJECT", reason)

    def test_reject_unblocked_after_human_reopen_logged(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        text = content_item.path.read_text(encoding="utf-8")
        content_item.path.write_text(text + "\n- HUMAN_REOPEN: SAFETY_REVIEWER\n", encoding="utf-8")
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        reviews = [_review(1, ReviewVerdict.REJECT)]
        allowed, reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)
        self.assertTrue(allowed, reason)

    # --- Test 13: PASS becomes stale if reviewed content changes ---
    def test_pass_hash_mismatches_after_content_changes(self):
        bundle = load_safety_bundle(self.root)
        original_hash = compute_reviewed_content_hash(bundle)

        script_path = self.root / "SCRIPT.md"
        script_path.write_text(script_path.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")

        changed_bundle = load_safety_bundle(self.root)
        new_hash = compute_reviewed_content_hash(changed_bundle)
        self.assertNotEqual(original_hash, new_hash)

    # --- Test 14: review attempts remain immutable/sequential ---
    def test_two_consecutive_revision_required_blocks_third_attempt(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        reviews = [
            _review(1, ReviewVerdict.REVISION_REQUIRED),
            _review(2, ReviewVerdict.REVISION_REQUIRED),
        ]
        self.assertEqual(consecutive_autonomous_revision_required(reviews), 2)
        allowed, reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)
        self.assertFalse(allowed)
        self.assertIn("escalation", reason.lower())

    def test_apply_writes_sequential_numbered_attempts(self):
        first = run_safety_review(self.root, apply=True)
        second = run_safety_review(self.root, apply=True)
        self.assertTrue(Path(first.review_path).name.endswith("-1.md"))
        self.assertTrue(Path(second.review_path).name.endswith("-2.md"))
        # Attempt 1's file is untouched by attempt 2.
        first_text_after = Path(first.review_path).read_text(encoding="utf-8")
        self.assertIn("attempt 1", first_text_after)


if __name__ == "__main__":
    unittest.main()
