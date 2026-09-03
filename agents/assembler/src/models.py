"""Assembler-specific data model. Reuses agents/producer/src.hashing,
agents/assets/src.hashing, and agents/assets/src.scene_reader directly
rather than redefining them — see README.md "Relationship to other
agents".
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SceneTimelineEntry:
    scene_id: str
    filename: str
    order: int
    start: int
    end: int
    duration_seconds: int
    narration_reference: str
    visual_reference: str
    captions_reference: str
    transition_in: str
    transition_out: str
    claim_ids: list[str]


@dataclass
class AssemblyResult:
    content_id: str
    production_id: str
    timeline_id: str
    filename: str
    scenes: list[SceneTimelineEntry]
    total_duration: int
    assembly_content_hash: str
    renderer_label: str
    output_reference: str
    output_format: str
    output_hash: str
    playable: str
    assembly_status: str
    reasons: list[str]
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    stale: bool = False
    stale_reason: str = ""
    already_up_to_date: bool = False
    timeline_path: str = ""
    output_path: str = ""
    production_path: str = ""

    @property
    def produced(self) -> bool:
        return bool(self.timeline_path)
