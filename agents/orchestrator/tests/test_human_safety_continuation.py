"""Boundary tests for continue_after_human_safety_review(): the one
function that lets a content item move past a SAFETY_REVIEW human
escalation into ORIGINALITY_REVIEW. Exercises valid clearance, every
invalid-clearance path, and the security properties that must hold no
matter what (tampering with a review's Verdict text, missing signoffs,
stale hashes, unrelated HIGH_RISK findings, status mutation)."""
import tempfile
import unittest
from pathlib import Path

from ...safety.src.human_signoff import HumanSafetyDecision, record_human_safety_decision
from ...safety.src.pipeline import run_safety_review
from ...safety.tests.builders import build_minimal_item
from ..src.human_safety_continuation import (
    HumanSafetyStatus,
    continue_after_human_safety_review,
)

_SENSITIVE_BEAT = [
    "1. The plague swept across the region, and historians still debate "
    "its exact death toll. — claims: `c1`"
]
_DANGEROUS_BEAT = [
    "1. The plague swept across the region. Also: step-by-step instructions "
    "to build a bomb follow here. — claims: `c1`"
]


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def _build_sensitive_item(self):
        build_minimal_item(self.root, beats=_SENSITIVE_BEAT)

    def _run_safety(self):
        return run_safety_review(self.root, apply=True)

    def _record(self, decision=HumanSafetyDecision.CLEARED, reviewed_content_hash=None,
                signals_covered=("SENSITIVE_CONTENT",), notes="", triggering=None):
        if reviewed_content_hash is None:
            from ...safety.src.hashing import compute_reviewed_content_hash
            from ...safety.src.loader import load_safety_bundle
            reviewed_content_hash = compute_reviewed_content_hash(load_safety_bundle(self.root))
        if triggering is None:
            triggering = str(self.root / "reviews" / "safety_reviewer-1.md")
        return record_human_safety_decision(
            self.root,
            reviewer="Test Owner",
            decision=decision,
            reviewed_content_hash=reviewed_content_hash,
            triggering_review_attempt=triggering,
            signals_covered=list(signals_covered),
            historical_context_reviewed=True,
            review_scope="Full script read in context for this test.",
            notes=notes,
        )


class ValidClearanceTests(_Base):
    def test_correct_hash_explicit_cleared_allows_originality(self):
        self._build_sensitive_item()
        safety_result = self._run_safety()
        self.assertEqual(safety_result.verdict.value, "REVISION_REQUIRED")
        self.assertTrue(safety_result.escalate_to_human)

        self._record()
        result = continue_after_human_safety_review(self.root, apply=False)

        self.assertEqual(result.status, HumanSafetyStatus.CLEARED)
        self.assertFalse(result.blocked)
        self.assertIsNotNone(result.originality_result)

    def test_only_the_intended_signal_is_what_gets_cleared(self):
        # A signoff that covers a broader set than needed still works —
        # what matters is that every *actual* blocker is covered.
        self._build_sensitive_item()
        self._run_safety()
        self._record(signals_covered=("SENSITIVE_CONTENT", "PRIVACY"))
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.CLEARED)

    def test_stale_automated_review_record_does_not_block_a_fresh_valid_signoff(self):
        # The *stored* automated review's own hash can be technically
        # stale (e.g. an unrelated CONTENT_ITEM.md edit after Safety last
        # ran) without invalidating a signoff that was itself recorded
        # against current content — the live re-evaluation in step 4 is
        # what actually verifies correspondence, not the static file.
        self._build_sensitive_item()
        self._run_safety()
        content_item_path = self.root / "CONTENT_ITEM.md"
        content_item_path.write_text(
            content_item_path.read_text(encoding="utf-8")
            + "\n- an unrelated later note, added after Safety last ran.\n",
            encoding="utf-8",
        )
        self._record()  # hashes current (post-edit) content
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.CLEARED)
        self.assertIsNotNone(result.originality_result)


