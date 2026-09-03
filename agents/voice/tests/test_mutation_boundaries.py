"""Tests 14, 15, 16: dry-run makes no mutation at all; apply writes only
the Voice agent's allowed files/fields; every protected field (content
status, approval, claims, reviewer states, production approval,
publishing status, existing review history) is untouched by a Voice run.
"""
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item


class MutationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(self.root)

    # --- Test 14: dry-run makes no mutation ---
    def test_dry_run_makes_no_mutation(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_voice_generation(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        self.assertEqual(before, after)
        self.assertFalse(result.produced)
        self.assertEqual(result.voice_path, "")
        self.assertFalse((self.root / "voice").exists())
        self.assertTrue(result.source_narration)  # still computed, just not written

    # --- Test 15: apply writes only voice-owned fields/files ---
    def test_apply_writes_only_voice_files_and_production_voiceover_section(self):
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        scenes_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }

        result = run_voice_generation(self.root, apply=True)

        self.assertTrue(Path(result.voice_path).is_file())
        self.assertTrue(Path(result.audio_path).is_file())

        self.assertEqual((self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), content_item_before)
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)
        scenes_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }
        self.assertEqual(scenes_before, scenes_after)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Voice record | `voice/voice-01.md` |", production_text)
        self.assertIn("| Production status | `VISUAL_PLANNING` |", production_text)

    # --- Test 16: every protected field remains protected ---
    def test_mutate_rejects_non_whitelisted_voice_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_voice_file(self.root, "not-a-voice-file.md", "content")

    def test_mutate_rejects_non_whitelisted_audio_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_audio_artifact(self.root, "not-audio.mp3", "content")

    def test_apply_never_touches_content_item_status_or_approval(self):
        run_voice_generation(self.root, apply=True)
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)
        self.assertIn("| Owner approval state |", content_item_text)


if __name__ == "__main__":
    unittest.main()
