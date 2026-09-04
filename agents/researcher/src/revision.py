"""Autonomous Revision Mode — see agents/researcher/CONTRACT.md's
"Autonomous Revision Mode" section for the full contract this module
implements. A narrow component, not a rewrite of the Researcher:

    FACT-CHECK RESULT
      -> REVISION DIAGNOSIS      (diagnose_claim, per claim)
      -> PERMITTED SUCCESSOR CREATION  (create_successor_claim, Case A only)
      -> RE-FACT-CHECK           (run_fact_check_with_autonomous_revision)
      -> PASS / REVISION_REQUIRED / HUMAN ESCALATION

Reuses agents/researcher/src's existing hashing, parsing, atomicity,
evidence, and multipass logic directly — this module adds no competing
implementation of any of those. It never touches SCRIPT.md, never edits
an existing claim's `Exact claim`/`Classification`, and never invents
evidence: see "Evidence requirements" below for the three cases this
follows exactly.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from . import factcheck, mutate
from .atomicity import check_atomicity
from .evidence import evaluate_claim
from .loader import load_claims as _load_claims
from .hashing import compute_claim_hash
from .loader import load_bundle, load_reviews
from .models import (
    Claim,
    ClaimRevisionOutcome,
    Classification,
    ConfidenceLevel,
    ContentBundle,
    FactCheckResult,
    FactCheckStatus,
    ResearchEntry,
    RevisionCase,
    RevisionResult,
    RevisionStatus,
    ReviewVerdict,
    SourceReliability,
)
from .multipass import can_run_new_attempt
from .pipeline import ROLE as FACT_CHECKER_ROLE
from .pipeline import run_fact_check
from .revision_writer import render_revision_markdown

# Claims in these Fact-check statuses (or classifications) are not
# revision candidates at all — either nothing is wrong, or this agent
# categorically never re-evaluates them (see CONTRACT.md's Claim
# handling / Fact-check statuses).
_NEEDS_NO_REVISION = {FactCheckStatus.VERIFIED, FactCheckStatus.NOT_APPLICABLE}


def _claims_needing_revision(
    bundle: ContentBundle, evaluations: list,
) -> list[Claim]:
    """Which claims genuinely still need revision — determined from the
    just-computed ClaimEvaluation list (evidence.evaluate_claim's fresh
    result), never from a claim file's own possibly-stale on-disk
    `Fact-check status` (ordinary FACT_CHECK does not always write that
    field back — see pipeline.py's `_apply_result`). Using the stale
    on-disk value here would wrongly flag an already-fine claim whose
    file just hasn't been updated yet.
    """
    out = []
    for evaluation in evaluations:
        if evaluation.classification is not Classification.FACT:
            continue  # only FACT claims are ever fact-checked/revised — see CONTRACT.md
        if evaluation.fact_check_status in _NEEDS_NO_REVISION:
            continue
        if evaluation.fact_check_status is FactCheckStatus.FALSE:
            continue  # sticky FALSE requires a human/editorial script rewrite, never autonomous revision
        claim = bundle.claims.get(evaluation.short_id)
        if claim is not None:
            out.append(claim)
    return out


def _find_reciprocal_uncited_source(claim: Claim, bundle: ContentBundle) -> ResearchEntry | None:
    """Case A's mechanical, no-fabrication detector: a research entry that
    ALREADY exists on disk and ALREADY, reciprocally names this claim in
    its own `Related claims` field, but is not yet listed in the claim's
    own `Supporting sources`. This is "existing evidence supports a
    correction" made mechanically checkable — never a judgment call, never
    NLP, never a new source invented. Prefers the highest-reliability
    match if more than one exists, for determinism.
    """
    cited = set(claim.supporting_sources)
    candidates = [
        entry
        for key, entry in sorted(bundle.research.items())
        if claim.short_id in entry.related_claims
        and key not in cited
        and f"research/{key}.md" not in cited
    ]
    if not candidates:
        return None
    order = {SourceReliability.HIGH: 0, SourceReliability.MEDIUM: 1, SourceReliability.LOW: 2, SourceReliability.UNVERIFIED: 3}
    candidates.sort(key=lambda e: order.get(e.source_reliability, 9))
    return candidates[0]


def diagnose_claim(claim: Claim, bundle: ContentBundle) -> tuple[RevisionCase, str, ResearchEntry | None]:
    """Returns (case, reason, reciprocal_entry). `reciprocal_entry` is
    only ever set for RevisionCase.FIXABLE.
    """
    violations = check_atomicity(claim.exact_claim)
    if violations:
        return (
            RevisionCase.ATOMICITY_VIOLATION,
            "the claim itself violates templates/CLAIM.md's Atomicity rule ("
            + "; ".join(violations)
            + ") — fixing this would require rewording the claim, which this "
            "engine never fabricates; a human must split it",
            None,
        )

    if not _is_empty_contradictory(claim.contradictory_evidence):
        return (
            RevisionCase.CONTRADICTED,
            f"Contradictory evidence is already recorded ({claim.contradictory_evidence!r}) — "
            "existing evidence conflicts with this claim, but nothing on file establishes "
            "what the correct replacement should say; this engine never invents one",
            None,
        )

    reciprocal = _find_reciprocal_uncited_source(claim, bundle)
    if reciprocal is not None:
        return (
            RevisionCase.FIXABLE,
            f"research/{reciprocal.path.stem}.md already reciprocally lists this claim in its "
            "own Related claims field but is not yet cited in Supporting sources — a real, "
            "already-existing evidence gap this engine may close",
            reciprocal,
        )

    return (
        RevisionCase.INSUFFICIENT_EVIDENCE,
        "no supporting source is recorded, and no existing research entry reciprocally "
        "supports this claim either — there is nothing on file to correct with; a human "
        "must add real research before this can be resolved",
        None,
    )


def _is_empty_contradictory(text: str) -> bool:
    t = text.strip().strip("`").strip().lower()
    return t in ("", "n/a", "none found", "none found.")




def _confidence_for(reliability: SourceReliability) -> ConfidenceLevel:
    return {
        SourceReliability.HIGH: ConfidenceLevel.HIGH,
        SourceReliability.MEDIUM: ConfidenceLevel.MEDIUM,
    }.get(reliability, ConfidenceLevel.LOW)


def _render_successor_claim_markdown(
    new_short_id: str, exact_claim: str, classification: Classification, old_claim: Claim,
    new_supporting_sources: list[str], confidence: ConfidenceLevel,
) -> str:
    sources_cell = ", ".join(f"`{s}`" for s in new_supporting_sources) or "`N/A`"
    derived_cell = ", ".join(f"`{d}`" for d in old_claim.derived_from) or "`N/A`"
    return f"""# Claim {new_short_id}

Successor to `{old_claim.short_id}` — created by
`agents/researcher/src/revision.py`'s Autonomous Revision Mode. See
`revisions/` for the full revision record linking the two. This claim's
own table is subject to the exact same rules as any other
`templates/CLAIM.md` file from this point forward (immutable `Exact
claim`/`Classification`; `Fact-check status`/`Evidence`/`Contradictory
evidence`/`Confidence level` may still be updated in place).

| Field | Value |
|---|---|
| Claim ID | `{old_claim.content_id}-{new_short_id}` |
| Content ID | `{old_claim.content_id}` |
| Exact claim | {exact_claim} |
| Supporting sources | {sources_cell} |
| Derived from | {derived_cell} |
| Evidence | Carried forward from `{old_claim.short_id}`, plus newly-linked `{new_supporting_sources[-1] if new_supporting_sources else "N/A"}` — see revisions/ for the exact change. |
| Confidence level | `{confidence.value}` |
| Classification | `{classification.value}` |
| Contradictory evidence | `N/A` |
| Fact-check status | `UNVERIFIED` |
"""


def _next_short_id(old_short_id: str, claims_dir: Path) -> str:
    n = 2
    while True:
        candidate = f"{old_short_id}_rev{n - 1}"
        if not (claims_dir / f"{candidate}.md").exists():
            return candidate
        n += 1


def _next_revision_number(root: Path) -> int:
    revisions_dir = root / "revisions"
    if not revisions_dir.is_dir():
        return 1
    existing = [p for p in revisions_dir.glob("revision-*.md")]
    numbers = []
    for p in existing:
        try:
            numbers.append(int(p.stem.split("-")[-1]))
        except ValueError:
            continue
    return (max(numbers) + 1) if numbers else 1


def create_successor_claim(
    root: Path, old_claim: Claim, reciprocal_entry: ResearchEntry, apply: bool,
    bundle: ContentBundle,
) -> ClaimRevisionOutcome:
    """Case A only: builds (and, if apply, writes) a successor claim whose
    `Exact claim`/`Classification`/`Derived from` are byte-identical to
    the predecessor's — the only thing that changes is `Supporting
    sources` (gaining the already-existing, already-reciprocal research
    entry) and `Confidence level` (deterministically derived from that
    entry's own `Source reliability`, never guessed). Never invents a
    citation: the entry already existed and already named this claim
    before this function ever ran.
    """
    old_hash = compute_claim_hash(old_claim.raw_text)
    real_existing_sources = [s for s in old_claim.supporting_sources if s.strip().upper() != "N/A"]
    new_supporting_sources = real_existing_sources + [f"research/{reciprocal_entry.path.stem}.md"]
    confidence = _confidence_for(reciprocal_entry.source_reliability)
    changes_made = (
        f"Supporting sources: {real_existing_sources or ['N/A']} -> "
        f"{new_supporting_sources}; Confidence level: {old_claim.confidence_level.value} -> "
        f"{confidence.value}. Exact claim, Classification, and Derived from are unchanged."
    )

    outcome = ClaimRevisionOutcome(
        original_short_id=old_claim.short_id,
        case=RevisionCase.FIXABLE,
        reason=(
            f"research/{reciprocal_entry.path.stem}.md reciprocally supports this claim "
            "and was not yet cited"
        ),
        evidence_used=[f"research/{reciprocal_entry.path.stem}.md"],
        changes_made=changes_made,
        original_hash=old_hash,
    )

    if not apply:
        return outcome

    new_short_id = _next_short_id(old_claim.short_id, old_claim.path.parent)

    def _template_render(short_id, exact_claim, classification, old):
        return _render_successor_claim_markdown(
            short_id, exact_claim, classification, old, new_supporting_sources, confidence,
        )

    new_path_str = mutate.supersede_claim(
        old_claim,
        new_short_id,
        old_claim.exact_claim,
        old_claim.classification,
        reason=(
            f"autonomous revision: added existing, reciprocally-confirming source "
            f"research/{reciprocal_entry.path.stem}.md — see revisions/ for the full record"
        ),
        template_render=_template_render,
    )
    new_text = Path(new_path_str).read_text(encoding="utf-8")

    outcome.successor_short_id = new_short_id
    outcome.new_hash = compute_claim_hash(new_text)

    # Immediately re-verify the successor — reusing evidence.evaluate_claim
    # directly (its optional `predecessor_short_id` parameter is exactly
    # this case: the successor's cited research entry still, correctly,
    # names the predecessor it superseded, since research/*.md is
    # immutable too — see evidence.py's own docstring) — and record its
    # own Fact-check status in place, the same whitelisted field any
    # claim already permits (mutate.CLAIM_WRITABLE_FIELDS), never Exact
    # claim/Classification. This is what makes "Verification result"
    # meaningful in the revision record without waiting for a separate
    # item-level re-fact-check pass, and keeps this creation-time check
    # and the later re-fact-check pass using the exact same logic.
    new_claim = _load_claims(old_claim.path.parent)[new_short_id]
    verification = evaluate_claim(new_claim, bundle, old_claim.short_id)
    mutate.update_claim_field(
        new_claim.path, "Fact-check status", f"`{verification.fact_check_status.value}`"
    )
    outcome.verification_result = verification.fact_check_status.value
    return outcome


def run_autonomous_revision(
    root: Path, apply: bool = False, fact_check_result: FactCheckResult | None = None,
) -> RevisionResult:
    """Diagnoses the given (or the latest on-disk) FACT_CHECKER
    REVISION_REQUIRED result and creates permitted successor claims where,
    and only where, existing evidence genuinely supports a correction
    (Case A). Never called for a REJECT verdict — see CONTRACT.md's
    "Retry limits". Does not itself re-run fact-check; see
    run_fact_check_with_autonomous_revision below for the full cycle.
    """

    def _empty(**overrides) -> RevisionResult:
        base = dict(
            content_id="", triggering_review_attempt=0, claim_outcomes=[], reasons=[],
            escalate_to_human=False,
        )
        base.update(overrides)
        return RevisionResult(**base)

    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")

    try:
        bundle = load_bundle(root)
    except Exception as exc:  # noqa: BLE001 — a load failure is never a revision
        return _empty(aborted=True, abort_reason=str(exc))

    content_id = bundle.content_item.content_id

    reviews = load_reviews(root / "reviews", FACT_CHECKER_ROLE)
    if not reviews:
        return _empty(
            content_id=content_id, aborted=True,
            abort_reason="no reviews/fact_checker-*.md exists yet — nothing to revise",
        )
    latest = reviews[-1]

    if latest.verdict is ReviewVerdict.REJECT:
        return _empty(
            content_id=content_id, blocked=True,
            blocked_reason=(
                "latest FACT_CHECKER attempt is REJECT — Autonomous Revision Mode never "
                "autonomously reopens a REJECT verdict (CONTRACT.md's Retry limits); a human "
                "must log a reopen decision first"
            ),
            escalate_to_human=True,
        )

    if latest.verdict is not ReviewVerdict.REVISION_REQUIRED:
        return _empty(
            content_id=content_id, triggering_review_attempt=latest.attempt,
            reasons=[f"latest attempt #{latest.attempt} is {latest.verdict.value} — nothing to revise"],
        )

    # Reuse (never duplicate) the existing two-consecutive-attempts gate:
    # if the underlying REVIEW.md multipass rule already refuses a new
    # attempt, revision must not even try — that decision belongs to
    # can_run_new_attempt alone (CONTRACT.md's "Retry limits").
    allowed, block_reason = can_run_new_attempt(reviews, bundle.content_item, "FACT_CHECKER")
    if not allowed:
        return _empty(
            content_id=content_id, triggering_review_attempt=latest.attempt,
            blocked=True, blocked_reason=block_reason, escalate_to_human=True,
        )

    if fact_check_result is not None and fact_check_result.claim_evaluations:
        evaluations = fact_check_result.claim_evaluations
    else:
        # No fresh result supplied — evaluate now (reusing factcheck.py's
        # own evaluate_all, never a second implementation) rather than
        # trust any on-disk Fact-check status field, which can be stale —
        # see _claims_needing_revision's own docstring.
        evaluations, _ = factcheck.evaluate_all(bundle)
    candidates = _claims_needing_revision(bundle, evaluations)

    outcomes: list[ClaimRevisionOutcome] = []
    escalate = False
    reasons: list[str] = []
    revision_number = _next_revision_number(root)

    for claim in candidates:
        case, reason, reciprocal = diagnose_claim(claim, bundle)
        if case is RevisionCase.FIXABLE:
            outcome = create_successor_claim(root, claim, reciprocal, apply, bundle)
            outcomes.append(outcome)
            reasons.append(f"{claim.short_id}: FIXABLE — {reason}")
        else:
            escalate = True
            outcomes.append(
                ClaimRevisionOutcome(
                    original_short_id=claim.short_id, case=case, reason=reason,
                    original_hash=compute_claim_hash(claim.raw_text),
                )
            )
            reasons.append(f"{claim.short_id}: {case.value} — {reason}")

    if apply:
        for outcome in outcomes:
            revision_path = _write_revision_record(root, outcome, latest.attempt, revision_number, content_id)
            outcome.revision_path = revision_path
            revision_number += 1

    return RevisionResult(
        content_id=content_id,
        triggering_review_attempt=latest.attempt,
        claim_outcomes=outcomes,
        reasons=reasons or ["no FACT claim under review needed revision"],
        escalate_to_human=escalate,
    )


def _write_revision_record(
    root: Path, outcome: ClaimRevisionOutcome, triggering_attempt: int, revision_number: int,
    content_id: str, today: date | None = None,
) -> str:
    status = (
        RevisionStatus.SUCCESSOR_CREATED
        if outcome.successor_short_id
        else {
            RevisionCase.CONTRADICTED: RevisionStatus.ESCALATED_CONTRADICTORY_EVIDENCE,
            RevisionCase.INSUFFICIENT_EVIDENCE: RevisionStatus.ESCALATED_INSUFFICIENT_EVIDENCE,
            RevisionCase.ATOMICITY_VIOLATION: RevisionStatus.ESCALATED_ATOMICITY_VIOLATION,
        }[outcome.case]
    )
    revision_id = f"{content_id}-revision-{revision_number}"
    text = render_revision_markdown(
        revision_id=revision_id,
        content_id=content_id,
        outcome=outcome,
        triggering_attempt=triggering_attempt,
        status=status,
        today=today,
    )
    path = mutate.write_revision_file(root, f"revision-{revision_number}.md", text)
    return str(path)


def run_fact_check_with_autonomous_revision(
    root: Path, apply: bool = False,
) -> tuple[FactCheckResult, RevisionResult | None]:
    """The full narrow-component cycle: FACT-CHECK -> (if
    REVISION_REQUIRED) REVISION DIAGNOSIS -> PERMITTED SUCCESSOR CREATION
    -> RE-FACT-CHECK. Returns (final FactCheckResult, RevisionResult or
    None if revision was never attempted). The re-fact-check reuses
    run_fact_check unmodified except for its optional
    `claim_substitutions` parameter — see pipeline.py; this never becomes
    a second, competing fact-check implementation.

    The second FactCheckResult's own `reviews/fact_checker-<n>.md`
    attempt is number 2 in the exact same reviews/ sequence CONTRACT.md's
    Multi-pass resolution already governs — no separate retry counter
    exists here (CONTRACT.md's "Retry limits").
    """
    first = run_fact_check(root, apply=apply)

    if first.verdict is not ReviewVerdict.REVISION_REQUIRED or first.blocked:
        return first, None

    revision_result = run_autonomous_revision(root, apply=apply, fact_check_result=first)
    if revision_result.aborted or revision_result.blocked or not revision_result.produced:
        return first, revision_result

    if not apply:
        # A dry run diagnoses but writes no successor, so there is
        # nothing on disk yet for a second fact-check pass to evaluate —
        # see README.md "Known limitations". The caller sees the
        # diagnosis via revision_result.
        return first, revision_result

    second = run_fact_check(root, apply=True, claim_substitutions=revision_result.claim_substitutions)
    return second, revision_result
