"""The owner-authorized voice provider: a second `VoiceProvider`
implementation (provider.py) for narrating episodes in the channel's
human owner's own voice, once a real voice-cloning engine and the
owner's consent-backed voice sample are actually configured. Nothing in
`pipeline.py`, `mutate.py`, or `templates/VOICE.md` changes for this to
exist — same seam Phase 8's `FliteVoiceProvider` already used.

Design constraints (see agents/voice/CONTRACT.md and this module's own
task): no specific commercial voice vendor is named or hard-coded
anywhere here; no cloud API is assumed configured; the owner's raw voice
sample is never read into any committed file or persisted metadata, only
referenced by a private, environment-configured filesystem path; this
provider is explicitly, permanently labeled `OWNER_AUTHORIZED_VOICE` — it
is not a generic arbitrary-person voice-cloning system and has no
capability to clone anyone else's voice.

Because no voice-cloning engine ships with this repository (a real one
would be a proprietary local model or a paid cloud service — this
module deliberately picks neither), synthesis is delegated to a small
`OwnerVoiceEngine` Protocol looked up by name
(`OWNER_VOICE_ENGINE`) in a registry that starts empty. Until a real
engine is registered (a future, separate piece of work, once an actual
provider is chosen per this task's own "Provider selection" criteria),
`check_owner_voice_availability()` always reports
`OwnerVoiceStatus.NOT_CONFIGURED` with a precise reason — never
`AVAILABLE`, and `OwnerVoiceProvider.generate()` always raises rather
than silently substituting a different voice.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from .provider import GeneratedAudio

OWNER_AUTHORIZATION_LABEL = "OWNER_AUTHORIZED_VOICE"

_ENV_SAMPLE_PATH = "OWNER_VOICE_SAMPLE_PATH"
_ENV_VOICE_ID = "OWNER_VOICE_ID"
_ENV_ENGINE = "OWNER_VOICE_ENGINE"
_ENV_MODEL = "OWNER_VOICE_MODEL"
_ENV_LANGUAGE = "OWNER_VOICE_LANGUAGE"
_ENV_STYLE = "OWNER_VOICE_STYLE"
_ENV_STABILITY = "OWNER_VOICE_STABILITY"
_ENV_CONSISTENCY = "OWNER_VOICE_CONSISTENCY"
_ENV_PRONUNCIATION = "OWNER_VOICE_PRONUNCIATION"

_DEFAULT_LANGUAGE = "en"


def _parse_pronunciation(raw: str | None) -> dict[str, str]:
    """"word=phonetic;word2=phonetic2" -> {"word": "phonetic", ...}. Never
    raises on malformed input — an optional convenience field, not a
    correctness-critical one; a malformed entry is just dropped."""
    if not raw:
        return {}
    overrides: dict[str, str] = {}
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        word, _, phonetic = pair.partition("=")
        word, phonetic = word.strip(), phonetic.strip()
        if word and phonetic:
            overrides[word] = phonetic
    return overrides


def _parse_float(raw: str | None) -> float | None:
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class OwnerVoiceConfig:
    """Everything needed to attempt owner-voice synthesis. Deliberately
    provider-agnostic: `engine_name` selects an `OwnerVoiceEngine`
    implementation (see registry below) by name — nothing here assumes
    what that engine actually is. `sample_path` is a private, local
    filesystem reference only; its *contents* are never read by this
    dataclass and never appear in any field this module returns to a
    caller (see `redacted_summary()`).
    """

    voice_id: str = ""
    engine_name: str = ""
    sample_path: Path | None = None
    model_id: str = ""
    language: str = _DEFAULT_LANGUAGE
    speaking_style: str = ""
    stability: float | None = None
    consistency: float | None = None
    pronunciation: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "OwnerVoiceConfig":
        env = environ if environ is not None else os.environ
        sample_raw = env.get(_ENV_SAMPLE_PATH, "").strip()
        return cls(
            voice_id=env.get(_ENV_VOICE_ID, "").strip(),
            engine_name=env.get(_ENV_ENGINE, "").strip(),
            sample_path=Path(sample_raw) if sample_raw else None,
            model_id=env.get(_ENV_MODEL, "").strip(),
            language=env.get(_ENV_LANGUAGE, "").strip() or _DEFAULT_LANGUAGE,
            speaking_style=env.get(_ENV_STYLE, "").strip(),
            stability=_parse_float(env.get(_ENV_STABILITY)),
            consistency=_parse_float(env.get(_ENV_CONSISTENCY)),
            pronunciation=_parse_pronunciation(env.get(_ENV_PRONUNCIATION)),
        )

    def redacted_summary(self) -> dict:
        """Safe to log/print/persist: names and identifiers only, never
        the sample file's contents, never any credential value. The
        sample path itself is deliberately omitted too — a local
        filesystem path is still private operational detail, not
        something this system's own output should echo back."""
        return {
            "voice_id": self.voice_id or None,
            "engine": self.engine_name or None,
            "model_id": self.model_id or None,
            "language": self.language,
            "speaking_style": self.speaking_style or None,
            "stability": self.stability,
            "consistency": self.consistency,
            "pronunciation_overrides": len(self.pronunciation),
            "sample_configured": self.sample_path is not None,
        }

    def voice_configuration_string(self) -> str:
        """The opaque, provider-agnostic string persisted into
        `templates/VOICE.md`'s `Voice configuration` field — identifiers
        only, matching `redacted_summary()`'s privacy boundary exactly."""
        parts = [
            f"owner-voice:engine={self.engine_name or 'n/a'}",
            f"voice_id={self.voice_id or 'n/a'}",
            f"model={self.model_id or 'n/a'}",
            f"language={self.language}",
            f"style={self.speaking_style or 'n/a'}",
        ]
        if self.stability is not None:
            parts.append(f"stability={self.stability}")
        if self.consistency is not None:
            parts.append(f"consistency={self.consistency}")
        if self.pronunciation:
            parts.append(f"pronunciation_overrides={len(self.pronunciation)}")
        return ";".join(parts)


