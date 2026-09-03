"""Voice-specific data model. Reuses agents/producer/src.hashing and
agents/visual_planner/src.loader directly rather than redefining them —
see README.md "Relationship to other agents".
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoiceResult:
    content_id: str
    production_id: str
    voice_id: str
    filename: str  # "voice-<n>.md"
    provider_label: str
    voice_configuration: str
    source_narration: str
    provider_ready_narration: str
    script_content_hash: str
    audio_reference: str  # "voice/voice-<n>.audio.txt" once apply writes it
    duration_seconds: int
    generation_status: str  # NOT_STARTED | IN_PROGRESS | GENERATED | REVISION_REQUIRED
    qa_status: str  # NOT_STARTED | IN_PROGRESS | PASS | REVISION_REQUIRED
    qa_reasons: list[str]
    reasons: list[str]
    is_placeholder: bool = False
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    stale: bool = False
    stale_reason: str = ""
    already_up_to_date: bool = False
    voice_path: str = ""
    audio_path: str = ""
    production_path: str = ""

    @property
    def produced(self) -> bool:
        """True only when this run actually wrote a new voice record."""
        return bool(self.voice_path)
