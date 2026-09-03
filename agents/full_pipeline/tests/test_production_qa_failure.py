"""Scenario 6: Production QA failure. Every prior production stage passes
cleanly, but Production QA itself reports REVISION_REQUIRED — the
documented, honest RETRIEVED-strategy limitation (no real retrieval
integration exists this phase — see agents/production_qa/CONTRACT.md's
"Known limitation"), not a fabricated failure.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ..src.models import PRODUCTION_QA, THUMBNAIL
from ..src.pipeline import run_full_pipeline
from .builders import build_fact_only_production_ready_item


class ProductionQAFailureTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_retrieved_strategy_limitation_surfaces_as_revision_required(self):
        build_fact_only_production_ready_item(self.root)
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "REVISION_REQUIRED")
        self.assertEqual(result.current_stage, PRODUCTION_QA)
        self.assertEqual(result.failed_stages, [PRODUCTION_QA])
        self.assertIn(PRODUCTION_QA, result.revision_requests)
        self.assertTrue(
            any("retrieved asset" in r.lower() for r in result.revision_requests[PRODUCTION_QA])
        )
        self.assertTrue(result.human_action_required)
        # Every stage up to and including THUMBNAIL genuinely completed —
        # only Production QA's own independent re-check caught the issue.
        self.assertIn(THUMBNAIL, result.completed_stages)
        # Production status never advanced to HUMAN_REVIEW.
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `METADATA` |", production_text)
        self.assertNotIn("| Production status | `HUMAN_REVIEW` |", production_text)
        # A qa/production-qa-01.md record was still written (QA does not
        # silently fail — it produces a real, inspectable record).
        self.assertTrue((self.root / "qa" / "production-qa-01.md").is_file())
        qa_text = (self.root / "qa" / "production-qa-01.md").read_text(encoding="utf-8")
        self.assertIn("REVISION_REQUIRED", qa_text)


if __name__ == "__main__":
    unittest.main()
