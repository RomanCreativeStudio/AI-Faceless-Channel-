"""Integration test (task Step 14): an isolated APPROVED test fixture
(CONTENT_ITEM + SCRIPT + several scenes + valid claims + a real Producer
run) flows through the Voice agent end to end. Verifies script hash
consistency, verbatim narration, the provider adapter, deterministic test
audio, that production stays separate from content status, and that no
protected field changes. The real golden sample is never used for
mutation here.
"""
import tempfile
import unittest
from pathlib import Path

from ...producer.src.hashing import compute_script_content_hash
from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item, write_claim
from ..src.pipeline import run_voice_generation


class VoiceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_approved_script_through_producer_to_voice_record(self):
        # TEST FIXTURE — APPROVED: approved CONTENT_ITEM, approved SCRIPT
        # with a Hook + 3 narrative beats (-> 4 scenes), valid claims
        # (including a non-FACT one for What If? coverage), and a real
        # Producer-generated PRODUCTION.md/scenes/.
        build_minimal_item(
            self.root,
            hook="An approved opening hook for this fixture.",
            beats=[
                "1. A factual first beat. — claims: `c1`",
                "2. A hypothetical second beat. — claims: `c4`",
                "3. A speculative third beat, where it's hard to say for certain. — claims: `c9`",
            ],
        )
        write_claim(self.root, "c4", classification="ASSUMPTION")
        write_claim(self.root, "c9", classification="SPECULATION")
        producer_result = run_producer(self.root, apply=True)
        self.assertTrue(producer_result.produced)
        self.assertEqual(len(producer_result.scenes), 4)  # hook + 3 beats

        voice_result = run_voice_generation(self.root, apply=True)

        # Script hash matches between Producer's record and Voice's.
        script_text = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        expected_hash = compute_script_content_hash(script_text)
        self.assertEqual(voice_result.script_content_hash, expected_hash)
        self.assertEqual(producer_result.script_content_hash, expected_hash)

        # Narration matches every scene's narration text, verbatim.
        for scene in producer_result.scenes:
            self.assertIn(scene.narration_text, voice_result.source_narration)
        self.assertIn("it's hard to say for certain", voice_result.source_narration)

        # Provider adapter worked; deterministic test audio exists.
        self.assertEqual(voice_result.provider_label, "local-test-provider")
        self.assertTrue(voice_result.is_placeholder)
        self.assertTrue(Path(voice_result.audio_path).is_file())
        audio_text = Path(voice_result.audio_path).read_text(encoding="utf-8")
        self.assertIn("TEST / PLACEHOLDER AUDIO", audio_text)

        # Production remains separate from content status.
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `VISUAL_PLANNING` |", production_text)

        # No protected field changed.
        claims_after = {p.name for p in (self.root / "claims").glob("*.md")}
        self.assertEqual(claims_after, {"c1.md", "c4.md", "c9.md"})
        for short_id, classification in (("c1", "FACT"), ("c4", "ASSUMPTION"), ("c9", "SPECULATION")):
            claim_text = (self.root / "claims" / f"{short_id}.md").read_text(encoding="utf-8")
            self.assertIn(f"| Classification | `{classification}` |", claim_text)


if __name__ == "__main__":
    unittest.main()
