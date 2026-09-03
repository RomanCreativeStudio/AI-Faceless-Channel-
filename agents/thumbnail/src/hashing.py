"""Computes templates/THUMBNAIL.md's `Thumbnail content hash` field:
sha256 of CONTENT_ITEM.md's Working title, content pillar, and every
referenced claim's Classification (in scene order).
"""
from __future__ import annotations

import hashlib


def compute_thumbnail_content_hash(
    working_title: str, content_pillar: str, classifications_in_order: list[str]
) -> str:
    hasher = hashlib.sha256()
    hasher.update(working_title.encode("utf-8"))
    hasher.update(content_pillar.encode("utf-8"))
    for classification in classifications_in_order:
        hasher.update(classification.encode("utf-8"))
    return hasher.hexdigest()
