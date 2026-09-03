"""Tests 6-10: stable scene IDs across identical re-runs; narration text
preserved verbatim; claim references preserved; What If? fact/hypothesis
distinctions survive into scenes (read-only rollup); duration is a
deterministic function of word count and words-per-minute.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.duration import estimate_duration_seconds
from ..src.pipeline import run_producer
from ..src.scene_builder import build_scenes
from .builders import build_minimal_item, write_claim, write_script


class SceneGenerationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 6: stable scene IDs ---
    def test_scene_ids_are_stable_and_ordered(self):
        build_minimal_item(
            self.root,
            beats=[
                "1. First beat text here. — claims: `c1`",
                "2. Second beat text here.",
            ],
        )
        result = run_producer(self.root, apply=True)
        scene_ids = [s.scene_id for s in result.scenes]
        self.assertEqual(
            scene_ids,
            ["test-item-scene-01", "test-item-scene-02", "test-item-scene-03"],
        )
        orders = [s.order for s in result.scenes]
        self.assertEqual(orders, sorted(orders))

    # --- Test 7: narration preserved verbatim ---
    def test_narration_text_is_verbatim_from_script(self):
        build_minimal_item(
            self.root,
            hook="Exact hook text that must survive unchanged.",
            beats=["1. Exact beat text that must survive unchanged. — claims: `c1`"],
        )
        result = run_producer(self.root, apply=True)
        narrations = [s.narration_text for s in result.scenes]
        self.assertIn("Exact hook text that must survive unchanged.", narrations)
        self.assertIn("Exact beat text that must survive unchanged.", narrations)

    # --- Test 8: claim references preserved ---
    def test_claim_references_carried_into_scenes(self):
        build_minimal_item(
            self.root,
            beats=["1. A beat citing two claims. — claims: `c1`, `c2`"],
        )
        write_claim(self.root, "c2", classification="FACT")
        result = run_producer(self.root, apply=True)
        beat_scene = [s for s in result.scenes if s.script_reference != "SCRIPT.md Hook"][0]
        self.assertEqual(beat_scene.claim_ids, ["c1", "c2"])

    # --- Test 9: What If? fact/hypothesis distinctions preserved ---
    def test_classification_rollup_preserves_what_if_distinctions(self):
        build_minimal_item(
            self.root,
            beats=["1. A speculative beat. — claims: `c1`, `c9`"],
        )
        write_claim(self.root, "c9", classification="SPECULATION")
        result = run_producer(self.root, apply=True)
        beat_scene = [s for s in result.scenes if s.script_reference != "SCRIPT.md Hook"][0]
        self.assertEqual(beat_scene.classifications_present, ["FACT", "SPECULATION"])

        scene_text = Path(result.scene_paths[-1]).read_text(encoding="utf-8")
        self.assertIn("FACT, SPECULATION", scene_text)

    # --- Test 10: deterministic duration ---
    def test_duration_is_deterministic_function_of_wpm(self):
        text = " ".join(["word"] * 30)  # 30 words
        self.assertEqual(estimate_duration_seconds(text, words_per_minute=150), 12)
        self.assertEqual(estimate_duration_seconds(text, words_per_minute=300), 6)

        build_minimal_item(self.root, hook="one two three four five", beats=[
            "1. one two three four five six seven eight. — claims: `c1`"
        ])
        script_text = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        from ...researcher.src.loader import load_claims
        claims = load_claims(self.root / "claims")
        scenes_150 = build_scenes(script_text, "test-item", claims, words_per_minute=150)
        scenes_300 = build_scenes(script_text, "test-item", claims, words_per_minute=300)
        for s150, s300 in zip(scenes_150, scenes_300):
            self.assertGreaterEqual(s150.duration_seconds, s300.duration_seconds)


if __name__ == "__main__":
    unittest.main()
