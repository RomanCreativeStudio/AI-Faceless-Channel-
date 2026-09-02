"""Tests 5-11 from the Phase 6 task: dangerous instruction, illegal
facilitation, synthetic media, impersonation, misleading title,
unsupported certainty, and an ambiguous case that escalates to a human."""
import tempfile
import unittest
from pathlib import Path

from ..src.models import RiskLevel
from ..src.pipeline import run_safety_review
from .builders import build_minimal_item, write_claim, write_content_item, write_script


class SignalDetectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _signal(self, result, name):
        return next(e for e in result.signal_evaluations if e.signal.value == name)

    # --- Test 5: dangerous instruction ---
    def test_dangerous_instruction_fails(self):
        build_minimal_item(
            self.root,
            beats=[
                "1. A beat with step-by-step instructions to make a bomb "
                "described in detail. — claims: `c1`"
            ],
        )
        result = run_safety_review(self.root, apply=False)
        self.assertEqual(self._signal(result, "DANGEROUS_INSTRUCTION").risk_level, RiskLevel.HIGH_RISK)
        self.assertIn(result.verdict.value, ("REVISION_REQUIRED", "REJECT"))
        self.assertEqual(result.verdict.value, "REJECT")  # REJECT-tier per CONTRACT.md
        self.assertTrue(result.escalate_to_human)

    # --- Test 6: explicit illegal facilitation ---
    def test_illegal_facilitation_fails(self):
        build_minimal_item(
            self.root,
            beats=["1. A beat explaining how to launder money in detail. — claims: `c1`"],
        )
        result = run_safety_review(self.root, apply=False)
        self.assertEqual(self._signal(result, "ILLEGAL_ACTIVITY").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REJECT")

    # --- Test 7: realistic synthetic media -> disclosure/review signal ---
    def test_synthetic_media_triggers_review_signal(self):
        build_minimal_item(
            self.root,
            ai_disclosure='`YES` — disclosed via on-screen caption throughout',
            beats=["1. A beat using a deepfake recreation of a historical figure. — claims: `c1`"],
        )
        result = run_safety_review(self.root, apply=False)
        sig = self._signal(result, "SYNTHETIC_MEDIA")
        self.assertIn(sig.risk_level, (RiskLevel.REVIEW_REQUIRED, RiskLevel.HIGH_RISK))
        self.assertNotEqual(result.verdict.value, "PASS")

    # --- Test 8: impersonation ---
    def test_impersonation_fails(self):
        build_minimal_item(
            self.root,
            ai_disclosure='`NO` — no AI-generated content requiring disclosure',
            beats=["1. A beat where the narrator pretends to be Jane Smith throughout. — claims: `c1`"],
        )
        result = run_safety_review(self.root, apply=False)
        self.assertEqual(self._signal(result, "IMPERSONATION").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")
        self.assertTrue(result.escalate_to_human)

    # --- Test 9: misleading title/thumbnail ---
    def test_misleading_what_if_title_requires_revision(self):
        self.root.mkdir(parents=True, exist_ok=True)
        write_content_item(
            self.root, pillar="what-if",
            title="Modern Medicine Cured the Black Death",  # no hypothetical marker
        )
        write_claim(self.root, "c1", classification="FACT")
        write_script(
            self.root,
            fact_hypothesis_section=(
                "- **KNOWN FACT** — baseline (`c1`).\n"
                "- **ASSUMPTION** — N/A.\n- **INFERENCE** — N/A.\n- **SPECULATION** — N/A."
            ),
        )
        result = run_safety_review(self.root, apply=False)
        self.assertEqual(
            self._signal(result, "TITLE_THUMBNAIL_MISREPRESENTATION").risk_level, RiskLevel.HIGH_RISK
        )
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    # --- Test 10: unsupported certainty in hypothetical content ---
    def test_unsupported_certainty_requires_revision(self):
        self.root.mkdir(parents=True, exist_ok=True)
        write_content_item(self.root, pillar="what-if", title="What If Example Scenario?")
        write_claim(self.root, "c1", classification="FACT")
        write_claim(self.root, "c2", classification="SPECULATION",
                    exact_claim="SPECULATION: the outcome cannot be confidently estimated.")
        write_script(
            self.root,
            beats=[
                "1. Known baseline. — claims: `c1`",
                "2. This will DEFINITELY happen exactly this way. — claims: `c2`",
            ],
            verified_claims_rows=[
                "| `c1` | `FACT` | `NOT_APPLICABLE` | 1 |",
                "| `c2` | `SPECULATION` | `NOT_APPLICABLE` | 2 |",
            ],
            fact_hypothesis_section=(
                "- **KNOWN FACT** — baseline (`c1`).\n"
                "- **ASSUMPTION** — N/A.\n"
                "- **INFERENCE** — N/A.\n"
                "- **SPECULATION** — outcome uncertain (`c2`)."
            ),
        )
        result = run_safety_review(self.root, apply=False)
        self.assertEqual(self._signal(result, "MISINFORMATION_RISK").risk_level, RiskLevel.HIGH_RISK)
        self.assertEqual(result.verdict.value, "REVISION_REQUIRED")

    # --- Test 11: ambiguous safety situation -> human escalation, never PASS ---
    def test_ambiguous_situation_escalates_not_passes(self):
        build_minimal_item(
            self.root,
            beats=["1. A beat claiming a named competitor committed fraud. — claims: `c1`"],
        )
        result = run_safety_review(self.root, apply=False)
        defamation = self._signal(result, "DEFAMATION")
        self.assertEqual(defamation.risk_level, RiskLevel.REVIEW_REQUIRED)
        self.assertTrue(result.escalate_to_human)
        self.assertNotEqual(result.verdict.value, "PASS")


if __name__ == "__main__":
    unittest.main()
