"""Tests 4, 5, 17: script content hash is recorded on the voice record;
a changed SCRIPT.md after voice generation makes the existing voice
result stale (never silently reused or regenerated); prior voice history
is never overwritten in place.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.src.hashing import compute_script_content_hash
from ...producer.src.pipeline import run_producer
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item


class HashingStalenessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(self.root)

    # --- Test 4: script content hash recorded ---
    def test_script_content_hash_is_recorded_and_correct(self):
        result = run_voice_generation(self.root, apply=True)
        script_text = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        self.assertEqual(result.script_content_hash, compute_script_content_hash(script_text))

        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn(f"| Script content hash | `{result.script_content_hash}` |", voice_text)

    # --- Test 5: script change after voice generation -> stale ---
    def test_script_change_after_generation_makes_voice_stale(self):
        first = run_voice_generation(self.root, apply=True)
        self.assertTrue(first.produced)

        # Re-run the Producer so PRODUCTION.md's own hash stays consistent
        # with the changed script (otherwise Voice would block earlier, on
        # the Producer<->script mismatch, rather than reach its own
        # voice-record staleness check).
        (self.root / "SCRIPT.md").write_text(
            (self.root / "SCRIPT.md").read_text(encoding="utf-8") + "\n\nEdited after voice generation.\n",
            encoding="utf-8",
        )
        (self.root / "PRODUCTION.md").unlink()
        for scene_file in (self.root / "scenes").glob("*.md"):
            scene_file.unlink()
        producer_result = run_producer(self.root, apply=True)
        self.assertTrue(producer_result.produced)

        second = run_voice_generation(self.root, apply=True)
        self.assertTrue(second.stale)
        self.assertFalse(second.produced)
        self.assertIn("changed", second.stale_reason)

    # --- Test 17: existing voice history is never overwritten ---
    def test_stale_run_does_not_overwrite_existing_voice_record_or_audio(self):
        run_voice_generation(self.root, apply=True)
        voice_before = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        audio_before = (self.root / "voice" / "voice-01.audio.txt").read_text(encoding="utf-8")

        (self.root / "SCRIPT.md").write_text(
            (self.root / "SCRIPT.md").read_text(encoding="utf-8") + "\n\nEdited after voice generation.\n",
            encoding="utf-8",
        )
        (self.root / "PRODUCTION.md").unlink()
        for scene_file in (self.root / "scenes").glob("*.md"):
            scene_file.unlink()
        run_producer(self.root, apply=True)
        run_voice_generation(self.root, apply=True)

        voice_after = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        audio_after = (self.root / "voice" / "voice-01.audio.txt").read_text(encoding="utf-8")
        self.assertEqual(voice_before, voice_after)
        self.assertEqual(audio_before, audio_after)

    def test_unchanged_script_rerun_is_a_noop(self):
        run_voice_generation(self.root, apply=True)
        voice_before = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")

        second = run_voice_generation(self.root, apply=True)
        self.assertTrue(second.already_up_to_date)
        self.assertFalse(second.stale)
        self.assertFalse(second.produced)

        voice_after = (self.root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        self.assertEqual(voice_before, voice_after)


if __name__ == "__main__":
    unittest.main()
