"""Tests 1-4 from the task: unique business/history/technology content
and a clearly-labeled What If? concept should all PASS."""
import tempfile
import unittest
from pathlib import Path

from ..src.models import RiskLevel
from ..src.pipeline import run_originality_review
from .builders import build_minimal_item, write_claim, write_content_item, write_script


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

    def test_unique_business_case_study_passes(self):
        build_minimal_item(
            self.root, pillar="business-stories",
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
        )
        self._assert_pass(run_originality_review(self.root, apply=False, channel_index=[]))

    def test_unique_historical_framing_passes(self):
        build_minimal_item(
            self.root, pillar="history",
            title="The Founding of the First Public Library",
            premise="Why a merchant's private book collection became the "
                    "template every public library still follows today.",
            hook="One merchant's argument with a city council reshaped how "
                 "the world shares books.",
        )
        self._assert_pass(run_originality_review(self.root, apply=False, channel_index=[]))

    def test_unique_technology_story_passes(self):
        build_minimal_item(
            self.root, pillar="technology",
            title="How Solid-State Drives Store Data",
            premise="The physics trade-off inside every SSD that explains "
                    "why they eventually wear out.",
            hook="Every SSD is quietly counting down to its own failure — "
                 "here's the trade-off that causes it.",
        )
        self._assert_pass(run_originality_review(self.root, apply=False, channel_index=[]))

    def test_clearly_labeled_what_if_passes(self):
        self.root.mkdir(parents=True, exist_ok=True)
        write_content_item(
            self.root, pillar="what-if",
            title="What If the Printing Press Arrived 50 Years Earlier?",
            premise="How European literacy might have changed had movable "
                    "type spread a half-century sooner than it did.",
        )
        write_claim(self.root, "c1", classification="FACT",
                    exact_claim="The printing press was introduced in Europe around 1440.",
                    supporting_sources="`research/01-source.md`")
        write_claim(self.root, "c2", classification="ASSUMPTION",
                    exact_claim="ASSUMPTION: this scenario moves that invention 50 years earlier.")
        write_claim(self.root, "c3", classification="INFERENCE",
                    exact_claim="INFERENCE: literacy could plausibly have spread somewhat sooner.")
        write_script(
            self.root,
            hook="What if movable type had reached Europe two generations earlier?",
            beats=[
                "1. Known baseline: the real timeline. — claims: `c1`",
                "2. The hypothetical shift. — claims: `c2`",
                "3. Why literacy's spread might have changed. — claims: `c3`",
            ],
            verified_claims_rows=[
                "| `c1` | `FACT` | `NOT_APPLICABLE` | 1 |",
                "| `c2` | `ASSUMPTION` | `NOT_APPLICABLE` | 2 |",
                "| `c3` | `INFERENCE` | `NOT_APPLICABLE` | 3 |",
            ],
        )
        self._assert_pass(run_originality_review(self.root, apply=False, channel_index=[]))


if __name__ == "__main__":
    unittest.main()
