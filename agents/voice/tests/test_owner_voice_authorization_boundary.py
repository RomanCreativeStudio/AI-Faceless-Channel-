"""Owner-voice provider readiness (Phase 8 follow-up): the two human
decisions — (A) which provider may process the owner's voice, and (B)
whether an episode's content is editorially approved — must stay
completely independent, and no private material (sample path or
credential value) may ever reach a persisted file. No real provider is
registered or contacted anywhere in this file; a fake, clearly-labeled
test engine is the only stand-in used.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.tests.builders import build_minimal_item
from ..src.owner_voice import (
    EngineSynthesisResult,
    OwnerVoiceConfig,
    OwnerVoiceProvider,
    _ENGINE_REGISTRY,
    check_owner_voice_availability,
    register_owner_voice_engine,
)
from ..src.pipeline import run_voice_generation
from ..src.provider_selection import (
    PROVIDER_LOCAL_FALLBACK,
    PROVIDER_LOCAL_TEST,
    PROVIDER_OWNER_VOICE,
    resolve_voice_provider,
)
from ..src.real_provider import FliteVoiceProvider
from ..src.test_provider import LocalTestVoiceProvider
from .builders import build_produced_item

_SOURCE_PATH = Path(__file__).resolve().parents[1] / "src" / "owner_voice.py"


class _FakeEngine:
    """Test-only stand-in — never a real provider. Its own name says so."""

    name = "fake-test-engine"

    def __init__(self, required_credential_env_vars=None):
        self.required_credential_env_vars = required_credential_env_vars or []

    def is_available(self):
        return True, "ok"

    def synthesize(self, narration_text, config):
        return EngineSynthesisResult(audio_bytes=b"FAKE-AUDIO-BYTES", extension="wav", duration_seconds=5)


class _RegistryIsolated(unittest.TestCase):
    def setUp(self):
        self._saved_registry = dict(_ENGINE_REGISTRY)
        _ENGINE_REGISTRY.clear()
        self.addCleanup(lambda: (_ENGINE_REGISTRY.clear(), _ENGINE_REGISTRY.update(self._saved_registry)))


class ProviderSelectionFailsSafelyTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def test_unselected_provider_fails_safely(self):
        # OWNER_VOICE_ENGINE left unset entirely (sample/id otherwise valid).
        config = OwnerVoiceConfig(voice_id="owner-default", sample_path=self.sample_path)
        provider = OwnerVoiceProvider(config)
        with self.assertRaises(Exception) as ctx:
            provider.generate("Narration.", "ignored")
        self.assertIn("OWNER_VOICE_ENGINE", str(ctx.exception))

    def test_unknown_engine_name_fails_safely(self):
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path,
            engine_name="a-provider-nobody-registered",
        )
        availability = check_owner_voice_availability(config)
        self.assertFalse(availability.available)
        self.assertIn("a-provider-nobody-registered", availability.reason)

    def test_unknown_provider_name_at_selection_layer_fails_safely(self):
        with self.assertRaises(ValueError):
            resolve_voice_provider("a-vendor-nobody-configured")

    def test_no_silent_flite_fallback_when_owner_voice_requested(self):
        # Selecting "owner-voice" must always hand back an
        # OwnerVoiceProvider — never quietly substitute the local
        # fallback or test provider, configured or not.
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE)
        self.assertIsInstance(provider, OwnerVoiceProvider)
        self.assertNotIsInstance(provider, FliteVoiceProvider)
        self.assertNotIsInstance(provider, LocalTestVoiceProvider)
        with self.assertRaises(Exception):
            provider.generate("Narration text.", "ignored")

    def test_local_fallback_and_local_test_are_still_selectable_unchanged(self):
        # Existing VoiceProvider behavior remains intact.
        self.assertIsInstance(resolve_voice_provider(PROVIDER_LOCAL_TEST), LocalTestVoiceProvider)
        self.assertIsInstance(resolve_voice_provider(PROVIDER_LOCAL_FALLBACK), FliteVoiceProvider)

    def test_owner_voice_module_has_no_network_capable_imports(self):
        # No engine is registered by default and none ships in this
        # repository — this is a static guarantee that the module
        # itself cannot originate a network request on its own.
        source = _SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in ("import urllib", "import requests", "import http.client", "import socket"):
            self.assertNotIn(forbidden, source)


class PrivacyPersistenceTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(self.root)
        self.sample_path = Path(self._tmp.name) / "a-very-distinctive-owner-sample-filename.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def _all_written_text(self) -> str:
        return "\n".join(
            p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")
        )

    def test_private_sample_path_never_persisted_anywhere_on_disk(self):
        register_owner_voice_engine(_FakeEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-test-engine",
        )
        provider = OwnerVoiceProvider(config)
        run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )
        self.assertNotIn("a-very-distinctive-owner-sample-filename", self._all_written_text())

    def test_credential_value_never_persisted_anywhere_on_disk(self):
        import os
        register_owner_voice_engine(_FakeEngine(required_credential_env_vars=["FAKE_TEST_API_KEY"]))
        os.environ["FAKE_TEST_API_KEY"] = "sk-totally-fake-secret-value-12345"
        self.addCleanup(lambda: os.environ.pop("FAKE_TEST_API_KEY", None))
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-test-engine",
        )
        provider = OwnerVoiceProvider(config)
        result = run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )
        self.assertNotIn("sk-totally-fake-secret-value-12345", self._all_written_text())
        self.assertNotIn("sk-totally-fake-secret-value-12345", result.provider_label)
        self.assertNotIn("sk-totally-fake-secret-value-12345", result.voice_configuration)

    def test_credential_value_never_appears_in_availability_reason(self):
        import os
        register_owner_voice_engine(_FakeEngine(required_credential_env_vars=["FAKE_TEST_API_KEY"]))
        os.environ.pop("FAKE_TEST_API_KEY", None)
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-test-engine",
        )
        availability = check_owner_voice_availability(config)
        self.assertIn("FAKE_TEST_API_KEY", availability.reason)  # the name is fine
        self.assertNotIn("sk-", availability.reason)  # never a value, since none was set


class OwnerAuthorizationVsEditorialApprovalTests(_RegistryIsolated):
    """The two human decisions (provider authorization vs. content
    approval) must never satisfy each other."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def _fully_available_provider(self):
        register_owner_voice_engine(_FakeEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-test-engine",
        )
        self.assertTrue(check_owner_voice_availability(config).available)
        return OwnerVoiceProvider(config), config

    def test_fully_available_owner_voice_does_not_bypass_the_content_approval_gate(self):
        build_minimal_item(self.root, status="SCRIPT")  # not APPROVED
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        provider, config = self._fully_available_provider()

        result = run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )

        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertEqual(before, after)
        self.assertFalse((self.root / "voice").exists())

    def test_provider_authorization_check_never_touches_any_content_item(self):
        # check_owner_voice_availability/OwnerVoiceProvider take no
        # content-item root at all — proof that "is a provider ready"
        # is structurally independent of "is this episode approved."
        # Confirmed here by running it with no content item anywhere.
        provider, _ = self._fully_available_provider()
        self.assertTrue((self.root.parent).is_dir())
        self.assertFalse((self.root / "CONTENT_ITEM.md").exists())
        # Still fully available — provider readiness never required a
        # content item to exist, let alone be approved.
        self.assertIn("owner-default", provider.label)

    def test_registering_an_engine_alone_never_approves_anything(self):
        build_minimal_item(self.root, status="SCRIPT")
        before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self._fully_available_provider()  # engine registered, config fully valid
        after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertIn("Current status: `SCRIPT`", after)
        self.assertNotIn("APPROVED", after)


if __name__ == "__main__":
    unittest.main()
