"""Tests 15-18: a malformed script (no Narrative beats) fails safely
rather than crashing or inventing scenes; a beat citing a claim with no
corresponding claims/*.md file fails safely rather than fabricating one;
the Producer never invents a claim; the Producer never changes a claim's
classification.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_producer
from .builders import build_minimal_item


class FailureSafetyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 15: malformed script (no Narrative beats) fails safely ---
    def test_missing_narrative_beats_section_fails_safely(self):
        build_minimal_item(self.root)
        script_path = self.root / "SCRIPT.md"
        text = script_path.read_text(encoding="utf-8")
        # Remove the Narrative beats section entirely.
        head, _, tail = text.partition("## Narrative beats")
        _, _, after = tail.partition("## Verified claims")
        script_path.write_text(head + "## Verified claims" + after, encoding="utf-8")

        result = run_producer(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("Narrative beats", result.abort_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "PRODUCTION.md").exists())

    # --- Test 16: missing claim reference fails safely ---
    def test_missing_claim_file_fails_safely(self):
        build_minimal_item(
            self.root,
            beats=["1. A beat citing a claim that doesn't exist. — claims: `c99`"],
        )
        result = run_producer(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("c99", result.abort_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "PRODUCTION.md").exists())
        self.assertFalse((self.root / "claims" / "c99.md").exists())

    # --- Test 17: never invents a claim ---
    def test_never_creates_a_claim_file(self):
        build_minimal_item(self.root)
        claims_before = set((self.root / "claims").glob("*.md"))
        run_producer(self.root, apply=True)
        claims_after = set((self.root / "claims").glob("*.md"))
        self.assertEqual(claims_before, claims_after)

    # --- Test 18: never changes a claim's classification ---
    def test_never_changes_claim_classification(self):
        build_minimal_item(self.root)
        claim_path = self.root / "claims" / "c1.md"
        before = claim_path.read_text(encoding="utf-8")
        run_producer(self.root, apply=True)
        after = claim_path.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertIn("| Classification | `FACT` |", after)


if __name__ == "__main__":
    unittest.main()
