"""Phase 8's first real thumbnail image renderer — reuses
agents/assets/src/illustration.py's generic, deterministic, offline PNG
renderer directly (agents/thumbnail/src/pipeline.py already imports
agents/assets/src's generic scene-reading helpers, so reusing this
equally generic rendering helper the same way is consistent with this
repo's established sibling-agent boundary: generic infrastructure is
shared, domain judgment never is).

Turns an already-produced `ThumbnailSpec` (agents/thumbnail/src/provider.py
— never rewritten or second-guessed here) into a real 1280x720 PNG. Never
generates a spec of its own, never invents title/visual concepts — this
module only renders what the spec already says, honestly labeled
GENERATED_RECONSTRUCTION-style (the same "AI-GENERATED RECONSTRUCTION"
watermark every illustration.py output carries) since a rendered
thumbnail is, definitionally, never authentic historical media.
"""
from __future__ import annotations

from ...assets.src.illustration import render_illustration_png
from .models import ThumbnailSpec

THUMBNAIL_IMAGE_LABEL = "local-illustration-renderer (Pillow, offline, no network, no external model)"
_THUMBNAIL_WIDTH, _THUMBNAIL_HEIGHT = 1280, 720


def render_thumbnail_image(spec: ThumbnailSpec) -> bytes:
    """Deterministic: the same spec always renders to the same PNG bytes."""
    prompt = spec.visual_concept or spec.title_concept
    caption = spec.text_overlay if spec.text_overlay and spec.text_overlay != "N/A" else spec.title_concept
    return render_illustration_png(
        prompt, caption=caption, width=_THUMBNAIL_WIDTH, height=_THUMBNAIL_HEIGHT,
    )
