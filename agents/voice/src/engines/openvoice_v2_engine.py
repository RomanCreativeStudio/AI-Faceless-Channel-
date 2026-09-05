"""Local, free, open-source `OwnerVoiceEngine` adapter: OpenVoice V2
(MyShell, MIT license — see `agents/voice/PROVIDER_EVALUATION.md`
Section 3.5 for why it was picked as the first real engine to test, and
`agents/voice/CONTRACT.md`'s "Owner-voice adapter contract" for the
interface this satisfies).

Fully local inference — no cloud API, no account, no credentials
(`required_credential_env_vars = []`). Two local models are involved,
both run entirely offline from checkpoint files already on disk:
MeloTTS synthesizes a base-speaker utterance of the narration text, then
OpenVoice's own `ToneColorConverter` converts that utterance's tone
color toward the owner's reference sample's extracted voice embedding.

Heavy ML dependencies (torch, the `openvoice` package, MeloTTS, the
`unidic` dictionary) are deliberately never added to this repository's
own `requirements.txt` — they live only in an isolated virtual
environment set up separately (see `agents/voice/src/engines/README.md`
for the exact, reproducible setup this adapter was actually tested
against), so the rest of this project's test suite and production
pipeline never depends on them and is never destabilized by them. Every
import of those packages below is therefore lazy (inside
`is_available()`/`synthesize()`, never at module import time) — merely
importing this module never raises just because that environment isn't
active; `is_available()` reports the precise missing-dependency reason
instead.

Never registered automatically as a side effect of using
`agents/voice/`. Nothing in `pipeline.py`, `provider_selection.py`, or
`owner_voice.py` imports this module — an operator who has actually set
up the isolated environment must explicitly `import
agents.voice.src.engines.openvoice_v2_engine` (which registers the
engine, at the bottom of this file) before
`OWNER_VOICE_ENGINE=openvoice-v2` can resolve to anything. This keeps
`agents/voice/`'s provider registry genuinely empty by default,
everywhere else in this codebase.
"""
from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path

from ..owner_voice import EngineSynthesisResult, OwnerVoiceConfig, register_owner_voice_engine

ENGINE_NAME = "openvoice-v2"

_ENV_CHECKPOINT_DIR = "OPENVOICE_V2_CHECKPOINT_DIR"
_ENV_DEVICE = "OPENVOICE_V2_DEVICE"

# MeloTTS's own language codes (demo_part3.ipynb), keyed by this
# project's OwnerVoiceConfig.language's leading subtag (e.g. "en-US" -> "en").
_MELO_LANGUAGE_BY_PREFIX = {
    "en": "EN", "es": "ES", "fr": "FR", "zh": "ZH", "ja": "JP", "jp": "JP", "ko": "KR", "kr": "KR",
}
_DEFAULT_SPEAKER_KEY_BY_LANGUAGE = {
    "EN": "en-default", "ES": "es", "FR": "fr", "ZH": "zh", "JP": "jp", "KR": "kr",
}
# The base speaker embeddings OpenVoice V2's checkpoint ships for
# English accents — config.speaking_style may name one of these
# directly (e.g. "en-us") to override the language's own default.
_KNOWN_EN_SPEAKER_KEYS = {"en-us", "en-br", "en-au", "en-india", "en-default", "en-newest"}


def _melo_language_and_speaker(config: OwnerVoiceConfig) -> tuple[str, str]:
    lang_prefix = (config.language or "en").strip().lower().split("-")[0]
    melo_language = _MELO_LANGUAGE_BY_PREFIX.get(lang_prefix, "EN")
    style = (config.speaking_style or "").strip().lower()
    if melo_language == "EN" and style in _KNOWN_EN_SPEAKER_KEYS:
        speaker_key = style
    else:
        speaker_key = _DEFAULT_SPEAKER_KEY_BY_LANGUAGE[melo_language]
    return melo_language, speaker_key


