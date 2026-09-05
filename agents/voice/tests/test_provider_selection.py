"""resolve_voice_provider(): selecting owner voice, local fallback, or
local test by name, and rejecting anything unrecognized rather than
silently defaulting."""
import unittest

from ..src.owner_voice import OwnerVoiceConfig, OwnerVoiceProvider
from ..src.provider_selection import (
    PROVIDER_LOCAL_FALLBACK,
    PROVIDER_LOCAL_TEST,
    PROVIDER_OWNER_VOICE,
    resolve_voice_provider,
)
from ..src.real_provider import FliteVoiceProvider, LocalFallbackVoiceProvider
from ..src.test_provider import LocalTestVoiceProvider


class ProviderSelectionTests(unittest.TestCase):
    def test_local_test_selected(self):
        provider = resolve_voice_provider(PROVIDER_LOCAL_TEST, words_per_minute=180)
        self.assertIsInstance(provider, LocalTestVoiceProvider)
        self.assertEqual(provider.words_per_minute, 180)

    def test_local_fallback_selected_and_is_flite(self):
        # LocalFallbackVoiceProvider is the Flite provider under its
        # role-accurate name — not a rewrite, not a deletion.
        self.assertIs(LocalFallbackVoiceProvider, FliteVoiceProvider)
        provider = resolve_voice_provider(PROVIDER_LOCAL_FALLBACK, fallback_voice="kal", fallback_sample_rate=16000)
        self.assertIsInstance(provider, FliteVoiceProvider)
        self.assertEqual(provider.voice, "kal")
        self.assertEqual(provider.sample_rate, 16000)

    def test_owner_voice_selected_with_explicit_config(self):
        config = OwnerVoiceConfig(voice_id="owner-default")
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE, owner_voice_config=config)
        self.assertIsInstance(provider, OwnerVoiceProvider)
        self.assertIs(provider.config, config)

    def test_owner_voice_selected_falls_back_to_env_when_no_config_given(self):
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE)
        self.assertIsInstance(provider, OwnerVoiceProvider)

    def test_unknown_provider_name_rejected(self):
        with self.assertRaises(ValueError):
            resolve_voice_provider("some-cloud-vendor-nobody-configured")

    def test_unknown_provider_name_never_silently_defaults(self):
        # A typo must fail loudly, not quietly hand back local-test.
        with self.assertRaises(ValueError) as ctx:
            resolve_voice_provider("owner-voice-typo")
        self.assertIn("owner-voice-typo", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
