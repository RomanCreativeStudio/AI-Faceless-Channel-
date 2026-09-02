"""Tests 19, 20, 23: missing/malformed content produces SYSTEM_ERROR, not
PASS; a reviewer exception produces SYSTEM_ERROR, not PASS; human
escalation stays visible in the final result."""
import tempfile
import unittest
from pathlib import Path

from ..src.models import FACT_CHECK, SAFETY_REVIEW
from ..src.pipeline import run_automated_review
from .builders import build_all_pass_item


def _crashing_run(root, apply):
    raise RuntimeError("simulated reviewer crash")


class ErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 19: missing/malformed content -> SYSTEM_ERROR, not PASS ---
    def test_missing_content_item_is_system_error(self):
        self.root.mkdir(parents=True)  # empty directory, no CONTENT_ITEM.md at all
        result = run_automated_review(self.root, apply=False, originality_channel_index=[])
        self.assertEqual(result.overall_result.value, "SYSTEM_ERROR")
        self.assertEqual(result.pipeline_status, "SYSTEM_ERROR")
        self.assertNotEqual(result.overall_result.value, "PASS")
        self.assertEqual(result.stages_executed, [FACT_CHECK])
        self.assertEqual(result.stage_results[FACT_CHECK].system_error, True)

    def test_missing_script_is_system_error(self):
        build_all_pass_item(self.root)
        (self.root / "SCRIPT.md").unlink()
        result = run_automated_review(self.root, apply=False, originality_channel_index=[])
        self.assertEqual(result.overall_result.value, "SYSTEM_ERROR")
        self.assertNotEqual(result.overall_result.value, "PASS")

    # --- Test 20: reviewer exception -> SYSTEM_ERROR, not PASS ---
    def test_reviewer_exception_is_system_error_not_pass(self):
        build_all_pass_item(self.root)
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={SAFETY_REVIEW: _crashing_run},
        )
        self.assertEqual(result.overall_result.value, "SYSTEM_ERROR")
        self.assertNotEqual(result.overall_result.value, "PASS")
        self.assertEqual(result.first_blocking_stage, SAFETY_REVIEW)
        self.assertIn("RuntimeError", result.blocking_reason)
        self.assertIn("simulated reviewer crash", result.blocking_reason)
        # The crash never wrote anything.
        self.assertFalse((self.root / "reviews").exists())

    def test_reviewer_exception_does_not_run_later_stages(self):
        build_all_pass_item(self.root)
        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={FACT_CHECK: _crashing_run},
        )
        self.assertEqual(result.stages_executed, [FACT_CHECK])
        self.assertEqual(result.stages_skipped, [SAFETY_REVIEW, "ORIGINALITY_REVIEW"])

    # --- Test 23: human escalation remains visible in final result ---
    def test_human_escalation_visible_on_reject(self):
        build_all_pass_item(self.root)
        from ...researcher.src.models import ReviewVerdict

        def stub(root, apply):
            class R:
                content_id = "test-item"
                verdict = ReviewVerdict.REJECT
                reasons = ["simulated"]
                required_changes = []
                escalate_to_human = True
                blocked = False
                blocked_reason = ""
                aborted = False
                abort_reason = ""
                review_path = ""
            return R()

        result = run_automated_review(
            self.root, apply=False, originality_channel_index=[],
            stage_overrides={FACT_CHECK: stub},
        )
        self.assertTrue(result.human_escalation)
        self.assertEqual(result.overall_result.value, "REJECT")


if __name__ == "__main__":
    unittest.main()
