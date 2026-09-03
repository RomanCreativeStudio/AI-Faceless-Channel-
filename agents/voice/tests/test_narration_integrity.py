"""Tests 6, 7: narration text is preserved verbatim (SOURCE NARRATION,
not the PROVIDER-READY normalization) end to end into the voice record;
What If? fact/hypothesis distinctions (hedged, uncertain language) survive
untouched — the Voice agent never removes uncertainty labels or rewrites
narration.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.narration import build_provider_ready_narration, build_source_narration
from ..src.pipeline import run_voice_generation
from .builders import build_produced_item


class NarrationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 6: narration preserved verbatim ---
    def test_source_narration_is_verbatim_and_unaltered(self):
        build_produced_item(
            self.root,
            hook="Exact hook text that must survive unchanged.",
            beats=["1. Exact beat text that must survive unchanged. — claims: `c1`"],
        )
        result = run_voice_generation(self.root, apply=True)
        self.assertIn("Exact hook text that must survive unchanged.", result.source_narration)
        self.assertIn("Exact beat text that must survive unchanged.", result.source_narration)

        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn("Exact hook text that must survive unchanged.", voice_text)
        self.assertIn("Exact beat text that must survive unchanged.", voice_text)

    # --- Test 7: What If? fact/hypothesis distinctions (hedged language) preserved ---
    def test_hedged_uncertainty_language_is_never_altered_or_removed(self):
        hedge = "it's hard to say for certain, but this remains only a hypothesis"
        build_produced_item(
            self.root,
            beats=[f"1. A speculative beat where {hedge}. — claims: `c1`"],
        )
        result = run_voice_generation(self.root, apply=True)
        self.assertIn(hedge, result.source_narration)
        self.assertIn(hedge, result.provider_ready_narration)

        voice_text = Path(result.voice_path).read_text(encoding="utf-8")
        self.assertIn(hedge, voice_text)

    def test_provider_ready_transform_only_normalizes_quotes_and_whitespace(self):
        source = "He said “it's   uncertain”  —  a  hedge."
        ready = build_provider_ready_narration(source)
        self.assertNotIn("“", ready)
        self.assertNotIn("”", ready)
        self.assertNotIn("  ", ready)
        self.assertIn('"it\'s uncertain"', ready)
        # No word/fact content changed — only quote glyphs and whitespace.
        self.assertIn("hedge.", ready)
        self.assertIn("He said", ready)


if __name__ == "__main__":
    unittest.main()
