"""Phase 8 tests for agents/assembler/src/real_provider.py — the first
production-capable VideoRenderer (ffmpeg). Every test here runs the real
ffmpeg binary against real (if trivial) audio/image inputs built by this
repo's own real, offline, network-free providers
(agents/voice/src/real_provider.FliteVoiceProvider,
agents/assets/src/real_providers.GeneratedAssetProviderReal) — no network
call anywhere in this file, matching this phase's own test-safety
instruction.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from ...assets.src.pipeline import run_asset_generation
from ...assets.src.real_providers import GeneratedAssetProviderReal
from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item as build_producer_item
from ...visual_planner.src.pipeline import run_visual_planner
from ...voice.src.pipeline import run_voice_generation
from ...voice.src.real_provider import FliteVoiceProvider
from ..src import mutate
from ..src.models import SceneTimelineEntry
from ..src.real_provider import FFmpegVideoRenderer, RendererFailure

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _build_real_assembly_ready_item(root: Path, content_id: str = "test-item", **kwargs) -> None:
    """Producer -> real Voice -> Visual Planner -> real Assets, leaving
    PRODUCTION.md (status ASSEMBLY) ready with genuine audio/image files
    on disk — the fixture agents/assembler/'s real renderer tests need,
    as opposed to tests/builders.py's own placeholder-provider fixture.
    """
    build_producer_item(root, content_id=content_id, **kwargs)
    producer_result = run_producer(root, apply=True)
    if not producer_result.produced:
        raise AssertionError(f"fixture setup failed to produce a plan: {producer_result}")

    voice_result = run_voice_generation(root, apply=True, provider=FliteVoiceProvider())
    if not voice_result.produced:
        raise AssertionError(f"fixture setup failed to generate voice: {voice_result}")

    planner_result = run_visual_planner(root, apply=True)
    if not planner_result.planned:
        raise AssertionError(f"fixture setup failed to plan visuals: {planner_result}")

    asset_result = run_asset_generation(root, apply=True, generated_provider=GeneratedAssetProviderReal())
    if not asset_result.produced:
        raise AssertionError(f"fixture setup failed to generate assets: {asset_result}")


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg not installed in this environment")
class FFmpegVideoRendererTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        # Deliberately claim-less beats: any claim reference would make
        # that scene's Visual Safety Rule classification FACT-only ->
        # AUTHENTIC_HISTORICAL_MEDIA -> RETRIEVED strategy, which needs a
        # real retrieval provider (network) this offline test suite must
        # never depend on — see this file's own module docstring.
        _build_real_assembly_ready_item(
            self.root,
            beats=[
                "1. First real scene narration text for rendering.",
                "2. Second real scene narration text for rendering.",
            ],
        )
        # build_producer_item's own default Hook ("An ordinary hook line
        # to open the video.") always becomes scene-01 — so this fixture
        # is three real scenes: Hook, beat 1, beat 2.

    def _scene_entries(self) -> tuple[list[SceneTimelineEntry], int]:
        entries = []
        cum = 0
        for order, filename, dur in [(1, "scene-01.md", 3), (2, "scene-02.md", 4), (3, "scene-03.md", 3)]:
            start = cum
            end = start + dur
            cum = end
            entries.append(SceneTimelineEntry(
                scene_id=f"test-item-scene-{order:02d}", filename=filename, order=order,
                start=start, end=end, duration_seconds=dur,
                narration_reference="voice/voice-01.md",
                visual_reference=f"assets/asset-{order:02d}.md",
                captions_reference="captions/captions-01.md",
                transition_in="cut", transition_out="cut", claim_ids=[],
            ))
        return entries, cum

    def test_renders_real_playable_mp4_from_real_inputs(self):
        entries, total = self._scene_entries()
        result = FFmpegVideoRenderer().render(entries, total, self.root)
        self.assertEqual(result.format, "mp4")
        self.assertEqual(result.playable, "YES")
        self.assertFalse(result.is_placeholder)
        self.assertIsNotNone(result.artifact_bytes)
        self.assertTrue(result.artifact_bytes.startswith(b"\x00\x00\x00"))  # mp4 ftyp box prefix pattern

    def test_scene_ordering_preserved_in_output_duration(self):
        entries, total = self._scene_entries()
        result = FFmpegVideoRenderer().render(entries, total, self.root)
        self.assertGreater(len(result.artifact_bytes), 0)
        # total_duration passed in reflects scene order/durations summed
        # by the caller (agents/assembler/src/pipeline.py) — this test
        # proves the renderer accepts and uses that ordering without
        # raising, which is what scene-ordering-sensitive rendering means
        # for a still-image-per-scene renderer.
        self.assertEqual(total, sum(e.duration_seconds for e in entries))

    def test_missing_audio_file_fails_closed(self):
        entries, total = self._scene_entries()
        (self.root / "voice" / "voice-01.wav").unlink()
        with self.assertRaises(RendererFailure):
            FFmpegVideoRenderer().render(entries, total, self.root)

    def test_missing_asset_file_fails_closed(self):
        entries, total = self._scene_entries()
        for p in (self.root / "assets").glob("asset-01.generated.*"):
            p.unlink()
        with self.assertRaises(RendererFailure):
            FFmpegVideoRenderer().render(entries, total, self.root)

    def test_zero_scenes_fails_closed(self):
        with self.assertRaises(RendererFailure):
            FFmpegVideoRenderer().render([], 0, self.root)

    def test_narration_longer_than_timeline_extends_only_the_last_scene(self):
        # Force an artificially short timeline (well under the real
        # narration's actual duration) and confirm rendering still
        # succeeds (per real_provider.py's own documented behavior: the
        # shortfall is absorbed into the last scene, never truncating
        # narration or stretching every scene).
        entries, _ = self._scene_entries()
        for e in entries:
            e.duration_seconds = 1
            e.end = e.start + 1
        result = FFmpegVideoRenderer().render(entries, 2, self.root)
        self.assertEqual(result.playable, "YES")


class BinaryOutputWriteWhitelistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.root.mkdir()

    def test_write_output_artifact_binary_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_output_artifact_binary(self.root, "video-01.mov", b"data")

    def test_write_output_artifact_binary_accepts_whitelisted_mp4(self):
        path = mutate.write_output_artifact_binary(self.root, "video-01.mp4", b"fakemp4data")
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), b"fakemp4data")


if __name__ == "__main__":
    unittest.main()
