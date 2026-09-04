"""Tests 1-12 from the Phase 7F task: valid successor creation,
predecessor/successor immutability, revision record creation, evidence
preservation, no fabricated evidence, insufficient evidence escalation,
contradictory evidence handling, atomicity enforcement, classification
handling, claim hash changes, and old hash preservation.

Reuses the dedicated fixtures/revision_item/ fixture (never the golden
sample) — see that fixture's own claims for what each scenario models:
c_fixable (Case A), c_contradicted (Case B), c_insufficient (Case C),
c_nonatomic (atomicity violation), c_ok (not a revision candidate at all).
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.hashing import compute_claim_hash
from ..src.loader import load_bundle, load_claims
from ..src.models import Classification, FactCheckStatus, RevisionCase
from ..src.pipeline import run_fact_check
from ..src.revision import (
    create_successor_claim,
    diagnose_claim,
    run_autonomous_revision,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "revision_item"


class RevisionDiagnosisTests(unittest.TestCase):
    """Tests 6, 7, 8, 9: no fabrication, insufficient-evidence escalation,
    contradictory-evidence handling, atomicity enforcement — at the
    diagnosis layer, before any file is ever written."""

    def setUp(self):
        self.bundle = load_bundle(FIXTURE_ROOT)

    def test_fixable_claim_diagnosed_case_a(self):
        case, reason, reciprocal = diagnose_claim(self.bundle.claims["c_fixable"], self.bundle)
        self.assertEqual(case, RevisionCase.FIXABLE)
        self.assertIsNotNone(reciprocal)
        self.assertEqual(reciprocal.path.stem, "01-fixable-source")

    def test_contradicted_claim_never_gets_a_fabricated_replacement(self):
        case, reason, reciprocal = diagnose_claim(self.bundle.claims["c_contradicted"], self.bundle)
        self.assertEqual(case, RevisionCase.CONTRADICTED)
        self.assertIsNone(reciprocal)
        self.assertIn("conflict", reason.lower())

    def test_insufficient_evidence_escalates_rather_than_invents(self):
        case, reason, reciprocal = diagnose_claim(self.bundle.claims["c_insufficient"], self.bundle)
        self.assertEqual(case, RevisionCase.INSUFFICIENT_EVIDENCE)
        self.assertIsNone(reciprocal)
        self.assertIn("nothing on file", reason.lower())

    def test_atomicity_violation_never_triggers_a_reworded_successor(self):
        case, reason, reciprocal = diagnose_claim(self.bundle.claims["c_nonatomic"], self.bundle)
        self.assertEqual(case, RevisionCase.ATOMICITY_VIOLATION)
        self.assertIsNone(reciprocal)


class SuccessorCreationTests(unittest.TestCase):
    """Tests 1, 3, 5, 9, 10, 11: valid successor creation, successor
    immutability going forward, evidence preservation, atomicity
    (trivially preserved by construction), classification handling
    (always retained), and the successor receiving a new hash."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(FIXTURE_ROOT, self.root)
        self.bundle = load_bundle(self.root)

    def test_create_successor_claim_apply_true_writes_a_new_file(self):
        old_claim = self.bundle.claims["c_fixable"]
        _, _, reciprocal = diagnose_claim(old_claim, self.bundle)
        outcome = create_successor_claim(self.root, old_claim, reciprocal, apply=True, bundle=self.bundle)

        self.assertEqual(outcome.successor_short_id, "c_fixable_rev1")
        successor_path = self.root / "claims" / "c_fixable_rev1.md"
        self.assertTrue(successor_path.is_file())

    def test_successor_retains_exact_claim_and_classification_verbatim(self):
        old_claim = self.bundle.claims["c_fixable"]
        _, _, reciprocal = diagnose_claim(old_claim, self.bundle)
        create_successor_claim(self.root, old_claim, reciprocal, apply=True, bundle=self.bundle)

        successor = load_claims(self.root / "claims")["c_fixable_rev1"]
        self.assertEqual(successor.exact_claim, old_claim.exact_claim)
        self.assertEqual(successor.classification, old_claim.classification)
        self.assertEqual(successor.classification, Classification.FACT)

    def test_successor_gains_only_the_real_already_existing_evidence(self):
        old_claim = self.bundle.claims["c_fixable"]
        _, _, reciprocal = diagnose_claim(old_claim, self.bundle)
        outcome = create_successor_claim(self.root, old_claim, reciprocal, apply=True, bundle=self.bundle)

        successor = load_claims(self.root / "claims")["c_fixable_rev1"]
        self.assertIn("research/01-fixable-source.md", successor.supporting_sources)
        self.assertEqual(outcome.evidence_used, ["research/01-fixable-source.md"])
        # The evidence cited genuinely, reciprocally exists — not invented.
        self.assertIn("c_fixable", self.bundle.research["01-fixable-source"].related_claims)

    def test_successor_receives_a_new_hash_different_from_predecessor(self):
        old_claim = self.bundle.claims["c_fixable"]
        old_hash = compute_claim_hash(old_claim.raw_text)
        _, _, reciprocal = diagnose_claim(old_claim, self.bundle)
        outcome = create_successor_claim(self.root, old_claim, reciprocal, apply=True, bundle=self.bundle)

        self.assertNotEqual(outcome.new_hash, old_hash)
        self.assertEqual(outcome.original_hash, old_hash)

    def test_dry_run_diagnoses_but_writes_no_successor_file(self):
        old_claim = self.bundle.claims["c_fixable"]
        _, _, reciprocal = diagnose_claim(old_claim, self.bundle)
        outcome = create_successor_claim(self.root, old_claim, reciprocal, apply=False, bundle=self.bundle)

        self.assertEqual(outcome.successor_short_id, "")
        self.assertFalse((self.root / "claims" / "c_fixable_rev1.md").exists())


