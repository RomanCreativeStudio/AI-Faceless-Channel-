"""Implements templates/REVIEW.md's Multi-pass resolution rule: latest
attempt wins, REJECT is terminal without a logged human reopen, PASS goes
stale when reviewed artifacts change, and two consecutive autonomous
REVISION_REQUIRED verdicts require human escalation rather than a third
attempt.

Human reopen convention (documented here since templates/REVIEW.md leaves
the exact mechanics to the implementation): a line in CONTENT_ITEM.md's
Notes/history log containing the literal marker `HUMAN_REOPEN: <ROLE>`,
e.g. `HUMAN_REOPEN: FACT_CHECKER`. See README.md.
"""
from __future__ import annotations

from .hashing import compute_reviewed_content_hash
from .models import ContentBundle, ContentItem, ReviewRecord, ReviewVerdict


def latest_review(reviews: list[ReviewRecord]) -> ReviewRecord | None:
    return reviews[-1] if reviews else None


def has_human_reopen(content_item: ContentItem, role: str) -> bool:
    marker = f"HUMAN_REOPEN: {role}"
    return marker in content_item.raw_text


def reject_is_blocking(reviews: list[ReviewRecord], content_item: ContentItem, role: str) -> bool:
    """True if the latest attempt is REJECT and no human reopen is logged."""
    latest = latest_review(reviews)
    if latest is None or latest.verdict is not ReviewVerdict.REJECT:
        return False
    return not has_human_reopen(content_item, role)


def consecutive_autonomous_revision_required(reviews: list[ReviewRecord]) -> int:
    """Count trailing REVISION_REQUIRED attempts at the end of the
    attempt history (a PASS or REJECT breaks the streak)."""
    count = 0
    for record in reversed(reviews):
        if record.verdict is ReviewVerdict.REVISION_REQUIRED:
            count += 1
        else:
            break
    return count


def can_run_new_attempt(
    reviews: list[ReviewRecord], content_item: ContentItem, role: str
) -> tuple[bool, str]:
    """Whether a new automated attempt for `role` may be created now.

    Returns (allowed, reason). `allowed=False` means: stop, escalate to a
    human, do not write a new reviews/<role>-<n>.md file.
    """
    if reject_is_blocking(reviews, content_item, role):
        return (
            False,
            f"latest {role} attempt is REJECT and terminal — a human must log "
            f"'HUMAN_REOPEN: {role}' in CONTENT_ITEM.md's Notes/history log "
            "before any new attempt (Multi-pass resolution rule 3)",
        )
    streak = consecutive_autonomous_revision_required(reviews)
    if streak >= 2:
        return (
            False,
            f"{streak} consecutive REVISION_REQUIRED attempts for {role} — "
            "human escalation required instead of a third autonomous attempt "
            "(Multi-pass resolution rule 5)",
        )
    return True, ""


def effective_stage_state(
    reviews: list[ReviewRecord], bundle: ContentBundle
) -> tuple[str, str]:
    """The role's effective gate state right now, accounting for PASS
    staleness. Returns (state, explanation) where state is one of
    NOT_STARTED / IN_PROGRESS / PASS / REVISION_REQUIRED / REJECT, matching
    templates/CONTENT_ITEM.md's gate-state vocabulary.
    """
    latest = latest_review(reviews)
    if latest is None:
        return "NOT_STARTED", "no review attempts recorded yet"

    if latest.verdict is not ReviewVerdict.PASS:
        return latest.verdict.value, f"latest attempt #{latest.attempt} verdict"

    if latest.reviewed_content_hash in ("", "N/A"):
        return "PASS", "latest attempt is PASS (hash not recorded — staleness unchecked)"

    claim_ids = [row.short_id for row in bundle.script_claim_rows]
    current_hash = compute_reviewed_content_hash(bundle, claim_ids)
    if current_hash != latest.reviewed_content_hash:
        return (
            "REVISION_REQUIRED",
            f"latest attempt #{latest.attempt} was PASS but SCRIPT.md/claims "
            "changed since (content hash mismatch) — stale per Multi-pass "
            "resolution rule 4",
        )
    return "PASS", f"latest attempt #{latest.attempt} is PASS and unchanged since review"


def next_attempt_number(reviews: list[ReviewRecord]) -> int:
    return (reviews[-1].attempt + 1) if reviews else 1
