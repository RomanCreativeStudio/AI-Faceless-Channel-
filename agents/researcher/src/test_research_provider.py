"""Deterministic local/test ResearchProvider — no external API, no
network, no real retrieval of any kind. Exists to prove the bounded
research pipeline end-to-end; a real provider implements the same
ResearchProvider interface (research_provider.py) and can be swapped in
(research.py's `provider=` argument) without changing research.py or
revision.py at all.

Results are supplied per-claim, not generated — this provider never
invents a source; it only ever returns exactly what a test fixture
configured, deterministically, every time. See CONTRACT.md's "Bounded
Research Mode" -> "Test provider" for the six required fixture cases
(A-F), each with a ready-made factory function below.
"""
from __future__ import annotations

from .research_provider import ProviderSourceResult, ResearchProviderResult, ResearchQuery

PLACEHOLDER_LABEL = "TEST / PLACEHOLDER RESEARCH PROVIDER — no real retrieval, no network access"


class LocalTestResearchProvider:
    """Deterministic stand-in provider. `results_by_claim` maps a claim's
    short_id to the exact list of ProviderSourceResult objects `.search`
    returns for any query about that claim — no randomness, no network
    calls, no real source retrieval of any kind. A claim with no entry
    returns zero results (never fabricates a plausible-looking one).
    """

    label = "local-test-research-provider"

    def __init__(self, results_by_claim: dict[str, list[ProviderSourceResult]] | None = None):
        self.results_by_claim = results_by_claim or {}

    def search(self, query: ResearchQuery) -> ResearchProviderResult:
        results = list(self.results_by_claim.get(query.claim_short_id, []))
        return ResearchProviderResult(query=query, results=results[: query.max_results])


# --- Fixture factories for the six required test cases (CONTRACT.md's
# "Bounded Research Mode" -> "Test provider"). Each returns a single
# ProviderSourceResult; callers wrap it in a list for
# LocalTestResearchProvider's results_by_claim.


def strong_support_result(claim_short_id: str, result_id: str = "r1") -> ProviderSourceResult:
    """Case A — strong support: a HIGH-reliability, fully-verified,
    fully-provenanced source directly supporting the claim."""
    return ProviderSourceResult(
        provider_result_id=result_id,
        query_text=f"fixture query for {claim_short_id}",
        source_title="Fixture Authoritative Source",
        source_url="https://example.invalid/fixture-authoritative-source",
        source_publisher="Fixture Public Health Authority",
        publication_date="2024-01-01",
        retrieved_at="2026-09-05T00:00:00Z",
        claimed_reliability="HIGH",
        evidence_excerpt="Fixture excerpt directly supporting the claim under test.",
        claim_support="SUPPORTS",
        retrieval_verified=True,
    )


def contradiction_result(claim_short_id: str, result_id: str = "r2") -> ProviderSourceResult:
    """Case B — contradiction: a HIGH-reliability source contradicting
    the claim. Must never trigger an automatic rewrite."""
    return ProviderSourceResult(
        provider_result_id=result_id,
        query_text=f"fixture query for {claim_short_id}",
        source_title="Fixture Contradicting Source",
        source_url="https://example.invalid/fixture-contradicting-source",
        source_publisher="Fixture Research Institute",
        publication_date="2024-02-01",
        retrieved_at="2026-09-05T00:00:00Z",
        claimed_reliability="HIGH",
        evidence_excerpt="Fixture excerpt directly contradicting the claim under test.",
        claim_support="CONTRADICTS",
        retrieval_verified=True,
    )


def weak_irrelevant_result(claim_short_id: str, result_id: str = "r3") -> ProviderSourceResult:
    """Case C — insufficient evidence: a weak/irrelevant source, verified
    but with no strong reliability claim and no real bearing on the
    claim."""
    return ProviderSourceResult(
        provider_result_id=result_id,
        query_text=f"fixture query for {claim_short_id}",
        source_title="Fixture Weak Source",
        source_url="https://example.invalid/fixture-weak-source",
        source_publisher="Fixture Blog",
        publication_date="unknown",
        retrieved_at="2026-09-05T00:00:00Z",
        claimed_reliability="LOW",
        evidence_excerpt="Fixture excerpt only tangentially related to the claim.",
        claim_support="UNRELATED",
        retrieval_verified=True,
    )


def unverified_source_result(claim_short_id: str, result_id: str = "r4") -> ProviderSourceResult:
    """Case D — unverified source: plausible-looking, well-formed, but
    this environment cannot confirm retrieval actually happened. Must
    never become ACCEPTED evidence."""
    return ProviderSourceResult(
        provider_result_id=result_id,
        query_text=f"fixture query for {claim_short_id}",
        source_title="Fixture Plausible Source",
        source_url="https://example.invalid/fixture-plausible-source",
        source_publisher="Fixture Institute",
        publication_date="2024-03-01",
        retrieved_at="2026-09-05T00:00:00Z",
        claimed_reliability="HIGH",
        evidence_excerpt="Fixture excerpt that looks plausible but is unverifiable.",
        claim_support="SUPPORTS",
        retrieval_verified=False,
    )


def malformed_result(claim_short_id: str, result_id: str = "r5") -> ProviderSourceResult:
    """Case E — fabricated/malformed provider result: missing publisher,
    missing evidence, malformed URL. Must be safely rejected, no
    mutation."""
    return ProviderSourceResult(
        provider_result_id=result_id,
        query_text=f"fixture query for {claim_short_id}",
        source_title="",
        source_url="not-a-real-url",
        source_publisher="",
        publication_date="unknown",
        retrieved_at="2026-09-05T00:00:00Z",
        claimed_reliability="HIGH",
        evidence_excerpt="",
        claim_support="SUPPORTS",
        retrieval_verified=True,
    )


def conflicting_pair(claim_short_id: str) -> list[ProviderSourceResult]:
    """Case F — source disagreement: one authoritative source supports,
    another authoritative source contradicts. Must produce an explicit
    conflict state, never a silent pick of whichever is convenient."""
    return [
        strong_support_result(claim_short_id, result_id="r6-support"),
        contradiction_result(claim_short_id, result_id="r6-contradict"),
    ]