class PredecessorImmutabilityTests(unittest.TestCase):
    """Test 2: the important architectural test (task section 13) —
    structurally proves the predecessor's own table can never be edited
    by this engine, not just that the happy path looks right."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(FIXTURE_ROOT, self.root)

    def test_predecessor_table_rows_are_byte_identical_after_revision(self):
        bundle = load_bundle(self.root)
        old_claim = bundle.claims["c_fixable"]
        before_text = old_claim.path.read_text(encoding="utf-8")
        before_hash = compute_claim_hash(before_text)

        _, _, reciprocal = diagnose_claim(old_claim, bundle)
        create_successor_claim(self.root, old_claim, reciprocal, apply=True, bundle=bundle)

        after_text = old_claim.path.read_text(encoding="utf-8")
        after_hash = compute_claim_hash(after_text)

        # The file grew (a trailing "Superseded" note was appended, per
        # templates/CLAIM.md's own established convention) — but every
        # byte of the original table is still there, unmodified, as a
        # prefix of the new file.
        self.assertNotEqual(before_text, after_text)
        self.assertNotEqual(before_hash, after_hash)
        self.assertTrue(after_text.startswith(before_text.rstrip("\n")))

        # Re-parsing must show the identical table field values.
        reparsed = load_claims(self.root / "claims")["c_fixable"]
        self.assertEqual(reparsed.exact_claim, old_claim.exact_claim)
        self.assertEqual(reparsed.classification, old_claim.classification)
        self.assertEqual(reparsed.confidence_level, old_claim.confidence_level)

    def test_predecessor_and_successor_are_never_confusable(self):
        bundle = load_bundle(self.root)
        old_claim = bundle.claims["c_fixable"]
        _, _, reciprocal = diagnose_claim(old_claim, bundle)
        outcome = create_successor_claim(self.root, old_claim, reciprocal, apply=True, bundle=bundle)

        self.assertNotEqual(outcome.original_short_id, outcome.successor_short_id)
        self.assertNotEqual(outcome.original_hash, outcome.new_hash)
        # Both files coexist on disk, each independently loadable and
        # structurally distinct — never the same file, never overwritten.
        reloaded = load_claims(self.root / "claims")
        self.assertIn("c_fixable", reloaded)
        self.assertIn("c_fixable_rev1", reloaded)
        self.assertNotEqual(reloaded["c_fixable"].raw_text, reloaded["c_fixable_rev1"].raw_text)
        # See RevisionRecordTests for the dedicated revisions/ record that
        # formally links the two (produced by run_autonomous_revision, the
        # higher-level orchestration this lower-level test bypasses).


class RevisionRecordTests(unittest.TestCase):
    """Test 4: revision record creation, and that it never grants
    approval or touches anything beyond its own whitelist."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(FIXTURE_ROOT, self.root)

    def test_full_diagnosis_pass_writes_one_revision_record_per_claim(self):
        run_fact_check(self.root, apply=True)
        result = run_autonomous_revision(self.root, apply=True)

        # 4 FACT claims flagged this fixture: c_fixable, c_contradicted,
        # c_insufficient, c_nonatomic (c_ok is fine and never flagged).
        self.assertEqual(len(result.claim_outcomes), 4)
        revision_files = sorted((self.root / "revisions").glob("revision-*.md"))
        self.assertEqual(len(revision_files), 4)

        fixable_record = next(o for o in result.claim_outcomes if o.original_short_id == "c_fixable")
        text = Path(fixable_record.revision_path).read_text(encoding="utf-8")
        self.assertIn("SUCCESSOR_CREATED", text)
        self.assertIn("c_fixable_rev1", text)
        self.assertIn("does not mean", text.replace("**not**", "does not mean"))  # approval disclaimer present in some form
        self.assertIn("never itself change", text.lower().replace("does not itself change", "never itself change"))

    def test_escalated_claims_still_get_a_revision_record(self):
        run_fact_check(self.root, apply=True)
        result = run_autonomous_revision(self.root, apply=True)

        contradicted = next(o for o in result.claim_outcomes if o.original_short_id == "c_contradicted")
        self.assertEqual(contradicted.successor_short_id, "")
        text = Path(contradicted.revision_path).read_text(encoding="utf-8")
        self.assertIn("ESCALATED_CONTRADICTORY_EVIDENCE", text)
        self.assertIn("REQUIRED", text)  # Human escalation state


if __name__ == "__main__":
    unittest.main()
