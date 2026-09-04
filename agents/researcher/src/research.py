"""Bounded Research Mode's provider-independent engine (Phase 7G). See
agents/researcher/CONTRACT.md's "Bounded Research Mode" for the full
contract this module implements.

    FACT-CHECK RESULT (REVISION_REQUIRED)
      -> REVISION DIAGNOSIS            (revision.diagnose_claim, unchanged)
      -> EXISTING-EVIDENCE REPAIR      (revision.create_successor_claim, unchanged)
      -> BOUNDED RESEARCH              (this module, only when existing evidence is insufficient)
      -> NEW RESEARCH RECORD
      -> RE-FACT-CHECK
      -> PASS / REVISION_REQUIRED / ESCALATE

This is NOT general autonomous browsing: exactly one query is ever issued
per claim, built from that claim's own exact text verbatim (never
rewritten, never broadened); results are capped, evaluated
deterministically against source_policy.py, and a claim's evidence gap is
only ever closed by a source this module can show is both independently
verified and structurally complete. Anything short of that escalates —
never "keep searching."

Reuses, never duplicates: source_policy.py for reliability, mutate.py's
existing write whitelist, and — once a supporting research entry is
written — revision.create_successor_claim's exact existing mechanism to
turn it into a successor claim (this module never creates a claim
itself).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path

from . import mutate, source_policy
from .loader import load_research
from .models import (
    Claim,
    ClaimSupportRelationship,
    Classification,
    DiscoveryStatus,
    ResearchEntry,
    RetrievalVerified,
    SourceReliability,
)
from .research_provider import ProviderSourceResult, ResearchProvider, ResearchProviderResult, ResearchQuery
from .research_writer import render_research_entry_markdown
from .test_research_provider import LocalTestResearchProvider

# --- Research limits (CONTRACT.md's "Research limits") — hard-coded,
# conservative, in exactly one place. A limit reached means
# ESCALATE_TO_HUMAN, never "keep searching."
MAX_QUERIES_PER_CLAIM = 1  # exactly the claim's own exact text, verbatim — never reworded or broadened
MAX_PROVIDER_RESULTS_PER_QUERY = 5
MAX_ACCEPTED_SOURCES_PER_CLAIM = 2
MAX_RESEARCH_ATTEMPTS_PER_REVISION = 1  # one bounded-research pass per revision cycle, no in-process loop
RELIABILITY_THRESHOLD = SourceReliability.MEDIUM  # minimum to ever close an evidence gap


@dataclass
class ResearchRequest:
    """A bounded, deterministic research request derived entirely from
    one claim — never open-ended, never broadened to a related topic.
    """

    claim_short_id: str
    exact_claim: str
    classification: Classification
    existing_supporting_sources: list[str]
    existing_conflicting_note: str
    reason: str
    max_queries: int
    max_accepted_sources: int
    reliability_threshold: SourceReliability
    primary_source_preference: bool


@dataclass
class EvaluatedSource:
    """The Researcher's own evaluation of one provider result — kept
    structurally distinct from the raw ProviderSourceResult (CONTRACT.md:
    "provider output is preserved distinctly from the Researcher's own
    evaluation").
    """

    provider_result: ProviderSourceResult
    discovery_status: DiscoveryStatus
    reliability: SourceReliability
    reliability_reason: str
    claim_support: ClaimSupportRelationship
    rejection_reason: str  # "N/A" if accepted
    planned_filename: str  # deterministic, computed whether or not apply writes it
    research_short_id: str = ""  # populated once actually written (apply=True only)


@dataclass
class ResearchOutcome:
    claim_short_id: str
    request: ResearchRequest
    evaluated_sources: list[EvaluatedSource] = field(default_factory=list)
    verdict: str = "INSUFFICIENT"  # "SUPPORTED" | "CONTRADICTED" | "CONFLICT" | "INSUFFICIENT"
    reason: str = ""
    escalate_to_human: bool = True
    research_paths: list[str] = field(default_factory=list)  # populated only when apply=True

    @property
    def accepted_supporting(self) -> list[EvaluatedSource]:
        return [
            e for e in self.evaluated_sources
            if e.discovery_status is DiscoveryStatus.ACCEPTED
            and e.claim_support is ClaimSupportRelationship.SUPPORTS
        ]

    @property
    def accepted_contradicting(self) -> list[EvaluatedSource]:
        return [
            e for e in self.evaluated_sources
            if e.discovery_status is DiscoveryStatus.ACCEPTED
            and e.claim_support is ClaimSupportRelationship.CONTRADICTS
        ]

    @property
    def produced(self) -> bool:
        return bool(self.research_paths)


def build_research_request(claim: Claim, reason: str) -> ResearchRequest:
    """Deterministic and conservative: the query text (built later, in
    run_bounded_research) is always this claim's own `Exact claim` text,
    verbatim — this function never rewrites or broadens it, it only
    packages the bounded parameters research is allowed to use.
    """
    return ResearchRequest(
        claim_short_id=claim.short_id,
        exact_claim=claim.exact_claim,
        classification=claim.classification,
        existing_supporting_sources=list(claim.supporting_sources),
        existing_conflicting_note=claim.contradictory_evidence,
        reason=reason,
        max_queries=MAX_QUERIES_PER_CLAIM,
        max_accepted_sources=MAX_ACCEPTED_SOURCES_PER_CLAIM,
        reliability_threshold=RELIABILITY_THRESHOLD,
        primary_source_preference=claim.classification is Classification.FACT,
    )


def _parse_claim_support(raw: str) -> ClaimSupportRelationship:
    try:
        return ClaimSupportRelationship(raw)
    except ValueError:
        return ClaimSupportRelationship.UNVERIFIED


def _slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:40] or fallback


def _next_research_number(research_dir: Path) -> int:
    if not research_dir.is_dir():
        return 1
    numbers = []
    for p in research_dir.glob("*.md"):
        m = re.match(r"^(\d+)-", p.stem)
        if m:
            numbers.append(int(m.group(1)))
    return (max(numbers) + 1) if numbers else 1


def evaluate_provider_result(
    request: ResearchRequest, result: ProviderSourceResult, planned_filename: str,
) -> EvaluatedSource:
    """Evaluates exactly one provider result — deterministic given
    identical input, no randomness, no network, no LLM/NLP dependency.
    """
    malformed, malformed_reason = source_policy.check_malformed(result)
    if malformed:
        return EvaluatedSource(
            provider_result=result, discovery_status=DiscoveryStatus.REJECTED,
            reliability=SourceReliability.UNVERIFIED,
            reliability_reason="not assessed — result is malformed",
            claim_support=ClaimSupportRelationship.UNVERIFIED,
            rejection_reason=f"malformed provider result: {malformed_reason}",
            planned_filename=planned_filename,
        )

    reliability, reliability_reason = source_policy.evaluate_source_reliability(result)
    claim_support = _parse_claim_support(result.claim_support)

    meets_threshold = reliability in (SourceReliability.HIGH, SourceReliability.MEDIUM) and (
        (reliability is SourceReliability.HIGH)
        or (reliability is SourceReliability.MEDIUM and request.reliability_threshold is not SourceReliability.HIGH)
    )
    actionable = claim_support in (ClaimSupportRelationship.SUPPORTS, ClaimSupportRelationship.CONTRADICTS)

    if meets_threshold and actionable:
        return EvaluatedSource(
            provider_result=result, discovery_status=DiscoveryStatus.ACCEPTED,
            reliability=reliability, reliability_reason=reliability_reason,
            claim_support=claim_support, rejection_reason="N/A",
            planned_filename=planned_filename,
        )

    if not actionable:
        rejection_reason = (
            f"claim-support relationship {claim_support.value!r} is not actionable "
            "(only SUPPORTS/CONTRADICTS can ever close or dispute an evidence gap)"
        )
    else:
        rejection_reason = (
            f"reliability {reliability.value!r} below the required threshold "
            f"{request.reliability_threshold.value!r} — {reliability_reason}"
        )
    return EvaluatedSource(
        provider_result=result, discovery_status=DiscoveryStatus.REJECTED,
        reliability=reliability, reliability_reason=reliability_reason,
        claim_support=claim_support, rejection_reason=rejection_reason,
        planned_filename=planned_filename,
    )


_RELIABILITY_ORDER = {
    SourceReliability.HIGH: 0, SourceReliability.MEDIUM: 1,
    SourceReliability.LOW: 2, SourceReliability.UNVERIFIED: 3,
}


def _enforce_accepted_source_limit(
    evaluated: list[EvaluatedSource], max_accepted: int,
) -> list[EvaluatedSource]:
    """MAX_ACCEPTED_SOURCES_PER_CLAIM, enforced. If more sources
    independently passed reliability+actionability than this claim is
    allowed to accept, only the highest-reliability `max_accepted` are
    kept `ACCEPTED` (ties broken by original evaluation order, for
    determinism); the rest are demoted to `REJECTED` with an explicit
    reason — never silently dropped, never silently over-accepted.
    """
    accepted_indices = [i for i, e in enumerate(evaluated) if e.discovery_status is DiscoveryStatus.ACCEPTED]
    if len(accepted_indices) <= max_accepted:
        return evaluated

    ranked = sorted(accepted_indices, key=lambda i: (_RELIABILITY_ORDER.get(evaluated[i].reliability, 9), i))
    keep = set(ranked[:max_accepted])

    result = list(evaluated)
    for i in accepted_indices:
        if i in keep:
            continue
        result[i] = replace(
            result[i],
            discovery_status=DiscoveryStatus.REJECTED,
            rejection_reason=(
                f"exceeds MAX_ACCEPTED_SOURCES_PER_CLAIM={max_accepted} — this source "
                "independently passed reliability and actionability checks but was not "
                f"among the top {max_accepted} by reliability for this claim"
            ),
        )
    return result


def run_bounded_research(
    root: Path, claim: Claim, reason: str, apply: bool = False,
    provider: ResearchProvider | None = None,
) -> ResearchOutcome:
    """The one entry point. Issues exactly one query (this claim's own
    exact text, verbatim), evaluates every returned result deterministically,
    and determines a verdict — never inventing evidence, never silently
    picking a side when authoritative sources disagree (see "Case F" in
    CONTRACT.md).
    """
    request = build_research_request(claim, reason)
    active_provider = provider or LocalTestResearchProvider()

    query = ResearchQuery(
        text=request.exact_claim, claim_short_id=claim.short_id,
        max_results=MAX_PROVIDER_RESULTS_PER_QUERY,
    )
    provider_result: ResearchProviderResult = active_provider.search(query)
    capped_results = provider_result.results[:MAX_PROVIDER_RESULTS_PER_QUERY]

    research_dir = root / "research"
    next_number = _next_research_number(research_dir)
    existing_filenames = {p.name for p in research_dir.glob("*.md")} if research_dir.is_dir() else set()

    evaluated: list[EvaluatedSource] = []
    for result in capped_results:
        slug = _slugify(result.source_publisher or result.source_title, f"{claim.short_id}-source")
        filename = f"{next_number:02d}-{slug}.md"
        while filename in existing_filenames:
            next_number += 1
            filename = f"{next_number:02d}-{slug}.md"
        existing_filenames.add(filename)
        evaluated.append(evaluate_provider_result(request, result, filename))
        next_number += 1

    evaluated = _enforce_accepted_source_limit(evaluated, request.max_accepted_sources)

    outcome = ResearchOutcome(claim_short_id=claim.short_id, request=request, evaluated_sources=evaluated)

    accepted_supporting = outcome.accepted_supporting
    accepted_contradicting = outcome.accepted_contradicting

    if accepted_supporting and accepted_contradicting:
        outcome.verdict = "CONFLICT"
        outcome.escalate_to_human = True
        outcome.reason = (
            f"{len(accepted_supporting)} accepted source(s) support this claim while "
            f"{len(accepted_contradicting)} accepted source(s) contradict it — an explicit "
            "conflict between authoritative sources; never silently resolved by picking one"
        )
    elif accepted_contradicting:
        outcome.verdict = "CONTRADICTED"
        outcome.escalate_to_human = True
        outcome.reason = (
            f"{len(accepted_contradicting)} accepted, verified source(s) contradict this "
            "claim — never automatically rewritten; human review required"
        )
    elif accepted_supporting:
        outcome.verdict = "SUPPORTED"
        outcome.escalate_to_human = False
        outcome.reason = (
            f"{len(accepted_supporting)} accepted, verified, reliability-threshold-meeting "
            "source(s) support this claim"
        )
    else:
        outcome.verdict = "INSUFFICIENT"
        outcome.escalate_to_human = True
        rejected_count = len([e for e in evaluated if e.discovery_status is DiscoveryStatus.REJECTED])
        outcome.reason = (
            f"no accepted supporting or contradicting source found "
            f"({rejected_count} candidate(s) evaluated and rejected, or none returned at all) — "
            "insufficient evidence; never manufactured"
        )

    if apply:
        _apply_outcome(root, claim, outcome)

    return outcome


def _apply_outcome(root: Path, claim: Claim, outcome: ResearchOutcome) -> None:
    for evaluated in outcome.evaluated_sources:
        text = render_research_entry_markdown(claim, evaluated)
        path = mutate.write_research_file(root, evaluated.planned_filename, text)
        evaluated.research_short_id = path.stem
        outcome.research_paths.append(str(path))
