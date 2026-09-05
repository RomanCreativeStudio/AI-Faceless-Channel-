"""Human Safety signoff: model/loader/writer round trip, and that a
malformed or incomplete signoff is never silently trusted."""
import tempfile
import unittest
from pathlib import Path

from ..src.human_signoff import (
    HumanSafetyDecision,
    MalformedSignoff,
    load_human_safety_signoffs,
    next_signoff_attempt_number,
    record_human_safety_decision,
)
from .builders import build_minimal_item


class RecordAndLoadRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    def test_cleared_round_trips(self):
        path = record_human_safety_decision(
            self.root,
            reviewer="Owner",
            decision=HumanSafetyDecision.CLEARED,
            reviewed_content_hash="a" * 64,
            triggering_review_attempt="reviews/safety_reviewer-1.md",
            signals_covered=["SENSITIVE_CONTENT"],
            historical_context_reviewed=True,
            review_scope="Full script read in context.",
        )
        self.assertEqual(path, self.root / "human_safety_signoffs" / "signoff-1.md")

        signoffs = load_human_safety_signoffs(self.root / "human_safety_signoffs")
        self.assertEqual(len(signoffs), 1)
        s = signoffs[0]
        self.assertEqual(s.attempt, 1)
        self.assertEqual(s.decision, HumanSafetyDecision.CLEARED)
        self.assertEqual(s.reviewer, "Owner")
        self.assertEqual(s.reviewed_content_hash, "a" * 64)
        self.assertEqual(s.signals_covered, ["SENSITIVE_CONTENT"])
        self.assertTrue(s.historical_context_reviewed)

    def test_not_cleared_requires_notes(self):
        with self.assertRaises(ValueError):
            record_human_safety_decision(
                self.root,
                reviewer="Owner",
                decision=HumanSafetyDecision.NOT_CLEARED,
                reviewed_content_hash="a" * 64,
                triggering_review_attempt="reviews/safety_reviewer-1.md",
                signals_covered=["SENSITIVE_CONTENT"],
                historical_context_reviewed=True,
                review_scope="Full script read in context.",
                notes="",
            )

    def test_not_cleared_with_notes_round_trips(self):
        path = record_human_safety_decision(
            self.root,
            reviewer="Owner",
            decision=HumanSafetyDecision.NOT_CLEARED,
            reviewed_content_hash="b" * 64,
            triggering_review_attempt="reviews/safety_reviewer-1.md",
            signals_covered=["SENSITIVE_CONTENT"],
            historical_context_reviewed=True,
            review_scope="Full script read in context.",
            notes="Tone needs softening in beat 3.",
        )
        signoffs = load_human_safety_signoffs(path.parent)
        self.assertEqual(signoffs[0].decision, HumanSafetyDecision.NOT_CLEARED)
        self.assertIn("softening", signoffs[0].notes)

    def test_missing_reviewer_rejected(self):
        with self.assertRaises(ValueError):
            record_human_safety_decision(
                self.root,
                reviewer="   ",
                decision=HumanSafetyDecision.CLEARED,
                reviewed_content_hash="a" * 64,
                triggering_review_attempt="reviews/safety_reviewer-1.md",
                signals_covered=["SENSITIVE_CONTENT"],
                historical_context_reviewed=True,
                review_scope="scope",
            )

    def test_missing_signals_covered_rejected(self):
        with self.assertRaises(ValueError):
            record_human_safety_decision(
                self.root,
                reviewer="Owner",
                decision=HumanSafetyDecision.CLEARED,
                reviewed_content_hash="a" * 64,
                triggering_review_attempt="reviews/safety_reviewer-1.md",
                signals_covered=[],
                historical_context_reviewed=True,
                review_scope="scope",
            )

    def test_sequential_numbering_never_overwrites(self):
        first = record_human_safety_decision(
            self.root, reviewer="Owner", decision=HumanSafetyDecision.NOT_CLEARED,
            reviewed_content_hash="a" * 64, triggering_review_attempt="reviews/safety_reviewer-1.md",
            signals_covered=["SENSITIVE_CONTENT"], historical_context_reviewed=True,
            review_scope="scope", notes="needs work",
        )
        second = record_human_safety_decision(
            self.root, reviewer="Owner", decision=HumanSafetyDecision.CLEARED,
            reviewed_content_hash="b" * 64, triggering_review_attempt="reviews/safety_reviewer-2.md",
            signals_covered=["SENSITIVE_CONTENT"], historical_context_reviewed=True,
            review_scope="scope, revised",
        )
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())
        signoffs = load_human_safety_signoffs(self.root / "human_safety_signoffs")
        self.assertEqual([s.attempt for s in signoffs], [1, 2])
        self.assertEqual(signoffs[-1].decision, HumanSafetyDecision.CLEARED)

    def test_next_attempt_number(self):
        self.assertEqual(next_signoff_attempt_number([]), 1)


class MalformedSignoffTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)
        self.signoffs_dir = self.root / "human_safety_signoffs"
        self.signoffs_dir.mkdir()

    def _write(self, text: str, name: str = "signoff-1.md") -> None:
        (self.signoffs_dir / name).write_text(text, encoding="utf-8")

    def test_missing_decision_field_raises(self):
        self._write(
            "# Human Safety Signoff 1\n\n| Field | Value |\n|---|---|\n"
            "| Reviewer | Owner |\n| Reviewed content hash | `" + "a" * 64 + "` |\n"
            "| Signals covered | `SENSITIVE_CONTENT` |\n"
            "| Historical/sensitive context reviewed | `YES` |\n"
        )
        with self.assertRaises(MalformedSignoff):
            load_human_safety_signoffs(self.signoffs_dir)

    def test_bad_decision_value_raises(self):
        self._write(
            "# Human Safety Signoff 1\n\n| Field | Value |\n|---|---|\n"
            "| Reviewer | Owner |\n| Decision | `MAYBE` |\n"
            "| Reviewed content hash | `" + "a" * 64 + "` |\n"
            "| Signals covered | `SENSITIVE_CONTENT` |\n"
            "| Historical/sensitive context reviewed | `YES` |\n"
        )
        with self.assertRaises(MalformedSignoff):
            load_human_safety_signoffs(self.signoffs_dir)

    def test_missing_hash_raises(self):
        self._write(
            "# Human Safety Signoff 1\n\n| Field | Value |\n|---|---|\n"
            "| Reviewer | Owner |\n| Decision | `CLEARED` |\n"
            "| Reviewed content hash | `N/A` |\n"
            "| Signals covered | `SENSITIVE_CONTENT` |\n"
            "| Historical/sensitive context reviewed | `YES` |\n"
        )
        with self.assertRaises(MalformedSignoff):
            load_human_safety_signoffs(self.signoffs_dir)

    def test_missing_signals_covered_raises(self):
        self._write(
            "# Human Safety Signoff 1\n\n| Field | Value |\n|---|---|\n"
            "| Reviewer | Owner |\n| Decision | `CLEARED` |\n"
            "| Reviewed content hash | `" + "a" * 64 + "` |\n"
            "| Signals covered |  |\n"
            "| Historical/sensitive context reviewed | `YES` |\n"
        )
        with self.assertRaises(MalformedSignoff):
            load_human_safety_signoffs(self.signoffs_dir)

    def test_missing_reviewer_raises(self):
        self._write(
            "# Human Safety Signoff 1\n\n| Field | Value |\n|---|---|\n"
            "| Reviewer |  |\n| Decision | `CLEARED` |\n"
            "| Reviewed content hash | `" + "a" * 64 + "` |\n"
            "| Signals covered | `SENSITIVE_CONTENT` |\n"
            "| Historical/sensitive context reviewed | `YES` |\n"
        )
        with self.assertRaises(MalformedSignoff):
            load_human_safety_signoffs(self.signoffs_dir)

    def test_bad_context_reviewed_value_raises(self):
        self._write(
            "# Human Safety Signoff 1\n\n| Field | Value |\n|---|---|\n"
            "| Reviewer | Owner |\n| Decision | `CLEARED` |\n"
            "| Reviewed content hash | `" + "a" * 64 + "` |\n"
            "| Signals covered | `SENSITIVE_CONTENT` |\n"
            "| Historical/sensitive context reviewed | `MAYBE` |\n"
        )
        with self.assertRaises(MalformedSignoff):
            load_human_safety_signoffs(self.signoffs_dir)

    def test_non_matching_filename_ignored(self):
        self._write("not a signoff", name="notes.md")
        self.assertEqual(load_human_safety_signoffs(self.signoffs_dir), [])

    def test_missing_directory_returns_empty(self):
        self.assertEqual(
            load_human_safety_signoffs(self.root / "does_not_exist"), []
        )


if __name__ == "__main__":
    unittest.main()
