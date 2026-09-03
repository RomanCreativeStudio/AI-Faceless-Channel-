"""Tests 11, 12, 13, 18: missing narration, missing SCRIPT.md, missing
provider configuration, and a malformed existing VOICE.md all fail
safely — a structured aborted result and zero mutation, never a crash or
an invented value.
"""
import re
import tempfile
import unittest
from pathlib import Path

from ...producer.src.pipeline import run_producer
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item

_NARRATION_ROW_RE = re.compile(r"^\|\s*Narration text\s*\|.*\|\s*$", re.MULTILINE)


class FailureSafetyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 11: missing narration -> safe failure ---
    def test_missing_narration_fails_safely(self):
        build_produced_item(self.root)
        for scene_file in (self.root / "scenes").glob("*.md"):
            text = scene_file.read_text(encoding="utf-8")
            text = _NARRATION_ROW_RE.sub("| Narration text |  |", text)
            scene_file.write_text(text, encoding="utf-8")

        result = run_voice_generation(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("narration", result.abort_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "voice").exists())

    # --- Test 12: missing SCRIPT.md -> safe failure ---
    def test_missing_script_fails_safely(self):
        build_produced_item(self.root)
        (self.root / "SCRIPT.md").unlink()

        result = run_voice_generation(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("SCRIPT.md", result.abort_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "voice").exists())

    # --- Test 13: missing provider configuration -> safe failure ---
    def test_missing_provider_configuration_fails_safely(self):
        build_produced_item(self.root)
        result = run_voice_generation(self.root, apply=True, voice_configuration="")
        self.assertTrue(result.aborted)
        self.assertIn("voice configuration", result.abort_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "voice").exists())

    # --- Test 18: malformed existing VOICE.md fails safely ---
    def test_malformed_existing_voice_record_fails_safely(self):
        build_produced_item(self.root)
        run_voice_generation(self.root, apply=True)

        voice_path = self.root / "voice" / "voice-01.md"
        text = voice_path.read_text(encoding="utf-8")
        # Corrupt the record by blanking its Script content hash field.
        text = text.replace(
            [l for l in text.splitlines() if l.startswith("| Script content hash |")][0],
            "| Script content hash |  |",
        )
        voice_path.write_text(text, encoding="utf-8")

        result = run_voice_generation(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("malformed", result.abort_reason)
        self.assertFalse(result.produced)


if __name__ == "__main__":
    unittest.main()
