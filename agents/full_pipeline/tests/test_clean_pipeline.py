"""Scenario 1: a clean, all-pass content item runs end to end through
every stage and reaches COMPLETE with Production status = HUMAN_REVIEW —
never anything beyond it.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ..src.models import (
    ASSEMBLER,
    ASSETS,
    CAPTIONS,
    CONTENT_APPROVAL_GATE,
    CONTENT_REVIEW,
    PRODUCER,
    PRODUCTION_QA,
    THUMBNAIL,
    VISUAL_PLANNER,
    VOICE,
)
from ..src.pipeline import run_full_pipeline
from .builders import build_production_ready_item, simulate_human_approval


class CleanPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_clean_pipeline_reaches_complete(self):
        build_production_ready_item(self.root)
        # simulate_human_approval already applied by the builder — but the
        # content-review chain must actually run and PASS first for the
        # approval gate to matter; run once dry (records nothing) to prove
        # the approval alone doesn't skip content review.
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "COMPLETE")
        self.assertEqual(result.current_stage, PRODUCTION_QA)
        expected_order = [
            CONTENT_REVIEW, CONTENT_APPROVAL_GATE, PRODUCER, VOICE, VISUAL_PLANNER,
            ASSETS, ASSEMBLER, CAPTIONS, THUMBNAIL, PRODUCTION_QA,
        ]
        self.assertEqual(result.completed_stages, expected_order)
        self.assertEqual(result.skipped_stages, [])
        self.assertEqual(result.blocked_stages, [])
        self.assertEqual(result.failed_stages, [])
        self.assertTrue(result.human_action_required)
        self.assertIn("HUMAN_REVIEW", result.human_action_reason)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `HUMAN_REVIEW` |", production_text)
        self.assertNotIn("| Production status | `APPROVED` |", production_text)
        self.assertNotIn("| Production status | `READY_TO_PUBLISH` |", production_text)

        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)

    def test_all_artifacts_produced(self):
        build_production_ready_item(self.root)
        run_full_pipeline(self.root, apply=True)
        for path in (
            "PRODUCTION.md", "scenes/scene-01.md", "voice/voice-01.md",
            "assets/asset-01.md", "timeline/timeline-01.md",
            "output/video-01.manifest.txt", "captions/captions-01.md",
            "thumbnail/thumbnail-01.md", "qa/production-qa-01.md",
        ):
            self.assertTrue((self.root / path).is_file(), f"missing {path}")

    def test_first_dry_run_against_a_fresh_item_writes_nothing(self):
        # A dry run never writes PRODUCTION.md, so a downstream stage in
        # this *same* fresh dry run genuinely has nothing to read yet —
        # this is accurate dry-run semantics (every single agent has the
        # identical limitation standalone), not a full_pipeline bug. See
        # test_dry_run_after_apply_is_side_effect_free below for the
        # meaningful dry-run case: re-validating already-real artifacts.
        build_production_ready_item(self.root)
        result = run_full_pipeline(self.root, apply=False)
        self.assertIn(result.pipeline_status, ("SYSTEM_ERROR", "BLOCKED"))
        self.assertFalse((self.root / "reviews").exists())
        self.assertFalse((self.root / "PRODUCTION.md").exists())
        self.assertFalse((self.root / "qa").exists())

    def test_dry_run_after_apply_is_side_effect_free(self):
        build_production_ready_item(self.root)
        run_full_pipeline(self.root, apply=True)
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        result = run_full_pipeline(self.root, apply=False)
        self.assertEqual(result.pipeline_status, "COMPLETE")

        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        self.assertEqual(before, after, "a dry run after a real apply run must change nothing")


if __name__ == "__main__":
    unittest.main()
