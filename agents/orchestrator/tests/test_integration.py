"""End-to-end integration tests using only the real agents (no stage
overrides): FACT_CHECK -> PASS -> SAFETY_REVIEW -> PASS ->
ORIGINALITY_REVIEW -> PASS -> AUTOMATED_REVIEW_COMPLETE, and a second
fixture where an early stage genuinely blocks the pipeline so later
stages are never invoked. Also confirms the real golden sample is
untouched by running this suite."""
import tempfile
import unittest
from pathlib import Path

from ...researcher.src.loader import load_reviews
from ..src.models import FACT_CHECK, ORIGINALITY_REVIEW, SAFETY_REVIEW
from ..src.pipeline import run_automated_review
from .builders import build_all_pass_item, build_fact_check_blocked_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class EndToEndAllPassTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_all_pass_item(self.root)

    def test_full_pipeline_reaches_automated_review_complete(self):
        result = run_automated_review(self.root, apply=True, originality_channel_index=[])

        self.assertEqual(result.overall_result.value, "PASS")
        self.assertEqual(result.pipeline_status, "AUTOMATED_REVIEW_COMPLETE")
        self.assertEqual(result.stages_executed, [FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW])
        self.assertEqual(result.stages_skipped, [])
        self.assertIsNone(result.first_blocking_stage)
        self.assertFalse(result.human_escalation)

        for stage in (FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW):
            outcome = result.stage_results[stage]
            self.assertEqual(outcome.verdict.value, "PASS")
            self.assertTrue(Path(outcome.review_path).is_file())

        # Each agent's own review file and field really landed.
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("| Fact-check state | `PASS` |", content_item_text)
        self.assertIn("| Safety state | `PASS` |", content_item_text)
        self.assertIn("| Originality state | `PASS` |", content_item_text)
        self.assertEqual(len(load_reviews(self.root / "reviews", "fact_checker")), 1)
        self.assertEqual(len(load_reviews(self.root / "reviews", "safety_reviewer")), 1)
        self.assertEqual(len(load_reviews(self.root / "reviews", "originality_reviewer")), 1)


class EndToEndEarlyBlockTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_fact_check_blocked_item(self.root)

    def test_fact_check_blocks_and_later_stages_never_run(self):
        result = run_automated_review(self.root, apply=True, originality_channel_index=[])

        self.assertNotEqual(result.overall_result.value, "PASS")
        self.assertEqual(result.pipeline_status, "BLOCKED_AT_FACT_CHECK")
        self.assertEqual(result.stages_executed, [FACT_CHECK])
        self.assertEqual(result.stages_skipped, [SAFETY_REVIEW, ORIGINALITY_REVIEW])

        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("| Safety state | `NOT_STARTED` |", content_item_text)
        self.assertIn("| Originality state | `NOT_STARTED` |", content_item_text)
        self.assertFalse((self.root / "reviews" / "safety_reviewer-1.md").exists())
        self.assertFalse((self.root / "reviews" / "originality_reviewer-1.md").exists())


class GoldenSampleUntouchedTests(unittest.TestCase):
    def test_dry_run_against_real_golden_sample_never_writes(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_automated_review(GOLDEN_SAMPLE, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertEqual(before, after)
        self.assertFalse((GOLDEN_SAMPLE / "reviews").exists())
        # The real golden sample has known content gaps (c1 DISPUTED,
        # c11 UNRESOLVED — see agents/researcher/README.md) and is
        # expected to block at FACT_CHECK, not reach PASS.
        self.assertEqual(result.first_blocking_stage, FACT_CHECK)


if __name__ == "__main__":
    unittest.main()
