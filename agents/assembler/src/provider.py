"""Renderer abstraction for video assembly. No specific rendering engine
is named or assumed anywhere in this module — see
agents/assembler/CONTRACT.md's "Renderer abstraction" and "Actual video
artifact status". A real renderer is a future implementation; nothing in
agents/assembler/src/pipeline.py needs to change to swap one in.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class RenderResult:
    provider_label: str
    artifact_content: str  # text content to persist as the output artifact
    format: str  # file extension / container label
    is_placeholder: bool
    playable: str  # "YES" | "NO" | "UNVERIFIED"
    # Phase 8 addition — optional/defaulted so the existing placeholder
    # renderer keeps working unchanged. A real renderer sets
    # artifact_bytes to a genuine binary video file; pipeline.py/mutate.py
    # persist whichever of artifact_content/artifact_bytes is actually
    # set — see mutate.write_output_artifact/write_output_artifact_binary.
    artifact_bytes: bytes | None = None


class VideoRenderer(Protocol):
    label: str

    def render(self, scenes: list, total_duration: int, root: Path) -> RenderResult:
        """`root` is the content item's directory — a real renderer needs
        it to resolve scenes' narration_reference/visual_reference/
        captions_reference into actual files on disk (Phase 8; the
        placeholder renderer ignores it, it only needs the string
        references themselves)."""
        ...
