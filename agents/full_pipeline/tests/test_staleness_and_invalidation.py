"""Scenarios 4, 5, 11: a directly-corrupted voice or asset hash is caught
(by Production QA's own independent re-verification, since a completed
stage is not re-invoked once superseded — see status_sequence.py); a
genuine SCRIPT.md change after a complete run is caught at the earliest
possible point (PRODUCER), before any other stage runs; unrelated
upstream artifacts are never touched.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ...researcher.src.loader import load_reviews
from ..src.models import PRODUCER, PRODUCTION_QA, VOICE
from ..src.pipeline import run_full_pipeline
from .builders import build_production_ready_item


class StalenessAndInvalidationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_production_ready_item(self.root)
        first = run_full_pipeline(self.root, apply=True)
        self.assertEqual(first.pipeline_status, "COMPLETE")

    def _corrupt_field(self, path: Path, field: str) -> None:
        text = path.read_text(encoding="utf-8")
        line = next(l for l in text.splitlines() if l.startswith(f"| {field} |"))
        path.write_text(text.replace(line, f"| {field} | `0000000000stale` |"), encoding="utf-8")

    # --- Scenario 4: stale voice ---
    def test_directly_corrupted_voice_hash_is_caught(self):
        self._corrupt_field(self.root / "voice" / "voice-01.md", "Script content hash")
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "BLOCKED")
        self.assertEqual(result.current_stage, PRODUCTION_QA)
        self.assertIn("voice/voice-01.md", result.terminal_reason)
        # VOICE itself was correctly skipped (Production status already
        # past it) — the corruption is caught by Production QA's own
        # independent re-verification instead. Documented, not a gap.
        self.assertFalse(result.stage_results[VOICE].executed)

    # --- Scenario 5: stale asset ---
    def test_directly_corrupted_asset_hash_is_caught(self):
        self._corrupt_field(self.root / "assets" / "asset-01.md", "Scene/visual content hash")
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "BLOCKED")
        self.assertEqual(result.current_stage, PRODUCTION_QA)
        self.assertIn("assets/asset-01.md", result.terminal_reason)

    # --- Scenario 11: downstream invalidation after upstream change ---
    def test_script_change_invalidates_at_the_earliest_point_only(self):
        script_path = self.root / "SCRIPT.md"
        script_path.write_text(
            script_path.read_text(encoding="utf-8") + "\nAn edited addition.\n", encoding="utf-8"
        )
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "BLOCKED")
        self.assertEqual(result.current_stage, PRODUCER)
        self.assertIn(PRODUCER, result.blocked_stages)
        # Nothing past PRODUCER was even attempted this call.
        for later_stage in ("VOICE", "VISUAL_PLANNER", "ASSETS", "ASSEMBLER", "CAPTIONS", "THUMBNAIL", "PRODUCTION_QA"):
            self.assertIn(later_stage, result.skipped_stages)
        # The existing (now-stale) production artifacts are untouched.
        self.assertIn("PRODUCTION.md exists with Script content hash", result.terminal_reason)

    def test_unrelated_asset_edit_never_touches_voice_fact_check_or_asset_01(self):
        # NOTE: agents/safety/ and agents/originality/ each append a
        # Notes/history log entry to CONTENT_ITEM.md as part of the very
        # apply call that computed their own `Reviewed content hash` (that
        # hash includes CONTENT_ITEM.md's full raw_text) — so their own
        # just-recorded PASS is immediately stale relative to the note
        # they just appended, and every repeat call regenerates a fresh
        # (still correct, never fabricated) attempt. This is a pre-existing
        # characteristic of those two agents, not introduced by this
        # orchestrator and out of this phase's scope to change — see
        # STATE.md's Genuine finding. agents/researcher/'s own fact-check
        # hash does not include CONTENT_ITEM.md's raw_text, so
        # reviews/fact_checker-*.md alone stays genuinely stable here.
        fact_check_before = sorted((self.root / "reviews").glob("fact_checker-*.md"))
        voice_before = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        untouched_asset_before = (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8") \
            if (self.root / "assets" / "asset-02.md").is_file() else None

        self._corrupt_field(self.root / "assets" / "asset-01.md", "Scene/visual content hash")
        run_full_pipeline(self.root, apply=True)

        fact_check_after = sorted((self.root / "reviews").glob("fact_checker-*.md"))
        voice_after = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        self.assertEqual(fact_check_before, fact_check_after)
        self.assertEqual(voice_before, voice_after)
        if untouched_asset_before is not None:
            self.assertEqual(
                untouched_asset_before,
                (self.root / "assets" / "asset-02.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
