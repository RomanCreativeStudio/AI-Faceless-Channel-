"""OpenVoice V2 (agents/voice/src/engines/openvoice_v2_engine.py) — the
first real OwnerVoiceEngine. This test environment does NOT have torch/
openvoice/MeloTTS installed (they live only in the isolated venv under
.voice-experiments/, per that module's own README) — so most tests here
exercise the REAL adapter's genuine, honest failure path in exactly the
environment most CI/dev machines will actually have, proving it fails
clearly rather than silently substituting a different voice. A handful
of pipeline-level guarantees (narration/script-hash/metadata) are tested
with a separate, clearly-labeled fake engine, per this task's own
instruction never to claim a real provider generated audio in a test.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.tests.builders import build_minimal_item
from ..src import engines
from ..src.engines.openvoice_v2_engine import (
    ENGINE_NAME,
    OpenVoiceV2Engine,
    _chunk_narration,
    _melo_language_and_speaker,
)
from ..src.owner_voice import (
    EngineSynthesisResult,
    OwnerVoiceConfig,
    OwnerVoiceNotConfiguredError,
    OwnerVoiceProvider,
    _ENGINE_REGISTRY,
    check_owner_voice_availability,
    register_owner_voice_engine,
)
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item

_MODULE_PATH = Path(engines.__file__).parent / "openvoice_v2_engine.py"
_WORKER_MODULE_PATH = Path(engines.__file__).parent / "_openvoice_v2_chunk_worker.py"


class _RegistryIsolated(unittest.TestCase):
    def setUp(self):
        self._saved_registry = dict(_ENGINE_REGISTRY)
        _ENGINE_REGISTRY.clear()
        self.addCleanup(lambda: (_ENGINE_REGISTRY.clear(), _ENGINE_REGISTRY.update(self._saved_registry)))


class LanguageMappingTests(unittest.TestCase):
    def test_plain_english_defaults(self):
        config = OwnerVoiceConfig(language="en")
        self.assertEqual(_melo_language_and_speaker(config), ("EN", "en-default"))

    def test_english_region_tag_still_maps_to_en(self):
        config = OwnerVoiceConfig(language="en-US")
        self.assertEqual(_melo_language_and_speaker(config)[0], "EN")

    def test_speaking_style_selects_a_specific_english_accent(self):
        config = OwnerVoiceConfig(language="en", speaking_style="en-us")
        self.assertEqual(_melo_language_and_speaker(config), ("EN", "en-us"))

    def test_unknown_speaking_style_falls_back_to_language_default(self):
        config = OwnerVoiceConfig(language="en", speaking_style="dramatic-narrator")
        self.assertEqual(_melo_language_and_speaker(config), ("EN", "en-default"))

    def test_spanish_maps_to_es(self):
        config = OwnerVoiceConfig(language="es")
        self.assertEqual(_melo_language_and_speaker(config), ("ES", "es"))

    def test_unrecognized_language_defaults_to_english(self):
        config = OwnerVoiceConfig(language="xx")
        self.assertEqual(_melo_language_and_speaker(config)[0], "EN")


class NarrationChunkingTests(unittest.TestCase):
    """_chunk_narration() bounds peak memory for long scripts (see its own
    module-level comment — a real OOM was reproduced and fixed by
    chunking) without ever altering narration content: every chunk is
    real sentences from the input, in order, and rejoining them with
    single spaces reconstructs the exact original text.
    """

    def test_reconstructs_original_text_exactly(self):
        text = (
            "In 1347, a disease killed up to 60% of the people. What if the "
            "people living through it had known? Between 1347 and 1351, the "
            "Black Death swept across Europe."
        )
        chunks = _chunk_narration(text, max_words=10)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(" ".join(chunks), text)

    def test_never_splits_a_sentence_in_half(self):
        text = "First sentence here. Second sentence here. Third sentence here."
        chunks = _chunk_narration(text, max_words=3)
        for chunk in chunks:
            self.assertTrue(chunk.rstrip().endswith("."))

    def test_single_short_sentence_is_one_chunk(self):
        self.assertEqual(_chunk_narration("Just one short sentence.", max_words=100), ["Just one short sentence."])

    def test_empty_text_produces_no_chunks(self):
        self.assertEqual(_chunk_narration("   "), [])

    def test_long_narration_produces_multiple_bounded_chunks(self):
        # A ~470-word script (Episode 1's real approximate length) must
        # split into more than one chunk at the engine's real default —
        # proof the memory-bounding fix actually activates for
        # realistic narration lengths, not just in a contrived test.
        sentence = "This is a representative sentence with several words in it."
        text = " ".join([sentence] * 40)  # ~440 words
        chunks = _chunk_narration(text)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(" ".join(chunks), text)


class ChunkWorkerSubprocessTests(unittest.TestCase):
    """The per-chunk synthesis worker (_openvoice_v2_chunk_worker.py,
    invoked as a subprocess by synthesize() — see that module's own
    docstring for why: three real, independently-reproduced OOM kills at
    the same memory ceiling, even with chunking and inference_mode()
    already applied) must never receive or be able to leak the owner's
    raw sample path, and must have no network-capable imports of its own.
    """

    def test_worker_module_exists_and_has_a_main_entry_point(self):
        self.assertTrue(_WORKER_MODULE_PATH.is_file())
        source = _WORKER_MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("def main(", source)

    def test_worker_module_has_no_network_capable_imports_at_module_level(self):
        source = _WORKER_MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in ("import urllib", "import requests", "import http.client", "import socket"):
            self.assertNotIn(forbidden, source)

    def test_worker_module_never_declares_a_sample_path_argument(self):
        # The worker receives only a checkpoint dir, device, language/
        # speaker identifiers, chunk text, a target-embedding path, and
        # an output path — never the owner's raw sample path. Asserted
        # structurally so this stays true even if the worker is edited.
        source = _WORKER_MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("sample-path", source)
        self.assertNotIn("sample_path", source)

    def test_engine_module_invokes_the_worker_via_subprocess_not_in_process_synthesis(self):
        source = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("subprocess.run", source)
        self.assertIn("_CHUNK_WORKER_PATH", source)


class EngineIdentityTests(unittest.TestCase):
    def test_name_matches_module_constant(self):
        self.assertEqual(OpenVoiceV2Engine().name, ENGINE_NAME)
        self.assertEqual(ENGINE_NAME, "openvoice-v2")

    def test_local_and_free_requires_no_credentials(self):
        self.assertEqual(OpenVoiceV2Engine().required_credential_env_vars, [])

    def test_conforms_to_the_owner_voice_engine_shape(self):
        engine = OpenVoiceV2Engine()
        self.assertTrue(hasattr(engine, "name"))
        self.assertTrue(hasattr(engine, "required_credential_env_vars"))
        self.assertTrue(callable(engine.is_available))
        self.assertTrue(callable(engine.synthesize))
        ok, reason = engine.is_available()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(reason, str)

    def test_accepts_a_configured_local_sample_path_without_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = Path(tmp) / "owner.wav"
            sample_path.write_bytes(b"not-real-audio-just-nonempty")
            # Constructing the config/engine pairing itself must never
            # raise just because a real sample is referenced — only
            # is_available()/synthesize() judge readiness.
            config = OwnerVoiceConfig(
                voice_id="owner-default", engine_name=ENGINE_NAME, sample_path=sample_path,
            )
            engine = OpenVoiceV2Engine(checkpoint_dir=str(Path(tmp) / "checkpoints_v2"))
            ok, reason = engine.is_available()
            self.assertFalse(ok)  # no real checkpoint/torch here — expected
            self.assertIsInstance(reason, str)
            self.assertTrue(reason)

    def test_module_has_no_network_capable_imports_at_module_level(self):
        source = _MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in ("import urllib", "import requests", "import http.client", "import socket"):
            self.assertNotIn(forbidden, source)


class RealFailureBehaviorTests(_RegistryIsolated):
    """These exercise the REAL OpenVoiceV2Engine's actual is_available()/
    synthesize() in this test environment, which genuinely lacks torch/
    openvoice/MeloTTS — this is not a mock; it is what happens if
    OWNER_VOICE_ENGINE=openvoice-v2 is set on a machine that hasn't set
    up the isolated environment yet."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def test_is_available_false_with_a_precise_reason_in_this_environment(self):
        engine = OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        ok, reason = engine.is_available()
        self.assertFalse(ok)
        self.assertTrue(reason)

    def test_synthesize_raises_rather_than_returning_degraded_audio(self):
        engine = OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name=ENGINE_NAME, sample_path=self.sample_path,
        )
        with self.assertRaises(RuntimeError) as ctx:
            engine.synthesize("Some narration.", config)
        self.assertIn("not available", str(ctx.exception))

    def test_registered_engine_reached_by_availability_check(self):
        register_owner_voice_engine(
            OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        )
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name=ENGINE_NAME, sample_path=self.sample_path,
        )
        availability = check_owner_voice_availability(config)
        self.assertFalse(availability.available)
        # Reached this real engine's own is_available() reason, not a
        # generic "no engine registered" message.
        self.assertNotIn("no engine implementation registered", availability.reason)

    def test_owner_voice_provider_fails_explicitly_never_falls_back(self):
        register_owner_voice_engine(
            OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        )
        config = OwnerVoiceConfig(
            voice_id="owner-default", engine_name=ENGINE_NAME, sample_path=self.sample_path,
        )
        provider = OwnerVoiceProvider(config)
        with self.assertRaises(OwnerVoiceNotConfiguredError):
            provider.generate("Some narration.", "ignored")

    def test_register_helper_populates_registry_under_the_right_name(self):
        from ..src.engines.openvoice_v2_engine import register
        register()
        self.assertIn(ENGINE_NAME, _ENGINE_REGISTRY)
        self.assertIsInstance(_ENGINE_REGISTRY[ENGINE_NAME], OpenVoiceV2Engine)

    def test_distinctive_sample_filename_never_leaks_into_failure_message(self):
        distinctive = Path(self._tmp.name) / "a-very-distinctive-owner-filename.wav"
        distinctive.write_bytes(b"not-real-audio-just-nonempty")
        register_owner_voice_engine(
            OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        )
        config = OwnerVoiceConfig(voice_id="owner-default", engine_name=ENGINE_NAME, sample_path=distinctive)
        provider = OwnerVoiceProvider(config)
        try:
            provider.generate("Some narration.", "ignored")
            self.fail("expected OwnerVoiceNotConfiguredError")
        except OwnerVoiceNotConfiguredError as exc:
            self.assertNotIn("a-very-distinctive-owner-filename", str(exc))


class ApprovalBoundaryTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")

    def test_openvoice_configured_still_blocked_by_unapproved_content_item(self):
        build_minimal_item(self.root, status="SCRIPT")  # not APPROVED
        register_owner_voice_engine(
            OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        )
        config = OwnerVoiceConfig(voice_id="owner-default", engine_name=ENGINE_NAME, sample_path=self.sample_path)
        provider = OwnerVoiceProvider(config)
        before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")

        result = run_voice_generation(
            self.root, apply=True, provider=provider, voice_configuration=config.voice_configuration_string(),
        )

        after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertEqual(before, after)


class _FakeEngineForPipelineTests:
    """A clearly-labeled TEST DOUBLE — never OpenVoice, never any real
    provider. Used only to prove pipeline-level guarantees (narration
    integrity, script-hash relationship, metadata determinism) that hold
    for any conforming OwnerVoiceEngine, independent of which one is
    actually plugged in."""

    name = "fake-engine-for-openvoice-pipeline-tests"
    required_credential_env_vars: list[str] = []

    def is_available(self):
        return True, "ok"

    def synthesize(self, narration_text, config):
        return EngineSynthesisResult(audio_bytes=b"FAKE-AUDIO", extension="wav", duration_seconds=5)


class PipelineGuaranteesTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(self.root)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")
        register_owner_voice_engine(_FakeEngineForPipelineTests())
        self.config = OwnerVoiceConfig(
            voice_id="owner-default",
            engine_name="fake-engine-for-openvoice-pipeline-tests",
            sample_path=self.sample_path,
        )

    def test_narration_and_script_hash_relationship_preserved(self):
        provider = OwnerVoiceProvider(self.config)
        result = run_voice_generation(
            self.root, apply=True, provider=provider, voice_configuration=self.config.voice_configuration_string(),
        )
        self.assertTrue(result.produced)
        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn(result.script_content_hash, voice_text)
        self.assertIn(result.source_narration.strip(), voice_text)

    def test_provider_metadata_is_deterministic_across_runs(self):
        provider_a = OwnerVoiceProvider(self.config)
        provider_b = OwnerVoiceProvider(self.config)
        label_a = provider_a.label
        label_b = provider_b.label
        self.assertEqual(label_a, label_b)
        self.assertEqual(
            self.config.voice_configuration_string(), self.config.voice_configuration_string(),
        )


if __name__ == "__main__":
    unittest.main()
