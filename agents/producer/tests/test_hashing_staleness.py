"""Tests 4, 5, 14: script content hash is recorded; a changed SCRIPT.md
after production makes the plan stale (Producer refuses to silently
regenerate); prior production history is never overwritten in place.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.hashing import compute_script_content_hash
from ..src.pipeline import run_producer
from .builders import build_minimal_item


class HashingStalenessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    # --- Test 4: script content hash recorded ---
    def test_script_content_hash_is_recorded_and_correct(self):
        result = run_producer(self.root, apply=True)
        script_text = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        self.assertEqual(result.script_content_hash, compute_script_content_hash(script_text))

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn(f"| Script content hash | `{result.script_content_hash}` |", production_text)

    # --- Test 5: script change after production -> stale, not silently continued ---
    def test_script_change_after_production_makes_plan_stale(self):
        first = run_producer(self.root, apply=True)
        self.assertTrue(first.produced)

        (self.root / "SCRIPT.md").write_text(
            (self.root / "SCRIPT.md").read_text(encoding="utf-8") + "\n\nEdited after production.\n",
            encoding="utf-8",
        )

        second = run_producer(self.root, apply=True)
        self.assertTrue(second.stale)
        self.assertFalse(second.produced)
        self.assertIn("changed", second.stale_reason)

    # --- Test 14: existing production history is never overwritten ---
    def test_stale_run_does_not_overwrite_existing_production_or_scenes(self):
        run_producer(self.root, apply=True)
        production_before = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        scenes_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }

        (self.root / "SCRIPT.md").write_text(
            (self.root / "SCRIPT.md").read_text(encoding="utf-8") + "\n\nEdited after production.\n",
            encoding="utf-8",
        )
        run_producer(self.root, apply=True)

        production_after = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        scenes_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "scenes").glob("*.md")
        }
        self.assertEqual(production_before, production_after)
        self.assertEqual(scenes_before, scenes_after)

    def test_unchanged_script_rerun_is_a_noop(self):
        run_producer(self.root, apply=True)
        production_before = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")

        second = run_producer(self.root, apply=True)
        self.assertTrue(second.already_up_to_date)
        self.assertFalse(second.stale)
        self.assertFalse(second.produced)

        production_after = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertEqual(production_before, production_after)


if __name__ == "__main__":
    unittest.main()
