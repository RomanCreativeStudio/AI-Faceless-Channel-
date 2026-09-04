"""Phase 7G full-pipeline integration test: Bounded Research Mode flows
transparently through run_full_pipeline() with no change to its own
control flow (see agents/researcher/src/revision.py's
run_autonomous_revision, which agents/full_pipeline/'s own
_attempt_researcher_revision already calls unmodified) — the only change
needed here was threading an optional `research_provider` parameter
through so a test (or a future real deployment) can supply one.

Proves: a claim with genuinely zero research on disk (Case C) still
reaches CONTENT_REVIEW = PASS via bounded research when a provider
actually supports it, SAFETY_REVIEW/ORIGINALITY_REVIEW still run only
after that, and the human approval gate is still the only reason
production hasn't started.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ...orchestrator.tests.builders import write_claim, write_content_item, write_research, write_script
from ...researcher.src.test_research_provider import LocalTestResearchProvider, strong_support_result
from ..src.models import CONTENT_APPROVAL_GATE, CONTENT_REVIEW
from ..src.pipeline import run_full_pipeline


class BoundedResearchFullPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.root.mkdir(parents=True)

    def _write_evidence_free_item(self) -> None:
        write_content_item(self.root)
        # c1 has zero evidence anywhere on disk — Case C, the one
        # precondition Bounded Research Mode's extension exists for.
        write_claim(self.root, "c1", supporting_sources="`N/A`")
        # c2 already has its own, different, existing source — kept
        # deliberately separate from c1 so ORIGINALITY_REVIEW's unrelated
        # source-diversity heuristic doesn't trip on a single-source
        # concern (mirrors test_researcher_revision_integration.py's own
        # established two-claim pattern).
        write_research(self.root, related_claims="`c2`")
        write_claim(
            self.root, "c2", exact_claim="A second, independently checkable fixture fact.",
            supporting_sources="`research/01-source.md`",
        )
        write_script(
            self.root,
            beats=[
                "1. Why the old delivery routes cost so much, and how rerouting "
                "changed the math. — claims: `c1`, `c2`"
            ],
            verified_claims_rows=[
                "| `c1` | `FACT` | `UNVERIFIED` | 1 |", "| `c2` | `FACT` | `UNVERIFIED` | 1 |",
            ],
        )

    def test_full_pipeline_resolves_fact_check_via_bounded_research_and_proceeds(self):
        self._write_evidence_free_item()
        provider = LocalTestResearchProvider({"c1": [strong_support_result("c1")]})

        result = run_full_pipeline(self.root, apply=True, research_provider=provider)

        self.assertEqual(result.pipeline_status, "PASS")
        self.assertIn(CONTENT_REVIEW, result.completed_stages)
        self.assertIn(CONTENT_APPROVAL_GATE, result.blocked_stages)

        # A real research record and a real successor claim were created —
        # never fabricated, never skipped. (research/01-source.md is c2's
        # pre-existing source; bounded research adds one more for c1.)
        research_files = sorted((self.root / "research").glob("*.md"))
        self.assertEqual(len(research_files), 2)
        self.assertTrue((self.root / "claims" / "c1_rev1.md").is_file())

        # Safety and originality only ever ran once fact-check genuinely
        # cleared — never skipped, never run against an unresolved claim.
        self.assertTrue((self.root / "reviews" / "safety_reviewer-1.md").is_file())
        self.assertTrue((self.root / "reviews" / "originality_reviewer-1.md").is_file())

        # SCRIPT.md is untouched — the human approval gate, not this
        # engine, is the reason production hasn't started.
        self.assertIn("`c1`", (self.root / "SCRIPT.md").read_text(encoding="utf-8"))
        self.assertNotIn("c1_rev1", (self.root / "SCRIPT.md").read_text(encoding="utf-8"))

    def test_full_pipeline_still_escalates_when_bounded_research_finds_nothing(self):
        self._write_evidence_free_item()
        # No research_provider supplied — defaults to the local test
        # provider with no fixture data for c1, so bounded research finds
        # nothing and the pipeline still correctly stops for a human,
        # never continuing into production with an unresolved fact.
        result = run_full_pipeline(self.root, apply=True)

        self.assertEqual(result.pipeline_status, "REVISION_REQUIRED")
        self.assertTrue(result.human_action_required)
        self.assertFalse((self.root / "PRODUCTION.md").exists())
        self.assertFalse((self.root / "reviews" / "safety_reviewer-1.md").exists())


if __name__ == "__main__":
    unittest.main()
