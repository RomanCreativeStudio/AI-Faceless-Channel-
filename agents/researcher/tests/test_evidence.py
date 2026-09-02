"""Tests 6-9 from the Phase 5 task: missing-source detection, unsupported-
claim detection, contradictory-evidence detection, classification
preservation."""
import unittest
from dataclasses import replace
from pathlib import Path

from ..src.evidence import evaluate_claim
from ..src.loader import load_bundle
from ..src.models import Classification, EvidenceSupport, FactCheckStatus

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_item"


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle(FIXTURE_ROOT)

    def test_missing_source_detection(self):
        claim = self.bundle.claims["c_missing_source"]
        result = evaluate_claim(claim, self.bundle)
        self.assertEqual(result.evidence_support, EvidenceSupport.UNRESOLVED)
        # Never defaults to VERIFIED or FALSE on a missing source.
        self.assertEqual(result.fact_check_status, FactCheckStatus.UNVERIFIED)

    def test_unsupported_claim_detection(self):
        claim = self.bundle.claims["c_unsupported"]
        result = evaluate_claim(claim, self.bundle)
        self.assertEqual(result.evidence_support, EvidenceSupport.UNSUPPORTED)
        self.assertEqual(result.fact_check_status, FactCheckStatus.UNVERIFIED)

    def test_contradictory_evidence_detection(self):
        claim = self.bundle.claims["c_contradicted"]
        result = evaluate_claim(claim, self.bundle)
        self.assertEqual(result.evidence_support, EvidenceSupport.CONTRADICTED)
        self.assertEqual(result.fact_check_status, FactCheckStatus.DISPUTED)
        # Never auto-escalated to FALSE — that needs stronger judgment.
        self.assertNotEqual(result.fact_check_status, FactCheckStatus.FALSE)

    def test_supported_fact_is_verified(self):
        claim = self.bundle.claims["c_fact_ok"]
        result = evaluate_claim(claim, self.bundle)
        self.assertEqual(result.evidence_support, EvidenceSupport.SUPPORTED)
        self.assertEqual(result.fact_check_status, FactCheckStatus.VERIFIED)

    def test_classification_is_never_modified_by_evaluation(self):
        for short_id, claim in self.bundle.claims.items():
            original_classification = claim.classification
            result = evaluate_claim(claim, self.bundle)
            self.assertEqual(
                claim.classification,
                original_classification,
                f"{short_id}: evaluate_claim must never mutate Classification",
            )
            self.assertEqual(result.classification, original_classification)

    def test_assumption_is_never_fact_checked(self):
        claim = self.bundle.claims["c_assumption_ok"]
        result = evaluate_claim(claim, self.bundle)
        self.assertEqual(result.evidence_support, EvidenceSupport.NOT_APPLICABLE)
        self.assertEqual(result.fact_check_status, FactCheckStatus.NOT_APPLICABLE)

    def test_prior_false_status_is_never_silently_cleared(self):
        # Use a copy, not the shared class-level bundle's claim object —
        # mutating that in place would leak into other tests.
        original = self.bundle.claims["c_fact_ok"]
        falsified = replace(original, fact_check_status=FactCheckStatus.FALSE)
        result = evaluate_claim(falsified, self.bundle)
        self.assertEqual(result.fact_check_status, FactCheckStatus.FALSE)
        self.assertIn("preserved", result.reason)
        # The original, unmutated object is unaffected.
        self.assertEqual(original.fact_check_status, FactCheckStatus.UNVERIFIED)


if __name__ == "__main__":
    unittest.main()
