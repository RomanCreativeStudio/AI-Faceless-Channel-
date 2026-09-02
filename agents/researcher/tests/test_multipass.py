"""Tests 11-14 from the Phase 5 task: REVISION_REQUIRED behavior, two
autonomous attempts -> human escalation, REJECT terminal behavior, PASS
becoming stale when reviewed artifacts change."""
import unittest
from dataclasses import replace
from pathlib import Path

from ..src.hashing import compute_reviewed_content_hash
from ..src.loader import load_bundle, load_content_item
from ..src.models import ReviewRecord, ReviewVerdict
from ..src.multipass import (
    can_run_new_attempt,
    consecutive_autonomous_revision_required,
    effective_stage_state,
    next_attempt_number,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_item"


def _review(attempt, verdict, content_hash="N/A"):
    return ReviewRecord(
        path=FIXTURE_ROOT / f"reviews/fact_checker-{attempt}.md",
        role="fact_checker",
        attempt=attempt,
        verdict=verdict,
        reviewed_content_hash=content_hash,
    )


class MultipassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle(FIXTURE_ROOT)
        cls.content_item = load_content_item(FIXTURE_ROOT / "CONTENT_ITEM.md")

    # --- Test 11: REVISION_REQUIRED is actionable autonomously ---
    def test_single_revision_required_allows_next_attempt(self):
        reviews = [_review(1, ReviewVerdict.REVISION_REQUIRED)]
        allowed, reason = can_run_new_attempt(reviews, self.content_item, "FACT_CHECKER")
        self.assertTrue(allowed, reason)
        self.assertEqual(next_attempt_number(reviews), 2)

    # --- Test 12: two consecutive autonomous attempts -> escalation ---
    def test_two_consecutive_revision_required_blocks_third_attempt(self):
        reviews = [
            _review(1, ReviewVerdict.REVISION_REQUIRED),
            _review(2, ReviewVerdict.REVISION_REQUIRED),
        ]
        self.assertEqual(consecutive_autonomous_revision_required(reviews), 2)
        allowed, reason = can_run_new_attempt(reviews, self.content_item, "FACT_CHECKER")
        self.assertFalse(allowed)
        self.assertIn("escalation", reason.lower())

    def test_pass_between_revisions_resets_the_streak(self):
        reviews = [
            _review(1, ReviewVerdict.REVISION_REQUIRED),
            _review(2, ReviewVerdict.PASS, content_hash="deadbeef"),
            _review(3, ReviewVerdict.REVISION_REQUIRED),
        ]
        self.assertEqual(consecutive_autonomous_revision_required(reviews), 1)
        allowed, _ = can_run_new_attempt(reviews, self.content_item, "FACT_CHECKER")
        self.assertTrue(allowed)

    # --- Test 13: REJECT is terminal without a logged human reopen ---
    def test_reject_blocks_new_attempt_without_human_reopen(self):
        reviews = [_review(1, ReviewVerdict.REJECT)]
        allowed, reason = can_run_new_attempt(reviews, self.content_item, "FACT_CHECKER")
        self.assertFalse(allowed)
        self.assertIn("REJECT", reason)
        self.assertIn("terminal", reason)

    def test_reject_unblocked_after_logged_human_reopen(self):
        reopened_item = replace(
            self.content_item,
            raw_text=self.content_item.raw_text + "\n- HUMAN_REOPEN: FACT_CHECKER\n",
        )
        reviews = [_review(1, ReviewVerdict.REJECT)]
        allowed, reason = can_run_new_attempt(reviews, reopened_item, "FACT_CHECKER")
        self.assertTrue(allowed, reason)

    # --- Test 14: PASS becomes stale when reviewed artifacts change ---
    def test_pass_is_valid_when_hash_matches_current_content(self):
        claim_ids = [row.short_id for row in self.bundle.script_claim_rows]
        current_hash = compute_reviewed_content_hash(self.bundle, claim_ids)
        reviews = [_review(1, ReviewVerdict.PASS, content_hash=current_hash)]
        state, explanation = effective_stage_state(reviews, self.bundle)
        self.assertEqual(state, "PASS")
        self.assertNotIn("stale", explanation)

    def test_pass_goes_stale_when_script_changes(self):
        claim_ids = [row.short_id for row in self.bundle.script_claim_rows]
        original_hash = compute_reviewed_content_hash(self.bundle, claim_ids)
        reviews = [_review(1, ReviewVerdict.PASS, content_hash=original_hash)]

        changed_bundle = replace(self.bundle, script_text=self.bundle.script_text + "\nedited\n")
        state, explanation = effective_stage_state(reviews, changed_bundle)
        self.assertEqual(state, "REVISION_REQUIRED")
        self.assertIn("stale", explanation)

    def test_no_reviews_yet_is_not_started(self):
        state, _ = effective_stage_state([], self.bundle)
        self.assertEqual(state, "NOT_STARTED")


if __name__ == "__main__":
    unittest.main()
