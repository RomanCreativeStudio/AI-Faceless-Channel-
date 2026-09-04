"""Thumbnail-specific data model."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThumbnailSpec:
    title_concept: str
    visual_concept: str
    text_overlay: str
    focal_subject: str
    composition: str


@dataclass
class ThumbnailResult:
    content_id: str
    production_id: str
    thumbnail_id: str
    filename: str
    spec: ThumbnailSpec | None
    claim_theme_relationship: str
    authenticity_considerations: str
    generation_strategy: str
    thumbnail_content_hash: str
    thumbnail_status: str
    reasons: list[str]
    # Phase 8 addition — optional/defaulted, spec-only runs are unaffected.
    image_reference: str = "NOT_RENDERED"
    image_bytes: bytes | None = None
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    stale: bool = False
    stale_reason: str = ""
    already_up_to_date: bool = False
    thumbnail_path: str = ""
    production_path: str = ""

    @property
    def produced(self) -> bool:
        return bool(self.thumbnail_path)
