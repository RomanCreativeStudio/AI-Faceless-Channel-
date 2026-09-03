"""Tests 8, 9, 10: the pipeline depends only on the VoiceProvider
interface, not a specific implementation (a fake provider can be
substituted); the built-in local test provider produces a deterministic
placeholder (same input -> same output, always); placeholder output is
never automatically marked production-ready.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_voice_generation
from ..src.provider import GeneratedAudio
from ..src.test_provider import LocalTestVoiceProvider
from .builders import build_produced_item


class _FakeProvider:
    """A minimal stand-in VoiceProvider, proving pipeline.py never
    hardcodes LocalTestVoiceProvider's internals."""

    label = "fake-provider-for-tests"

    def __init__(self):
        self.calls = []

    def generate(self, narration_text: str, voice_configuration: str) -> GeneratedAudio:
        self.calls.append((narration_text, voice_configuration))
        return GeneratedAudio(
            provider_label=self.label,
            voice_configuration=voice_configuration,
            artifact_content=f"FAKE AUDIO for: {narration_text}",
            duration_seconds=42,
            is_placeholder=True,
        )


class ProviderAbstractionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(self.root)

    # --- Test 8: provider abstraction works (a custom provider can be swapped in) ---
    def test_pipeline_uses_the_injected_provider_not_a_hardcoded_one(self):
        fake = _FakeProvider()
        result = run_voice_generation(self.root, apply=True, provider=fake)
        self.assertEqual(result.provider_label, "fake-provider-for-tests")
        self.assertEqual(result.duration_seconds, 42)
        self.assertEqual(len(fake.calls), 1)

        audio_text = Path(result.audio_path).read_text(encoding="utf-8")
        self.assertTrue(audio_text.startswith("FAKE AUDIO for:"))

    # --- Test 9: the built-in test provider is deterministic ---
    def test_local_test_provider_is_deterministic(self):
        provider = LocalTestVoiceProvider(words_per_minute=150)
        first = provider.generate("The same narration text.", "voice-config-a")
        second = provider.generate("The same narration text.", "voice-config-a")
        self.assertEqual(first.artifact_content, second.artifact_content)
        self.assertEqual(first.duration_seconds, second.duration_seconds)
        self.assertTrue(first.is_placeholder)

    # --- Test 10: placeholder is never marked production-ready automatically ---
    def test_placeholder_output_is_always_labeled_and_never_production_ready(self):
        result = run_voice_generation(self.root, apply=True)
        self.assertTrue(result.is_placeholder)

        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn("TEST / PLACEHOLDER AUDIO", voice_text)
        audio_text = Path(result.audio_path).read_text(encoding="utf-8")
        self.assertIn("TEST / PLACEHOLDER AUDIO", audio_text)
        # Nowhere does apply mark this "production-ready" or advance human
        # review — QA passing (structural checks only) is not the same
        # claim as production-quality speech.
        self.assertNotIn("PRODUCTION_READY", voice_text)
        self.assertIn("not real speech, not production-quality", voice_text)


if __name__ == "__main__":
    unittest.main()
