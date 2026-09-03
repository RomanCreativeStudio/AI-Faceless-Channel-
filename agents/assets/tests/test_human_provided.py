"""Test 11: a HUMAN_PROVIDED asset with unknown/no stated provenance
must never automatically become authentic — it is flagged
REVIEW_REQUIRED rather than silently trusted.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.models import HistoricalAuthenticity
from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item


class HumanProvidedProvenanceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_visual_planned_item(self.root)  # default: c1 FACT beat -> asset-02.md

    def _plan_for(self, filename: str, result):
        matches = [p for p in result.plans if p.filename == filename]
        self.assertEqual(len(matches), 1)
        return matches[0]

    # --- Test 11: unknown human-provided provenance -> REVIEW_REQUIRED ---
    def test_no_stated_source_becomes_review_required(self):
        result = run_asset_generation(
            self.root, apply=True, human_provided={"scene-02.md": {}},
        )
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.verification_status, "REVIEW_REQUIRED")

    def test_explicit_unknown_source_becomes_review_required(self):
        result = run_asset_generation(
            self.root, apply=True,
            human_provided={"scene-02.md": {"source": "unknown"}},
        )
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.verification_status, "REVIEW_REQUIRED")

    def test_review_required_does_not_change_authenticity_field(self):
        # Authenticity is always derived from claim data, never from
        # strategy/provenance — see CONTRACT.md's Authenticity classification.
        result = run_asset_generation(
            self.root, apply=True, human_provided={"scene-02.md": {}},
        )
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.authenticity, HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA)
        self.assertEqual(plan.verification_status, "REVIEW_REQUIRED")

        asset_text = (self.root / "assets" / plan.filename).read_text(encoding="utf-8")
        self.assertIn("`REVIEW_REQUIRED`", asset_text)
        self.assertIn("`AUTHENTIC_HISTORICAL_MEDIA`", asset_text)

    def test_credible_source_does_not_require_review(self):
        result = run_asset_generation(
            self.root, apply=True,
            human_provided={"scene-02.md": {"source": "family archive photograph, 1928"}},
        )
        plan = self._plan_for("asset-02.md", result)
        self.assertEqual(plan.verification_status, "NOT_STARTED")


if __name__ == "__main__":
    unittest.main()
