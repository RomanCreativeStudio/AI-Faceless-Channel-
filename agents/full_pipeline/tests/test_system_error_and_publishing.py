"""Scenario 10: missing/malformed content produces SYSTEM_ERROR, never a
false PASS. Scenario 12: no publishing capability exists anywhere in this
orchestrator's source, and no full pipeline run — however far it
progresses — ever advances CONTENT_ITEM.md status or PRODUCTION.md's
Production status beyond what CONSTITUTION.md rule 2 permits.
"""
from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from ..src.models import CONTENT_REVIEW
from ..src.pipeline import run_full_pipeline
from .builders import build_production_ready_item

SRC_DIR = Path(__file__).resolve().parents[1] / "src"


class SystemErrorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_missing_content_item_is_system_error_not_pass(self):
        self.root.mkdir(parents=True)  # empty directory
        result = run_full_pipeline(self.root, apply=False)
        self.assertEqual(result.pipeline_status, "SYSTEM_ERROR")
        self.assertNotEqual(result.pipeline_status, "PASS")
        self.assertEqual(result.current_stage, CONTENT_REVIEW)

    def test_missing_script_after_review_pass_is_system_error(self):
        build_production_ready_item(self.root)
        (self.root / "SCRIPT.md").unlink()
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "SYSTEM_ERROR")
        self.assertNotEqual(result.pipeline_status, "PASS")

    def test_reviewer_crash_is_system_error_not_pass(self):
        # Reuses agents/orchestrator/'s own stage_overrides mechanism
        # indirectly is not possible here (run_full_pipeline doesn't
        # expose it — by design, this orchestrator never intercepts a
        # coordinated agent's call), so this exercises the equivalent
        # real failure mode instead: a structurally broken CONTENT_ITEM.md
        # that agents/researcher/'s own loader cannot parse.
        self.root.mkdir(parents=True)
        (self.root / "CONTENT_ITEM.md").write_text("not a valid content item at all", encoding="utf-8")
        result = run_full_pipeline(self.root, apply=False)
        self.assertEqual(result.pipeline_status, "SYSTEM_ERROR")


class NoPublishingCapabilityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_no_publishing_identifiers_anywhere_in_source(self):
        forbidden = {"upload", "publish", "post_video", "youtube", "schedule_publish"}
        for py_file in SRC_DIR.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    self.assertNotIn(node.id.lower(), forbidden, f"{py_file}: {node.id!r}")
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr.lower(), forbidden, f"{py_file}: {node.attr!r}")

    def test_no_publish_cli_flag(self):
        from ..src.__main__ import main
        with self.assertRaises(SystemExit):
            main(["--publish", str(self.root)])

    def test_only_apply_flag_registered(self):
        source = SRC_DIR.joinpath("__main__.py").read_text(encoding="utf-8")
        add_argument_calls = [
            line.strip() for line in source.splitlines() if "add_argument(" in line
        ]
        self.assertTrue(any('"--apply"' in line for line in add_argument_calls))
        self.assertFalse(any("publish" in line.lower() for line in add_argument_calls))

    def test_full_pipeline_has_no_mutate_module(self):
        self.assertFalse((SRC_DIR / "mutate.py").exists())

    def test_complete_run_never_sets_status_beyond_human_review(self):
        build_production_ready_item(self.root)
        result = run_full_pipeline(self.root, apply=True)
        self.assertEqual(result.pipeline_status, "COMPLETE")

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `HUMAN_REVIEW` |", production_text)
        self.assertNotIn("| Production status | `APPROVED` |", production_text)
        self.assertNotIn("| Production status | `READY_TO_PUBLISH` |", production_text)

        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertNotIn("Current status: `PUBLISHED`", content_item_text)


if __name__ == "__main__":
    unittest.main()
