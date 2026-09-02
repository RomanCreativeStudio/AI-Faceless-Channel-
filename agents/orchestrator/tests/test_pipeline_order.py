"""Tests 1-12: stage order, early-stop, skip reporting, and the
override-driven synthetic scenarios for REJECT vs. HUMAN_ESCALATION vs.
plain REVISION_REQUIRED. `stage_overrides` substitutes a stage's `run`
callable to construct scenarios not easily reached with the real
reviewers alone — see pipeline.py's docstring for why this seam exists
(tests only, never normal use)."""
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path

from ...researcher.src.models import ReviewVerdict
from ..src.models import FACT_CHECK, ORIGINALITY_REVIEW, SAFETY_REVIEW
from ..src.pipeline import run_automated_review
from .builders import build_all_pass_item, build_fact_check_blocked_item


@dataclass
class _FakeResult:
    content_id: str = "test-item"
    verdict: ReviewVerdict = ReviewVerdict.PASS
    reasons: list = field(default_factory=list)
    required_changes: list = field(default_factory=list)
    escalate_to_human: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    aborted: bool = False
    abort_reason: str = ""
    review_path: str = ""


def _stub(verdict, escalate=False, reasons=None):
    def run(root, apply):
        return _FakeResult(verdict=verdict, escalate_to_human=escalate, reasons=reasons or [])
    return run


class PipelineOrderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_all_pass_item(self.root)

    # --- Test 1: all three PASS -> overall PASS ---
    def test_all_three_pass_yields_overall_pass(self):
        result = run_automated_review(self.root, apply=False, originality_channel_index=[])
        self.assertEqual(result.overall_result.value, "PASS")
        self.assertEqual(result.pipeline_status, "AUTOMATED_REVIEW_COMPLETE")
        self.assertEqual(result.stages_executed, [FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW])
        self.assertEqual(result.stages_skipped, [])
        self.assertIsNone(result.first_blocking_stage)

    # --- Test 2: Fact Check REVISION_REQUIRED -> pipeline stops ---
    def test_fact_check_revision_required_stops_pipeline(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={FACT_CHECK: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=False)},
        )
        self.assertEqual(result.overall_result.value, "REVISION_REQUIRED")
        self.assertEqual(result.first_blocking_stage, FACT_CHECK)
        self.assertEqual(result.stages_executed, [FACT_CHECK])
        self.assertEqual(result.stages_skipped, [SAFETY_REVIEW, ORIGINALITY_REVIEW])

    # --- Test 3: Fact Check REJECT -> pipeline stops ---
    def test_fact_check_reject_stops_pipeline(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={FACT_CHECK: _stub(ReviewVerdict.REJECT, escalate=True)},
        )
        self.assertEqual(result.overall_result.value, "REJECT")
        self.assertEqual(result.first_blocking_stage, FACT_CHECK)
        self.assertEqual(result.stages_skipped, [SAFETY_REVIEW, ORIGINALITY_REVIEW])
        self.assertTrue(result.human_escalation)  # still visible even though label is REJECT

    # --- Test 4: Fact Check HUMAN_ESCALATION -> pipeline stops ---
    def test_fact_check_human_escalation_stops_pipeline(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={FACT_CHECK: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=True)},
        )
        self.assertEqual(result.overall_result.value, "HUMAN_ESCALATION")
        self.assertTrue(result.human_escalation)
        self.assertEqual(result.stages_skipped, [SAFETY_REVIEW, ORIGINALITY_REVIEW])

    # --- Test 5: Safety REVISION_REQUIRED -> Originality does not run ---
    def test_safety_revision_required_blocks_originality(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={SAFETY_REVIEW: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=False)},
        )
        self.assertEqual(result.stages_executed, [FACT_CHECK, SAFETY_REVIEW])
        self.assertEqual(result.stages_skipped, [ORIGINALITY_REVIEW])
        self.assertEqual(result.first_blocking_stage, SAFETY_REVIEW)

    # --- Test 6: Safety REJECT -> Originality does not run ---
    def test_safety_reject_blocks_originality(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={SAFETY_REVIEW: _stub(ReviewVerdict.REJECT, escalate=True)},
        )
        self.assertEqual(result.overall_result.value, "REJECT")
        self.assertEqual(result.stages_skipped, [ORIGINALITY_REVIEW])

    # --- Test 7: Safety HUMAN_ESCALATION -> Originality does not run ---
    def test_safety_human_escalation_blocks_originality(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={SAFETY_REVIEW: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=True)},
        )
        self.assertEqual(result.overall_result.value, "HUMAN_ESCALATION")
        self.assertEqual(result.stages_skipped, [ORIGINALITY_REVIEW])

    # --- Test 8: Originality REVISION_REQUIRED -> overall blocked ---
    def test_originality_revision_required_blocks_overall(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={ORIGINALITY_REVIEW: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=False)},
        )
        self.assertEqual(result.overall_result.value, "REVISION_REQUIRED")
        self.assertEqual(result.stages_executed, [FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW])
        self.assertEqual(result.stages_skipped, [])
        self.assertEqual(result.first_blocking_stage, ORIGINALITY_REVIEW)

    # --- Test 9: Originality HUMAN_ESCALATION -> overall blocked ---
    def test_originality_human_escalation_blocks_overall(self):
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={ORIGINALITY_REVIEW: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=True)},
        )
        self.assertEqual(result.overall_result.value, "HUMAN_ESCALATION")
        self.assertEqual(result.first_blocking_stage, ORIGINALITY_REVIEW)

    # --- Test 10: later stages cannot override an earlier failure ---
    def test_later_pass_cannot_override_earlier_failure(self):
        # Safety and Originality would both PASS if run, but Fact Check
        # fails first — they must never run, so their "PASS" opinion
        # cannot possibly override the block.
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={
                FACT_CHECK: _stub(ReviewVerdict.REVISION_REQUIRED, escalate=False),
                SAFETY_REVIEW: _stub(ReviewVerdict.PASS),
                ORIGINALITY_REVIEW: _stub(ReviewVerdict.PASS),
            },
        )
        self.assertEqual(result.overall_result.value, "REVISION_REQUIRED")
        self.assertEqual(result.stages_executed, [FACT_CHECK])
        self.assertNotIn(SAFETY_REVIEW, result.stage_results)
        self.assertNotIn(ORIGINALITY_REVIEW, result.stage_results)

    # --- Test 11: stage execution order is always correct ---
    def test_stage_order_is_fact_check_then_safety_then_originality(self):
        result = run_automated_review(self.root, apply=False, originality_channel_index=[])
        self.assertEqual(result.stages_executed, [FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW])

    # --- Test 12: skipped stages are explicitly reported ---
    def test_skipped_stages_explicitly_reported(self):
        with tempfile.TemporaryDirectory() as tmp2:
            root2 = Path(tmp2) / "item"
            build_fact_check_blocked_item(root2)
            result = run_automated_review(root2, apply=False, originality_channel_index=[])
            self.assertEqual(result.stages_skipped, [SAFETY_REVIEW, ORIGINALITY_REVIEW])
            self.assertNotIn(SAFETY_REVIEW, result.stage_results)
            self.assertNotIn(ORIGINALITY_REVIEW, result.stage_results)


if __name__ == "__main__":
    unittest.main()
