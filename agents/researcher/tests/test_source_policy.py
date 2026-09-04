"""Phase 7G tests for agents/researcher/src/source_policy.py — the
deterministic, conservative, never-domain-hardcoded reliability model.
Covers task areas: malformed result rejection, source reliability
evaluation, "never upgraded past what's structurally verifiable."
"""
from __future__ import annotations

import unittest

from ..src.models import SourceReliability
from ..src.research_provider import ProviderSourceResult
from ..src.source_policy import check_malformed, evaluate_source_reliability


def _result(**overrides) -> ProviderSourceResult:
    base = dict(
        provider_result_id="r1", query_text="q", source_title="A Title",
        source_url="https://example.invalid/a", source_publisher="A Publisher",
        publication_date="2024-01-01", retrieved_at="2026-09-05T00:00:00Z",
        claimed_reliability="HIGH", evidence_excerpt="An excerpt.",
        claim_support="SUPPORTS", retrieval_verified=True,
    )
    base.update(overrides)
    return ProviderSourceResult(**base)


class MalformedResultTests(unittest.TestCase):
    def test_well_formed_result_is_not_malformed(self):
        malformed, reason = check_malformed(_result())
        self.assertFalse(malformed)
        self.assertEqual(reason, "")

    def test_missing_url_is_malformed(self):
        malformed, reason = check_malformed(_result(source_url=""))
        self.assertTrue(malformed)
        self.assertIn("URL", reason)

    def test_placeholder_url_is_malformed(self):
        malformed, _ = check_malformed(_result(source_url="N/A"))
        self.assertTrue(malformed)

    def test_missing_publisher_is_malformed(self):
        malformed, reason = check_malformed(_result(source_publisher=""))
        self.assertTrue(malformed)
        self.assertIn("publisher", reason)

    def test_missing_excerpt_is_malformed(self):
        malformed, reason = check_malformed(_result(evidence_excerpt=""))
        self.assertTrue(malformed)
        self.assertIn("excerpt", reason)

    def test_missing_title_is_malformed(self):
        malformed, reason = check_malformed(_result(source_title=""))
        self.assertTrue(malformed)
        self.assertIn("title", reason)

    def test_multiple_defects_all_named_in_reason(self):
        malformed, reason = check_malformed(
            _result(source_title="", source_publisher="", evidence_excerpt="")
        )
        self.assertTrue(malformed)
        self.assertIn("title", reason)
        self.assertIn("publisher", reason)
        self.assertIn("excerpt", reason)


class ReliabilityEvaluationTests(unittest.TestCase):
    def test_full_completeness_yields_high(self):
        reliability, _ = evaluate_source_reliability(_result())
        self.assertEqual(reliability, SourceReliability.HIGH)

    def test_unverified_retrieval_hard_caps_at_unverified_even_with_high_claim(self):
        reliability, reason = evaluate_source_reliability(_result(retrieval_verified=False))
        self.assertEqual(reliability, SourceReliability.UNVERIFIED)
        self.assertIn("not independently verified", reason)

    def test_never_upgraded_past_what_provider_claims(self):
        # Provider claims only LOW — even with a publisher and date present,
        # this must never be silently upgraded to HIGH/MEDIUM.
        reliability, _ = evaluate_source_reliability(_result(claimed_reliability="LOW"))
        self.assertEqual(reliability, SourceReliability.LOW)

    def test_missing_publication_date_caps_below_high(self):
        reliability, reason = evaluate_source_reliability(_result(publication_date="unknown"))
        self.assertEqual(reliability, SourceReliability.MEDIUM)
        self.assertIn("never upgraded", reason)

    def test_missing_publisher_caps_at_unverified(self):
        reliability, reason = evaluate_source_reliability(_result(source_publisher=""))
        self.assertEqual(reliability, SourceReliability.UNVERIFIED)
        self.assertIn("no publisher", reason.lower())

    def test_unrecognized_claimed_reliability_string_never_crashes(self):
        reliability, _ = evaluate_source_reliability(_result(claimed_reliability="TOTALLY MADE UP"))
        # Treated as UNVERIFIED provider claim; publisher alone -> LOW.
        self.assertEqual(reliability, SourceReliability.LOW)

    def test_source_never_becomes_high_merely_because_provider_returned_it(self):
        # This is the explicit contract requirement: a source claiming HIGH
        # but missing a publication date is capped at MEDIUM, never HIGH,
        # regardless of how confidently the provider asserts it.
        reliability, _ = evaluate_source_reliability(
            _result(claimed_reliability="HIGH", publication_date="")
        )
        self.assertNotEqual(reliability, SourceReliability.HIGH)


if __name__ == "__main__":
    unittest.main()
