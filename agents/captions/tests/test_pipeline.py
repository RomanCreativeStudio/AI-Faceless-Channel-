"""Full-pipeline tests: 19-25 exercised end to end — deterministic
generation, faithful caption text, no new claims, dry-run/apply
boundaries, protected fields, plus the standard approval/staleness gates.
"""
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.pipeline import run_caption_generation
from .builders import build_captions_ready_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class CaptionsPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_captions_ready_item(
            self.root,
            hook="Exact hook text that must survive unchanged.",
            beats=["1. A factual beat, where it's hard to say for certain. — claims: `c1`"],
        )

    def test_approved_fixture_generates_captions(self):
        result = run_caption_generation(self.root, apply=True)
        self.assertFalse(result.blocked)
        self.assertFalse(result.aborted)
        self.assertTrue(result.produced)
        self.assertEqual(result.generation_status, "GENERATED")

    def test_unapproved_content_blocks(self):
        from ...producer.tests.builders import write_content_item
        write_content_item(self.root, content_id="test-item", status="SCRIPT")
        result = run_caption_generation(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)

    def test_golden_sample_never_modified(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_caption_generation(GOLDEN_SAMPLE, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertTrue(result.blocked)
        self.assertEqual(before, after)

    # --- Test 21 (pipeline level): caption text faithful to narration ---
    def test_all_caption_text_is_verbatim_substring_of_narration(self):
        result = run_caption_generation(self.root, apply=True)
        scenes_by_filename = {}
        for scene_dir in (self.root / "scenes").glob("*.md"):
            text = scene_dir.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.startswith("| Narration text |"):
                    scenes_by_filename[scene_dir.name] = line
        for scene in result.scenes:
            narration_line = scenes_by_filename[scene.scene_filename]
            for chunk in scene.chunks:
                self.assertIn(chunk.text, narration_line)

    # --- Test 22 (pipeline level): hedge language preserved end to end ---
    def test_hedge_language_preserved_in_generated_file(self):
        result = run_caption_generation(self.root, apply=True)
        captions_text = Path(result.captions_path).read_text(encoding="utf-8")
        self.assertIn("hard to say for certain", captions_text)

    # --- Test 23: no new claims introduced ---
    def test_no_claims_created_or_changed(self):
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_caption_generation(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    # --- Test 24: dry-run/apply boundaries work ---
    def test_dry_run_makes_no_mutation(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_caption_generation(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        self.assertEqual(before, after)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "captions").exists())

    def test_apply_writes_only_captions_file_and_production_section(self):
        scenes_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")

        result = run_caption_generation(self.root, apply=True)

        self.assertTrue(Path(result.captions_path).is_file())
        scenes_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }
        self.assertEqual(scenes_before, scenes_after)
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `THUMBNAIL` |", production_text)

    # --- Test 25: protected fields remain protected ---
    def test_mutate_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_captions_file(self.root, "not-captions.md", "content")

    def test_stale_narration_change_blocks_silent_reuse(self):
        run_caption_generation(self.root, apply=True)
        captions_before = Path(self.root / "captions" / "captions-01.md").read_text(encoding="utf-8")

        scene_path = self.root / "scenes" / "scene-02.md"
        text = scene_path.read_text(encoding="utf-8")
        import re
        text = re.sub(
            r"^\|\s*Narration text\s*\|.*\|\s*$",
            "| Narration text | Edited narration after caption generation. |",
            text, flags=re.MULTILINE,
        )
        scene_path.write_text(text, encoding="utf-8")

        result = run_caption_generation(self.root, apply=True)
        self.assertTrue(result.stale)
        self.assertFalse(result.produced)
        captions_after = Path(self.root / "captions" / "captions-01.md").read_text(encoding="utf-8")
        self.assertEqual(captions_before, captions_after)


if __name__ == "__main__":
    unittest.main()
