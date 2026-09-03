"""Tests 21, 22, 23: the Voice agent cannot modify claims, cannot modify
any reviewer/review-history state, and has no publishing capability
anywhere in its code.
"""
import ast
import tempfile
import unittest
from pathlib import Path

VOICE_SRC = Path(__file__).resolve().parents[1] / "src"


class ProtectedCapabilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

        from .builders import build_produced_item
        build_produced_item(self.root)

    # --- Test 21: cannot modify claims ---
    def test_claims_never_changed(self):
        from ..src.pipeline import run_voice_generation
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_voice_generation(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    # --- Test 22: cannot modify reviewer/review-history state ---
    def test_reviewer_states_never_changed(self):
        from ..src.pipeline import run_voice_generation
        (self.root / "reviews").mkdir(exist_ok=True)
        review_path = self.root / "reviews" / "safety_reviewer-1.md"
        review_path.write_text("# Review\n\n| Verdict | `PASS` |\n", encoding="utf-8")

        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        review_before = review_path.read_text(encoding="utf-8")

        run_voice_generation(self.root, apply=True)

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

    # --- Test 23: no publishing capability exists anywhere in the source ---
    def test_no_publishing_capability_in_source(self):
        forbidden_calls = {"upload", "publish", "post_video", "youtube"}
        for py_file in VOICE_SRC.glob("*.py"):
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
