"""Idempotency: before invoking a stage, check whether it already has a
current, unstale PASS on disk and reuse it instead of generating a
duplicate review attempt. Reuses agents/researcher/src.loader.load_reviews
and .models.ReviewVerdict directly (both already generic) — no new
staleness algorithm, just the same hash-comparison each agent's own
Multi-pass resolution rule already defines (templates/REVIEW.md rule 4).
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src.loader import load_reviews
from ...researcher.src.models import ReviewRecord, ReviewVerdict
from .stages import StageAdapter


def find_fresh_pass(root: Path, adapter: StageAdapter) -> ReviewRecord | None:
    """Returns the existing ReviewRecord if the stage's latest attempt is
    PASS and its stored hash still matches the current content — i.e. a
    fresh, still-valid PASS that does not need to be regenerated. Returns
    None if there's no review yet, the latest isn't PASS, the hash can't
    be verified, or the content has changed since (stale).
    """
    reviews = load_reviews(root / "reviews", adapter.review_role_prefix)
    if not reviews:
        return None
    latest = reviews[-1]
    if latest.verdict is not ReviewVerdict.PASS:
        return None
    if not latest.reviewed_content_hash or latest.reviewed_content_hash == "N/A":
        return None

    try:
        bundle = adapter.load_bundle(root)
    except Exception:
        return None  # can't verify freshness — fall through to a real run

    current_hash = adapter.compute_hash(bundle)
    if current_hash != latest.reviewed_content_hash:
        return None  # stale — the reviewed artifact changed since this PASS

    return latest
