"""Builds SOURCE NARRATION (verbatim, scene-order narration text) and
PROVIDER-READY NARRATION (a minimal, deterministic, documented
normalization for TTS compatibility) from a production's scenes. Reuses
agents/visual_planner/src.loader.load_scenes directly — generic
scene-file reading, not visual-planning domain logic — rather than
re-parsing scene files a third time.

The only transformation SOURCE -> PROVIDER-READY narration ever performs:
normalizing curly quotes/apostrophes to straight ASCII ones and
collapsing repeated whitespace. Nothing else. This never changes a word,
a number, a hedge phrase ("it's hard to say"), or a What If? claim
distinction — see CONTRACT.md's "Narration integrity"/Forbidden actions.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...visual_planner.src.loader import load_scenes

_WHITESPACE_RE = re.compile(r"\s+")
_QUOTE_MAP = str.maketrans(
    {"‘": "'", "’": "'", "“": '"', "”": '"'}
)


def build_source_narration(scenes_dir: Path) -> str:
    scenes = load_scenes(scenes_dir)
    scenes.sort(key=lambda s: s.order)
    return " ".join(s.narration_text for s in scenes if s.narration_text.strip())


def build_provider_ready_narration(source_narration: str) -> str:
    normalized = source_narration.translate(_QUOTE_MAP)
    return _WHITESPACE_RE.sub(" ", normalized).strip()
