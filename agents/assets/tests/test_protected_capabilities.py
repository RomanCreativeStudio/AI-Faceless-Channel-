"""Tests 29, 30, 31: the Asset agent cannot modify claims, cannot modify
any reviewer/review-history state, and has no publishing capability
anywhere in its code.
"""
import ast
import tempfile
import unittest
from pathlib import Path

ASSETS_SRC = Path(__file__).resolve().parents[1] / "src"


class ProtectedCapabilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

        from .builders import build_visual_planned_item
        build_visual_planned_item(self.root)

    # --- Test 29: cannot modify claims ---
    def test_claims_never_changed(self):
        from ..src.pipeline import run_asset_generation
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_asset_generation(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    # --- Test 30: cannot modify reviewer/review-history state ---
    def test_reviewer_states_never_changed(self):
        from ..src.pipeline import run_asset_generation
        (self.root / "reviews").mkdir(exist_ok=True)
        review_path = self.root / "reviews" / "safety_reviewer-1.md"
        review_path.write_text("# Review\n\n| Verdict | `PASS` |\n", encoding="utf-8")

        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        review_before = review_path.read_text(encoding="utf-8")

        run_asset_generation(self.root, apply=True)

        content_item_after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        review_after = review_path.read_text(encoding="utf-8")
        self.assertEqual(content_item_before, content_item_after)
        self.assertEqual(review_before, review_after)
        for field_line in (
            "| Fact-check state | `PASS` |",
            "| Safety state | `PASS` |",
            "| Originality state | `PASS` |",
        ):
            self.assertIn(field_line, content_item_after)

    def test_voice_records_never_changed(self):
        import tempfile as _tempfile
        from ..src.pipeline import run_asset_generation
        from .builders import build_full_pipeline_item

        tmp = _tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "item"
        build_full_pipeline_item(root)  # Producer -> Voice -> Visual Planner

        voice_before = (root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        run_asset_generation(root, apply=True)
        voice_after = (root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        self.assertEqual(voice_before, voice_after)

    # --- Test 31: no publishing capability exists anywhere in the source ---
    def test_no_publishing_capability_in_source(self):
        forbidden_calls = {"upload", "publish", "post_video", "youtube"}
        for py_file in ASSETS_SRC.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    self.assertNotIn(
                        node.id.lower(), forbidden_calls,
                        f"{py_file} references a publishing-like identifier {node.id!r}",
                    )
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(
                        node.attr.lower(), forbidden_calls,
                        f"{py_file} references a publishing-like attribute {node.attr!r}",
                    )


if __name__ == "__main__":
    unittest.main()
