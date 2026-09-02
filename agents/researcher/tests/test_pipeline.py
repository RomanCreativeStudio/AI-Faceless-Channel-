"""End-to-end pipeline tests, including test 15: the real Phase 3 golden
sample's c11 (no dedicated source) must stay unresolved with no fabricated
citation."""
import unittest
from pathlib import Path

from ..src.models import EvidenceSupport, FactCheckStatus, ReviewVerdict
from ..src.pipeline import run_fact_check

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_item"
REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_SAMPLE = REPO_ROOT / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"


class MiniFixturePipelineTests(unittest.TestCase):
    def test_dry_run_does_not_touch_disk(self):
        before = (FIXTURE_ROOT / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        result = run_fact_check(FIXTURE_ROOT, apply=False)
        after = (FIXTURE_ROOT / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(result.review_path, "")

    def test_mixed_fixture_yields_revision_required(self):
        result = run_fact_check(FIXTURE_ROOT, apply=False)
        self.assertEqual(result.verdict, ReviewVerdict.REVISION_REQUIRED)
        self.assertFalse(result.aborted)
        self.assertFalse(result.blocked)

    def test_deterministic_output(self):
        result_a = run_fact_check(FIXTURE_ROOT, apply=False)
        result_b = run_fact_check(FIXTURE_ROOT, apply=False)
        self.assertEqual(result_a.content_hash, result_b.content_hash)
        self.assertEqual(result_a.verdict, result_b.verdict)
        self.assertEqual(
            [(e.short_id, e.fact_check_status) for e in result_a.claim_evaluations],
            [(e.short_id, e.fact_check_status) for e in result_b.claim_evaluations],
        )


class GoldenSampleTests(unittest.TestCase):
    """Test 15: c11 remains unresolved without fabricated evidence."""

    @classmethod
    def setUpClass(cls):
        if not GOLDEN_SAMPLE.is_dir():
            raise unittest.SkipTest(f"golden sample not found at {GOLDEN_SAMPLE}")
        cls.result = run_fact_check(GOLDEN_SAMPLE, apply=False)

    def test_c11_stays_unresolved(self):
        c11 = next(e for e in self.result.claim_evaluations if e.short_id == "c11")
        self.assertEqual(c11.evidence_support, EvidenceSupport.UNRESOLVED)
        self.assertEqual(c11.fact_check_status, FactCheckStatus.UNVERIFIED)
        self.assertNotEqual(c11.fact_check_status, FactCheckStatus.VERIFIED)

    def test_c11_gap_is_named_not_fabricated(self):
        c11 = next(e for e in self.result.claim_evaluations if e.short_id == "c11")
        self.assertIn("not found", c11.reason.lower())
        # The claim's own file must be untouched: still N/A supporting
        # sources, no invented citation.
        text = (GOLDEN_SAMPLE / "claims" / "c11.md").read_text(encoding="utf-8")
        self.assertIn("`N/A`", text)

    def test_overall_verdict_is_revision_required_not_pass(self):
        # c11's gap alone is enough to block a clean PASS.
        self.assertEqual(self.result.verdict, ReviewVerdict.REVISION_REQUIRED)
        c11_named = any("c11" in r for r in self.result.reasons)
        self.assertTrue(c11_named, self.result.reasons)


if __name__ == "__main__":
    unittest.main()
