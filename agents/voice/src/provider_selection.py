"""resolve_voice_provider() — the one place a caller (CLI, full_pipeline,
a human running production) names which `VoiceProvider` it wants, by a
short, stable string, without needing to import or know about the
provider classes themselves. Supports today's three implementations and
nothing pipeline.py/mutate.py needs to change for a fourth: add a case
here, or (for owner voice's own real engines) call
`agents/voice/src/owner_voice.py`'s `register_owner_voice_engine`
instead — this function itself never grows vendor-specific branches.
"""
from __future__ import annotations

from .owner_voice import OwnerVoiceConfig, OwnerVoiceProvider
from .provider import VoiceProvider
from .real_provider import DEFAULT_SAMPLE_RATE, DEFAULT_VOICE, LocalFallbackVoiceProvider
from .test_provider import DEFAULT_TEST_WORDS_PER_MINUTE, LocalTestVoiceProvider

PROVIDER_LOCAL_TEST = "local-test"
PROVIDER_LOCAL_FALLBACK = "local-fallback"
PROVIDER_OWNER_VOICE = "owner-voice"

KNOWN_PROVIDER_NAMES = (PROVIDER_LOCAL_TEST, PROVIDER_LOCAL_FALLBACK, PROVIDER_OWNER_VOICE)


def resolve_voice_provider(
    name: str,
    *,
    words_per_minute: int = DEFAULT_TEST_WORDS_PER_MINUTE,
    fallback_voice: str = DEFAULT_VOICE,
    fallback_sample_rate: int = DEFAULT_SAMPLE_RATE,
    owner_voice_config: OwnerVoiceConfig | None = None,
) -> VoiceProvider:
    """Raises ValueError for any name not in KNOWN_PROVIDER_NAMES —
    never silently falls back to a default provider for a typo'd or
    unrecognized request, since that is exactly the kind of silent
    identity switch agents/voice/CONTRACT.md and this task's own
    "Failure behavior" rule out."""
    if name == PROVIDER_LOCAL_TEST:
        return LocalTestVoiceProvider(words_per_minute=words_per_minute)
    if name == PROVIDER_LOCAL_FALLBACK:
        return LocalFallbackVoiceProvider(voice=fallback_voice, sample_rate=fallback_sample_rate)
    if name == PROVIDER_OWNER_VOICE:
        return OwnerVoiceProvider(owner_voice_config)
    raise ValueError(
        f"unknown voice provider {name!r} — expected one of {list(KNOWN_PROVIDER_NAMES)}"
    )
