"""Tests 5-12 and 18 from the task: duplicate topic, reused hook,
source dependence, generic AI-style framing, external reference
similarity, shared facts vs. copied structure, similar format vs.
distinct content, ambiguous escalation, and the no-overclaim guarantee."""
import tempfile
import unittest
from pathlib import Path

from ..src.models import ChannelItemSummary, RiskLevel
from ..src.pipeline import run_originality_review
from .builders import build_minimal_item, write_claim


class SignalDetectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _signal(self, result, name):
        return next(e for e in result.signal_evaluations if e.signal.value == name)

    # --- Test 5: duplicate internal topic ---
    def test_duplicate_internal_topic_requires_revision(self):
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
        )
        sibling = ChannelItemSummary(
            content_id="bs-existing-bakery",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
        )
        result = run_originality_review(self.root, apply=False, channel_index=[sibling])
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")
        self.assertNotEqual(result.verdict.value, "REJECT")  # never REJECT for content signals

    # --- Test 6: reused hook ---
    def test_reused_hook_requires_revision(self):
        build_minimal_item(
            self.root,
            title="Totally Different Title About Something Else",
            premise="An entirely different premise about a different subject "
                    "matter with no relation to the sibling item at all.",
            hook="A regional chain's forty-store expansion started with one "
                 "surprising ingredient decision.",
        )
        sibling = ChannelItemSummary(
            content_id="bs-existing-2",
            title="Unrelated Sibling Title",
            premise="Unrelated sibling premise text about something else.",
            hook="A regional chain's forty store expansion started with one "
                 "surprising ingredient decision made early on.",
        )
        result = run_originality_review(self.root, apply=False, channel_index=[sibling])
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    # --- Test 7: excessively source-dependent script ---
    def test_excessive_source_dependence_requires_revision(self):
        self.root.mkdir(parents=True, exist_ok=True)
        from .builders import write_content_item, write_script
        write_content_item(self.root)
        write_claim(self.root, "c1", classification="FACT", supporting_sources="`research/01-source.md`")
        write_claim(self.root, "c2", classification="FACT", supporting_sources="`research/01-source.md`")
        write_claim(self.root, "c3", classification="FACT", supporting_sources="`research/01-source.md`")
        write_script(
            self.root,
            beats=[
                "1. Why the first point matters. — claims: `c1`",
                "2. Why the second point follows. — claims: `c2`",
                "3. Why the third point matters. — claims: `c3`",
            ],
            verified_claims_rows=[
                "| `c1` | `FACT` | `NOT_APPLICABLE` | 1 |",
                "| `c2` | `FACT` | `NOT_APPLICABLE` | 2 |",
                "| `c3` | `FACT` | `NOT_APPLICABLE` | 3 |",
            ],
        )
        result = run_originality_review(self.root, apply=False, channel_index=[])
        self.assertEqual(self._signal(result, "SOURCE_DEPENDENCE").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    # --- Test 8: generic AI-style framing -> appropriate result ---
    def test_generic_ai_style_framing_flagged(self):
        build_minimal_item(
            self.root,
            hook="Have you ever wondered why bakeries expand the way they do?",
            conclusion="In conclusion, this is why the chain succeeded.",
        )
        result = run_originality_review(self.root, apply=False, channel_index=[])
        sig = self._signal(result, "SCRIPT_DISTINCTIVENESS")
        self.assertEqual(sig.risk_level, RiskLevel.REVIEW_REQUIRED)
        self.assertNotEqual(result.verdict.value, "PASS")
        self.assertNotEqual(result.verdict.value, "REJECT")

    # --- Test 9: high similarity to supplied reference material ---
    def test_high_external_similarity_triggers_review_or_failure(self):
        build_minimal_item(self.root)
        ref_path = Path(self._tmp.name) / "reference.txt"
        ref_path.write_text(
            "Why the chain's early growth stalled and how a single sourcing "
            "decision changed the trajectory the real driver was a supply "
            "chain choice not marketing a lesson other small chains overlook",
            encoding="utf-8",
        )
        result = run_originality_review(
            self.root, apply=False, channel_index=[], reference_paths=[ref_path]
        )
        sig = self._signal(result, "EXTERNAL_SIMILARITY_RISK")
        self.assertIn(sig.risk_level, (RiskLevel.REVIEW_REQUIRED, RiskLevel.HIGH_RISK))
        self.assertNotEqual(result.verdict.value, "PASS")
        self.assertNotEqual(result.verdict.value, "REJECT")

    # --- Test 10: shared historical facts without copied structure -> not automatic fail ---
    def test_shared_facts_alone_do_not_auto_fail(self):
        build_minimal_item(
            self.root, pillar="history",
            title="The Signing of a Trade Agreement in 1815",
            premise="Why a minor clerical error in an 1815 trade agreement "
                    "reshaped decades of maritime commerce.",
        )
        # Shares the historical event/keyword but a distinct angle/premise —
        # low word overlap, should not be treated as duplication.
        sibling = ChannelItemSummary(
            content_id="hist-existing-1815",
            title="Naval Tactics During the 1815 Campaign",
            premise="How a single admiral's unconventional maneuver decided "
                    "the outcome of a coastal blockade.",
            hook="A blockade nobody expected to work almost didn't.",
        )
        result = run_originality_review(self.root, apply=False, channel_index=[sibling])
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.LOW_RISK)
        self.assertNotEqual(result.verdict.value, "REJECT")

    # --- Test 11: similar format but distinct content -> not automatic fail ---
    def test_similar_format_distinct_content_does_not_auto_fail(self):
        build_minimal_item(
            self.root,
            title="How a Regional Airline Cut Costs",
            premise="An airline restructured its maintenance schedule and "
                    "cut costs without cutting safety margins at all.",
            hook="One scheduling change quietly saved this airline millions.",
        )
        # Same beat count / generic shape, but no shared vocabulary at all.
        sibling = ChannelItemSummary(
            content_id="bs-existing-format",
            title="How a Textile Mill Automated Weaving",
            premise="A textile mill replaced manual looms with automated "
                    "ones and tripled output within two years.",
            hook="A single machine change tripled this mill's output.",
            beat_count=1,
        )
        result = run_originality_review(self.root, apply=False, channel_index=[sibling])
        self.assertNotEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertNotEqual(self._signal(result, "TEMPLATE_REPETITION").risk_level, RiskLevel.HIGH_RISK)
        self.assertNotEqual(result.verdict.value, "REJECT")

    # --- Test 12: ambiguous similarity -> human escalation, never silently PASS ---
    def test_ambiguous_similarity_escalates(self):
        build_minimal_item(
            self.root,
            title="How a Bakery Chain Expanded Its Supply Chain",
            premise="A bakery chain changed its flour supplier network and "
                    "saw uneven regional results across its stores.",
        )
        sibling = ChannelItemSummary(
            content_id="bs-existing-similar",
            title="How a Bakery Chain Changed Its Supplier Network",
            premise="A different bakery reworked its ingredient sourcing "
                    "network and saw regional results vary afterward.",
            hook="Unrelated hook text here.",
        )
        result = run_originality_review(self.root, apply=False, channel_index=[sibling])
        sig = self._signal(result, "INTERNAL_DUPLICATION")
        self.assertEqual(sig.risk_level, RiskLevel.REVIEW_REQUIRED)
        self.assertTrue(result.escalate_to_human)
        self.assertNotEqual(result.verdict.value, "PASS")

    # --- Test 18: never claims comprehensive internet-wide detection ---
    def test_never_claims_comprehensive_detection_without_reference_material(self):
        build_minimal_item(self.root)
        result = run_originality_review(self.root, apply=False, channel_index=[])
        sig = self._signal(result, "EXTERNAL_SIMILARITY_RISK")
        self.assertEqual(sig.risk_level, RiskLevel.NOT_APPLICABLE)
        self.assertIn("does NOT perform internet-wide", sig.reason)


if __name__ == "__main__":
    unittest.main()