class OwnerVoiceStatus(str, Enum):
    OWNER_VOICE_AVAILABLE = "OWNER_VOICE_AVAILABLE"
    OWNER_VOICE_NOT_CONFIGURED = "OWNER_VOICE_NOT_CONFIGURED"


@dataclass
class OwnerVoiceAvailability:
    status: OwnerVoiceStatus
    reason: str

    @property
    def available(self) -> bool:
        return self.status is OwnerVoiceStatus.OWNER_VOICE_AVAILABLE


@dataclass
class EngineSynthesisResult:
    audio_bytes: bytes
    extension: str
    duration_seconds: int
    model_label: str = ""


class OwnerVoiceEngine(Protocol):
    """A real voice-cloning/TTS backend, looked up by name. No
    implementation ships in this repository — this is the seam a future,
    deliberately-chosen provider (local model or paid cloud service)
    fills in, per this task's own "Provider selection" priorities
    (owner-authorized cloning, quality, privacy, predictable cost,
    accessibility, cross-episode consistency)."""

    name: str
    required_credential_env_vars: list[str]

    def is_available(self) -> tuple[bool, str]:
        """Engine-specific extra checks beyond credentials (e.g. a
        required local package is importable, a local model file is
        present). Returns (ok, reason)."""
        ...

    def synthesize(self, narration_text: str, config: OwnerVoiceConfig) -> EngineSynthesisResult:
        ...


_ENGINE_REGISTRY: dict[str, OwnerVoiceEngine] = {}


def register_owner_voice_engine(engine: OwnerVoiceEngine) -> None:
    _ENGINE_REGISTRY[engine.name] = engine


def get_owner_voice_engine(name: str) -> OwnerVoiceEngine | None:
    return _ENGINE_REGISTRY.get(name)


def registered_engine_names() -> list[str]:
    return sorted(_ENGINE_REGISTRY)


