"""Test 15 from the Phase 6 task: the Safety Reviewer cannot modify
protected fields — claim classification/wording, owner approval,
publishing/content status, research/fact-check state."""
import tempfile
import unittest
from pathlib import Path

from ..src.mutate import CONTENT_ITEM_WRITABLE_FIELDS, update_content_item_field
from .builders import build_minimal_item


class ProtectedFieldsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    def test_whitelist_is_exactly_safety_state(self):
        self.assertEqual(CONTENT_ITEM_WRITABLE_FIELDS, {"Safety state"})

    def test_cannot_write_status(self):
        with self.assertRaises(PermissionError):
            update_content_item_field(self.root / "CONTENT_ITEM.md", "status", "`PUBLISHED`")

    def test_cannot_write_owner_approval_state(self):
        with self.assertRaises(PermissionError):
            update_content_item_field(self.root / "CONTENT_ITEM.md", "Owner approval state", "`PASS`")

    def test_cannot_write_research_state(self):
        with self.assertRaises(PermissionError):
            update_content_item_field(self.root / "CONTENT_ITEM.md", "Research state", "`COMPLETE`")

    def test_cannot_write_fact_check_state(self):
        with self.assertRaises(PermissionError):
            update_content_item_field(self.root / "CONTENT_ITEM.md", "Fact-check state", "`PASS`")

    def test_has_no_claim_writing_function_at_all(self):
        import agents.safety.src.mutate as safety_mutate
        self.assertFalse(hasattr(safety_mutate, "update_claim_field"))

    def test_safety_state_is_writable(self):
        update_content_item_field(self.root / "CONTENT_ITEM.md", "Safety state", "`PASS`")
        text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("| Safety state | `PASS` |", text)


if __name__ == "__main__":
    unittest.main()
