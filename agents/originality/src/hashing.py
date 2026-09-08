"""Originality's own `Reviewed content hash` — sha256 of CONTENT_ITEM.md's
Identity and Originality-context sections, SCRIPT.md's content, every
cited claims/*.md file, and any supplied reference material (sorted by
path for stability). Same algorithm shape as
agents/researcher/src/hashing.py and agents/safety/src/hashing.py,
computed independently since "what counts as the reviewed content"
includes supplied reference material here.

Scoped to Identity + Originality context only (not the whole file) —
the same real, previously-latent self-invalidation bug
agents/safety/src/hashing.py's own docstring documents and fixes:
hashing the *entire* CONTENT_ITEM.md used to include the "Stage states"/
"Notes / history log" sections that this very agent's own `_apply_result`
mutates immediately after computing the hash (`Originality state` and a
Notes/history-log line, both written right after `content_hash =
compute_reviewed_content_hash(bundle)` runs). That made every freshly-
applied Originality `PASS`'s own stored hash mismatch the content on
disk the instant you re-checked it, defeating
`agents/orchestrator/src/freshness.py`'s generic PASS-reuse check for
Originality specifically (discovered directly: Episode 1's real,
already-`PASS`ed `reviews/originality_reviewer-2.md` no longer matched
a live re-hash of its own reviewed content, purely because of its own
prior apply step's Stage-states/Notes-log writes). Identity + Originality
context is exactly what `signals.py`'s own checks actually read from
CONTENT_ITEM.md (title/premise via the Identity table,
`acknowledged_internal_fixture` via Originality context) — the one part
this role never writes to, mirroring Safety's identical fix and
reasoning exactly.
"""
from __future__ import annotations

import hashlib

from ...researcher.src import parsing
from .models import OriginalityBundle


def compute_reviewed_content_hash(bundle: OriginalityBundle) -> str:
    sections = parsing.parse_sections(bundle.content_item.raw_text)
    hasher = hashlib.sha256()
    hasher.update(sections.get("Identity", "").encode("utf-8"))
    hasher.update(sections.get("Originality context", "").encode("utf-8"))
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
