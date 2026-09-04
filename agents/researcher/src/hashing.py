"""Computes templates/REVIEW.md's `Reviewed content hash` field: sha256 of
SCRIPT.md's content plus every cited claims/*.md file's content, sorted by
claim ID for a stable, order-independent result. This is what makes
Multi-pass resolution rule 4 (PASS staleness) mechanically checkable.
"""
from __future__ import annotations

import hashlib

from .models import ContentBundle


def compute_reviewed_content_hash(bundle: ContentBundle, claim_ids: list[str]) -> str:
    hasher = hashlib.sha256()
    hasher.update(bundle.script_text.encode("utf-8"))
    for short_id in sorted(set(claim_ids)):
        claim = bundle.claims.get(short_id)
        if claim is not None:
            hasher.update(short_id.encode("utf-8"))
            hasher.update(claim.raw_text.encode("utf-8"))
    return hasher.hexdigest()


def compute_claim_hash(claim_raw_text: str) -> str:
    """sha256 of one claims/<short-id>.md file's exact raw content — used
    by the Autonomous Revision Mode (revision.py) to prove, mechanically,
    that a predecessor claim's bytes are unchanged after a successor is
    created (see templates/REVISION.md's "Original claim hash" /
    "New claim hash" fields and agents/researcher/CONTRACT.md's
    "Autonomous Revision Mode"). Not used by ordinary FACT_CHECK — that
    mode hashes the whole reviewed bundle (see
    compute_reviewed_content_hash above), never a single claim in
    isolation.
    """
    return hashlib.sha256(claim_raw_text.encode("utf-8")).hexdigest()
