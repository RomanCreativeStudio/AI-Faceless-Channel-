"""Cross-cutting integration checks: the golden sample is never mutated by
any full pipeline run; later stages are never executed once an earlier
one blocks/escalates/errors; the CLI prints a well-formed JSON result.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ..src.models import PRODUCTION_STAGE_ORDER
from ..src.pipeline import run_full_pipeline
from .builders import build_fact_only_production_ready_item, build_production_ready_item

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_SAMPLE = REPO_ROOT / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"


class GoldenSampleTests(unittest.TestCase):
    def test_golden_sample_never_modified(self):
        # apply=False only — matching agents/orchestrator/tests/
        # test_integration.py's own convention exactly. CONTENT_REVIEW
        # (unlike the eight production stages) is legitimately allowed to
        # write against non-APPROVED content, so an apply=True run here
        # would genuinely create reviews/*.md and update the golden
        # sample's own Fact-check/Safety/Originality state fields — not a
        # bug, but not a golden-sample-safety test either. Dry run proves
        # the same zero-mutation guarantee without that risk.
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_full_pipeline(GOLDEN_SAMPLE, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertEqual(before, after, "golden sample must never be mutated by the full pipeline")
        # No *new* reviews/ directory was created this run. (PRODUCTION.md
        # already exists as the Phase 7A hand-built golden fixture — see
        # agents/README.md — so its mere presence is not itself a signal
        # of anything this test wrote.)
        self.assertFalse((GOLDEN_SAMPLE / "reviews").exists())
        # The golden sample's CONTENT_ITEM.md status is intentionally
        # never APPROVED, so it should never progress into production —
        # whatever CONTENT_REVIEW itself reports, the approval gate (or an
        # earlier system error) must be the true stopping point.
        self.assertNotEqual(result.pipeline_status, "COMPLETE")


class LaterStagesNotExecutedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_stages_after_the_blocking_one_are_never_executed(self):
        build_fact_only_production_ready_item(self.root)
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "REVISION_REQUIRED")
        # PRODUCTION_QA is the last stage in this fixture's real order —
        # confirm nothing claims to have executed after it (there is
        # nothing after it) and that every stage before it genuinely did.
        self.assertEqual(result.stage_results["PRODUCTION_QA"].executed, True)
        for stage in PRODUCTION_STAGE_ORDER[:-1]:
            self.assertIn(stage, result.completed_stages)

    def test_content_review_block_prevents_every_production_stage(self):
        from ...orchestrator.tests.builders import write_claim, write_content_item, write_script

        # No research exists anywhere -> genuinely Case C (insufficient
        # evidence per agents/researcher/CONTRACT.md's "Autonomous
        # Revision Mode"), unfixable by Phase 7F's revision engine too —
        # this test's point is that REVISION_REQUIRED correctly blocks
        # every production stage, not that nothing could ever fix it.
        self.root.mkdir(parents=True)
        write_content_item(self.root)
        write_claim(self.root, "c1", supporting_sources="`N/A`")
        write_script(self.root)

        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "REVISION_REQUIRED")
        for stage in PRODUCTION_STAGE_ORDER:
            self.assertIn(stage, result.skipped_stages)
            self.assertNotIn(stage, result.completed_stages)
        self.assertFalse((self.root / "PRODUCTION.md").exists())
        self.assertFalse((self.root / "scenes").exists())


class CLITests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_cli_prints_valid_json(self):
        build_production_ready_item(self.root)
        proc = subprocess.run(
            [sys.executable, "-m", "agents.full_pipeline.src", str(self.root), "--apply"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["pipeline_status"], "COMPLETE")
        self.assertIn("stages", payload)
        self.assertIn("PRODUCTION_QA", payload["stages"])

    def test_cli_dry_run_default_writes_nothing(self):
        build_production_ready_item(self.root)
        files_before = sorted(self.root.rglob("*"))
        proc = subprocess.run(
            [sys.executable, "-m", "agents.full_pipeline.src", str(self.root)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files_after = sorted(self.root.rglob("*"))
        self.assertEqual(files_before, files_after)


if __name__ == "__main__":
    unittest.main()
