"""Deterministic local/test VoiceProvider — no external API, no network,
no real speech synthesis. Exists to prove the pipeline end-to-end; a real
TTS provider implements the same VoiceProvider interface (provider.py)
and can be swapped in (agents/voice/src/pipeline.py's `provider=`
argument) without changing pipeline.py or mutate.py at all.

Output is explicitly, permanently labeled placeholder — never mistaken
for production-quality speech (CONTRACT.md's "Forbidden actions": "Mark
placeholder output as production-ready").
"""
from __future__ import annotations

import hashlib

from ...producer.src.duration import estimate_duration_seconds
from .provider import GeneratedAudio

PLACEHOLDER_LABEL = "TEST / PLACEHOLDER AUDIO — not real speech, not production-quality"
DEFAULT_TEST_WORDS_PER_MINUTE = 150


class LocalTestVoiceProvider:
    """Deterministic stand-in provider. Same narration + same
    words_per_minute always produces the same duration and the same
    placeholder artifact content — no randomness, no network calls, no
    real audio synthesis of any kind."""

    label = "local-test-provider"

    def __init__(self, words_per_minute: int = DEFAULT_TEST_WORDS_PER_MINUTE):
        self.words_per_minute = words_per_minute

    def generate(self, narration_text: str, voice_configuration: str) -> GeneratedAudio:
        duration = estimate_duration_seconds(narration_text, self.words_per_minute)
        content_hash = hashlib.sha256(narration_text.encode("utf-8")).hexdigest()[:16]
        artifact_content = (
            f"{PLACEHOLDER_LABEL}\n"
            f"Provider: {self.label}\n"
            f"Voice configuration: {voice_configuration}\n"
            f"Narration content hash: {content_hash}\n"
            f"Estimated duration: {duration}s\n"
            "---\n"
            f"{narration_text}\n"
        )
        return GeneratedAudio(
            provider_label=self.label,
            voice_configuration=voice_configuration,
            artifact_content=artifact_content,
            duration_seconds=duration,
            is_placeholder=True,
        )
