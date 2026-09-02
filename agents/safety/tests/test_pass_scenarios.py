"""Tests 1-4 from the Phase 6 task: ordinary business/history/technology
content and a clearly-labeled What If? scenario should all PASS."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.models import RiskLevel
from ..src.pipeline import run_safety_review
from .builders import build_minimal_item, write_claim, write_script


class PassScenarioTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _assert_pass(self, result):
        self.assertFalse(result.aborted, result.abort_reason)
        self.assertFalse(result.blocked, result.blocked_reason)
        for e in result.signal_evaluations:
            self.assertIn(
                e.risk_level, (RiskLevel.LOW_RISK, RiskLevel.NOT_APPLICABLE),
                f"{e.signal.value} unexpectedly {e.risk_level.value}: {e.reason}",
            )
        self.assertEqual(result.verdict.value, "PASS")
        self.assertFalse(result.escalate_to_human)

    def test_ordinary_business_story_passes(self):
        build_minimal_item(
            self.root, pillar="business-stories",
            title="How a Small Bakery Chain Expanded Regionally",
        )
        self._assert_pass(run_safety_review(self.root, apply=False))

    def test_ordinary_history_story_passes(self):
        build_minimal_item(
            self.root, pillar="history",
            title="The Founding of the First Public Library",
        )
        self._assert_pass(run_safety_review(self.root, apply=False))

    def test_ordinary_technology_story_passes(self):
        build_minimal_item(
            self.root, pillar="technology",
            title="How Solid-State Drives Store Data",
        )
        self._assert_pass(run_safety_review(self.root, apply=False))

    def test_clearly_labeled_what_if_passes(self):
        from .builders import write_content_item
        self.root.mkdir(parents=True, exist_ok=True)
        write_content_item(
            self.root, pillar="what-if",
            title="What If the Printing Press Arrived 50 Years Earlier?",
        )
        write_claim(self.root, "c1", classification="FACT",
                    exact_claim="The printing press was introduced in Europe around 1440.")
        write_claim(self.root, "c2", classification="ASSUMPTION",
                    exact_claim="ASSUMPTION: this scenario moves that invention 50 years earlier.")
        write_claim(self.root, "c3", classification="INFERENCE",
                    exact_claim="INFERENCE: literacy could plausibly have spread somewhat sooner.")
        write_script(
            self.root,
            beats=[
                "1. Known baseline. — claims: `c1`",
                "2. The hypothetical. — claims: `c2`",
                "3. What might follow. — claims: `c3`",
            ],
            verified_claims_rows=[
                "| `c1` | `FACT` | `NOT_APPLICABLE` | 1 |",
                "| `c2` | `ASSUMPTION` | `NOT_APPLICABLE` | 2 |",
                "| `c3` | `INFERENCE` | `NOT_APPLICABLE` | 3 |",
            ],
            fact_hypothesis_section=(
                "- **KNOWN FACT** — The printing press's real introduction date (`c1`).\n"
                "- **ASSUMPTION** — Moved 50 years earlier (`c2`).\n"
                "- **INFERENCE** — Literacy could plausibly spread somewhat sooner (`c3`).\n"
                "- **SPECULATION** — N/A for this fixture."
            ),
        )
        self._assert_pass(run_safety_review(self.root, apply=False))


if __name__ == "__main__":
    unittest.main()
