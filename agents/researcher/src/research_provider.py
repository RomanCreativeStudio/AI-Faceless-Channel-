"""Provider abstraction for Bounded Research Mode (Phase 7G). No specific
search/retrieval vendor is named or assumed anywhere in this module —
mirrors agents/voice/src/provider.py's and agents/assets/src/provider.py's
established shape exactly. A real web-search/archive-retrieval provider
is a future ResearchProvider implementation; nothing in research.py needs
to change to swap one in. See agents/researcher/CONTRACT.md's "Bounded
Research Mode" -> "Provider abstraction".

The pipeline (research.py) depends only on this Protocol and the
dataclasses below — no provider-specific field, vendor name, or API shape
leaks into claim/evidence logic anywhere else in this package.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ResearchQuery:
    """One bounded, deterministic query derived from a claim — see
    research.py's build_research_request(). Never a free-form question;
    always traceable back to the exact claim text it was built from.
    """

    text: str
    claim_short_id: str
    max_results: int


@dataclass
class ProviderSourceResult:
    """One candidate source a provider returns for one query. Every
    field here is the provider's own *claim* about the source — never
    trusted as final by research.py until source_policy.py evaluates it
    (CONTRACT.md: "A source must never become HIGH merely because a
    provider returned it."). Preserved distinctly from the Researcher's
    own evaluation (see EvaluatedSource in research.py) so raw provider
    output is never silently conflated with what this codebase actually
    accepted.
    """

    provider_result_id: str  # the provider's own identifier for this result, "" if none
    query_text: str
    source_title: str
    source_url: str
    source_publisher: str
    publication_date: str  # "YYYY-MM-DD" or "unknown" — never fabricated
    retrieved_at: str  # ISO timestamp the provider claims retrieval happened
    claimed_reliability: str  # the provider's own opinion; advisory only, never trusted as-is
    evidence_excerpt: str  # verbatim or close-paraphrase excerpt, never invented by research.py
    claim_support: str  # "SUPPORTS" | "CONTRADICTS" | "UNRELATED" | "UNVERIFIED" — provider's own read
    retrieval_verified: bool  # True only if the provider itself can attest the URL was actually fetched


@dataclass
class ResearchProviderResult:
    query: ResearchQuery
    results: list[ProviderSourceResult] = field(default_factory=list)


class ResearchProvider(Protocol):
    """Adapter interface every research provider (test or real)
    implements. research.py calls this and nothing else — see
    CONTRACT.md's "Bounded Research Mode" -> "Provider abstraction".
    """

    label: str

    def search(self, query: ResearchQuery) -> ResearchProviderResult:
        ...
