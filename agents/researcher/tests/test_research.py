"""Phase 7G tests for agents/researcher/src/research.py — Bounded
Research Mode's provider-independent engine. Covers task areas: provider
abstraction, bounded query construction, the six required fixture cases
(strong support / contradiction / insufficient / unverified / malformed /
conflicting sources), query limit, accepted-source limit, no invented
URLs, provenance preservation, dry-run vs apply-mode.

Never touches the golden sample — every test builds its own tempdir claim.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from ..src import research
from ..src.models import (
    Claim,
    ClaimSupportRelationship,
    Classification,
    ConfidenceLevel,
    DiscoveryStatus,
    FactCheckStatus,
    SourceReliability,
)
from ..src.research_provider import ProviderSourceResult, ResearchQuery
from ..src.test_research_provider import (
    LocalTestResearchProvider,
    conflicting_pair,
    contradiction_result,
    malformed_result,
    strong_support_result,
    unverified_source_result,
    weak_irrelevant_result,
)


def _make_claim(short_id="c99", exact_claim="The plague was caused by Yersinia pestis.") -> Claim:
    return Claim(
        path=Path(f"/tmp/fake/claims/{short_id}.md"), short_id=short_id,
        claim_id=f"wi-test-{short_id}", content_id="wi-test", exact_claim=exact_claim,
        supporting_sources=[], derived_from=[], evidence="", confidence_level=ConfidenceLevel.MEDIUM,
        classification=Classification.FACT, contradictory_evidence="none",
        fact_check_status=FactCheckStatus.UNVERIFIED,
    )


class TempRootMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        (self.root / "research").mkdir(parents=True)


class ProviderAbstractionTests(unittest.TestCase):
    """The pipeline depends only on the Protocol — a second, independent
    implementation (not LocalTestResearchProvider) works unmodified."""

    def test_a_second_independent_provider_implementation_works_unmodified(self):
        class _AltProvider:
            label = "alt-test-provider"

            def search(self, query: ResearchQuery):
                from ..src.research_provider import ResearchProviderResult
                return ResearchProviderResult(query=query, results=[strong_support_result(query.claim_short_id)])

        claim = _make_claim()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "item"
            (root / "research").mkdir(parents=True)
            outcome = research.run_bounded_research(root, claim, reason="t", apply=False, provider=_AltProvider())
        self.assertEqual(outcome.verdict, "SUPPORTED")

    def test_default_provider_is_the_local_test_provider_and_returns_nothing_by_default(self):
        claim = _make_claim()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "item"
            (root / "research").mkdir(parents=True)
            outcome = research.run_bounded_research(root, claim, reason="t", apply=False)
        self.assertEqual(outcome.verdict, "INSUFFICIENT")
        self.assertEqual(outcome.evaluated_sources, [])


class BoundedQueryConstructionTests(unittest.TestCase):
    def test_request_uses_claim_exact_text_verbatim_never_reworded(self):
        claim = _make_claim(exact_claim="A very specific, one-sentence factual assertion.")
        req = research.build_research_request(claim, reason="insufficient evidence")
        self.assertEqual(req.exact_claim, claim.exact_claim)

    def test_request_is_bounded_to_exactly_one_query_and_two_accepted_sources(self):
        claim = _make_claim()
        req = research.build_research_request(claim, reason="x")
        self.assertEqual(req.max_queries, research.MAX_QUERIES_PER_CLAIM)
        self.assertEqual(research.MAX_QUERIES_PER_CLAIM, 1)
        self.assertEqual(req.max_accepted_sources, research.MAX_ACCEPTED_SOURCES_PER_CLAIM)

    def test_exactly_one_query_is_issued_per_claim(self):
        calls = []

        class _CountingProvider:
            label = "counting"

            def search(self, query):
                calls.append(query)
                from ..src.research_provider import ResearchProviderResult
                return ResearchProviderResult(query=query, results=[])

        claim = _make_claim()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "item"
            (root / "research").mkdir(parents=True)
            research.run_bounded_research(root, claim, reason="x", apply=False, provider=_CountingProvider())
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].text, claim.exact_claim)


class SixFixtureCaseTests(TempRootMixin, unittest.TestCase):
    """CONTRACT.md's "Bounded Research Mode" -> "Test provider" — the six
    required cases (A-F)."""

    def test_case_a_strong_support_is_accepted_and_verdict_supported(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [strong_support_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "SUPPORTED")
        self.assertFalse(outcome.escalate_to_human)
        self.assertEqual(len(outcome.accepted_supporting), 1)
        self.assertEqual(outcome.accepted_supporting[0].discovery_status, DiscoveryStatus.ACCEPTED)

    def test_case_b_contradiction_escalates_never_auto_rewrites(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [contradiction_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "CONTRADICTED")
        self.assertTrue(outcome.escalate_to_human)

    def test_case_c_insufficient_weak_evidence_escalates(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [weak_irrelevant_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "INSUFFICIENT")
        self.assertTrue(outcome.escalate_to_human)

    def test_case_d_unverified_source_never_becomes_accepted(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [unverified_source_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "INSUFFICIENT")
        self.assertEqual(outcome.evaluated_sources[0].discovery_status, DiscoveryStatus.REJECTED)
        self.assertEqual(outcome.evaluated_sources[0].reliability, SourceReliability.UNVERIFIED)

    def test_case_e_malformed_result_safely_rejected_no_mutation(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [malformed_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "INSUFFICIENT")
        self.assertEqual(outcome.evaluated_sources[0].discovery_status, DiscoveryStatus.REJECTED)
        self.assertIn("malformed", outcome.evaluated_sources[0].rejection_reason.lower())

    def test_case_f_source_disagreement_is_explicit_conflict_never_silent_pick(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: conflicting_pair(claim.short_id)})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "CONFLICT")
        self.assertTrue(outcome.escalate_to_human)
        self.assertEqual(len(outcome.accepted_supporting), 1)
        self.assertEqual(len(outcome.accepted_contradicting), 1)


class AcceptedSourceLimitTests(TempRootMixin, unittest.TestCase):
    def test_more_accepted_candidates_than_the_limit_are_capped(self):
        claim = _make_claim()
        three = [strong_support_result(claim.short_id, result_id=f"r{i}") for i in range(3)]
        provider = LocalTestResearchProvider({claim.short_id: three})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.verdict, "SUPPORTED")
        self.assertEqual(len(outcome.accepted_supporting), research.MAX_ACCEPTED_SOURCES_PER_CLAIM)
        capped = [e for e in outcome.evaluated_sources if "MAX_ACCEPTED_SOURCES_PER_CLAIM" in e.rejection_reason]
        self.assertEqual(len(capped), 1)
        self.assertEqual(capped[0].discovery_status, DiscoveryStatus.REJECTED)

    def test_provider_results_beyond_max_per_query_are_never_evaluated(self):
        claim = _make_claim()
        many = [strong_support_result(claim.short_id, result_id=f"r{i}") for i in range(10)]
        provider = LocalTestResearchProvider({claim.short_id: many})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=False, provider=provider)
        self.assertEqual(len(outcome.evaluated_sources), research.MAX_PROVIDER_RESULTS_PER_QUERY)


class ProvenanceTests(TempRootMixin, unittest.TestCase):
    def test_no_invented_urls_every_accepted_source_traces_to_a_real_provider_result(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [strong_support_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        accepted = outcome.accepted_supporting[0]
        self.assertEqual(accepted.provider_result.source_url, "https://example.invalid/fixture-authoritative-source")
        text = Path(outcome.research_paths[0]).read_text(encoding="utf-8")
        self.assertIn("https://example.invalid/fixture-authoritative-source", text)

    def test_rejected_sources_never_appear_as_accepted_on_disk(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [malformed_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        text = Path(outcome.research_paths[0]).read_text(encoding="utf-8")
        self.assertIn("`REJECTED`", text)
        self.assertNotIn("`ACCEPTED`", text)

    def test_every_rejected_source_has_a_recorded_reason(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [malformed_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        rejected = outcome.evaluated_sources[0]
        self.assertNotEqual(rejected.rejection_reason.strip(), "")
        self.assertNotEqual(rejected.rejection_reason.strip().upper(), "N/A")

    def test_every_accepted_source_rejection_reason_is_na(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [strong_support_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        self.assertEqual(outcome.accepted_supporting[0].rejection_reason, "N/A")

    def test_provider_output_preserved_distinctly_from_evaluation(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [contradiction_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=False, provider=provider)
        evaluated = outcome.evaluated_sources[0]
        # provider_result.claim_support is the provider's raw string claim;
        # evaluated.claim_support is this module's own parsed enum — kept
        # as two separate attributes, never conflated into one field.
        self.assertEqual(evaluated.provider_result.claim_support, "CONTRADICTS")
        self.assertEqual(evaluated.claim_support, ClaimSupportRelationship.CONTRADICTS)


class DryRunApplyTests(TempRootMixin, unittest.TestCase):
    def test_dry_run_creates_zero_files(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [strong_support_result(claim.short_id)]})
        before = sorted(self.root.rglob("*"))
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=False, provider=provider)
        after = sorted(self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(outcome.research_paths, [])
        self.assertFalse(outcome.produced)
        # But the verdict is still fully computed, for the caller to see.
        self.assertEqual(outcome.verdict, "SUPPORTED")

    def test_apply_writes_only_through_the_research_whitelist(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({claim.short_id: [strong_support_result(claim.short_id), malformed_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        for path_str in outcome.research_paths:
            path = Path(path_str)
            self.assertEqual(path.parent.name, "research")
            self.assertRegex(path.name, r"^\d+-[a-z0-9][a-z0-9-]*\.md$")

    def test_apply_never_overwrites_an_existing_research_file(self):
        claim = _make_claim()
        preexisting_path = self.root / "research" / "01-fixture-public-health-authority.md"
        preexisting_path.write_text("preexisting", encoding="utf-8")
        provider = LocalTestResearchProvider({claim.short_id: [strong_support_result(claim.short_id)]})
        outcome = research.run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        # The engine picked a non-colliding filename rather than overwrite.
        self.assertEqual(preexisting_path.read_text(encoding="utf-8"), "preexisting")
        self.assertTrue(outcome.produced)
        self.assertNotIn(str(preexisting_path), outcome.research_paths)


if __name__ == "__main__":
    unittest.main()
