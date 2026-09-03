"""Scenarios 2, 3, 9: a safety-escalating beat, an originality-escalating
hook, and general human escalation all stop the pipeline before any
production stage runs, reported as ESCALATE_TO_HUMAN.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ...orchestrator.tests.builders import write_claim, write_content_item, write_research, write_script
from ...originality.src.models import ChannelItemSummary
from ..src.models import CONTENT_REVIEW
from ..src.pipeline import run_full_pipeline


class ContentReviewEscalationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Scenario 2: safety escalation (impersonation is HIGH_RISK, escalates) ---
    def test_safety_escalation_stops_before_production(self):
        self.root.mkdir(parents=True)
        write_content_item(self.root)
        write_research(self.root)
        write_claim(self.root, "c1")
        write_script(
            self.root,
            beats=["1. A beat where the narrator pretends to be Jane Smith throughout. — claims: `c1`"],
        )
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "ESCALATE_TO_HUMAN")
        self.assertEqual(result.completed_stages, [])
        self.assertIn("PRODUCER", result.skipped_stages)
        self.assertIn(CONTENT_REVIEW, result.escalated_stages)
        self.assertTrue(result.human_action_required)
        # No production stage ever ran — nothing beyond CONTENT_REVIEW exists.
        self.assertFalse((self.root / "PRODUCTION.md").exists())

    # --- Scenario 3: originality escalation (ambiguous similarity -> REVIEW_REQUIRED, escalates) ---
    def test_originality_escalation_stops_before_production(self):
        self.root.mkdir(parents=True)
        write_content_item(
            self.root, title="How a Bakery Chain Expanded Its Supply Chain",
            premise="A bakery chain changed its flour supplier network and "
                    "saw uneven regional results across its stores.",
        )
        write_research(self.root)
        write_claim(self.root, "c1")
        write_script(self.root, beats=["1. An ordinary beat. — claims: `c1`"])
        sibling = ChannelItemSummary(
            content_id="bs-existing-similar",
            title="How a Bakery Chain Changed Its Supplier Network",
            premise="A different bakery reworked its ingredient sourcing "
                    "network and saw regional results vary afterward.",
            hook="Unrelated hook text here.",
        )
        result = run_full_pipeline(self.root, apply=True, originality_channel_index=[sibling])
        self.assertEqual(result.pipeline_status, "ESCALATE_TO_HUMAN")
        self.assertIn(CONTENT_REVIEW, result.escalated_stages)
        self.assertFalse((self.root / "PRODUCTION.md").exists())

    # --- Scenario 9: general human escalation surfaced clearly ---
    def test_escalation_names_the_blocking_stage_and_reason(self):
        self.root.mkdir(parents=True)
        write_content_item(self.root)
        write_research(self.root)
        write_claim(self.root, "c1")
        write_script(
            self.root,
            beats=["1. A beat explaining how to launder money in detail. — claims: `c1`"],
        )
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "ESCALATE_TO_HUMAN")
        self.assertTrue(result.human_action_required)
        self.assertTrue(result.human_action_reason)
        self.assertIn("CONTENT_REVIEW", result.human_action_reason)


if __name__ == "__main__":
    unittest.main()
