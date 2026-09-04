"""Evidence evaluation — the RESEARCH-COLLECTION-vs-FACT-CHECK-EVALUATION
separation the Phase 5 task requires. Finding a source does not by itself
prove a claim, and a claim missing evidence is UNRESOLVED, not FALSE.

Deterministic, structural-signal only: no semantic/NLP comparison of claim
text against source text. It checks what the existing templates already
record (Source reliability, reciprocal Related claims listing, presence
of Contradictory evidence, Derived-from chain integrity) rather than
guessing meaning. See CONTRACT.md's Phase 5 implementation notes for the
full rationale and the not-auto-FALSE decision.
"""
from __future__ import annotations

from .loader import normalize_research_ref
from .models import (
    Claim,
    ClaimEvaluation,
    Classification,
    ConfidenceLevel,
    ContentBundle,
    EvidenceSupport,
    FactCheckStatus,
    SourceReliability,
)

_STRONG_RELIABILITY = {SourceReliability.HIGH, SourceReliability.MEDIUM}


def _is_empty_or_none_found(text: str) -> bool:
    t = text.strip().strip("`").strip().lower()
    return t in ("", "n/a", "none found", "none found.")


def _evaluate_fact(
    claim: Claim, bundle: ContentBundle, predecessor_short_id: str | None = None,
) -> tuple[EvidenceSupport, str]:
    """`predecessor_short_id` (Autonomous Revision Mode's one extension
    point — see agents/researcher/src/revision.py) lets a just-created
    successor claim's reciprocal check also accept a research entry that
    names the claim it superseded. A research entry's own `Related
    claims` field is itself immutable once written (CONTRACT.md's
    Forbidden actions), so it still, correctly, names the predecessor —
    never the successor. Since the successor's `Exact claim` text is
    always byte-identical to the predecessor's (this engine never
    rewords a claim), a source that already, truthfully confirmed the
    predecessor's assertion is equally valid evidence for the successor.
    `None` (every call site before Phase 7F) reproduces prior behavior.
    """
    if not _is_empty_or_none_found(claim.contradictory_evidence):
        return (
            EvidenceSupport.CONTRADICTED,
            f"Contradictory evidence recorded: {claim.contradictory_evidence!r}",
        )

    if not claim.supporting_sources:
        return (
            EvidenceSupport.UNRESOLVED,
            "no Supporting sources recorded — evidence gap, not a false claim",
        )

    existing = []
    missing_refs = []
    confirmed = []
    unconfirmed = []
    for ref in claim.supporting_sources:
        key = normalize_research_ref(ref)
        entry = bundle.research.get(key)
        if entry is None:
            missing_refs.append(ref)
            continue
        existing.append(entry)
        if claim.short_id in entry.related_claims or (
            predecessor_short_id is not None and predecessor_short_id in entry.related_claims
        ):
            confirmed.append(entry)
        else:
            unconfirmed.append(entry)

    if not existing:
        return (
            EvidenceSupport.UNRESOLVED,
            f"cited source(s) {missing_refs} not found on disk — evidence gap",
        )
    if not confirmed:
        return (
            EvidenceSupport.UNSUPPORTED,
            "cited source(s) exist but none reciprocally list this claim in "
            "their own Related claims field",
        )
    if missing_refs or unconfirmed:
        return (
            EvidenceSupport.PARTIALLY_SUPPORTED,
            "some cited sources missing or not reciprocally confirmed",
        )
    if any(e.source_reliability in _STRONG_RELIABILITY for e in confirmed):
        return (
            EvidenceSupport.SUPPORTED,
            "all cited sources found, reciprocally confirmed, at least one "
            "HIGH/MEDIUM reliability",
        )
    return (
        EvidenceSupport.PARTIALLY_SUPPORTED,
        "all cited sources confirmed but only LOW/UNVERIFIED reliability — "
        "insufficient alone per CONTRACT.md source standards",
    )


