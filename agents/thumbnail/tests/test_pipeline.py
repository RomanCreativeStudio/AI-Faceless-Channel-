"""Tests 26-31: thumbnail spec generated; theme matches script; a
hypothetical premise remains hypothetical (hedged, never asserted as
fact); no fabricated claims; dry-run/apply boundaries; protected fields.
"""
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.pipeline import run_thumbnail_generation
from .builders import build_thumbnail_ready_item

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ThumbnailPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 26: thumbnail spec generated ---
    def test_thumbnail_spec_generated_for_approved_fixture(self):
        build_thumbnail_ready_item(self.root)
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertFalse(result.blocked)
        self.assertFalse(result.aborted)
        self.assertTrue(result.produced)
        self.assertIsNotNone(result.spec)
        self.assertTrue(result.spec.title_concept)

    # --- Phase 8: real thumbnail image, opt-in ---
    def test_render_image_true_writes_a_real_png_and_records_its_reference(self):
        build_thumbnail_ready_item(self.root)
        result = run_thumbnail_generation(self.root, apply=True, render_image=True)
        self.assertTrue(result.produced)
        self.assertEqual(result.image_reference, "thumbnail/thumbnail-01.png")
        image_path = self.root / "thumbnail" / "thumbnail-01.png"
        self.assertTrue(image_path.is_file())
        self.assertTrue(image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        thumbnail_text = (self.root / "thumbnail" / "thumbnail-01.md").read_text(encoding="utf-8")
        self.assertIn("thumbnail/thumbnail-01.png", thumbnail_text)

    def test_render_image_false_default_never_writes_an_image(self):
        build_thumbnail_ready_item(self.root)
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertEqual(result.image_reference, "NOT_RENDERED")
        self.assertFalse((self.root / "thumbnail" / "thumbnail-01.png").exists())

    def test_unapproved_content_blocks(self):
        from ...producer.tests.builders import build_minimal_item
        build_minimal_item(self.root, status="SCRIPT")
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertTrue(result.blocked)
        self.assertIn("APPROVED", result.blocked_reason)

    def test_golden_sample_never_modified(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        result = run_thumbnail_generation(GOLDEN_SAMPLE, apply=True)
        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertTrue(result.blocked)
        self.assertEqual(before, after)

    # --- Test 27: theme matches script (claim/theme relationship references real claims) ---
    def test_claim_theme_relationship_references_actual_claims(self):
        build_thumbnail_ready_item(
            self.root,
            beats=["1. A factual beat. — claims: `c1`"],
        )
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertIn("c1", result.claim_theme_relationship)
        self.assertIn("FACT", result.claim_theme_relationship)

    # --- Test 28: hypothetical premise remains hypothetical ---
    def test_what_if_pillar_hedges_an_unhedged_title(self):
        build_thumbnail_ready_item(self.root, pillar="what-if", title="It Was Stopped")
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertTrue(result.spec.title_concept.lower().startswith("what if"))
        self.assertIn("It Was Stopped", result.spec.title_concept)
        # Never asserts the hypothetical as settled fact.
        self.assertNotEqual(result.spec.title_concept, "It Was Stopped")

    def test_already_hedged_title_is_used_verbatim(self):
        build_thumbnail_ready_item(
            self.root, pillar="what-if", title="Could Modern Medicine Have Stopped It?",
        )
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertEqual(result.spec.title_concept, "Could Modern Medicine Have Stopped It?")

    def test_non_what_if_pillar_title_is_never_wrapped(self):
        build_thumbnail_ready_item(self.root, pillar="history", title="The Real Event")
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertEqual(result.spec.title_concept, "The Real Event")

    def test_generated_reconstruction_authenticity_never_implies_it_happened(self):
        build_thumbnail_ready_item(
            self.root, pillar="what-if", title="Modern Medicine In The Black Death",
            beats=["1. A hypothetical beat. — claims: `c4`"],
            extra_claims=[("c4", "ASSUMPTION")],
        )
        result = run_thumbnail_generation(self.root, apply=True)
        self.assertIn("must not present it as authentic", result.authenticity_considerations)

    # --- Test 29: no fabricated claims ---
    def test_no_claims_created_or_changed(self):
        build_thumbnail_ready_item(self.root)
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_thumbnail_generation(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    # --- Test 30: dry-run/apply boundaries work ---
    def test_dry_run_makes_no_mutation(self):
        build_thumbnail_ready_item(self.root)
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_thumbnail_generation(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        self.assertEqual(before, after)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "thumbnail").exists())

    def test_apply_writes_only_thumbnail_file_and_production_sections(self):
        build_thumbnail_ready_item(self.root)
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")

        result = run_thumbnail_generation(self.root, apply=True)

        self.assertTrue(Path(result.thumbnail_path).is_file())
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)
        self.assertEqual((self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), content_item_before)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `METADATA` |", production_text)

    # --- Test 31: protected fields remain protected ---
    def test_mutate_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_thumbnail_file(self.root, "not-a-thumbnail.md", "content")

    def test_stale_title_change_blocks_silent_reuse(self):
        build_thumbnail_ready_item(self.root)
        run_thumbnail_generation(self.root, apply=True)
        thumbnail_before = (self.root / "thumbnail" / "thumbnail-01.md").read_text(encoding="utf-8")

        content_item_path = self.root / "CONTENT_ITEM.md"
        text = content_item_path.read_text(encoding="utf-8")
        text = text.replace(
            "| Working title | An Ordinary Business Story |",
            "| Working title | A Changed Title |",
        )
        content_item_path.write_text(text, encoding="utf-8")

        result = run_thumbnail_generation(self.root, apply=True)
        self.assertTrue(result.stale)
        self.assertFalse(result.produced)
        thumbnail_after = (self.root / "thumbnail" / "thumbnail-01.md").read_text(encoding="utf-8")
        self.assertEqual(thumbnail_before, thumbnail_after)


if __name__ == "__main__":
    unittest.main()
