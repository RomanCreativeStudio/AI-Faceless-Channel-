"""Integration test (task Step 18): an isolated APPROVED test fixture
flows through the full pipeline. Verifies scene references, visual
requirements, and claim references are all preserved; asset strategies
are created with explicit authenticity/provenance; generated placeholder
artifacts are clearly labeled; no protected content changes; no
publishing capability. Also verifies Producer -> Voice -> Visual Planner
-> Asset Agent, checking Voice's and the Asset agent's outputs remain
independent and neither overwrites the other. The real golden sample is
never used for mutation here.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item, write_claim
from ...visual_planner.src.pipeline import run_visual_planner
from ...voice.src.pipeline import run_voice_generation
from ..src.models import AssetStrategy, HistoricalAuthenticity
from ..src.pipeline import run_asset_generation
from .builders import build_full_pipeline_item


class AssetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_approved_content_through_producer_visual_planner_to_assets(self):
        build_minimal_item(
            self.root,
            hook="An approved opening hook for this fixture.",
            beats=[
                "1. A factual first beat. — claims: `c1`",
                "2. A hypothetical second beat. — claims: `c4`",
            ],
        )
        write_claim(self.root, "c4", classification="ASSUMPTION")

        producer_result = run_producer(self.root, apply=True)
        self.assertTrue(producer_result.produced)
        planner_result = run_visual_planner(self.root, apply=True)
        self.assertTrue(planner_result.planned)
        asset_result = run_asset_generation(self.root, apply=True)
        self.assertTrue(asset_result.produced)

        # Scene references / visual requirements / claim references all preserved.
        for plan in asset_result.plans:
            scene_text = (self.root / "scenes" / plan.scene.filename).read_text(encoding="utf-8")
            self.assertIn(plan.scene.scene_id, scene_text)
            asset_text = (self.root / "assets" / plan.filename).read_text(encoding="utf-8")
            self.assertIn(f"scenes/{plan.scene.filename}", asset_text)
            for claim_id in plan.scene.claim_ids:
                self.assertIn(f"`{claim_id}`", scene_text)

        # Strategies created; authenticity/provenance explicit.
        strategies = {p.filename: p.strategy for p in asset_result.plans}
        authenticities = {p.filename: p.authenticity for p in asset_result.plans}
        self.assertIn(AssetStrategy.RETRIEVED, strategies.values())
        self.assertIn(AssetStrategy.GENERATED, strategies.values())
        self.assertIn(HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA, authenticities.values())
        self.assertIn(HistoricalAuthenticity.GENERATED_RECONSTRUCTION, authenticities.values())
        for plan in asset_result.plans:
            self.assertTrue(plan.authenticity)
            self.assertTrue(plan.basis)

        # Generated placeholder artifacts clearly labeled.
        for plan in asset_result.plans:
            if plan.strategy is AssetStrategy.GENERATED:
                artifact_text = (self.root / "assets" / plan.artifact_filename).read_text(encoding="utf-8")
                self.assertIn("TEST / PLACEHOLDER GENERATED ASSET", artifact_text)

        # No protected content changed.
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)
        claims_after = {p.name for p in (self.root / "claims").glob("*.md")}
        self.assertEqual(claims_after, {"c1.md", "c4.md"})

        # No publishing capability: PRODUCTION.md never reaches a
        # publish-capable state as a side effect of this pipeline.
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertNotIn("PUBLISHED", production_text)

    def test_voice_and_assets_are_independent_and_do_not_overwrite_each_other(self):
        build_full_pipeline_item(
            self.root,
            beats=["1. A factual beat. — claims: `c1`"],
        )
        voice_before = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        production_after_voice = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Voice record | `voice/voice-01.md` |", production_after_voice)

        asset_result = run_asset_generation(self.root, apply=True)
        self.assertTrue(asset_result.produced)

        voice_after = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        self.assertEqual(voice_before, voice_after)

        production_after_assets = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        # Voice's rollup line survives the Asset agent's own rollup update.
        self.assertIn("| Voice record | `voice/voice-01.md` |", production_after_assets)
        self.assertIn("| Production status | `ASSEMBLY` |", production_after_assets)

        # Independent namespaces: neither wrote into the other's files.
        self.assertFalse((self.root / "voice" / "asset-01.md").exists())
        self.assertFalse((self.root / "assets" / "voice-01.md").exists())


if __name__ == "__main__":
    unittest.main()
