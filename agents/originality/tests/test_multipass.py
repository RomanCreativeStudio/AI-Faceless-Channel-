"""Tests 14-15 from the task: PASS becomes stale after reviewed content
changes; review attempts remain immutable/sequential. Reuses
agents/researcher/src/multipass's generic gating functions, same as the
pipeline does."""
import tempfile
import unittest
from pathlib import Path

from ...researcher.src.loader import load_content_item
from ...researcher.src.models import ReviewRecord, ReviewVerdict
from ...researcher.src.multipass import can_run_new_attempt, consecutive_autonomous_revision_required
from ..src.hashing import compute_reviewed_content_hash
from ..src.loader import load_originality_bundle
from ..src.pipeline import ROLE_FILE_PREFIX, ROLE_LABEL, run_originality_review
from .builders import build_minimal_item


def _review(attempt, verdict, content_hash="N/A"):
    return ReviewRecord(
        path=Path(f"reviews/{ROLE_FILE_PREFIX}-{attempt}.md"),
        role=ROLE_FILE_PREFIX, attempt=attempt, verdict=verdict, reviewed_content_hash=content_hash,
    )


class OriginalityMultipassTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    def test_reject_blocks_new_attempt_without_human_reopen(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        reviews = [_review(1, ReviewVerdict.REJECT)]
        allowed, reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)
        self.assertFalse(allowed)
        self.assertIn("REJECT", reason)

    def test_reject_unblocked_after_human_reopen_logged(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        text = content_item.path.read_text(encoding="utf-8")
        content_item.path.write_text(text + "\n- HUMAN_REOPEN: ORIGINALITY_REVIEWER\n", encoding="utf-8")
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        reviews = [_review(1, ReviewVerdict.REJECT)]
        allowed, reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)
        self.assertTrue(allowed, reason)

    # --- Test 14: PASS becomes stale if reviewed content changes ---
    def test_hash_changes_after_script_edit(self):
        bundle = load_originality_bundle(self.root, channel_index=[])
        original_hash = compute_reviewed_content_hash(bundle)

        script_path = self.root / "SCRIPT.md"
        script_path.write_text(script_path.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")

        changed_bundle = load_originality_bundle(self.root, channel_index=[])
        new_hash = compute_reviewed_content_hash(changed_bundle)
        self.assertNotEqual(original_hash, new_hash)

    def test_hash_changes_when_reference_material_changes(self):
        ref_path = Path(self._tmp.name) / "reference.txt"
        ref_path.write_text("original reference text", encoding="utf-8")
        bundle_a = load_originality_bundle(self.root, channel_index=[], reference_paths=[ref_path])
        hash_a = compute_reviewed_content_hash(bundle_a)

        ref_path.write_text("changed reference text", encoding="utf-8")
        bundle_b = load_originality_bundle(self.root, channel_index=[], reference_paths=[ref_path])
        hash_b = compute_reviewed_content_hash(bundle_b)
        self.assertNotEqual(hash_a, hash_b)

    # --- Test 15: review attempts remain immutable/sequential ---
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
        first = run_originality_review(self.root, apply=True, channel_index=[])
        second = run_originality_review(self.root, apply=True, channel_index=[])
        self.assertTrue(Path(first.review_path).name.endswith("-1.md"))
        self.assertTrue(Path(second.review_path).name.endswith("-2.md"))
        first_text_after = Path(first.review_path).read_text(encoding="utf-8")
        self.assertIn("attempt 1", first_text_after)


if __name__ == "__main__":
    unittest.main()
