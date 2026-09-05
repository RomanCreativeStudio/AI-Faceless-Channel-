"""continue_after_human_safety_review() — the one function that lets a
content item move past a `SAFETY_REVIEW` human escalation into
`ORIGINALITY_REVIEW`, once (and only once) a genuine, current, matching
human Safety signoff exists. See
`templates/HUMAN_SAFETY_SIGNOFF.md` for the record this reads.

This never runs Safety itself, never writes a Safety review, and never
touches `CONTENT_ITEM.md`'s Safety state — it only reads the *existing*
automated Safety result and an *existing* human signoff record, and
either blocks with a precise reason or invokes the real
`agents/originality/`'s own `run_originality_review` (the same function
`agents/orchestrator/src/stages.py` uses) exactly as
`agents/orchestrator/src/pipeline.py` would.

Four checks, in order, any of which can block:

1. An automated Safety review has run at least once (otherwise there is
   nothing for a signoff to be responding to). Its own recorded hash is
   *not* required to still match current content here — "does the
   original finding still correspond to the reviewed artifact" is
   verified directly, below, by re-evaluating Safety's real signals live
   against the current bundle, which is strictly stronger than trusting
   a static file's own stored hash.
2. A human signoff exists, and its decision is CLEARED.
3. The signoff's own recorded hash still matches the content item's
   *current* content (otherwise the signoff is stale — the reviewed
   script/content changed since the human decided, and a new human
   Safety review is required).
4. Re-evaluating Safety's real signals live right now produces no
   blocking finding (HIGH_RISK or REVIEW_REQUIRED) outside the exact set
   the signoff declares it covers — a human clearing SENSITIVE_CONTENT
   never clears a DANGEROUS_INSTRUCTION finding that happens to appear
   alongside it, now or later.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ...researcher.src.loader import load_reviews
from ...safety.src.hashing import compute_reviewed_content_hash
from ...safety.src.human_signoff import HumanSafetyDecision, load_human_safety_signoffs
from ...safety.src.loader import load_safety_bundle
from ...safety.src.models import RiskLevel
from ...safety.src.pipeline import ROLE_FILE_PREFIX as SAFETY_ROLE_PREFIX
from ...safety.src.signals import evaluate_all_signals
from ...originality.src.pipeline import run_originality_review


class HumanSafetyStatus(str, Enum):
    WAITING_FOR_HUMAN_SAFETY_REVIEW = "WAITING_FOR_HUMAN_SAFETY_REVIEW"
    EDITORIAL_REVISION_REQUIRED = "EDITORIAL_REVISION_REQUIRED"
    STALE_SIGNOFF = "STALE_SIGNOFF"
    BLOCKED_OTHER_SAFETY_FINDING = "BLOCKED_OTHER_SAFETY_FINDING"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CLEARED = "CLEARED"


@dataclass
class HumanSafetyContinuationResult:
    status: HumanSafetyStatus
    blocked: bool
    reason: str
    content_id: str = ""
    signoff_path: str = ""
    originality_result: object | None = None  # OriginalityReviewResult, only when status is CLEARED


def continue_after_human_safety_review(
    root: Path,
    apply: bool = False,
    channel_index=None,
    reference_paths=None,
) -> HumanSafetyContinuationResult:
    def _blocked(status: HumanSafetyStatus, reason: str, **kw) -> HumanSafetyContinuationResult:
        return HumanSafetyContinuationResult(status=status, blocked=True, reason=reason, **kw)

    try:
        bundle = load_safety_bundle(root)
    except Exception as exc:
        return _blocked(
            HumanSafetyStatus.SYSTEM_ERROR,
            f"could not load content for a Safety re-check: {type(exc).__name__}: {exc}",
        )
    content_id = bundle.content_item.content_id

    # 1: an automated Safety review must have run at least once — this
    # signoff has to be responding to something real. Its own recorded
    # hash is deliberately not required to still match current content:
    # step 4 below re-verifies "does the finding still correspond to the
    # reviewed artifact" directly and more robustly, by re-evaluating the
    # real signals live rather than trusting a static file.
    safety_reviews = load_reviews(root / "reviews", SAFETY_ROLE_PREFIX)
    if not safety_reviews:
        return _blocked(
            HumanSafetyStatus.WAITING_FOR_HUMAN_SAFETY_REVIEW,
            "no automated SAFETY_REVIEW has ever run for this content item — "
            "run Safety before any human signoff can be verified",
            content_id=content_id,
        )
    current_hash = compute_reviewed_content_hash(bundle)

    # 2: a human signoff must exist.
    try:
        signoffs = load_human_safety_signoffs(root / "human_safety_signoffs")
    except Exception as exc:
        return _blocked(
            HumanSafetyStatus.SYSTEM_ERROR,
            f"could not load human_safety_signoffs/: {type(exc).__name__}: {exc} — "
            "a malformed signoff file blocks exactly like a missing one; fix or "
            "remove it and record a fresh signoff",
            content_id=content_id,
        )
    if not signoffs:
        return _blocked(
            HumanSafetyStatus.WAITING_FOR_HUMAN_SAFETY_REVIEW,
            "no human Safety signoff has been recorded yet — see HUMAN_REVIEW.md "
            "for the review package; a human owner must record CLEARED or "
            "NOT_CLEARED via agents/safety/src/human_signoff_cli.py before this "
            "content item can proceed",
            content_id=content_id,
        )
    latest_signoff = signoffs[-1]

    # 2 (continued) & 3: the signoff's own decision and freshness.
    if latest_signoff.decision is not HumanSafetyDecision.CLEARED:
        return _blocked(
            HumanSafetyStatus.EDITORIAL_REVISION_REQUIRED,
            f"the latest human Safety signoff ({latest_signoff.path}) recorded "
            "NOT_CLEARED — EDITORIAL REVISION REQUIRED before Safety can be "
            "reconsidered; this system will not retry, rewrite the script, or "
            "proceed to Originality on its own",
            content_id=content_id, signoff_path=str(latest_signoff.path),
        )
    if latest_signoff.reviewed_content_hash != current_hash:
        return _blocked(
            HumanSafetyStatus.STALE_SIGNOFF,
            f"the latest human Safety signoff ({latest_signoff.path}) was recorded "
            f"against content hash {latest_signoff.reviewed_content_hash!r}, but the "
            f"content currently hashes to {current_hash!r} — the reviewed script/"
            "content changed since clearance; a new human Safety review is required",
            content_id=content_id, signoff_path=str(latest_signoff.path),
        )

    # 4: no blocking finding outside what this signoff actually covers.
    evaluations = evaluate_all_signals(bundle)
    blocking = [e for e in evaluations if e.risk_level in (RiskLevel.HIGH_RISK, RiskLevel.REVIEW_REQUIRED)]
    covered = set(latest_signoff.signals_covered)
    uncovered = [e for e in blocking if e.signal.value not in covered]
    if uncovered:
        names = ", ".join(f"{e.signal.value}:{e.risk_level.value}" for e in uncovered)
        return _blocked(
            HumanSafetyStatus.BLOCKED_OTHER_SAFETY_FINDING,
            f"unresolved Safety finding(s) not covered by this signoff: {names} — "
            f"the signoff only clears {sorted(covered)}; these require their own "
            "resolution (automated fix, or a separate human signoff) before "
            "Originality can run",
            content_id=content_id, signoff_path=str(latest_signoff.path),
        )

    originality_result = run_originality_review(
        root, apply=apply, channel_index=channel_index, reference_paths=reference_paths,
    )
    return HumanSafetyContinuationResult(
        status=HumanSafetyStatus.CLEARED,
        blocked=False,
        reason=(
            f"human Safety signoff {latest_signoff.path} verified CLEARED, current, "
            "and fully covering; no other Safety blocker present — Originality ran"
        ),
        content_id=content_id,
        signoff_path=str(latest_signoff.path),
        originality_result=originality_result,
    )
