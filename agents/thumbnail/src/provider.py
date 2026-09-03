"""Thumbnail concept provider abstraction. No external image-generation
vendor is named or assumed anywhere in this module — see
agents/thumbnail/CONTRACT.md's "Provider abstraction". A real
image-generation integration is a future implementation; nothing in
agents/thumbnail/src/pipeline.py needs to change to swap one in.
"""
from __future__ import annotations

from typing import Protocol

from .models import ThumbnailSpec


class ThumbnailProvider(Protocol):
    label: str

    def generate_spec(
        self, title_source: str, visual_source: str, hedge_required: bool, authenticity_summary: str
    ) -> ThumbnailSpec:
        ...
