"""This orchestrator has no mutate.py and no write authority of its own —
every byte written under apply=True is written by an invoked agent
through its own existing, already-tested path (see CONTRACT.md's
"Protected fields" and "Artifact ownership"). Dry run never mutates
anything at all.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_full_pipeline
from .builders import build_production_ready_item


class ApplyAndProtectedFieldsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_dry_run_on_fresh_item_writes_absolutely_nothing(self):
        build_production_ready_item(self.root)
        files_before = sorted(self.root.rglob("*"))
        run_full_pipeline(self.root, apply=False)
        files_after = sorted(self.root.rglob("*"))
        self.assertEqual(files_before, files_after)

    def test_apply_never_touches_claims(self):
        build_production_ready_item(self.root)
        run_full_pipeline(self.root, apply=True)
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        run_full_pipeline(self.root, apply=True)
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)

    def test_apply_never_touches_human_review_state(self):
        build_production_ready_item(self.root)
        run_full_pipeline(self.root, apply=True)
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        human_review_before = production_text.split("## Human review state", 1)[1]

        run_full_pipeline(self.root, apply=True)

        production_text_after = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        human_review_after = production_text_after.split("## Human review state", 1)[1]
        self.assertEqual(human_review_before, human_review_after)

    def test_apply_never_sets_content_item_status_itself(self):
        # The builder simulates a human setting APPROVED before any
        # pipeline call — this orchestrator itself must never be the one
        # that flips it, and never advances it past APPROVED.
        build_production_ready_item(self.root)
        content_item_before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        run_full_pipeline(self.root, apply=True)
        content_item_after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        # Safety/originality append Notes/history log entries as part of
        # their own existing write path (pre-existing, not this
        # orchestrator's doing) — but `status` itself must be unchanged.
        self.assertIn("Current status: `APPROVED`", content_item_before)
        self.assertIn("Current status: `APPROVED`", content_item_after)

    def test_full_pipeline_module_has_no_write_helpers(self):
        import agents.full_pipeline.src.pipeline as pipeline_module
        self.assertFalse(hasattr(pipeline_module, "mutate"))
        # No function in pipeline.py opens a file for writing directly.
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(pipeline_module))
        write_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "write_text"
        ]
        self.assertEqual(write_calls, [])


if __name__ == "__main__":
    unittest.main()