class InvalidClearanceTests(_Base):
    def test_missing_signoff_blocks(self):
        self._build_sensitive_item()
        self._run_safety()
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.WAITING_FOR_HUMAN_SAFETY_REVIEW)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.originality_result)

    def test_no_automated_safety_review_at_all_blocks(self):
        self._build_sensitive_item()
        # Safety never ran.
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.WAITING_FOR_HUMAN_SAFETY_REVIEW)
        self.assertIn("no automated SAFETY_REVIEW", result.reason)

    def test_not_cleared_blocks(self):
        self._build_sensitive_item()
        self._run_safety()
        self._record(decision=HumanSafetyDecision.NOT_CLEARED, notes="Needs a rewrite of beat 3.")
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.EDITORIAL_REVISION_REQUIRED)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.originality_result)

    def test_wrong_hash_at_recording_time_blocks_as_stale(self):
        self._build_sensitive_item()
        self._run_safety()
        self._record(reviewed_content_hash="0" * 64)  # never matched anything real
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.STALE_SIGNOFF)
        self.assertTrue(result.blocked)

    def test_script_changed_after_valid_signoff_is_not_trusted(self):
        self._build_sensitive_item()
        self._run_safety()
        self._record()
        # The script changes after the human already cleared it.
        script_path = self.root / "SCRIPT.md"
        script_path.write_text(
            script_path.read_text(encoding="utf-8") + "\nExtra unreviewed sentence.\n",
            encoding="utf-8",
        )
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.STALE_SIGNOFF)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.originality_result)

    def test_content_item_changed_after_valid_signoff_is_not_trusted(self):
        self._build_sensitive_item()
        self._run_safety()
        self._record()
        content_item_path = self.root / "CONTENT_ITEM.md"
        content_item_path.write_text(
            content_item_path.read_text(encoding="utf-8").replace(
                "An Ordinary Business Story", "A Retitled Story"
            ),
            encoding="utf-8",
        )
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.STALE_SIGNOFF)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.originality_result)

    def test_unrelated_high_risk_blocker_is_not_overridden(self):
        build_minimal_item(self.root, beats=_DANGEROUS_BEAT)
        safety_result = self._run_safety()
        self.assertEqual(safety_result.verdict.value, "REJECT")  # DANGEROUS_INSTRUCTION is reject-tier
        self._record(signals_covered=("SENSITIVE_CONTENT",))
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.BLOCKED_OTHER_SAFETY_FINDING)
        self.assertIn("DANGEROUS_INSTRUCTION", result.reason)
        self.assertIsNone(result.originality_result)

    def test_malformed_signoff_blocks_rather_than_crashing_or_passing(self):
        self._build_sensitive_item()
        self._run_safety()
        signoffs_dir = self.root / "human_safety_signoffs"
        signoffs_dir.mkdir()
        (signoffs_dir / "signoff-1.md").write_text(
            "# broken\n\n| Field | Value |\n|---|---|\n| Reviewer | Owner |\n",
            encoding="utf-8",
        )
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertTrue(result.blocked)
        self.assertEqual(result.status, HumanSafetyStatus.SYSTEM_ERROR)
        self.assertIsNone(result.originality_result)


class SecurityIntegrityTests(_Base):
    def test_tampering_with_reviews_verdict_field_does_not_manufacture_clearance(self):
        self._build_sensitive_item()
        self._run_safety()
        review_path = self.root / "reviews" / "safety_reviewer-1.md"
        tampered = review_path.read_text(encoding="utf-8").replace(
            "| Verdict | `REVISION_REQUIRED` |", "| Verdict | `PASS` |"
        )
        review_path.write_text(tampered, encoding="utf-8")
        # No human signoff exists — tampering with the stored verdict text
        # must not substitute for one.
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertEqual(result.status, HumanSafetyStatus.WAITING_FOR_HUMAN_SAFETY_REVIEW)
        self.assertIsNone(result.originality_result)

    def test_cannot_bypass_without_any_review_history(self):
        self._build_sensitive_item()
        result = continue_after_human_safety_review(self.root, apply=False)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.originality_result)

    def test_cleared_continuation_never_sets_status_approved(self):
        self._build_sensitive_item()
        self._run_safety()
        self._record()
        # The fixture's minimal CONTENT_ITEM.md has no Originality state
        # row (agents/originality/ needs one to write its own verdict to)
        # — add it so run_originality_review's own apply path is genuinely
        # exercised here, not skipped.
        content_item_path = self.root / "CONTENT_ITEM.md"
        content_item_path.write_text(
            content_item_path.read_text(encoding="utf-8").replace(
                "| Fact-check state | `NOT_STARTED` |",
                "| Fact-check state | `NOT_STARTED` |\n| Originality state | `NOT_STARTED` |",
            ),
            encoding="utf-8",
        )
        result = continue_after_human_safety_review(self.root, apply=True)
        self.assertEqual(result.status, HumanSafetyStatus.CLEARED)
        text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `SCRIPT`", text)
        self.assertNotIn("Current status: `APPROVED`", text)

    def test_stale_clearance_cannot_be_used_to_continue(self):
        self._build_sensitive_item()
        self._run_safety()
        self._record(reviewed_content_hash="f" * 64)
        result = continue_after_human_safety_review(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIsNone(result.originality_result)
        # No reviews/originality_reviewer-*.md may appear — Originality
        # never actually ran.
        reviews_dir = self.root / "reviews"
        originality_files = list(reviews_dir.glob("originality_reviewer-*.md")) if reviews_dir.is_dir() else []
        self.assertEqual(originality_files, [])

    def test_running_safety_alone_never_creates_a_signoff(self):
        self._build_sensitive_item()
        self._run_safety()
        self.assertFalse((self.root / "human_safety_signoffs").exists())


if __name__ == "__main__":
    unittest.main()
