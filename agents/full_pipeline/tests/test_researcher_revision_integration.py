"""Test 20 from the Phase 7F task: full-pipeline integration with
agents/researcher/'s Autonomous Revision Mode. Proves the orchestrator
recognizes a FACT_CHECK-level REVISION_REQUIRED, invokes the revision
engine, re-runs content review, and continues only if the resulting state
is genuinely clean — never continuing downstream with an unresolved
factual issue.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ...orchestrator.tests.builders import write_claim, write_content_item, write_research, write_script
from ..src.models import CONTENT_APPROVAL_GATE, CONTENT_REVIEW
from ..src.pipeline import run_full_pipeline
from .builders import simulate_human_approval


def _write_second_source(root: Path) -> None:
    (root / "research" / "02-source-b.md").write_text(
        """# Research Entry: Fixture Source B (test)

| Field | Value |
|---|---|
| Content ID | `test-item` |
| Source | Fixture Source B |
| Source type | `SECONDARY` |
| Source URL / reference | https://example.invalid/fixture-source-b |
| Publication date | unknown |
| Retrieved date | 2026-09-02 |
| Source reliability | `HIGH` (fixture) |

## Relevant evidence

Fixture evidence text B.

## Related claims

`c2`

## Conflicting evidence

None found.

## Researcher notes

Fixture only.
""",
        encoding="utf-8",
    )


class FullPipelineRevisionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.root.mkdir(parents=True)

    def _write_fixable_two_claim_item(self) -> None:
        write_content_item(self.root)
        write_research(self.root, related_claims="`c1`")
        _write_second_source(self.root)
        # c1 is Case A fixable: no Supporting sources cited yet, but
        # research/01-source.md already, reciprocally names it.
        write_claim(self.root, "c1", supporting_sources="`N/A`")
        write_claim(
            self.root, "c2", exact_claim="A second, independently checkable fixture fact.",
            supporting_sources="`research/02-source-b.md`",
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

    def test_full_pipeline_resolves_fact_check_via_revision_and_proceeds(self):
        self._write_fixable_two_claim_item()
        result = run_full_pipeline(self.root, apply=True)

        self.assertEqual(result.pipeline_status, "PASS")
        self.assertIn(CONTENT_REVIEW, result.completed_stages)
        self.assertIn(CONTENT_APPROVAL_GATE, result.blocked_stages)  # not yet APPROVED — expected

        # Fact-check genuinely reached PASS via a real successor claim,
        # not by skipping or fabricating anything.
        self.assertTrue((self.root / "claims" / "c1_rev1.md").is_file())
        self.assertTrue((self.root / "revisions").is_dir())
        reviews = sorted((self.root / "reviews").glob("fact_checker-*.md"))
        self.assertEqual(len(reviews), 2)

        # Safety and originality genuinely ran (never skipped) once
        # fact-check cleared.
        self.assertTrue((self.root / "reviews" / "safety_reviewer-1.md").is_file())
        self.assertTrue((self.root / "reviews" / "originality_reviewer-1.md").is_file())

        # SCRIPT.md is never touched by any part of this — the human
        # approval gate is the true reason production hasn't started yet.
        self.assertIn("`c1`", (self.root / "SCRIPT.md").read_text(encoding="utf-8"))

    def test_full_pipeline_proceeds_into_production_after_simulated_human_approval(self):
        self._write_fixable_two_claim_item()
        run_full_pipeline(self.root, apply=True)
        simulate_human_approval(self.root)

        result = run_full_pipeline(self.root, apply=True)
        # This fixture's claims are FACT-classified, so their scenes
        # default to the RETRIEVED asset strategy — which, per Phase 7D's
        # own documented, honest "Known limitation: RETRIEVED strategy"
        # (agents/production_qa/CONTRACT.md), can never fully pass
        # Production QA this phase (no real retrieval integration
        # exists). That is a real, separate, already-established gate —
        # this test's own point is that fact-check's revision-fixed PASS
        # correctly carries all the way through PRODUCTION_QA (the very
        # last stage) without being blocked anywhere in between by the
        # issue this phase's revision engine actually fixed.
        self.assertEqual(result.pipeline_status, "REVISION_REQUIRED")
        self.assertEqual(result.current_stage, "PRODUCTION_QA")
        for stage in (
            "PRODUCER", "VOICE", "VISUAL_PLANNER", "ASSETS", "ASSEMBLER", "CAPTIONS", "THUMBNAIL",
        ):
            self.assertIn(stage, result.completed_stages)
        # Never approves or publishes anything on its own, and Production
        # status never falsely advances past METADATA.
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `METADATA` |", production_text)
        self.assertNotIn("| Production status | `HUMAN_REVIEW` |", production_text)

    def test_revision_alone_never_bypasses_safety_or_originality(self):
        # A safety-escalating beat alongside a fixable fact-check issue —
        # revision must never make the pipeline continue past a genuine
        # safety problem.
        write_content_item(self.root)
        write_research(self.root, related_claims="`c1`")
        write_claim(self.root, "c1", supporting_sources="`N/A`")
        write_script(
            self.root,
            beats=[
                "1. A beat where the narrator pretends to be Jane Smith throughout. — claims: `c1`"
            ],
        )
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "ESCALATE_TO_HUMAN")
        self.assertFalse((self.root / "PRODUCTION.md").exists())


if __name__ == "__main__":
    unittest.main()
