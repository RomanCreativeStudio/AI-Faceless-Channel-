"""Deterministic, conservative source-reliability policy for Bounded
Research Mode (Phase 7G). See agents/researcher/CONTRACT.md's "Bounded
Research Mode" -> "Source policy".

Deliberately NOT a hard-coded per-domain authority list ("cnn.com is
HIGH", "wikipedia.org is MEDIUM", etc.) — that would pretend every domain
has the same authority hierarchy across every content pillar, which isn't
true and isn't this MVP's job to adjudicate. Instead this module applies
the same kind of structural-signal-only approach agents/researcher/src/
evidence.py already uses for ordinary fact-check: no semantic/NLP
judgment, only checkable facts about the result itself (is retrieval
independently verified, is a publisher recorded, is a publication date
recorded, what does the provider itself claim). A source can only ever be
capped *down* from what a provider claims, never up — "a source must
never become HIGH merely because a provider returned it."
"""
from __future__ import annotations

from .models import SourceReliability
from .research_provider import ProviderSourceResult

_PLACEHOLDER_TOKENS = {"", "N/A", "TODO", "UNKNOWN"}


def _looks_like_a_real_reference(url: str) -> bool:
    """Deterministic, structural-only check — never a real network/URL
    validator (out of scope; no network access exists in this MVP
    anyway). Just enough to reject an obviously missing/placeholder
    reference before it could ever be cited as evidence.
    """
    url = url.strip()
    if url.upper() in _PLACEHOLDER_TOKENS:
        return False
    if url.startswith("http://") or url.startswith("https://"):
        return len(url) > len("https://") + 3
    return len(url) >= 4


def check_malformed(result: ProviderSourceResult) -> tuple[bool, str]:
    """Returns (is_malformed, reason). A malformed result is rejected
    before reliability is ever assessed — see CONTRACT.md's Case E
    ("Fabricated/malformed provider result" -> "safe rejection with no
    mutation").
    """
    reasons: list[str] = []
    if not _looks_like_a_real_reference(result.source_url):
        reasons.append("missing or malformed Source URL / reference")
    if not result.source_publisher.strip():
        reasons.append("missing publisher/organization")
    if not result.evidence_excerpt.strip():
        reasons.append("missing evidence excerpt")
    if not result.source_title.strip():
        reasons.append("missing source title")
    return bool(reasons), "; ".join(reasons)


def evaluate_source_reliability(result: ProviderSourceResult) -> tuple[SourceReliability, str]:
    """Returns (reliability, reason). Caller must run check_malformed()
    first and reject before calling this — this function assumes the
    result is structurally well-formed.

    Never treats an unverified retrieval as verified (CONTRACT.md
    Forbidden actions) — that alone caps reliability at UNVERIFIED,
    regardless of anything else the provider claims.
    """
    if not result.retrieval_verified:
        return (
            SourceReliability.UNVERIFIED,
            "retrieval was not independently verified by this environment — "
            "never treated as verified evidence regardless of provider claims",
        )

    try:
        claimed = SourceReliability(result.claimed_reliability)
    except ValueError:
        claimed = SourceReliability.UNVERIFIED

    has_publisher = bool(result.source_publisher.strip())
    has_date = bool(result.publication_date.strip()) and (
        result.publication_date.strip().lower() != "unknown"
    )

    if claimed is SourceReliability.HIGH and has_publisher and has_date:
        return (
            SourceReliability.HIGH,
            "provider claims HIGH; retrieval independently verified; publisher and "
            "publication date both present",
        )
    if claimed in (SourceReliability.HIGH, SourceReliability.MEDIUM) and has_publisher:
        return (
            SourceReliability.MEDIUM,
            "retrieval verified and publisher present, but full HIGH-tier "
            "completeness not met (missing/unknown publication date, or provider's "
            "own claim capped below HIGH) — never upgraded past what's structurally "
            "verifiable",
        )
    if has_publisher:
        return (
            SourceReliability.LOW,
            "retrieval verified but provenance is incomplete (no strong reliability "
            "claim from the provider, or missing publication date)",
        )
    return (
        SourceReliability.UNVERIFIED,
        "no publisher recorded — cannot assess reliability beyond UNVERIFIED",
    )
