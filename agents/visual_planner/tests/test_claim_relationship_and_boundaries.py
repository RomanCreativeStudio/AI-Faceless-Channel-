"""Tests 25-30: a scene's claim relationship survives visual planning
unchanged; every field outside the Visual Planner's whitelist stays
byte-identical; dry-run makes no mutation; apply writes only whitelisted
fields/files; narration is never altered; claims/*.md are never altered.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_visual_planner
from .builders import build_produced_item


class ClaimRelationshipAndBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_produced_item(
            self.root,
            beats=["1. A beat citing two claims. — claims: `c1`, `c4`"],
            extra_claims=[("c4", "ASSUMPTION")],
        )

    # --- Test 25: claim relationship preserved ---
    def test_claim_relationship_preserved_through_planning(self):
        result = run_visual_planner(self.root, apply=True)
        plan = [p for p in result.plans if p.scene.filename == "scene-02.md"][0]
        self.assertEqual(plan.scene.claim_ids, ["c1", "c4"])

        scene_text = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")
        self.assertIn("`c1`, `c4`", scene_text)

    # --- Test 26: protected fields immutable ---
    def test_protected_scene_fields_untouched_by_apply(self):
        before_text = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")
        run_visual_planner(self.root, apply=True)
        after_text = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")

        for field_line in (
            "| Scene ID |", "| Content ID |", "| Order |", "| Duration |",
            "| Script reference |", "| Narration text |",
        ):
            before_value = next(l for l in before_text.splitlines() if l.startswith(field_line))
            after_value = next(l for l in after_text.splitlines() if l.startswith(field_line))
            self.assertEqual(before_value, after_value)

        self.assertIn("`NOT_STARTED`", after_text)  # Generation/retrieval + QA status untouched

    # --- Test 27: dry-run makes no mutation ---
    def test_dry_run_makes_no_mutation(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_visual_planner(self.root, apply=False)
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}

        self.assertEqual(before, after)
        self.assertFalse(result.planned)
        self.assertFalse((self.root / "assets").exists())

    # --- Test 28: apply respects the whitelist ---
    def test_apply_only_touches_whitelisted_fields_and_files(self):
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")

        run_visual_planner(self.root, apply=True)

        self.assertEqual((self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), content_item_before)
        self.assertEqual((self.root / "SCRIPT.md").read_text(encoding="utf-8"), script_before)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `ASSET_COLLECTION` |", production_text)
        self.assertTrue((self.root / "assets" / "asset-02.md").is_file())

    # --- Test 29: narration is never changed ---
    def test_narration_text_never_changed(self):
        before = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")
        before_narration = next(l for l in before.splitlines() if l.startswith("| Narration text |"))
        run_visual_planner(self.root, apply=True)
        after = (self.root / "scenes" / "scene-02.md").read_text(encoding="utf-8")
        after_narration = next(l for l in after.splitlines() if l.startswith("| Narration text |"))
        self.assertEqual(before_narration, after_narration)

    # --- Test 30: claims are never changed ---
    def test_claims_never_changed(self):
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_visual_planner(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)


if __name__ == "__main__":
    unittest.main()
