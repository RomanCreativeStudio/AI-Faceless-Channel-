"""Safety's own `Reviewed content hash` — sha256 of SCRIPT.md's content
plus every cited claims/*.md file's content, sorted by claim ID, plus
CONTENT_ITEM.md's Identity table text (title/premise matter for
TITLE_THUMBNAIL_MISREPRESENTATION in a way the Researcher's fact-check
hash doesn't need to care about). Same algorithm shape as
agents/researcher/src/hashing.py, computed independently since what
counts as "the reviewed content" differs slightly per role.
"""
from __future__ import annotations

import hashlib

from .models import SafetyBundle


def compute_reviewed_content_hash(bundle: SafetyBundle) -> str:
    hasher = hashlib.sha256()
    hasher.update(bundle.content_item.raw_text.encode("utf-8"))
    hasher.update(bundle.script_text.encode("utf-8"))
    for short_id in sorted(set(bundle.script_claim_ids)):
        claim = bundle.claims.get(short_id)
        if claim is not None:
            hasher.update(short_id.encode("utf-8"))
            hasher.update(claim.raw_text.encode("utf-8"))
    return hasher.hexdigest()
