"""Deterministic, offline illustration renderer — Pillow only, no external
image-generation API, no network call, no randomness. Turns a text prompt
into a genuinely real (not placeholder) PNG: a clean documentary/
infographic-style card — gradient background, a simple abstract geometric
motif, and a caption — deliberately never photorealistic, so it is always
honestly presentable as `GENERATED_RECONSTRUCTION`
(templates/ASSET.md), never mistaken for `AUTHENTIC_HISTORICAL_MEDIA`. A
small "AI-GENERATED RECONSTRUCTION" label is burned directly into the
image itself, in addition to (never instead of) the separately-recorded
Historical authenticity classification metadata.

Generic, domain-agnostic rendering only — no editorial/classification
judgment lives here (that stays in agents/assets/src/classification.py and
wherever a caller decides an asset needs one); this module only turns a
prompt + size into a deterministic image. Reused by both
agents/assets/src/real_providers.py and agents/thumbnail/src/real_provider.py
— agents/thumbnail/ already imports agents/assets/src's generic
scene-reading helpers directly (see thumbnail/src/pipeline.py), so reusing
this equally generic rendering helper the same way is consistent with this
repo's existing sibling-agent boundary (generic infrastructure is shared;
domain judgment is never imported cross-agent).
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
_TITLE_FONT_PATH = _FONT_DIR / "DejaVuSerif-Bold.ttf"
_LABEL_FONT_PATH = _FONT_DIR / "DejaVuSans-Bold.ttf"

# Deterministic keyword -> (top color, bottom color) palette, biased toward
# this project's actual recurring visual themes (Phase 8 task's own list:
# plague-era environments, medieval cities, quarantine/sanitation concepts,
# hospital/medical concepts, modern contrast, maps/diagrams). Never a
# per-domain "authority" judgment — purely a deterministic style choice.
_KEYWORD_PALETTES: list[tuple[tuple[str, ...], tuple[tuple[int, int, int], tuple[int, int, int]]]] = [
    (("plague", "black death", "medieval city", "medieval", "quarantine", "isolation"),
     ((46, 33, 26), (92, 68, 42))),
    (("sanitation", "clean water", "hygiene", "handwash"),
     ((21, 55, 63), (54, 112, 117))),
    (("hospital", "medical", "clinic", "physician", "doctor", "health worker"),
     ((28, 43, 66), (63, 94, 128))),
    (("modern", "contrast", "today", "contemporary"),
     ((17, 24, 39), (37, 99, 235))),
    (("map", "diagram", "chart", "infographic"),
     ((36, 40, 47), (80, 94, 118))),
]
_DEFAULT_PALETTE = ((35, 30, 40), (76, 61, 81))

WATERMARK_TEXT = "AI-GENERATED RECONSTRUCTION — ILLUSTRATIVE, NOT A HISTORICAL PHOTOGRAPH"


def _palette_for(text: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    lowered = text.lower()
    for keywords, palette in _KEYWORD_PALETTES:
        if any(k in lowered for k in keywords):
            return palette
    return _DEFAULT_PALETTE


def _deterministic_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if not current or draw.textlength(trial, font=font) <= max_width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def render_illustration_png(
    prompt: str, caption: str | None = None, width: int = 1920, height: int = 1080,
    draw_caption: bool = True,
) -> bytes:
    """Deterministic: the same (prompt, caption, width, height,
    draw_caption) always produces byte-identical PNG output — no
    randomness, no network call, no external model of any kind.

    `draw_caption=False` (Phase 8 — used by scene-asset generation, see
    agents/assets/src/real_providers.py) omits the burned-in title/caption
    text entirely, leaving only the background + motif + watermark. A
    scene's real narration is already captioned separately, in sync,
    by the video renderer's own subtitle burn-in
    (agents/assembler/src/real_provider.py) — this image's own caption
    text is not just redundant there, it visually collides with those
    real, timed subtitles (same lower-third placement, different text,
    unreadable overlap). `draw_caption=True` (the default) keeps this
    module's original behavior for callers that have no separate caption
    track of their own — e.g. agents/thumbnail/, which needs the image
    itself to carry its title text.
    """
    top, bottom = _palette_for(prompt)
    seed = _deterministic_seed(prompt)

    img = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        row = tuple(round(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
        draw.line([(0, y), (width, y)], fill=row)

    # Deterministic abstract motif (concentric rings) — position/size
    # derived from the prompt's own hash, never photorealistic.
    cx = width * (0.25 + 0.5 * ((seed % 1000) / 1000))
    cy = height * 0.40
    base_radius = min(width, height) * 0.30
    ring_color = tuple(min(255, c + 45) for c in bottom)
    for i in range(4, 0, -1):
        r = base_radius * (i / 4)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring_color, width=3)

    title_font = ImageFont.truetype(str(_TITLE_FONT_PATH), size=int(height * 0.052))
    label_font = ImageFont.truetype(str(_LABEL_FONT_PATH), size=max(14, int(height * 0.024)))

    if draw_caption:
        caption_text = (caption or prompt).strip()
        max_text_width = width * 0.82
        lines = _wrap_text(draw, caption_text, title_font, max_text_width)[:4]
        line_height = title_font.size + 10
        text_y = height * 0.72
        for i, line in enumerate(lines):
            line_width = draw.textlength(line, font=title_font)
            x = (width - line_width) / 2
            y = text_y + i * line_height
            draw.text((x + 2, y + 2), line, font=title_font, fill=(0, 0, 0))
            draw.text((x, y), line, font=title_font, fill=(255, 255, 255))

    label_width = draw.textlength(WATERMARK_TEXT, font=label_font)
    pad = max(6, int(height * 0.015))
    bar_height = label_font.size + pad * 2
    draw.rectangle([0, height - bar_height, min(width, label_width + pad * 2), height], fill=(0, 0, 0))
    draw.text((pad, height - bar_height + pad), WATERMARK_TEXT, font=label_font, fill=(255, 210, 90))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
