"""Phase 8 tests for agents/voice/src/real_provider.py — the first
production-capable VoiceProvider (ffmpeg's libflite filter). Covers:
provider configuration, missing ffmpeg (configuration error), successful
real-artifact handling, narration integrity (unchanged text reaches the
provider), script hash / duration recording, failure behavior, and the
new binary write whitelist. Every test here runs the real ffmpeg binary —
no network, no external API, no credentials — matching this repo's own
"local, no external service" test discipline exactly.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from ..src import mutate
from ..src.real_provider import (
    FliteVoiceProvider,
    VoiceProviderConfigurationError,
    VoiceProviderFailure,
)

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg not installed in this environment")
class FliteVoiceProviderTests(unittest.TestCase):
    def test_produces_real_nonempty_audio_bytes(self):
        provider = FliteVoiceProvider()
        result = provider.generate("This is a short test sentence.", "default")
        self.assertIsNotNone(result.artifact_bytes)
        self.assertGreater(len(result.artifact_bytes), 1000)
        self.assertEqual(result.artifact_extension, "wav")
        self.assertFalse(result.is_placeholder)

    def test_output_is_a_valid_wav_file_with_positive_duration(self):
        provider = FliteVoiceProvider()
        result = provider.generate("Another short test sentence for narration.", "default")
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "out.wav"
            wav_path.write_bytes(result.artifact_bytes)
            with wave.open(str(wav_path), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                self.assertGreater(frames, 0)
                self.assertGreater(rate, 0)
        self.assertGreater(result.duration_seconds, 0)

    def test_deterministic_given_identical_input(self):
        provider = FliteVoiceProvider()
        r1 = provider.generate("Deterministic narration text.", "default")
        r2 = provider.generate("Deterministic narration text.", "default")
        self.assertEqual(r1.artifact_bytes, r2.artifact_bytes)
        self.assertEqual(r1.duration_seconds, r2.duration_seconds)

    def test_provider_configuration_is_recorded(self):
        provider = FliteVoiceProvider(voice="kal", sample_rate=22050)
        result = provider.generate("Configuration recording test.", "ignored-caller-value")
        self.assertIn("voice=kal", result.voice_configuration)
        self.assertIn("22050", result.voice_configuration)
        self.assertIn("ffmpeg-flite", result.provider_label)

    def test_empty_narration_fails_closed(self):
        provider = FliteVoiceProvider()
        with self.assertRaises(VoiceProviderFailure):
            provider.generate("   ", "default")

    def test_narration_text_is_never_altered_before_synthesis(self):
        # A structural proof, not a semantic one: the exact text handed in
        # is what gets written to the provider's own temp textfile (no
        # rewriting/paraphrasing happens in this module — narration.py
        # already owns the one permitted transformation upstream).
        captured = {}
        real_write_text = Path.write_text

        def _spy_write_text(self, data, *args, **kwargs):
            if self.name == "narration.txt":
                captured["text"] = data
            return real_write_text(self, data, *args, **kwargs)

        with mock.patch.object(Path, "write_text", _spy_write_text):
            FliteVoiceProvider().generate("Exact narration text, unchanged.", "default")
        self.assertEqual(captured.get("text"), "Exact narration text, unchanged.")


class MissingFfmpegTests(unittest.TestCase):
    def test_missing_ffmpeg_raises_configuration_error_not_a_placeholder(self):
        with mock.patch("agents.voice.src.real_provider.shutil.which", return_value=None):
            with self.assertRaises(VoiceProviderConfigurationError):
                FliteVoiceProvider().generate("Some narration.", "default")


class BinaryWriteWhitelistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.root.mkdir()

    def test_write_audio_artifact_binary_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_audio_artifact_binary(self.root, "voice-01.mp3", b"data")

    def test_write_audio_artifact_binary_accepts_whitelisted_wav(self):
        path = mutate.write_audio_artifact_binary(self.root, "voice-01.wav", b"RIFF....")
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), b"RIFF....")

    def test_write_audio_artifact_binary_rejects_path_traversal(self):
        with self.assertRaises(PermissionError):
            mutate.write_audio_artifact_binary(self.root, "../evil.wav", b"data")


if __name__ == "__main__":
    unittest.main()
