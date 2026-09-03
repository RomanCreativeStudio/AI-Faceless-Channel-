"""Computes templates/CAPTIONS.md's `Captions content hash` field: sha256
of every scene's Narration text, concatenated in scene order — the exact
content captions are segmented from, so a change to any scene's
narration is detected without a separate computation.
"""
from __future__ import annotations

import hashlib


def compute_captions_content_hash(narration_texts_in_order: list[str]) -> str:
    hasher = hashlib.sha256()
    for text in narration_texts_in_order:
        hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()
