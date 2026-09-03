"""Tests 31-35: the full Producer -> Visual Planner handoff. An approved
script flows through both agents to a finalized visual plan; the
Producer's raw output is directly loadable by the Visual Planner; the
script content hash stays consistent across both agents' records; a
blocked/unproduced Producer run leaves nothing for the Visual Planner to
act on; the real golden sample (never APPROVED) is untouched by either
agent, end to end.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item
from ..src.pipeline import run_visual_planner

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ProducerToVisualPlannerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 31: approved script -> Producer -> Visual Planner ---
    def test_full_pipeline_approved_script_to_visual_plan(self):
        build_minimal_item(
            self.root,
            beats=[
                "1. A factual beat. — claims: `c1`",
                "2. A hypothetical beat. — claims: `c4`",
            ],
        )
        from ...producer.tests.builders import write_claim
        write_claim(self.root, "c4", classification="ASSUMPTION")

        producer_result = run_producer(self.root, apply=True)
        self.assertTrue(producer_result.produced)

        planner_result = run_visual_planner(self.root, apply=True)
        self.assertTrue(planner_result.planned)
        self.assertEqual(len(planner_result.plans), len(producer_result.scenes))

    # --- Test 32: Producer output is valid Visual Planner input ---
    def test_producer_output_is_directly_loadable_by_visual_planner(self):
        build_minimal_item(self.root)
        run_producer(self.root, apply=True)
        result = run_visual_planner(self.root, apply=False)
        self.assertFalse(result.aborted)
        self.assertFalse(result.blocked)
        self.assertTrue(result.plans)

    # --- Test 33: script hash consistent across both agents ---
    def test_script_hash_consistent_across_producer_and_visual_planner(self):
        build_minimal_item(self.root)
        producer_result = run_producer(self.root, apply=True)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn(f"`{producer_result.script_content_hash}`", production_text)

        # Visual Planner re-verifies this same hash internally; a clean
        # run (no blocked/stale result) proves it matched.
        planner_result = run_visual_planner(self.root, apply=True)
        self.assertFalse(planner_result.blocked)
        self.assertFalse(planner_result.aborted)

    # --- Test 34: a blocked Producer run prevents Visual Planner execution ---
    def test_blocked_producer_prevents_visual_planner_from_running(self):
        build_minimal_item(self.root, status="SCRIPT")  # not APPROVED
        producer_result = run_producer(self.root, apply=True)
        self.assertTrue(producer_result.blocked)
        self.assertFalse((self.root / "PRODUCTION.md").exists())

        planner_result = run_visual_planner(self.root, apply=True)
        self.assertTrue(planner_result.aborted)
        self.assertIn("PRODUCTION.md", planner_result.abort_reason)
        self.assertFalse(planner_result.planned)

    # --- Test 35: golden sample remains untouched end to end ---
    def test_golden_sample_untouched_by_full_pipeline(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}

        # Producer's own APPROVED gate reliably blocks before any write —
        # CONTENT_ITEM.md's status here is SCRIPT, never APPROVED — so
        # apply=True is safe to exercise directly (mirrors
        # agents/producer/tests/test_approval_gate.py).
        producer_result = run_producer(GOLDEN_SAMPLE, apply=True)
        self.assertTrue(producer_result.blocked)

        # The golden sample also carries a hand-built PRODUCTION.md
        # fixture (Phase 7A) whose status/hash legitimately satisfy the
        # Visual Planner's Phase 7B interim allowance — unlike the
        # Producer there is no gate here that's guaranteed to block, so
        # this deliberately only dry-runs (apply=False) rather than risk
        # actually mutating committed golden content. apply=True
        # correctness is already covered by the isolated-fixture tests in
        # test_claim_relationship_and_boundaries.py.
        run_visual_planner(GOLDEN_SAMPLE, apply=False)

        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertEqual(before, after, "golden sample must never be mutated by either agent")


if __name__ == "__main__":
    unittest.main()