def _evaluate_inference_or_speculation(
    claim: Claim, bundle: ContentBundle
) -> tuple[EvidenceSupport, str]:
    if not claim.derived_from:
        return EvidenceSupport.UNRESOLVED, "no Derived from claims recorded"

    missing = [d for d in claim.derived_from if d not in bundle.claims]
    if missing:
        return EvidenceSupport.UNRESOLVED, f"Derived from claim(s) {missing} not found"

    parents = [bundle.claims[d] for d in claim.derived_from]
    if any(p.fact_check_status == FactCheckStatus.FALSE for p in parents):
        return EvidenceSupport.CONTRADICTED, "built on a parent claim marked FALSE"
    if any(p.fact_check_status == FactCheckStatus.DISPUTED for p in parents):
        return EvidenceSupport.PARTIALLY_SUPPORTED, "built on a parent claim currently DISPUTED"
    return EvidenceSupport.SUPPORTED, "all Derived from claims found and not FALSE/DISPUTED"


def evaluate_claim(
    claim: Claim, bundle: ContentBundle, predecessor_short_id: str | None = None,
) -> ClaimEvaluation:
    """Compute EvidenceSupport and the resulting FactCheckStatus for one
    claim. Never touches claim.classification — that field is read-only
    here (CONTRACT.md Forbidden actions). `predecessor_short_id` — see
    _evaluate_fact's docstring; only ever set by Autonomous Revision
    Mode when re-verifying a just-created successor claim.
    """
    if claim.fact_check_status is FactCheckStatus.FALSE:
        # A prior FALSE is sticky: clearing it needs a human/editorial
        # decision after the script is rewritten, never an automatic
        # re-evaluation that happens to compute a cleaner result
        # (CONTRACT.md: lowering a quality standard is forbidden).
        return ClaimEvaluation(
            short_id=claim.short_id,
            classification=claim.classification,
            evidence_support=EvidenceSupport.CONTRADICTED,
            fact_check_status=FactCheckStatus.FALSE,
            reason="prior FALSE status preserved — clearing requires a human/"
            "editorial decision after the script is corrected, not automatic "
            "re-evaluation",
        )

    if claim.classification is Classification.ASSUMPTION:
        return ClaimEvaluation(
            short_id=claim.short_id,
            classification=claim.classification,
            evidence_support=EvidenceSupport.NOT_APPLICABLE,
            fact_check_status=FactCheckStatus.NOT_APPLICABLE,
            reason="ASSUMPTION is a stipulated premise, not fact-checked "
            "(CONTRACT.md Claim handling).",
        )

    if claim.classification in (Classification.INFERENCE, Classification.SPECULATION):
        support, reason = _evaluate_inference_or_speculation(claim, bundle)
        # Contract: "normally NOT_APPLICABLE unless the speculation itself
        # later becomes checkable" — MVP default is always NOT_APPLICABLE;
        # see README.md "Known limitations."
        return ClaimEvaluation(
            short_id=claim.short_id,
            classification=claim.classification,
            evidence_support=support,
            fact_check_status=FactCheckStatus.NOT_APPLICABLE,
            reason=reason,
        )

    # FACT
    support, reason = _evaluate_fact(claim, bundle, predecessor_short_id)
    if support is EvidenceSupport.CONTRADICTED:
        # Never auto-FALSE: that needs stronger judgment than this MVP
        # applies automatically (CONTRACT.md Fact-check statuses).
        status = FactCheckStatus.DISPUTED
    elif support is EvidenceSupport.SUPPORTED:
        if claim.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
            status = FactCheckStatus.VERIFIED
        else:
            status = FactCheckStatus.UNVERIFIED
            reason += " — but confidence is LOW, so it stays UNVERIFIED, never VERIFIED"
    else:
        status = FactCheckStatus.UNVERIFIED

    return ClaimEvaluation(
        short_id=claim.short_id,
        classification=claim.classification,
        evidence_support=support,
        fact_check_status=status,
        reason=reason,
    )
