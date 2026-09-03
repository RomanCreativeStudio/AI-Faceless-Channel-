"""Computes templates/PRODUCTION.md's `Script content hash` field: sha256
of SCRIPT.md's raw text. This is what makes production-plan staleness
(agents/producer/CONTRACT.md's "Re-running" section) mechanically
checkable, mirroring agents/researcher/src/hashing.py's role for reviews.
agents/visual_planner/ reuses this same function directly rather than
duplicating it — see that agent's pipeline.py.
"""
from __future__ import annotations

import hashlib


def compute_script_content_hash(script_text: str) -> str:
    return hashlib.sha256(script_text.encode("utf-8")).hexdigest()
