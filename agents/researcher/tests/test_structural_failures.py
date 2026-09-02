"""Structural failure conditions from CONTRACT.md: a SCRIPT.md-cited claim
with no file, an invalid Classification, and total retrieval failure (no
research/claims at all) all map to REJECT/abort, never a silent PASS."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.models import ReviewVerdict
from ..src.pipeline import run_fact_check

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_item"


class StructuralFailureTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(FIXTURE_ROOT, self.root)

    def test_script_citing_missing_claim_is_rejected(self):
        script_path = self.root / "SCRIPT.md"
        text = script_path.read_text(encoding="utf-8")
        text += "\n| `c_does_not_exist` | `FACT` | `UNVERIFIED` | 2 |\n"
        script_path.write_text(text, encoding="utf-8")

        result = run_fact_check(self.root, apply=False)
        self.assertEqual(result.verdict, ReviewVerdict.REJECT)
        self.assertTrue(result.escalate_to_human)
        self.assertFalse(result.aborted)

    def test_invalid_classification_is_rejected(self):
        claim_path = self.root / "claims" / "c_fact_ok.md"
        text = claim_path.read_text(encoding="utf-8")
        text = text.replace("| Classification | `FACT` |", "| Classification | `MAYBE` |")
        claim_path.write_text(text, encoding="utf-8")

        result = run_fact_check(self.root, apply=False)
        self.assertEqual(result.verdict, ReviewVerdict.REJECT)

    def test_no_research_or_claims_aborts_without_writing_review(self):
        empty_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty_root, ignore_errors=True)
        (empty_root / "CONTENT_ITEM.md").write_text(
            (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = run_fact_check(empty_root, apply=True)
        self.assertTrue(result.aborted)
        self.assertEqual(result.review_path, "")
        self.assertFalse((empty_root / "reviews").exists())

    def test_no_content_item_at_all_aborts(self):
        empty_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty_root, ignore_errors=True)
        result = run_fact_check(empty_root, apply=False)
        self.assertTrue(result.aborted)


if __name__ == "__main__":
    unittest.main()
