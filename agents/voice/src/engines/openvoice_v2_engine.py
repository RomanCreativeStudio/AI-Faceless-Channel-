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
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from ..owner_voice import EngineSynthesisResult, OwnerVoiceConfig, register_owner_voice_engine

_CHUNK_WORKER_PATH = Path(__file__).parent / "_openvoice_v2_chunk_worker.py"

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


# A full episode's narration synthesized in one MeloTTS + ToneColorConverter
# call was observed to exhaust this project's sandboxed environment's
# memory ceiling (real, reproduced OOM-kill during real testing — see
# STATE.md / OPENVOICE_V2_TEST_REPORT.md's "Full Episode 1 narration"
# section for the exact evidence). Splitting into bounded-size chunks and
# synthesizing/converting each independently, then concatenating the
# resulting PCM frames, keeps peak memory bounded regardless of total
# script length. This is purely an internal execution detail: the
# `narration_text` argument `synthesize()` receives is never altered,
# reordered, or dropped — only the audio it produces is assembled from
# pieces, with no effect on what run_voice_generation()/OwnerVoiceProvider
# record as the narration/script-hash relationship (those never see or
# depend on how the engine internally chose to synthesize the audio).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_DEFAULT_CHUNK_MAX_WORDS = 100


def _chunk_narration(text: str, max_words: int = _DEFAULT_CHUNK_MAX_WORDS) -> list[str]:
    """Greedily groups whole sentences (never splits mid-sentence) into
    chunks of at most `max_words` words each, in original order. Every
    chunk is an exact, verbatim substring-derived piece of `text` — no
    word is ever added, removed, or reordered across this function."""
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    if not sentences:
        return [text] if text.strip() else []
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        words = len(sentence.split())
        if current and current_words + words > max_words:
            chunks.append(" ".join(current))
            current = []
            current_words = 0
        current.append(sentence)
        current_words += words
    if current:
        chunks.append(" ".join(current))
    return chunks


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
        from openvoice import se_extractor

        converter = self._load_converter()
        melo_language, speaker_key = _melo_language_and_speaker(config)

        speaker_embedding_path = self.checkpoint_dir / "base_speakers" / "ses" / f"{speaker_key}.pth"
        if not speaker_embedding_path.is_file():
            raise RuntimeError(
                f"no base speaker embedding found for {speaker_key!r} at {speaker_embedding_path}"
            )

        chunks = _chunk_narration(narration_text)
        if not chunks:
            raise RuntimeError("OpenVoice V2 engine received empty narration text")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

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
            # Persisted only as a derived voice-embedding TENSOR (never
            # the raw sample itself) to this same ephemeral tempdir, so
            # the per-chunk subprocess below can load it without ever
            # touching config.sample_path — deleted with everything else
            # when this `with` block exits.
            target_se_path = tmp_path / "target_se.pt"
            torch.save(target_se, str(target_se_path))

            # Each chunk is synthesized and tone-converted in its OWN
            # subprocess (see _openvoice_v2_chunk_worker.py's module
            # docstring for why): THREE separate real attempts —
            # unchunked, chunked, and chunked + torch.inference_mode() —
            # were each independently OOM-killed at the same ~13.9GB
            # ceiling (confirmed via dmesg each time), pointing to
            # memory retained inside PyTorch's/MeloTTS's/OpenVoice's own
            # internals across repeated in-process calls, not something
            # `del`/`gc.collect()`/`inference_mode()` from within the
            # same process could force free. A subprocess's memory is
            # unconditionally reclaimed by the OS the instant it exits,
            # regardless of the exact cause — the only fix guaranteed to
            # work without depending on library-internal behavior this
            # adapter doesn't control.
            wav_params = None
            combined_frames = bytearray()
            for index, chunk_text in enumerate(chunks):
                text_path = tmp_path / f"chunk_{index}.txt"
                chunk_output_path = tmp_path / f"output_{index}.wav"
                text_path.write_text(chunk_text, encoding="utf-8")

                proc = subprocess.run(
                    [
                        sys.executable, str(_CHUNK_WORKER_PATH),
                        "--checkpoint-dir", str(self.checkpoint_dir),
                        "--device", self.device,
                        "--melo-language", melo_language,
                        "--speaker-key", speaker_key,
                        "--text-file", str(text_path),
                        "--target-se-path", str(target_se_path),
                        "--output-path", str(chunk_output_path),
                    ],
                    capture_output=True, text=True,
                )
                if proc.returncode != 0 or not chunk_output_path.is_file():
                    stderr_tail = (proc.stderr or "").strip().splitlines()[-1:] or ["(no stderr)"]
                    raise RuntimeError(
                        f"OpenVoice V2 chunk worker failed for narration chunk "
                        f"{index + 1}/{len(chunks)} (exit code {proc.returncode}): {stderr_tail[0]}"
                    )
                with wave.open(str(chunk_output_path), "rb") as wav_file:
                    params = wav_file.getparams()
                    frames = wav_file.readframes(wav_file.getnframes())
                if wav_params is None:
                    wav_params = params
                elif (params.nchannels, params.sampwidth, params.framerate) != (
                    wav_params.nchannels, wav_params.sampwidth, wav_params.framerate,
                ):
                    raise RuntimeError(
                        f"OpenVoice V2 chunk {index + 1}/{len(chunks)} produced audio with "
                        "different format than earlier chunks — refusing to concatenate "
                        "mismatched audio"
                    )
                combined_frames += frames

                text_path.unlink(missing_ok=True)
                chunk_output_path.unlink(missing_ok=True)

            if wav_params is None or not combined_frames:
                raise RuntimeError("OpenVoice V2 produced no audio output across any narration chunk")

            output_path = tmp_path / "output_combined.wav"
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setparams(wav_params)
                wav_file.writeframes(bytes(combined_frames))

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
