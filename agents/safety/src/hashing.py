"""Safety's own `Reviewed content hash` — sha256 of SCRIPT.md's content
plus every cited claims/*.md file's content, sorted by claim ID, plus
CONTENT_ITEM.md's Identity table text specifically (title/premise matter
for TITLE_THUMBNAIL_MISREPRESENTATION in a way the Researcher's
fact-check hash doesn't need to care about) — never the whole
CONTENT_ITEM.md file. Same algorithm shape as
agents/researcher/src/hashing.py, computed independently since what
counts as "the reviewed content" differs slightly per role.

Scoped to the Identity section only (not always true — a real,
previously-latent self-invalidation bug: hashing the *entire* file used
to include the "Stage states"/"Notes / history log" sections that this
very agent's own `_apply_result` mutates immediately after computing the
hash — Safety state and a Notes/history log line, both written *after*
`content_hash = compute_reviewed_content_hash(bundle)` runs. That made
every freshly-applied Safety review's own stored hash mismatch the
content on disk the moment you re-checked it, defeating
`agents/orchestrator/src/freshness.py`'s PASS-reuse check for Safety
specifically (Researcher's equivalent hash never touches CONTENT_ITEM.md
at all, so it never hit this). Hashing only the Identity section — the
one part of CONTENT_ITEM.md this role actually needs to care about, and
the one part Safety itself never writes to — fixes this without
widening what "the reviewed content" means.
"""
from __future__ import annotations

import hashlib

from ...researcher.src import parsing
from .models import SafetyBundle


def compute_reviewed_content_hash(bundle: SafetyBundle) -> str:
    identity_text = parsing.parse_sections(bundle.content_item.raw_text).get("Identity", "")
    hasher = hashlib.sha256()
    hasher.update(identity_text.encode("utf-8"))
    hasher.update(bundle.script_text.encode("utf-8"))
    for short_id in sorted(set(bundle.script_claim_ids)):
        claim = bundle.claims.get(short_id)
        if claim is not None:
            hasher.update(short_id.encode("utf-8"))
            hasher.update(claim.raw_text.encode("utf-8"))
    return hasher.hexdigest()