def check_owner_voice_availability(config: OwnerVoiceConfig) -> OwnerVoiceAvailability:
    """Never raises. Never returns AVAILABLE unless every real
    precondition — identity, a real sample, a real registered engine,
    that engine's own credentials, and that engine's own extra checks —
    genuinely holds. Reasons never include a credential's value or the
    sample file's contents; env var *names* and identifiers only."""
    def _not_configured(reason: str) -> OwnerVoiceAvailability:
        return OwnerVoiceAvailability(OwnerVoiceStatus.OWNER_VOICE_NOT_CONFIGURED, reason)

    if not config.voice_id:
        return _not_configured(
            f"no owner-authorized voice identifier configured (set {_ENV_VOICE_ID})"
        )
    if config.sample_path is None:
        return _not_configured(
            f"owner voice sample not configured (set {_ENV_SAMPLE_PATH} to a private, "
            "local audio/video file — never committed to this repository)"
        )
    if not config.sample_path.is_file():
        return _not_configured(
            f"{_ENV_SAMPLE_PATH} does not point to an existing file"
        )
    if config.sample_path.stat().st_size == 0:
        return _not_configured("the configured owner voice sample file is empty")
    if not config.engine_name:
        return _not_configured(
            f"no voice-cloning engine configured (set {_ENV_ENGINE}); no vendor is "
            "selected by default — see agents/voice/README.md's \"Provider selection\""
        )
    engine = get_owner_voice_engine(config.engine_name)
    if engine is None:
        available = registered_engine_names()
        return _not_configured(
            f"no engine implementation registered for {_ENV_ENGINE}={config.engine_name!r}"
            + (f" (registered: {available})" if available else " (none registered in this build)")
        )
    missing_creds = [v for v in engine.required_credential_env_vars if not os.environ.get(v)]
    if missing_creds:
        return _not_configured(
            "missing required credential environment variable(s): " + ", ".join(missing_creds)
        )
    engine_ok, engine_reason = engine.is_available()
    if not engine_ok:
        return _not_configured(engine_reason)
    return OwnerVoiceAvailability(
        OwnerVoiceStatus.OWNER_VOICE_AVAILABLE,
        f"engine {config.engine_name!r} ready for voice_id {config.voice_id!r}",
    )


class OwnerVoiceNotConfiguredError(Exception):
    """Raised by generate() whenever check_owner_voice_availability()
    would report NOT_CONFIGURED. Never caught internally — a production
    run explicitly requesting the owner's voice must fail visibly rather
    than silently narrate in a different voice (agents/voice/CONTRACT.md
    "Forbidden actions" already rules out masquerading placeholder/
    fallback output as production-ready; the same rule applies here with
    added force, since a wrong voice is a misrepresentation of who is
    speaking, not just of quality)."""


class OwnerVoiceProviderFailure(Exception):
    """The engine was available and ran, but produced no usable audio."""


class OwnerVoiceProvider:
    """`VoiceProvider` implementation for the channel owner's own,
    explicitly authorized voice. Every `GeneratedAudio` this returns
    carries `OWNER_AUTHORIZATION_LABEL` in its provider label — this is
    never a generic voice-cloning provider for an arbitrary person, and
    has no code path that could be pointed at anyone else's sample and
    still claim owner authorization."""

    def __init__(self, config: OwnerVoiceConfig | None = None):
        self.config = config or OwnerVoiceConfig.from_env()

    @property
    def label(self) -> str:
        return (
            f"owner-voice:{self.config.engine_name or 'unconfigured'} "
            f"({OWNER_AUTHORIZATION_LABEL}, voice_id={self.config.voice_id or 'unconfigured'})"
        )

    def generate(self, narration_text: str, voice_configuration: str) -> GeneratedAudio:
        if not narration_text.strip():
            raise OwnerVoiceProviderFailure("cannot synthesize empty narration text")

        availability = check_owner_voice_availability(self.config)
        if not availability.available:
            raise OwnerVoiceNotConfiguredError(
                f"OWNER_VOICE is not available: {availability.reason} — this production "
                "run will not silently substitute a different voice; configure the "
                "owner voice provider and retry, or explicitly select a different "
                "VoiceProvider if generic/fallback narration is actually intended."
            )

        engine = get_owner_voice_engine(self.config.engine_name)
        synthesized = engine.synthesize(narration_text, self.config)
        if not synthesized.audio_bytes or synthesized.duration_seconds <= 0:
            raise OwnerVoiceProviderFailure(
                f"engine {self.config.engine_name!r} reported success but produced "
                "no usable audio — refusing to report a synthesis that didn't happen"
            )

        return GeneratedAudio(
            provider_label=self.label,
            voice_configuration=self.config.voice_configuration_string(),
            artifact_content="",
            duration_seconds=synthesized.duration_seconds,
            is_placeholder=False,
            artifact_bytes=synthesized.audio_bytes,
            artifact_extension=synthesized.extension,
        )
