"""Tests 19-24: the Visual Safety Rule. Every representational scene gets
an explicit, unambiguous Historical authenticity classification; a scene
whose claims are entirely FACT is classified AUTHENTIC_HISTORICAL_MEDIA
(as sourcing intent only); a scene with any ASSUMPTION/INFERENCE/
SPECULATION claim is classified GENERATED_RECONSTRUCTION unconditionally,
covering both an "assumption" what-if scenario and an outright
SPECULATION claim; a scene with no claim references (a modern
infographic/framing scene) is NOT_APPLICABLE; a scene whose claim
provenance has gone missing blocks with a revision-required reason rather
than guessing.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.models import HistoricalAuthenticity
from ..src.pipeline import run_visual_planner
from .builders import build_produced_item


class AuthenticityClassificationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _plan_for(self, filename: str, result):
        matches = [p for p in result.plans if p.scene.filename == filename]
        self.assertEqual(len(matches), 1, f"expected exactly one plan for {filename}")
        return matches[0]

    # --- Test 19: every representational scene gets an explicit classification ---
    def test_every_scene_has_an_explicit_unambiguous_classification(self):
        build_produced_item(
            self.root,
            beats=[
                "1. A factual beat. — claims: `c1`",
                "2. A speculative beat. — claims: `c9`",
            ],
            extra_claims=[("c9", "SPECULATION")],
        )
        result = run_visual_planner(self.root, apply=True)
        self.assertTrue(result.planned)
        for plan in result.plans:
            self.assertIsInstance(plan.authenticity, HistoricalAuthenticity)
            self.assertTrue(plan.basis)

    # --- Test 20: ASSUMPTION claim -> GENERATED_RECONSTRUCTION ---
    def test_assumption_claim_forces_generated_reconstruction(self):
        build_produced_item(
            self.root,
            beats=["1. A what-if beat. — claims: `c1`, `c4`"],
            extra_claims=[("c4", "ASSUMPTION")],
        )
        result = run_visual_planner(self.root, apply=True)
        plan = self._plan_for("scene-02.md", result)
        self.assertEqual(plan.visual_type, "GENERATED_RECONSTRUCTION")
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.GENERATED_RECONSTRUCTION)

    # --- Test 21: all-FACT claims -> AUTHENTIC_HISTORICAL_MEDIA (intent only) ---
    def test_all_fact_claims_classified_authentic_historical_media(self):
        build_produced_item(self.root, beats=["1. A purely factual beat. — claims: `c1`"])
        result = run_visual_planner(self.root, apply=True)
        plan = self._plan_for("scene-02.md", result)
        self.assertEqual(plan.visual_type, "ARCHIVAL_IMAGE")
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA)

        asset_text = (self.root / "assets" / plan.asset_filename).read_text(encoding="utf-8")
        self.assertIn("`NOT_STARTED`", asset_text)
        self.assertIn("sourcing intent only", asset_text.replace("\n", " "))

    # --- Test 22: no claim references (modern infographic/framing) -> NOT_APPLICABLE ---
    def test_scene_with_no_claims_is_not_applicable(self):
        build_produced_item(self.root, hook="An ordinary framing hook with no claims.")
        result = run_visual_planner(self.root, apply=True)
        hook_plan = self._plan_for("scene-01.md", result)
        self.assertEqual(hook_plan.visual_type, "ON_SCREEN_TEXT_GRAPHIC")
        self.assertEqual(hook_plan.authenticity, HistoricalAuthenticity.NOT_APPLICABLE)
        self.assertFalse(hook_plan.needs_asset)

    # --- Test 23: SPECULATION ("what if"/alternate-history) claim -> GENERATED_RECONSTRUCTION ---
    def test_speculation_claim_forces_generated_reconstruction(self):
        build_produced_item(
            self.root,
            beats=["1. A speculative beat. — claims: `c1`, `c9`"],
            extra_claims=[("c9", "SPECULATION")],
        )
        result = run_visual_planner(self.root, apply=True)
        plan = self._plan_for("scene-02.md", result)
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.GENERATED_RECONSTRUCTION)
        self.assertNotEqual(plan.authenticity, HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA)

    # --- Defense-in-depth: CONTENT_ITEM.md status must be APPROVED too ---
    def test_blocks_when_content_item_status_is_not_approved(self):
        from ...producer.tests.builders import write_content_item

        build_produced_item(self.root, beats=["1. A factual beat. — claims: `c1`"])
        # Simulate a PRODUCTION.md that exists (e.g. a hand-built schema
        # fixture, like the real golden sample) while CONTENT_ITEM.md was
        # never actually approved — the Production-status-only precondition
        # would otherwise let this through via the Phase 7B interim
        # allowance.
        write_content_item(self.root, content_id="test-item", status="SCRIPT")

        result = run_visual_planner(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertFalse(result.planned)
        self.assertFalse((self.root / "assets").exists())

    # --- Test 24: missing claim provenance -> blocked / revision required ---
    def test_missing_claim_provenance_blocks_rather_than_guesses(self):
        build_produced_item(self.root, beats=["1. A beat citing c1. — claims: `c1`"])
        (self.root / "claims" / "c1.md").unlink()

        result = run_visual_planner(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("c1", result.blocked_reason)
        self.assertFalse(result.planned)
        # No scene or asset was touched — the whole run refused.
        scene_text = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")
        self.assertIn("`NOT_YET_PLANNED`", scene_text)
        self.assertFalse((self.root / "assets").exists())


if __name__ == "__main__":
    unittest.main()
