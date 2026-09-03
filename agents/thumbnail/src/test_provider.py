"""Deterministic local/test ThumbnailProvider — no external image-
generation API, no network, no real pixel generation. See CONTRACT.md's
"Fact / What If? framing" for the exact, deterministic title-hedging
rule this implements.
"""
from __future__ import annotations

from .models import ThumbnailSpec

_HEDGE_PREFIXES = ("what if", "could", "might")
PLACEHOLDER_NOTE = "placeholder specification only, not a real generated image"


def _already_hedged(title: str) -> bool:
    return "?" in title or title.strip().lower().startswith(_HEDGE_PREFIXES)


class LocalTestThumbnailProvider:
    """Deterministic stand-in provider. Never synthesizes new prose for
    the title — only ever wraps the existing, already-approved title in
    a fixed hedge template when required. No randomness, no network."""

    label = "local-test-thumbnail-provider"

    def generate_spec(
        self, title_source: str, visual_source: str, hedge_required: bool, authenticity_summary: str
    ) -> ThumbnailSpec:
        title = title_source.strip()
        if hedge_required and not _already_hedged(title):
            title_concept = f"What if: {title}?"
        else:
            title_concept = title

        if "GENERATED_RECONSTRUCTION" in authenticity_summary:
            focal_subject = "Generated reconstruction visual (see Authenticity considerations)"
        elif "AUTHENTIC_HISTORICAL_MEDIA" in authenticity_summary:
            focal_subject = "Authentic historical media subject (sourcing intent only)"
        else:
            focal_subject = "Text/graphic focal point"

        return ThumbnailSpec(
            title_concept=title_concept,
            visual_concept=visual_source.strip() or "N/A",
            text_overlay=title_concept,
            focal_subject=focal_subject,
            composition="Single dominant subject, minimal text, high contrast (default placeholder composition)",
        )
