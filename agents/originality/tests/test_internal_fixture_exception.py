"""Acknowledged internal engineering fixture exception (CONTRACT.md's
"Acknowledged internal engineering fixture exception") — the narrowly-
scoped mechanism that lets a content item deliberately developed from a
prior internal engineering/schema-validation fixture avoid a false
INTERNAL_DUPLICATION HIGH_RISK/REVIEW_REQUIRED finding against that exact
fixture, without weakening detection against anything else. Every test
here proves either (a) the exact declared relationship is honored, or
(b) the reviewer stays exactly as conservative as before in every case
that ISN'T that exact, two-sided, declared relationship.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.loader import _is_self_declared_engineering_fixture
from ..src.models import ChannelItemSummary, RiskLevel
from ..src.pipeline import run_originality_review
from .builders import build_minimal_item

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REAL_GOLDEN_SAMPLE_CONTENT_ITEM = (
    _REPO_ROOT / "content" / "what-if" / "wi-20260902-black-death-modern-medicine" / "CONTENT_ITEM.md"
)


class SignalHelper:
    def _signal(self, result, name):
        return next(e for e in result.signal_evaluations if e.signal.value == name)


class ExactAcknowledgedRelationshipTests(unittest.TestCase, SignalHelper):
    """The one relationship this mechanism exists for: a declared,
    two-sided match."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_acknowledged_fixture_relationship_is_low_risk_not_blocking(self):
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
            acknowledged_internal_fixture="bs-engineering-fixture",
        )
        fixture = ChannelItemSummary(
            content_id="bs-engineering-fixture",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
            is_self_declared_engineering_fixture=True,
        )
        result = run_originality_review(self.root, apply=False, channel_index=[fixture])
        signal = self._signal(result, "INTERNAL_DUPLICATION")
        self.assertEqual(signal.risk_level, RiskLevel.LOW_RISK)
        self.assertNotEqual(result.verdict.value, "REVISION_REQUIRED")

    def test_acknowledged_fixture_reason_stays_auditable(self):
        # The exception must never read as "no similarity found" — the
        # raw overlap and the exception's own reasoning must both be
        # visible in the recorded reason text.
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
            acknowledged_internal_fixture="bs-engineering-fixture",
        )
        fixture = ChannelItemSummary(
            content_id="bs-engineering-fixture",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
            is_self_declared_engineering_fixture=True,
        )
        result = run_originality_review(self.root, apply=False, channel_index=[fixture])
        reason = self._signal(result, "INTERNAL_DUPLICATION").reason
        self.assertIn("ACKNOWLEDGED INTERNAL ENGINEERING FIXTURE EXCEPTION", reason)
        self.assertIn("%", reason)  # the raw similarity score is still stated
        self.assertIn("bs-engineering-fixture", reason)


class ConservativeByDefaultTests(unittest.TestCase, SignalHelper):
    """Every case that is NOT the exact, two-sided declared relationship
    must behave exactly as before this mechanism existed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_no_declaration_still_blocks_even_against_a_real_fixture(self):
        # The fixture marker alone, on the OTHER side, is never enough —
        # THIS item must explicitly declare the acknowledgment itself.
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
            # acknowledged_internal_fixture left at default "N/A"
        )
        fixture = ChannelItemSummary(
            content_id="bs-engineering-fixture",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
            is_self_declared_engineering_fixture=True,
        )
        result = run_originality_review(self.root, apply=False, channel_index=[fixture])
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    def test_declared_id_matching_a_non_fixture_item_still_blocks(self):
        # THIS item declares an acknowledgment, but the matched item is
        # NOT independently self-identified as a fixture -- the
        # declarant's claim alone is never sufficient.
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
            acknowledged_internal_fixture="bs-not-actually-a-fixture",
        )
        not_a_fixture = ChannelItemSummary(
            content_id="bs-not-actually-a-fixture",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
            is_self_declared_engineering_fixture=False,
        )
        result = run_originality_review(self.root, apply=False, channel_index=[not_a_fixture])
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    def test_declared_id_that_does_not_match_the_triggering_item_still_blocks(self):
        # The declared acknowledgment names a DIFFERENT content ID than
        # the one that actually triggered the finding -- an external/
        # unrecognized duplicate must remain fully blocking.
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
            acknowledged_internal_fixture="bs-some-other-fixture-entirely",
        )
        real_duplicate = ChannelItemSummary(
            content_id="bs-an-actual-external-duplicate",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
            is_self_declared_engineering_fixture=False,
        )
        result = run_originality_review(self.root, apply=False, channel_index=[real_duplicate])
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    def test_acknowledgment_never_affects_external_similarity_risk(self):
        # A declared internal-fixture acknowledgment must have zero
        # effect on EXTERNAL_SIMILARITY_RISK -- a structurally separate
        # signal driven only by supplied reference_texts.
        build_minimal_item(
            self.root,
            title="How a Small Bakery Chain Expanded Regionally",
            premise="A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
            acknowledged_internal_fixture="bs-engineering-fixture",
        )
        # Near-total word overlap against the FULL script body (every
        # section _body_text concatenates), guaranteeing HIGH_RISK on
        # EXTERNAL_SIMILARITY_RISK regardless of dilution from sections
        # unrelated to the hook used in other tests in this file.
        reference_path = Path(self._tmp.name) / "reference.txt"
        script_text = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        reference_path.write_text(script_text, encoding="utf-8")
        fixture = ChannelItemSummary(
            content_id="bs-engineering-fixture",
            title="How a Regional Bakery Chain Expanded",
            premise="A regional bakery chain grew from a single shop to "
                    "dozens of locations by focusing on one product line.",
            hook="Some unrelated hook text entirely.",
            is_self_declared_engineering_fixture=True,
        )
        result = run_originality_review(
            self.root, apply=False, channel_index=[fixture], reference_paths=[reference_path],
        )
        # INTERNAL_DUPLICATION is exempted (declared + fixture-marked)...
        self.assertEqual(self._signal(result, "INTERNAL_DUPLICATION").risk_level, RiskLevel.LOW_RISK)
        # ...but EXTERNAL_SIMILARITY_RISK, against unrelated supplied
        # reference material, is untouched and still fires normally.
        self.assertEqual(self._signal(result, "EXTERNAL_SIMILARITY_RISK").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")


class RealGoldenSampleRecognitionTests(unittest.TestCase):
    """Confirms the marker-detection logic actually recognizes the real,
    untouched golden sample's own existing text -- not just a synthetic
    test double. Never writes to the golden sample."""

    def test_real_golden_sample_is_recognized_as_an_engineering_fixture(self):
        self.assertTrue(_REAL_GOLDEN_SAMPLE_CONTENT_ITEM.is_file())
        text = _REAL_GOLDEN_SAMPLE_CONTENT_ITEM.read_text(encoding="utf-8")
        self.assertTrue(_is_self_declared_engineering_fixture(text))

    def test_an_ordinary_content_item_is_not_recognized_as_a_fixture(self):
        episode_1 = (
            _REPO_ROOT / "content" / "what-if" / "wi-20260904-black-death-modern-medicine-ep1" / "CONTENT_ITEM.md"
        )
        self.assertTrue(episode_1.is_file())
        text = episode_1.read_text(encoding="utf-8")
        self.assertFalse(_is_self_declared_engineering_fixture(text))


if __name__ == "__main__":
    unittest.main()
