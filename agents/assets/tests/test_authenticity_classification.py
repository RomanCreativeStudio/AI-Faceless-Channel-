"""Tests 7-10: AUTHENTIC_HISTORICAL_MEDIA, GENERATED_RECONSTRUCTION, and
NOT_APPLICABLE classifications all work; a What If?/hypothetical claim
forces GENERATED_RECONSTRUCTION unconditionally.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.models import HistoricalAuthenticity
from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item


class AuthenticityClassificationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _plan_for(self, filename: str, result):
        matches = [p for p in result.plans if p.filename == filename]
        self.assertEqual(len(matches), 1, f"expected exactly one plan for {filename}")
        return matches[0]

    # --- Test 7: AUTHENTIC_HISTORICAL_MEDIA classification works ---
    def test_all_fact_claims_classified_authentic_historical_media(self):
        build_visual_planned_item(self.root)  # default beat cites c1 (FACT)
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA)

    # --- Test 8: GENERATED_RECONSTRUCTION classification works ---
    def test_assumption_claim_forces_generated_reconstruction(self):
        build_visual_planned_item(
            self.root,
            beats=["1. A what-if beat. — claims: `c1`, `c4`"],
            extra_claims=[("c4", "ASSUMPTION")],
        )
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.GENERATED_RECONSTRUCTION)

    # --- Test 9: NOT_APPLICABLE classification works ---
    def test_scene_with_no_claims_is_not_applicable(self):
        build_visual_planned_item(self.root, hook="An ordinary framing hook with no claims.")
        result = run_asset_generation(self.root, apply=True)
        hook_plan = self._plan_for("asset-01.md", result)
        self.assertEqual(hook_plan.authenticity, HistoricalAuthenticity.NOT_APPLICABLE)

    # --- Test 10: What If? (SPECULATION) visual becomes GENERATED_RECONSTRUCTION ---
    def test_speculation_claim_forces_generated_reconstruction(self):
        build_visual_planned_item(
            self.root,
            beats=["1. A speculative what-if beat. — claims: `c1`, `c9`"],
            extra_claims=[("c9", "SPECULATION")],
        )
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.GENERATED_RECONSTRUCTION)
        self.assertNotEqual(plan.authenticity, HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA)

    def test_authenticity_never_left_ambiguous(self):
        build_visual_planned_item(
            self.root,
            beats=["1. A factual beat. — claims: `c1`", "2. A what-if beat. — claims: `c4`"],
            extra_claims=[("c4", "ASSUMPTION")],
        )
        result = run_asset_generation(self.root, apply=True)
        for plan in result.plans:
            self.assertIsInstance(plan.authenticity, HistoricalAuthenticity)
            self.assertTrue(plan.basis)


if __name__ == "__main__":
    unittest.main()
