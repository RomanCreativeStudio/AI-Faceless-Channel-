"""Originality's own `Reviewed content hash` — sha256 of CONTENT_ITEM.md's
Identity text, SCRIPT.md's content, every cited claims/*.md file, and any
supplied reference material (sorted by path for stability). Same
algorithm shape as agents/researcher/src/hashing.py and
agents/safety/src/hashing.py, computed independently since "what counts
as the reviewed content" includes supplied reference material here.
"""
from __future__ import annotations

import hashlib

from .models import OriginalityBundle


def compute_reviewed_content_hash(bundle: OriginalityBundle) -> str:
    hasher = hashlib.sha256()
    hasher.update(bundle.content_item.raw_text.encode("utf-8"))
    hasher.update(bundle.script_text.encode("utf-8"))
    for short_id in sorted(set(bundle.script_claim_ids)):
        claim = bundle.claims.get(short_id)
        if claim is not None:
            hasher.update(short_id.encode("utf-8"))
            hasher.update(claim.raw_text.encode("utf-8"))
    for path in sorted(bundle.reference_texts):
        hasher.update(path.encode("utf-8"))
        hasher.update(bundle.reference_texts[path].encode("utf-8"))
    return hasher.hexdigest()
