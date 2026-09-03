"""Tests 4, 5, 6, 12, 13: each of the three asset strategies works;
GENERATED placeholders explicitly identify themselves as generated,
never as real media; RETRIEVED placeholders never invent a source.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.models import AssetStrategy
from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item


class StrategyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _plan_for(self, filename: str, result):
        matches = [p for p in result.plans if p.filename == filename]
        self.assertEqual(len(matches), 1, f"expected exactly one plan for {filename}")
        return matches[0]

    # --- Test 4: GENERATED strategy works ---
    def test_generated_strategy_works(self):
        build_visual_planned_item(
            self.root,
            beats=["1. A speculative beat. — claims: `c9`"],
            extra_claims=[("c9", "SPECULATION")],
        )
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.strategy, AssetStrategy.GENERATED)
        self.assertTrue(plan.artifact_filename)
        artifact_path = self.root / "assets" / plan.artifact_filename
        self.assertTrue(artifact_path.is_file())

    # --- Test 5: RETRIEVED strategy produces a structured retrieval requirement ---
    def test_retrieved_strategy_produces_structured_requirement(self):
        build_visual_planned_item(self.root)  # default: c1 FACT beat -> AUTHENTIC
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.strategy, AssetStrategy.RETRIEVED)
        self.assertEqual(plan.artifact_filename, "")
        self.assertIn("No external retrieval provider is integrated yet", plan.verification_notes)

    # --- Test 6: HUMAN_PROVIDED strategy works ---
    def test_human_provided_strategy_works(self):
        build_visual_planned_item(self.root)
        result = run_asset_generation(
            self.root, apply=True,
            human_provided={"scene-02.md": {"source": "family archive photograph, 1928"}},
        )
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.strategy, AssetStrategy.HUMAN_PROVIDED)
        self.assertEqual(plan.verification_status, "NOT_STARTED")
        self.assertIn("family archive photograph", plan.source)

    # --- Test 12: generated placeholder explicitly identifies itself as generated ---
    def test_generated_placeholder_is_explicitly_labeled(self):
        build_visual_planned_item(
            self.root,
            beats=["1. A speculative beat. — claims: `c9`"],
            extra_claims=[("c9", "SPECULATION")],
        )
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        artifact_text = (self.root / "assets" / plan.artifact_filename).read_text(encoding="utf-8")
        self.assertIn("TEST / PLACEHOLDER GENERATED ASSET", artifact_text)
        self.assertIn("this is NOT an actual image, video, or audio file", artifact_text)

        asset_text = (self.root / "assets" / plan.filename).read_text(encoding="utf-8")
        self.assertIn("TEST / PLACEHOLDER GENERATED ASSET", asset_text)

    # --- Test 13: retrieval placeholder never invents a source ---
    def test_retrieval_placeholder_never_invents_a_source(self):
        build_visual_planned_item(self.root)
        result = run_asset_generation(self.root, apply=True)
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.source, "not yet sourced")
        self.assertNotIn("http://", plan.verification_notes)
        self.assertNotIn("https://", plan.verification_notes)

        asset_text = (self.root / "assets" / plan.filename).read_text(encoding="utf-8")
        self.assertNotIn("http://", asset_text)
        self.assertNotIn("https://", asset_text)
        self.assertIn("not yet sourced", asset_text)


if __name__ == "__main__":
    unittest.main()
