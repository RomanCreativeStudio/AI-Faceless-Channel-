"""Tests 24, 25: a malformed existing assets/asset-<n>.md (an
Asset-agent-owned hash field present but blank) fails safely rather than
guessing; a missing PRODUCTION.md (no provenance/context to build assets
against) fails safely rather than crashing.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_asset_generation
from .builders import build_visual_planned_item


class FailureSafetyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 24: malformed existing ASSET.md fails safely ---
    def test_malformed_existing_asset_record_fails_safely(self):
        build_visual_planned_item(self.root)
        run_asset_generation(self.root, apply=True)

        asset_path = self.root / "assets" / "asset-02.md"
        text = asset_path.read_text(encoding="utf-8")
        line = [l for l in text.splitlines() if l.startswith("| Scene/visual content hash |")][0]
        text = text.replace(line, "| Scene/visual content hash |  |")
        asset_path.write_text(text, encoding="utf-8")

        result = run_asset_generation(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("malformed", result.abort_reason)
        self.assertFalse(result.produced)

    # --- Test 25: missing PRODUCTION.md fails safely ---
    def test_missing_production_plan_fails_safely(self):
        build_visual_planned_item(self.root)
        (self.root / "PRODUCTION.md").unlink()

        result = run_asset_generation(self.root, apply=True)
        self.assertTrue(result.aborted)
        self.assertIn("PRODUCTION.md", result.abort_reason)
        self.assertFalse(result.produced)
        self.assertFalse((self.root / "assets" / "asset-01.md").exists())


if __name__ == "__main__":
    unittest.main()
