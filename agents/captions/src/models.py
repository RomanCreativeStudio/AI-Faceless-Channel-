"""Captions-specific data model."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CaptionChunk:
    index: int
    start: float
    end: float
    text: str


@dataclass
class SceneCaptions:
    scene_filename: str
    scene_id: str
    chunks: list[CaptionChunk]


@dataclass
class CaptionsResult:
    content_id: str
    production_id: str
    captions_id: str
    filename: str
    scenes: list[SceneCaptions]
    captions_content_hash: str
    max_characters_per_line: int
    max_lines_per_caption: int
    generation_status: str
    reasons: list[str]
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    stale: bool = False
    stale_reason: str = ""
    already_up_to_date: bool = False
    captions_path: str = ""
    production_path: str = ""

    @property
    def produced(self) -> bool:
        return bool(self.captions_path)
