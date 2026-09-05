"""Phase 8's first production-capable VoiceProvider — genuine synthesized
speech via ffmpeg's built-in libflite text-to-speech filter. A second
`VoiceProvider` implementation (provider.py); nothing in pipeline.py or
mutate.py needed to change for it to exist beyond the additive
artifact_bytes/artifact_extension fields already on `GeneratedAudio` (see
provider.py's Phase 8 note).

Why flite rather than a cloud/paid TTS vendor: CONTRACT.md's Forbidden
actions already rule out "commit[ting] the rest of the system to a
specific TTS/voice provider," and Phase 8's own task explicitly warns
against assuming an API key exists or pretending real audio was generated
when a real provider cannot be authenticated. This environment has no
configured TTS API credentials of any kind (checked, not assumed — see
STATE.md's Phase 8 report). flite ships inside ffmpeg's own build
(`--enable-libflite`, already required by agents/assembler/'s real
renderer — see agents/assembler/src/real_provider.py), needs no
credentials, no network access, and produces real, intelligible (if
robotic-sounding) spoken English, deterministically, every time — a
genuine audio artifact, never a placeholder, never a fabricated
"success."

Fails closed, never silently: `VoiceProviderConfigurationError` if this
environment cannot run flite at all (ffmpeg missing); `VoiceProviderFailure`
if ffmpeg/flite ran but produced no usable audio. Neither is ever caught
here — callers must see the real failure, per Phase 8's "Provider failure
behavior" (never silently substitute a placeholder and pretend production
succeeded).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from .provider import GeneratedAudio

FLITE_LABEL = "ffmpeg-flite (offline TTS, no network, no API key)"
DEFAULT_VOICE = "kal"
DEFAULT_SAMPLE_RATE = 22050
_SYNTHESIS_TIMEOUT_SECONDS = 300


class VoiceProviderConfigurationError(Exception):
    """This environment cannot run the real voice provider at all (e.g. no
    ffmpeg, or ffmpeg without libflite support). Never caught silently —
    see agents/voice/CONTRACT.md's Phase 8 "Provider failure behavior".
    """


class VoiceProviderFailure(Exception):
    """ffmpeg/flite ran but did not produce usable audio (non-zero exit,
    no output file, or a zero-duration/empty result)."""


def _require_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise VoiceProviderConfigurationError(
            "ffmpeg is not installed in this environment — the real voice "
            "provider (ffmpeg's libflite filter) cannot run. This is a "
            "structured configuration error, not a placeholder fallback: "
            "install ffmpeg (built with --enable-libflite) before using "
            "FliteVoiceProvider, or pass a different real VoiceProvider."
        )
    return ffmpeg_path


class FliteVoiceProvider:
    """Deterministic given identical narration text and voice — same
    input always produces the same spoken audio (flite itself is a
    deterministic synthesizer, no randomness).
    """

    label = FLITE_LABEL

    def __init__(self, voice: str = DEFAULT_VOICE, sample_rate: int = DEFAULT_SAMPLE_RATE):
        self.voice = voice
        self.sample_rate = sample_rate

    def generate(self, narration_text: str, voice_configuration: str) -> GeneratedAudio:
        if not narration_text.strip():
            raise VoiceProviderFailure("cannot synthesize empty narration text")
        ffmpeg_path = _require_ffmpeg()

        with tempfile.TemporaryDirectory() as tmp:
            # Narration is written to a file and referenced via flite's
            # `textfile=` option — never interpolated into the ffmpeg
            # filter-graph string itself, so arbitrary narration text
            # (quotes, colons, commas — all meaningful in that mini
            # language) never needs escaping and can never break out of
            # the intended filter argument.
            text_path = Path(tmp) / "narration.txt"
            text_path.write_text(narration_text, encoding="utf-8")
            wav_path = Path(tmp) / "narration.wav"

            cmd = [
                ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi",
                "-i", f"flite=textfile={text_path}:voice={self.voice}",
                "-ar", str(self.sample_rate), "-ac", "1",
                str(wav_path),
            ]
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=_SYNTHESIS_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                raise VoiceProviderFailure(
                    f"ffmpeg flite synthesis timed out after {_SYNTHESIS_TIMEOUT_SECONDS}s"
                ) from exc

            if proc.returncode != 0 or not wav_path.is_file():
                raise VoiceProviderFailure(
                    f"ffmpeg flite synthesis failed (exit {proc.returncode}): "
                    f"{proc.stderr.strip()[-2000:]}"
                )

            audio_bytes = wav_path.read_bytes()
            with wave.open(str(wav_path), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = (frames / float(rate)) if rate else 0.0

        if not audio_bytes or duration <= 0:
            raise VoiceProviderFailure(
                "ffmpeg produced an empty or zero-duration audio file — "
                "refusing to report a synthesis success that didn't happen"
            )

        return GeneratedAudio(
            provider_label=self.label,
            voice_configuration=f"flite:voice={self.voice};sample_rate={self.sample_rate}Hz",
            artifact_content="",
            duration_seconds=max(1, round(duration)),
            is_placeholder=False,
            artifact_bytes=audio_bytes,
            artifact_extension="wav",
        )


# Owner-voice follow-up: the same class under the name that reflects its
# actual role once agents/voice/src/owner_voice.py's OwnerVoiceProvider
# exists — a real, offline, no-credential fallback for tests/development
# and for a run that explicitly chooses it, never a stand-in for the
# owner's own voice. The original name is kept too (never deleted) since
# existing code/tests already import it.
LocalFallbackVoiceProvider = FliteVoiceProvider
