"""Production activation (Phase 8 follow-up 8, VOICE_DECISION =
USE_FOR_PRODUCTION): once an operator has explicitly imported
agents/voice/src/engines/openvoice_v2_engine (which registers OpenVoice
V2 — see that module's own docstring) and configured OWNER_VOICE_* /
OPENVOICE_V2_* environment variables, the existing, unmodified
`owner-voice` selection string at agents/voice/src/provider_selection.py
must route to it — no new selection string was added, no architecture
was redesigned, and no silent fallback exists anywhere in the chain.

This test environment does not have torch/openvoice/MeloTTS installed
(they live only in the isolated venv under .voice-experiments/, per
agents/voice/src/engines/README.md), so these tests exercise the real
adapter's genuine failure path reached THROUGH resolve_voice_provider()
— proving the whole selection chain routes and fails correctly end to
end, not just the provider's own internals (already covered by
test_openvoice_v2_engine.py).
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.tests.builders import build_minimal_item
from ..src.engines.openvoice_v2_engine import ENGINE_NAME, OpenVoiceV2Engine
from ..src.owner_voice import (
    OwnerVoiceConfig,
    OwnerVoiceNotConfiguredError,
    OwnerVoiceProvider,
    _ENGINE_REGISTRY,
    register_owner_voice_engine,
)
from ..src.pipeline import run_voice_generation
from ..src.provider_selection import PROVIDER_OWNER_VOICE, resolve_voice_provider


class _RegistryIsolated(unittest.TestCase):
    def setUp(self):
        self._saved_registry = dict(_ENGINE_REGISTRY)
        _ENGINE_REGISTRY.clear()
        self.addCleanup(lambda: (_ENGINE_REGISTRY.clear(), _ENGINE_REGISTRY.update(self._saved_registry)))


class OwnerVoiceRoutesToOpenVoiceTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")
        register_owner_voice_engine(
            OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        )
        self.config = OwnerVoiceConfig(
            voice_id="owner-production-ep1", engine_name=ENGINE_NAME, sample_path=self.sample_path,
        )

    def test_owner_voice_selection_resolves_to_a_provider_bound_to_openvoice(self):
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE, owner_voice_config=self.config)
        self.assertIsInstance(provider, OwnerVoiceProvider)
        self.assertEqual(provider.config.engine_name, ENGINE_NAME)
        self.assertIn("openvoice-v2", provider.label)
        self.assertIn("OWNER_AUTHORIZED_VOICE", provider.label)

    def test_selection_layer_never_bypasses_engine_level_failure(self):
        # This test environment genuinely lacks torch/openvoice/MeloTTS,
        # so even a correctly-routed provider must still fail explicitly
        # rather than ever quietly substituting a different voice.
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE, owner_voice_config=self.config)
        with self.assertRaises(OwnerVoiceNotConfiguredError):
            provider.generate("Some narration.", "ignored")

    def test_no_publish_capable_surface_reachable_from_voice_selection(self):
        # No agent in this codebase has publishing authority
        # (CONSTITUTION.md rule 2); structurally, the object this
        # selection layer hands back exposes no publish-shaped method.
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE, owner_voice_config=self.config)
        self.assertFalse(any("publish" in attr.lower() for attr in dir(provider)))


def _heavy_deps_importable() -> bool:
    try:
        import torch  # noqa: F401
        import openvoice  # noqa: F401
        import melo  # noqa: F401
    except ImportError:
        return False
    return True


class InvalidOpenVoiceConfigurationTests(unittest.TestCase):
    """is_available() checks torch/openvoice/melo importability before it
    ever reaches the checkpoint-directory checks below (see
    openvoice_v2_engine.py's own ordering) — so the two "invalid
    checkpoint" scenarios here can only be genuinely exercised once the
    isolated environment (agents/voice/src/engines/README.md) is active.
    This is the same honest, environment-dependent skip pattern this
    codebase already uses for ffmpeg-dependent tests elsewhere; it is not
    a mock and never claims to have tested something it didn't.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_no_checkpoint_dir_configured_at_all_is_reported_precisely(self):
        # Reachable even without torch/openvoice/melo installed, since
        # is_available() would report the missing dependency first in
        # that case — this assertion only holds when it does NOT, i.e.
        # once the isolated environment is active.
        if not _heavy_deps_importable():
            self.skipTest("torch/openvoice/melo not importable in this environment")
        engine = OpenVoiceV2Engine(checkpoint_dir=None)
        ok, reason = engine.is_available()
        self.assertFalse(ok)
        self.assertIn("OPENVOICE_V2_CHECKPOINT_DIR", reason)

    def test_checkpoint_dir_configured_but_missing_files_is_reported_precisely(self):
        if not _heavy_deps_importable():
            self.skipTest("torch/openvoice/melo not importable in this environment")
        checkpoint_dir = Path(self._tmp.name) / "checkpoints_v2"
        (checkpoint_dir / "converter").mkdir(parents=True)
        # config.json/checkpoint.pth deliberately never written — a
        # genuinely invalid (not merely unconfigured) checkpoint dir.
        engine = OpenVoiceV2Engine(checkpoint_dir=str(checkpoint_dir))
        ok, reason = engine.is_available()
        self.assertFalse(ok)
        self.assertIn("checkpoint", reason.lower())

    def test_missing_torch_openvoice_or_melo_is_itself_a_reported_invalid_configuration(self):
        # In THIS test environment, this is what "invalid configuration"
        # actually looks like today — reported precisely, never silently
        # treated as available.
        if _heavy_deps_importable():
            self.skipTest("torch/openvoice/melo ARE importable here — the other tests in this class cover this environment instead")
        engine = OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        ok, reason = engine.is_available()
        self.assertFalse(ok)
        self.assertTrue(reason)


class ApprovalGateStillEnforcedThroughSelectionTests(_RegistryIsolated):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.sample_path = Path(self._tmp.name) / "owner.wav"
        self.sample_path.write_bytes(b"not-real-audio-just-nonempty")
        register_owner_voice_engine(
            OpenVoiceV2Engine(checkpoint_dir=str(Path(self._tmp.name) / "checkpoints_v2"))
        )

    def test_production_activation_still_blocked_on_unapproved_episode(self):
        build_minimal_item(self.root, status="SCRIPT")  # not APPROVED
        config = OwnerVoiceConfig(
            voice_id="owner-production-ep1", engine_name=ENGINE_NAME, sample_path=self.sample_path,
        )
        provider = resolve_voice_provider(PROVIDER_OWNER_VOICE, owner_voice_config=config)
        before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")

        result = run_voice_generation(
            self.root, apply=True, provider=provider, voice_configuration=config.voice_configuration_string(),
        )

        after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
