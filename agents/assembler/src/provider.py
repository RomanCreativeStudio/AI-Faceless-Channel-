"""Renderer abstraction for video assembly. No specific rendering engine
is named or assumed anywhere in this module — see
agents/assembler/CONTRACT.md's "Renderer abstraction" and "Actual video
artifact status". A real renderer is a future implementation; nothing in
agents/assembler/src/pipeline.py needs to change to swap one in.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RenderResult:
    provider_label: str
    artifact_content: str  # text content to persist as the output artifact
    format: str  # file extension / container label
    is_placeholder: bool
    playable: str  # "YES" | "NO" | "UNVERIFIED"


class VideoRenderer(Protocol):
    label: str

    def render(self, scenes: list, total_duration: int) -> RenderResult:
        ...
