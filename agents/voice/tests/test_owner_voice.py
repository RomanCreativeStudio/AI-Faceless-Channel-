"""Owner-voice provider: configuration, capability detection, generation,
security, and narration-integrity/human-approval-boundary behavior when
wired through the real pipeline. No real voice-cloning engine exists in
this repository — these tests use a minimal fake `OwnerVoiceEngine` to
exercise the full path without depending on any external service."""
import os
import tempfile
import unittest
from pathlib import Path

from ..src.owner_voice import (
    OWNER_AUTHORIZATION_LABEL,
    EngineSynthesisResult,
    OwnerVoiceConfig,
    OwnerVoiceNotConfiguredError,
    OwnerVoiceProvider,
    OwnerVoiceProviderFailure,
    OwnerVoiceStatus,
    _ENGINE_REGISTRY,
    check_owner_voice_availability,
    register_owner_voice_engine,
)
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item


class _FakeEngine:
    """A registered-for-tests-only stand-in engine. Never a real
    voice-cloning backend — proves the registry/credential/availability
    plumbing works without depending on any external service."""

    name = "fake-engine-for-tests"

    def __init__(self, required_credential_env_vars=None, available=True, available_reason="ok"):
        self.required_credential_env_vars = required_credential_env_vars or []
        self._available = available
        self._available_reason = available_reason
        self.calls = []

    def is_available(self):
        return self._available, self._available_reason

    def synthesize(self, narration_text, config):
        self.calls.append((narration_text, config))
        return EngineSynthesisResult(
            audio_bytes=b"FAKE-OWNER-VOICE-AUDIO-BYTES",
            extension="wav",
            duration_seconds=7,
            model_label=config.model_id or "fake-model",
        )


class _FailingEngine:
    name = "failing-engine-for-tests"
    required_credential_env_vars: list[str] = []

    def is_available(self):
        return True, "ok"

    def synthesize(self, narration_text, config):
        return EngineSynthesisResult(audio_bytes=b"", extension="wav", duration_seconds=0)


def _register(*engines):
    for e in engines:
        register_owner_voice_engine(e)


class _RegistryIsolated(unittest.TestCase):
    """Every test gets a clean engine registry — this module's registry
    is process-global by design (a real deployment registers its chosen
    engine once, at startup), so tests must not leak fakes between them."""

    def setUp(self):
        self._saved_registry = dict(_ENGINE_REGISTRY)
        _ENGINE_REGISTRY.clear()
        self.addCleanup(lambda: (_ENGINE_REGISTRY.clear(), _ENGINE_REGISTRY.update(self._saved_registry)))


class ConfigTests(_RegistryIsolated):
    def test_from_env_all_missing(self):
        config = OwnerVoiceConfig.from_env({})
        self.assertEqual(config.voice_id, "")
        self.assertEqual(config.engine_name, "")
        self.assertIsNone(config.sample_path)
        self.assertEqual(config.language, "en")
        self.assertEqual(config.pronunciation, {})

    def test_from_env_valid_configuration(self):
        config = OwnerVoiceConfig.from_env({
            "OWNER_VOICE_ID": "owner-default",
            "OWNER_VOICE_ENGINE": "fake-engine-for-tests",
            "OWNER_VOICE_SAMPLE_PATH": "/private/owner.wav",
            "OWNER_VOICE_MODEL": "v2",
            "OWNER_VOICE_LANGUAGE": "en-US",
            "OWNER_VOICE_STYLE": "calm-explainer",
            "OWNER_VOICE_STABILITY": "0.6",
            "OWNER_VOICE_CONSISTENCY": "0.8",
            "OWNER_VOICE_PRONUNCIATION": "flite=FLY-t; SCRIPT.md=script dot m d",
        })
        self.assertEqual(config.voice_id, "owner-default")
        self.assertEqual(config.engine_name, "fake-engine-for-tests")
        self.assertEqual(config.sample_path, Path("/private/owner.wav"))
        self.assertEqual(config.model_id, "v2")
        self.assertEqual(config.language, "en-US")
        self.assertEqual(config.speaking_style, "calm-explainer")
        self.assertEqual(config.stability, 0.6)
        self.assertEqual(config.consistency, 0.8)
        self.assertEqual(config.pronunciation, {"flite": "FLY-t", "SCRIPT.md": "script dot m d"})

    def test_malformed_numeric_fields_do_not_raise(self):
        config = OwnerVoiceConfig.from_env({
            "OWNER_VOICE_STABILITY": "not-a-number",
            "OWNER_VOICE_CONSISTENCY": "",
        })
        self.assertIsNone(config.stability)
        self.assertIsNone(config.consistency)

    def test_malformed_pronunciation_entries_are_dropped_not_raised(self):
        config = OwnerVoiceConfig.from_env({"OWNER_VOICE_PRONUNCIATION": "no-equals-sign;;=noword"})
        self.assertEqual(config.pronunciation, {})

    def test_redacted_summary_never_includes_sample_path_or_raw_values(self):
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name="fake-engine-for-tests",
            sample_path=Path("/private/very/specific/local/path/owner.wav"),
        )
        summary = config.redacted_summary()
        self.assertNotIn("/private/very/specific/local/path/owner.wav", str(summary))
        self.assertTrue(summary["sample_configured"])
        self.assertEqual(summary["voice_id"], "owner-default")

    def test_voice_configuration_string_never_includes_sample_path(self):
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name="fake-engine-for-tests",
            sample_path=Path("/private/very/specific/local/path/owner.wav"),
        )
        self.assertNotIn("/private/very/specific/local/path/owner.wav", config.voice_configuration_string())

    def test_config_has_no_credential_fields_at_all(self):
        # Credentials live only in the process environment, read by an
        # engine itself (via required_credential_env_vars) — never
        # captured onto the config object, so there is nothing here that
        # could ever be accidentally logged or persisted.
        field_names = {f for f in OwnerVoiceConfig.__dataclass_fields__}
        for suspicious in ("key", "token", "secret", "password", "credential"):
            self.assertFalse(
                any(suspicious in f.lower() for f in field_names),
                f"OwnerVoiceConfig unexpectedly has a field suggesting {suspicious!r}: {field_names}",
            )


class AvailabilityTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def test_missing_voice_id(self):
        config = OwnerVoiceConfig(sample_path=self.sample_path, engine_name="fake-engine-for-tests")
        result = check_owner_voice_availability(config)
        self.assertEqual(result.status, OwnerVoiceStatus.OWNER_VOICE_NOT_CONFIGURED)
        self.assertIn("OWNER_VOICE_ID", result.reason)

    def test_missing_sample_path(self):
        config = OwnerVoiceConfig(voice_id="owner-default", engine_name="fake-engine-for-tests")
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("OWNER_VOICE_SAMPLE_PATH", result.reason)

    def test_sample_path_does_not_exist(self):
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name="fake-engine-for-tests",
            sample_path=Path(self._tmp.name) / "does-not-exist.wav",
        )
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("does not point to an existing file", result.reason)

    def test_empty_sample_file(self):
        empty_path = Path(self._tmp.name) / "empty.wav"
        empty_path.write_bytes(b"")
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name="fake-engine-for-tests", sample_path=empty_path,
        )
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("empty", result.reason)

    def test_no_engine_configured(self):
        config = OwnerVoiceConfig(voice_id="owner-default", sample_path=self.sample_path)
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("OWNER_VOICE_ENGINE", result.reason)

    def test_unregistered_engine_name(self):
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="nonexistent-engine",
        )
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("nonexistent-engine", result.reason)

    def test_missing_credentials(self):
        _register(_FakeEngine(required_credential_env_vars=["SOME_VENDOR_API_KEY"]))
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        os.environ.pop("SOME_VENDOR_API_KEY", None)
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("SOME_VENDOR_API_KEY", result.reason)

    def test_engine_reports_itself_unavailable(self):
        _register(_FakeEngine(available=False, available_reason="local model file not found"))
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        result = check_owner_voice_availability(config)
        self.assertFalse(result.available)
        self.assertIn("local model file not found", result.reason)

    def test_fully_configured_reports_available(self):
        _register(_FakeEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        result = check_owner_voice_availability(config)
        self.assertEqual(result.status, OwnerVoiceStatus.OWNER_VOICE_AVAILABLE)
        self.assertTrue(result.available)

    def test_credential_present_satisfies_check(self):
        _register(_FakeEngine(required_credential_env_vars=["SOME_VENDOR_API_KEY"]))
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        os.environ["SOME_VENDOR_API_KEY"] = "test-value-never-logged"
        self.addCleanup(lambda: os.environ.pop("SOME_VENDOR_API_KEY", None))
        result = check_owner_voice_availability(config)
        self.assertTrue(result.available)
        self.assertNotIn("test-value-never-logged", result.reason)


class ProviderGenerateTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def test_generate_raises_when_not_configured(self):
        provider = OwnerVoiceProvider(OwnerVoiceConfig())
        with self.assertRaises(OwnerVoiceNotConfiguredError):
            provider.generate("Some narration.", "ignored")

    def test_generate_never_falls_back_to_a_different_provider(self):
        # The exception type itself is the "fail clearly" contract — no
        # GeneratedAudio (placeholder or otherwise) is ever returned.
        provider = OwnerVoiceProvider(OwnerVoiceConfig(voice_id="owner-default"))
        try:
            provider.generate("Some narration.", "ignored")
            self.fail("expected OwnerVoiceNotConfiguredError")
        except OwnerVoiceNotConfiguredError as exc:
            self.assertIn("OWNER_VOICE", str(exc))

    def test_generate_rejects_empty_narration(self):
        _register(_FakeEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        with self.assertRaises(OwnerVoiceProviderFailure):
            OwnerVoiceProvider(config).generate("   ", "ignored")

    def test_generate_succeeds_with_fully_configured_fake_engine(self):
        fake = _FakeEngine()
        _register(fake)
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        audio = OwnerVoiceProvider(config).generate("Narration text here.", "ignored")
        self.assertEqual(audio.artifact_bytes, b"FAKE-OWNER-VOICE-AUDIO-BYTES")
        self.assertEqual(audio.duration_seconds, 7)
        self.assertFalse(audio.is_placeholder)
        self.assertIn(OWNER_AUTHORIZATION_LABEL, audio.provider_label)
        self.assertEqual(len(fake.calls), 1)

    def test_generate_raises_on_engine_producing_no_audio(self):
        _register(_FailingEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="failing-engine-for-tests",
        )
        with self.assertRaises(OwnerVoiceProviderFailure):
            OwnerVoiceProvider(config).generate("Narration text.", "ignored")

    def test_label_reflects_the_actual_configured_identity_not_a_default(self):
        _register(_FakeEngine())
        config_a = OwnerVoiceConfig(
            voice_id="voice-a", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        config_b = OwnerVoiceConfig(
            voice_id="voice-b", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        audio_a = OwnerVoiceProvider(config_a).generate("Text.", "ignored")
        audio_b = OwnerVoiceProvider(config_b).generate("Text.", "ignored")
        self.assertIn("voice-a", audio_a.provider_label)
        self.assertIn("voice-b", audio_b.provider_label)
        self.assertNotEqual(audio_a.provider_label, audio_b.provider_label)

    def test_generated_audio_never_carries_sample_path(self):
        _register(_FakeEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default",
            sample_path=Path(self._tmp.name) / "a-very-specific-private-filename.wav",
            engine_name="fake-engine-for-tests",
        )
        self.sample_path.rename(config.sample_path)
        audio = OwnerVoiceProvider(config).generate("Text.", "ignored")
        self.assertNotIn("a-very-specific-private-filename", audio.provider_label)
        self.assertNotIn("a-very-specific-private-filename", audio.voice_configuration)


class PipelineIntegrationTests(_RegistryIsolated):
    """OwnerVoiceProvider wired through the real run_voice_generation —
    narration integrity, metadata, failure propagation, and the human
    approval boundary."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(self.root)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def _configured_provider(self):
        _register(_FakeEngine())
        config = OwnerVoiceConfig(
            voice_id="owner-default", sample_path=self.sample_path, engine_name="fake-engine-for-tests",
        )
        return OwnerVoiceProvider(config), config

    def test_script_hash_and_narration_text_preserved(self):
        provider, config = self._configured_provider()
        result = run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )
        self.assertTrue(result.produced)
        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn(result.script_content_hash, voice_text)
        self.assertIn(result.source_narration.strip(), voice_text)

    def test_metadata_records_owner_authorization_and_engine(self):
        provider, config = self._configured_provider()
        result = run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )
        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn(OWNER_AUTHORIZATION_LABEL, voice_text)
        self.assertIn("fake-engine-for-tests", voice_text)
        self.assertIn("owner-default", voice_text)

    def test_unconfigured_owner_voice_fails_the_whole_run_rather_than_falling_back(self):
        unconfigured = OwnerVoiceProvider(OwnerVoiceConfig(voice_id="owner-default"))
        with self.assertRaises(OwnerVoiceNotConfiguredError):
            run_voice_generation(self.root, apply=True, provider=unconfigured, voice_configuration="owner-voice")
        # And nothing was written — a failed provider call must not
        # leave a half-applied voice record behind.
        self.assertFalse((self.root / "voice" / "voice-01.md").exists())

    def test_voice_generation_never_touches_content_item_or_approval(self):
        content_item_path = self.root / "CONTENT_ITEM.md"
        before = content_item_path.read_text(encoding="utf-8")
        provider, config = self._configured_provider()
        run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )
        after = content_item_path.read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_voice_generation_does_not_advance_beyond_production_status(self):
        provider, config = self._configured_provider()
        run_voice_generation(
            self.root, apply=True, provider=provider,
            voice_configuration=config.voice_configuration_string(),
        )
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertNotIn("APPROVED_BY_VOICE", production_text)
        self.assertNotIn("PUBLISHED", production_text)


if __name__ == "__main__":
    unittest.main()
