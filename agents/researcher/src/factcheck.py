"""Orchestrates per-claim evidence evaluation into an overall FACT_CHECK
verdict, per agents/researcher/CONTRACT.md's Phase 5 implementation notes
"Verdict derivation" list. Structural failures (missing claim file,
invalid classification) are raised earlier by loader.py as
StructuralFailure/NoLoadableContent — this module handles content-quality
outcomes only (steps 3-6 of that list).
"""
from __future__ import annotations

from .atomicity import check_atomicity
from .evidence import evaluate_claim
from .models import ClaimEvaluation, ContentBundle, FactCheckStatus, ReviewVerdict


def claims_under_review(bundle: ContentBundle) -> list[str]:
    """Which claims this fact-check pass covers: everything SCRIPT.md
    cites, or — if there's no script yet — every loaded claim."""
    if bundle.script_claim_rows:
        return [row.short_id for row in bundle.script_claim_rows]
    return list(bundle.claims.keys())


def evaluate_all(
    bundle: ContentBundle,
) -> tuple[list[ClaimEvaluation], dict[str, list[str]]]:
    """Returns (evaluations, atomicity_violations). Structure validation
    (objective #4) happens here via check_atomicity — a claim that fails
    it still gets an evidence evaluation (so the caller sees everything),
    but derive_verdict() below forces at least REVISION_REQUIRED whenever
    atomicity_violations is non-empty.
    """
    evaluations = []
    atomicity_violations: dict[str, list[str]] = {}
    for short_id in claims_under_review(bundle):
        claim = bundle.claims.get(short_id)
        if claim is None:
            continue  # loader already guarantees this can't happen for script rows
        violations = check_atomicity(claim.exact_claim)
        if violations:
            atomicity_violations[short_id] = violations
        evaluations.append(evaluate_claim(claim, bundle))
    return evaluations, atomicity_violations


def derive_verdict(
    evaluations: list[ClaimEvaluation],
    atomicity_violations: dict[str, list[str]] | None = None,
) -> tuple[ReviewVerdict, list[str], list[str], bool]:
    """Returns (verdict, reasons, required_changes, escalate_to_human)."""
    atomicity_violations = atomicity_violations or {}
    reasons: list[str] = []
    required_changes: list[str] = []
    escalate = False

    for short_id, violations in atomicity_violations.items():
        reasons.append(f"{short_id}: Atomicity rule violation(s): {'; '.join(violations)}")
        required_changes.append(
            f"{short_id}: split into atomic claims per templates/CLAIM.md's "
            "Atomicity rule before this can be fact-checked as-is"
        )

    disputed_or_false = [
        e for e in evaluations if e.fact_check_status in (FactCheckStatus.DISPUTED, FactCheckStatus.FALSE)
    ]
    if evaluations and len(disputed_or_false) * 2 > len(evaluations):
        escalate = True
        reasons.append(
            f"more than half of the {len(evaluations)} claims under review are "
            f"DISPUTED or FALSE ({len(disputed_or_false)}) — item wasn't ready "
            "for fact-check, not a marginal revision (CONTRACT.md Failure conditions)"
        )

    any_false = any(e.fact_check_status is FactCheckStatus.FALSE for e in evaluations)
    any_disputed = any(e.fact_check_status is FactCheckStatus.DISPUTED for e in evaluations)
    unverified_facts = [
        e
        for e in evaluations
        if e.classification.value == "FACT" and e.fact_check_status is not FactCheckStatus.VERIFIED
    ]

    for e in evaluations:
        if e.fact_check_status is FactCheckStatus.FALSE:
            reasons.append(f"{e.short_id}: FALSE — {e.reason}")
            required_changes.append(f"{e.short_id}: script needs to be corrected, claim is FALSE")
            escalate = True
        elif e.fact_check_status is FactCheckStatus.DISPUTED:
            reasons.append(f"{e.short_id}: DISPUTED — {e.reason}")
            required_changes.append(f"{e.short_id}: resolve conflicting evidence before re-review")
        elif e.classification.value == "FACT" and e.fact_check_status is not FactCheckStatus.VERIFIED:
            reasons.append(f"{e.short_id}: not yet VERIFIED ({e.evidence_support.value}) — {e.reason}")
            required_changes.append(
                f"{e.short_id}: evidence gap — add/strengthen sourcing; do not "
                "fabricate a citation to close it"
            )

    if any_false or any_disputed or unverified_facts or atomicity_violations:
        verdict = ReviewVerdict.REVISION_REQUIRED
    else:
        verdict = ReviewVerdict.PASS
        reasons.append(
            f"all {len(evaluations)} claims under review are VERIFIED or "
            "NOT_APPLICABLE with no unresolved contradictions"
        )

    return verdict, reasons, required_changes, escalate
