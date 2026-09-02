"""Tests 13-16: existing valid PASS is reused, changed content causes
stale re-review, existing REJECT remains terminal, and review history is
never overwritten."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ...researcher.src.loader import load_reviews
from ..src.models import FACT_CHECK
from ..src.pipeline import run_automated_review
from .builders import build_all_pass_item


class IdempotencyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_all_pass_item(self.root)

    # --- Test 13: existing valid PASS can be reused ---
    def test_second_apply_run_reuses_fact_check_pass(self):
        first = run_automated_review(self.root, apply=True, originality_channel_index=[])
        self.assertEqual(first.overall_result.value, "PASS")
        self.assertFalse(first.stage_results[FACT_CHECK].reused_existing_pass)

        second = run_automated_review(self.root, apply=True, originality_channel_index=[])
        self.assertEqual(second.overall_result.value, "PASS")
        self.assertTrue(second.stage_results[FACT_CHECK].reused_existing_pass)
        self.assertFalse(second.stage_results[FACT_CHECK].executed)

        # Only one fact_checker attempt file exists — no duplicate was written.
        reviews = load_reviews(self.root / "reviews", "fact_checker")
        self.assertEqual(len(reviews), 1)

    def test_reuse_also_applies_in_dry_run(self):
        run_automated_review(self.root, apply=True, originality_channel_index=[])
        dry = run_automated_review(self.root, apply=False, originality_channel_index=[])
        self.assertTrue(dry.stage_results[FACT_CHECK].reused_existing_pass)
        # Dry run still writes nothing, even though it detected a reusable PASS.
        reviews = load_reviews(self.root / "reviews", "fact_checker")
        self.assertEqual(len(reviews), 1)

    # --- Test 14: changed content causes stale review handling ---
    def test_changed_script_causes_re_review_not_reuse(self):
        run_automated_review(self.root, apply=True, originality_channel_index=[])
        script_path = self.root / "SCRIPT.md"
        script_path.write_text(script_path.read_text(encoding="utf-8") + "\nedited content\n", encoding="utf-8")

        second = run_automated_review(self.root, apply=True, originality_channel_index=[])
        self.assertFalse(second.stage_results[FACT_CHECK].reused_existing_pass)
        self.assertTrue(second.stage_results[FACT_CHECK].executed)
        reviews = load_reviews(self.root / "reviews", "fact_checker")
        self.assertEqual(len(reviews), 2)  # a fresh attempt was appended, not reused

    # --- Test 15: existing REJECT remains terminal ---
    def test_reject_remains_terminal_across_orchestrator_runs(self):
        # Write a genuine prior REJECT attempt directly, the same way a
        # real earlier fact-check run would have (rather than an
        # override, which never touches disk) — see CONTRACT.md/
        # templates/REVIEW.md Multi-pass resolution rule 3.
        from ...researcher.src.models import FactCheckResult, ReviewVerdict
        from ...researcher.src.review_writer import render_review_markdown

        reviews_dir = self.root / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        prior = FactCheckResult(
            content_id="test-item", verdict=ReviewVerdict.REJECT,
            reasons=["structural failure: simulated"], required_changes=[], notes=[],
            claim_evaluations=[], escalate_to_human=True, content_hash="deadbeef",
        )
        (reviews_dir / "fact_checker-1.md").write_text(
            render_review_markdown(prior, attempt=1), encoding="utf-8"
        )

        result = run_automated_review(self.root, apply=True, originality_channel_index=[])
        self.assertEqual(result.overall_result.value, "REJECT")
        self.assertTrue(result.stage_results[FACT_CHECK].blocked)
        reviews = load_reviews(self.root / "reviews", "fact_checker")
        self.assertEqual(len(reviews), 1)  # no second attempt was created

        # Running it again changes nothing further.
        again = run_automated_review(self.root, apply=True, originality_channel_index=[])
        self.assertEqual(again.overall_result.value, "REJECT")
        reviews_again = load_reviews(self.root / "reviews", "fact_checker")
        self.assertEqual(len(reviews_again), 1)

    # --- Test 16: existing review history is not overwritten ---
    def test_review_history_files_are_never_overwritten(self):
        run_automated_review(self.root, apply=True, originality_channel_index=[])
        first_path = self.root / "reviews" / "fact_checker-1.md"
        first_text_before = first_path.read_text(encoding="utf-8")

        script_path = self.root / "SCRIPT.md"
        script_path.write_text(script_path.read_text(encoding="utf-8") + "\nedited again\n", encoding="utf-8")
        run_automated_review(self.root, apply=True, originality_channel_index=[])

        first_text_after = first_path.read_text(encoding="utf-8")
        self.assertEqual(first_text_before, first_text_after)
        self.assertTrue((self.root / "reviews" / "fact_checker-2.md").is_file())


if __name__ == "__main__":
    unittest.main()
