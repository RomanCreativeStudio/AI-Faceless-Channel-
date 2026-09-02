"""Tests 17, 18, 21, 22: dry-run causes no mutation; apply mode respects
each reviewer's own field whitelist; the orchestrator itself cannot
modify protected fields (it has no mutate.py / write path at all); no
publishing capability exists anywhere in this package."""
import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import run_automated_review
from .builders import build_all_pass_item

ORCHESTRATOR_SRC = Path(__file__).resolve().parents[1] / "src"


class ApplyAndProtectedFieldsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_all_pass_item(self.root)

    # --- Test 17: dry-run causes no mutation ---
    def test_dry_run_writes_nothing(self):
        before = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        result = run_automated_review(self.root, apply=False, originality_channel_index=[])
        after = {p: p.read_text(encoding="utf-8") for p in self.root.rglob("*.md")}
        self.assertEqual(before, after)
        self.assertFalse((self.root / "reviews").exists())
        self.assertEqual(result.overall_result.value, "PASS")  # sanity: it did run, just didn't write

    # --- Test 18: apply mode respects each reviewer's field whitelist ---
    def test_apply_only_touches_each_agents_own_whitelisted_field(self):
        before = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        run_automated_review(self.root, apply=True, originality_channel_index=[])
        after = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")

        self.assertIn("| Fact-check state | `PASS` |", after)
        self.assertIn("| Safety state | `PASS` |", after)
        self.assertIn("| Originality state | `PASS` |", after)
        # Untouched fields:
        self.assertIn("| Owner approval state | `NOT_STARTED` |", after)
        self.assertIn("Current status: `SCRIPT`", after)
        self.assertNotEqual(before, after)

        for role_prefix in ("fact_checker", "safety_reviewer", "originality_reviewer"):
            self.assertTrue((self.root / "reviews" / f"{role_prefix}-1.md").is_file())

    def test_apply_never_touches_claims_or_research(self):
        claims_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        research_before = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "research").glob("*.md")
        }
        run_automated_review(self.root, apply=True, originality_channel_index=[])
        claims_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "claims").glob("*.md")
        }
        research_after = {
            p: p.read_text(encoding="utf-8") for p in (self.root / "research").glob("*.md")
        }
        self.assertEqual(claims_before, claims_after)
        self.assertEqual(research_before, research_after)

    # --- Test 21: orchestrator cannot modify protected fields ---
    def test_orchestrator_has_no_mutate_module_or_write_function(self):
        import importlib

        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("agents.orchestrator.src.mutate")

        from ..src import pipeline as orch_pipeline
        # No function in pipeline.py should write CONTENT_ITEM.md/claim
        # fields directly — every write happens inside an invoked stage's
        # own agent.mutate module, never here.
        source = Path(orch_pipeline.__file__).read_text(encoding="utf-8")
        self.assertNotIn("update_content_item_field", source)
        self.assertNotIn("write_text", source)

    # --- Test 22: no publishing capability exists ---
    def test_no_publishing_code_anywhere_in_orchestrator(self):
        for py_file in ORCHESTRATOR_SRC.glob("*.py"):
            text = py_file.read_text(encoding="utf-8").lower()
            self.assertNotIn("publish", text, f"unexpected 'publish' reference in {py_file}")


if __name__ == "__main__":
    unittest.main()