class OpenVoiceV2Engine:
    """See module docstring. `checkpoint_dir`/`device` default to the
    `OPENVOICE_V2_CHECKPOINT_DIR`/`OPENVOICE_V2_DEVICE` environment
    variables when not passed explicitly — engine-specific configuration
    stays inside this adapter, never inside the vendor-neutral
    `OwnerVoiceConfig` (see `agents/voice/CONTRACT.md`)."""

    name = ENGINE_NAME
    required_credential_env_vars: list[str] = []  # local/free — nothing to authenticate

    def __init__(self, checkpoint_dir: str | None = None, device: str | None = None):
        raw_dir = checkpoint_dir or os.environ.get(_ENV_CHECKPOINT_DIR, "")
        self.checkpoint_dir = Path(raw_dir) if raw_dir else None
        self.device = device or os.environ.get(_ENV_DEVICE, "cpu")
        self._converter = None  # lazily constructed once, reused across calls

    def is_available(self) -> tuple[bool, str]:
        try:
            import torch  # noqa: F401
        except ImportError:
            return False, (
                "torch is not importable in the current Python environment — "
                "OpenVoice V2 requires the isolated environment described in "
                "agents/voice/src/engines/README.md (torch, openvoice, MeloTTS)"
            )
        try:
            import openvoice  # noqa: F401
        except ImportError:
            return False, "the 'openvoice' package is not importable in the current Python environment"
        try:
            import melo  # noqa: F401
        except ImportError:
            return False, "MeloTTS ('melo') is not importable in the current Python environment"

        if self.checkpoint_dir is None:
            return False, f"no OpenVoice V2 checkpoint directory configured (set {_ENV_CHECKPOINT_DIR})"
        converter_config = self.checkpoint_dir / "converter" / "config.json"
        converter_ckpt = self.checkpoint_dir / "converter" / "checkpoint.pth"
        if not converter_config.is_file() or not converter_ckpt.is_file():
            return False, (
                f"OpenVoice V2 converter checkpoint not found under {self.checkpoint_dir}/converter/ "
                "— see agents/voice/src/engines/README.md for how to obtain it"
            )
        return True, "ok"

    def _load_converter(self):
        from openvoice.api import ToneColorConverter
        if self._converter is None:
            self._converter = ToneColorConverter(
                str(self.checkpoint_dir / "converter" / "config.json"), device=self.device,
            )
            self._converter.load_ckpt(str(self.checkpoint_dir / "converter" / "checkpoint.pth"))
        return self._converter

    def synthesize(self, narration_text: str, config: OwnerVoiceConfig) -> EngineSynthesisResult:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(f"OpenVoice V2 engine is not available: {reason}")
        if config.sample_path is None or not config.sample_path.is_file():
            raise RuntimeError("OpenVoice V2 engine requires a real, existing owner voice sample")

        import torch
        from melo.api import TTS
        from openvoice import se_extractor

        converter = self._load_converter()
        melo_language, speaker_key = _melo_language_and_speaker(config)

        speaker_embedding_path = self.checkpoint_dir / "base_speakers" / "ses" / f"{speaker_key}.pth"
        if not speaker_embedding_path.is_file():
            raise RuntimeError(
                f"no base speaker embedding found for {speaker_key!r} at {speaker_embedding_path}"
            )
        source_se = torch.load(str(speaker_embedding_path), map_location=self.device)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_audio_path = tmp_path / "base.wav"
            output_path = tmp_path / "output.wav"

            # The only lines in this whole adapter (or anywhere in this
            # codebase) that read the owner's private sample's contents.
            # `target_dir` is pinned to this call's own ephemeral temp
            # directory — se_extractor otherwise defaults to writing
            # VAD-split audio segments and a cached embedding under
            # "processed/" *relative to the current working directory*,
            # which could land inside this very repository depending on
            # where the caller's process happens to be running from.
            # Everything under `tmp` is deleted the moment this `with`
            # block exits, regardless of success or failure.
            target_se, _ = se_extractor.get_se(
                str(config.sample_path), converter, target_dir=str(tmp_path / "se_processing"), vad=True,
            )

            model = TTS(language=melo_language, device=self.device)
            speaker_ids = model.hps.data.spk2id
            melo_speaker_key = next(
                (k for k in speaker_ids.keys() if k.lower().replace("_", "-") == speaker_key), None,
            )
            if melo_speaker_key is None:
                raise RuntimeError(
                    f"MeloTTS has no speaker matching {speaker_key!r} for language {melo_language!r}"
                )
            model.tts_to_file(narration_text, speaker_ids[melo_speaker_key], str(base_audio_path), speed=1.0)

            converter.convert(
                audio_src_path=str(base_audio_path),
                src_se=source_se,
                tgt_se=target_se,
                output_path=str(output_path),
                message="@MyShell",
            )

            if not output_path.is_file():
                raise RuntimeError("OpenVoice V2 conversion reported success but produced no output file")
            audio_bytes = output_path.read_bytes()
            with wave.open(str(output_path), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = (frames / float(rate)) if rate else 0.0

        if not audio_bytes or duration <= 0:
            raise RuntimeError(
                "OpenVoice V2 produced an empty or zero-duration output — refusing to "
                "report a synthesis success that didn't happen"
            )

        return EngineSynthesisResult(
            audio_bytes=audio_bytes,
            extension="wav",
            duration_seconds=max(1, round(duration)),
            model_label=f"openvoice-v2:{speaker_key}",
        )


def register() -> None:
    register_owner_voice_engine(OpenVoiceV2Engine())


register()
