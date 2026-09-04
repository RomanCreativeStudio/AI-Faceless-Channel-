"""Provider abstraction for voice generation. No specific TTS/voice
vendor is named or assumed anywhere in this module — see
templates/VOICE.md's "Provider-agnostic by design" and
agents/voice/CONTRACT.md's "Provider abstraction". A real TTS provider is
a future VoiceProvider implementation; nothing in
agents/voice/src/pipeline.py or mutate.py needs to change to swap one in.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class GeneratedAudio:
    provider_label: str
    voice_configuration: str
    artifact_content: str  # text content to persist as the audio artifact reference
    duration_seconds: int
    is_placeholder: bool  # True for any non-production-quality output
    # Phase 8 additions — both optional/defaulted so every existing
    # (placeholder/text) provider keeps working unchanged. A real provider
    # sets artifact_bytes to genuine binary audio data and artifact_extension
    # to its real container format ("wav", "mp3", ...); pipeline.py/mutate.py
    # persist whichever of artifact_content/artifact_bytes is actually set —
    # see mutate.write_audio_artifact/write_audio_artifact_binary.
    artifact_bytes: bytes | None = None
    artifact_extension: str = "audio.txt"


class VoiceProvider(Protocol):
    """Adapter interface every voice provider (test or real) implements."""

    label: str

    def generate(self, narration_text: str, voice_configuration: str) -> GeneratedAudio:
        ...
