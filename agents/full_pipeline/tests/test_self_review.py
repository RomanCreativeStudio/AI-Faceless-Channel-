"""Scenarios 7, 8: "autonomous revision" in this codebase means picking up
a fix applied out of band on a *later, separate* call — never an
in-process retry loop (see CONTRACT.md's "Self-review behavior" for why
no agent this phase can autonomously fix anything). Scenario 7:
re-invoking the pipeline after a human/operator fix resumes correctly.
Scenario 8: two consecutive REVISION_REQUIRED verdicts hit the underlying
agent's own two-consecutive-attempts limit and escalate to a human,
exactly as templates/REVIEW.md rule 5 already specifies.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ...researcher.src.loader import load_reviews
from ...orchestrator.tests.builders import write_claim, write_content_item, write_research, write_script
from ..src.models import CONTENT_REVIEW, MAX_STAGE_ATTEMPTS
from ..src.pipeline import run_full_pipeline
from .builders import build_production_ready_item, simulate_human_approval


class SelfReviewTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Scenario 7: a real out-of-band fix is picked up on the next call ---
    def test_pipeline_resumes_after_fix_applied_between_calls(self):
        # No research/claims/*.md evidence exists anywhere yet — this is
        # genuinely Case C (insufficient evidence per
        # agents/researcher/CONTRACT.md's "Autonomous Revision Mode"), so
        # Phase 7F's own revision engine correctly cannot fix it either
        # (see agents/orchestrator/tests/builders.build_fact_check_blocked_item,
        # the same shape). Only a real, later out-of-band fix — never
        # something either revision engine could have done itself — can
        # resolve it, which is exactly this test's point.
        self.root.mkdir(parents=True)
        write_content_item(self.root)
        # No supporting source, no research entry anywhere yet -> FACT_CHECK
        # returns REVISION_REQUIRED with nothing this phase can act on.
        write_claim(self.root, "c1", supporting_sources="`N/A`")
        write_script(self.root)

        first = run_full_pipeline(self.root, apply=True)
        self.assertEqual(first.pipeline_status, "REVISION_REQUIRED")
        self.assertEqual(first.current_stage, CONTENT_REVIEW)
        self.assertFalse((self.root / "PRODUCTION.md").exists())

        # A human/operator fixes the underlying issue out of band — adds
        # the real evidence and cites it — exactly what MAX_STAGE_ATTEMPTS=1
        # (never an in-process loop) requires: this orchestrator never
        # invents the fix itself.
        write_research(self.root)
        write_claim(self.root, "c1", supporting_sources="`research/01-source.md`")

        second = run_full_pipeline(self.root, apply=True)
        self.assertEqual(second.pipeline_status, "PASS")
        self.assertIn(CONTENT_REVIEW, second.completed_stages)

        # Fact-check now has two attempts on record — the first
        # REVISION_REQUIRED, the second (fixed) PASS — never overwritten.
        reviews = load_reviews(self.root / "reviews", "fact_checker")
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0].verdict.value, "REVISION_REQUIRED")
        self.assertEqual(reviews[1].verdict.value, "PASS")

    # --- Scenario 8: retry limit reached -> escalate ---
    def test_two_consecutive_revision_required_escalates(self):
        # No research exists anywhere -> genuinely Case C (insufficient
        # evidence), unfixable by Phase 7F's revision engine too — see
        # test_pipeline_resumes_after_fix_applied_between_calls above.
        self.root.mkdir(parents=True)
        write_content_item(self.root)
        write_claim(self.root, "c1", supporting_sources="`N/A`")
        write_script(self.root)

        first = run_full_pipeline(self.root, apply=True)
        self.assertEqual(first.pipeline_status, "REVISION_REQUIRED")

        # Nothing was actually fixed — a second call re-evaluates the
        # same unresolved issue, hitting FACT_CHECK's own
        # two-consecutive-REVISION_REQUIRED limit (templates/REVIEW.md
        # rule 5), surfaced by agents/orchestrator/ and never
        # reimplemented here.
        second = run_full_pipeline(self.root, apply=True)
        self.assertIn(second.pipeline_status, ("ESCALATE_TO_HUMAN", "REVISION_REQUIRED"))

        third = run_full_pipeline(self.root, apply=True)
        self.assertEqual(third.pipeline_status, "ESCALATE_TO_HUMAN")
        self.assertTrue(third.human_action_required)

        # No third autonomous attempt was ever created.
        reviews = load_reviews(self.root / "reviews", "fact_checker")
        self.assertLessEqual(len(reviews), 2)

    def test_max_stage_attempts_is_exactly_one_per_call(self):
        # Documents the constant directly — production stages never retry
        # in-process (see CONTRACT.md's "Self-review behavior").
        self.assertEqual(MAX_STAGE_ATTEMPTS, 1)

    def test_production_stage_revision_required_is_never_retried_in_process(self):
        from .builders import build_fact_only_production_ready_item

        build_fact_only_production_ready_item(self.root)
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "REVISION_REQUIRED")
        self.assertEqual(result.stage_results["PRODUCTION_QA"].attempt, 1)
        # A bare re-run with nothing fixed reports the identical outcome —
        # never silently converted into a PASS.
        again = run_full_pipeline(self.root, apply=True)
        self.assertEqual(again.pipeline_status, "REVISION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
