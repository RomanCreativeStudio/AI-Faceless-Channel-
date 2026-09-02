"""Test 10 from the Phase 5 task: immutable claim correction/supersession
— plus the field-writer whitelist that makes "update only permitted
fields" (objective #14) structurally enforced, not just documented."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.loader import load_claims, load_content_item
from ..src.models import Classification
from ..src.mutate import (
    append_notes_log,
    supersede_claim,
    update_claim_field,
    update_content_item_field,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_item"


def _render_new_claim(short_id, exact_claim, classification, old_claim):
    return (
        f"# Claim {short_id} (fixture, supersedes {old_claim.short_id})\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| Claim ID | `test-mini-fixture-{short_id}` |\n"
        f"| Content ID | `{old_claim.content_id}` |\n"
        f"| Exact claim | {exact_claim} |\n"
        "| Supporting sources | `N/A` |\n"
        "| Derived from | `N/A` |\n"
        "| Evidence | `N/A` |\n"
        "| Confidence level | `N/A` |\n"
        f"| Classification | `{classification.value}` |\n"
        "| Contradictory evidence | `N/A` |\n"
        "| Fact-check status | `UNVERIFIED` |\n"
    )


class MutateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(FIXTURE_ROOT, self.root)

    def test_claim_correction_creates_new_file_and_leaves_old_table_untouched(self):
        claims = load_claims(self.root / "claims")
        old_claim = claims["c_fact_ok"]
        old_text_before = old_claim.path.read_text(encoding="utf-8")

        new_path = supersede_claim(
            old_claim,
            "c_fact_ok_v2",
            "A corrected, still-atomic version of the original claim.",
            Classification.FACT,
            reason="test correction",
            template_render=_render_new_claim,
        )

        self.assertTrue(Path(new_path).is_file())
        new_claim = load_claims(self.root / "claims")["c_fact_ok_v2"]
        self.assertEqual(new_claim.classification, Classification.FACT)

        old_text_after = old_claim.path.read_text(encoding="utf-8")
        # The original table rows are byte-identical; only a trailing
        # note was appended.
        self.assertTrue(old_text_after.startswith(old_text_before.rstrip("\n")))
        self.assertIn("Superseded", old_text_after)
        self.assertIn("c_fact_ok_v2", old_text_after)

        # Re-parsing the old claim must show the SAME classification and
        # exact_claim as before — never silently changed in place.
        reparsed_old = load_claims(self.root / "claims")["c_fact_ok"]
        self.assertEqual(reparsed_old.classification, old_claim.classification)
        self.assertEqual(reparsed_old.exact_claim, old_claim.exact_claim)

    def test_supersede_refuses_to_overwrite_existing_file(self):
        claims = load_claims(self.root / "claims")
        old_claim = claims["c_fact_ok"]
        with self.assertRaises(FileExistsError):
            supersede_claim(
                old_claim,
                "c_assumption_ok",  # already exists
                "irrelevant",
                Classification.FACT,
                reason="test",
                template_render=_render_new_claim,
            )

    def test_update_claim_field_rejects_classification(self):
        claims = load_claims(self.root / "claims")
        with self.assertRaises(PermissionError):
            update_claim_field(claims["c_fact_ok"].path, "Classification", "`INFERENCE`")

    def test_update_claim_field_rejects_exact_claim(self):
        claims = load_claims(self.root / "claims")
        with self.assertRaises(PermissionError):
            update_claim_field(claims["c_fact_ok"].path, "Exact claim", "rewritten")

    def test_update_claim_field_allows_fact_check_status(self):
        claims = load_claims(self.root / "claims")
        path = claims["c_fact_ok"].path
        update_claim_field(path, "Fact-check status", "`VERIFIED`")
        reloaded = load_claims(self.root / "claims")["c_fact_ok"]
        self.assertEqual(reloaded.fact_check_status.value, "VERIFIED")
        self.assertEqual(reloaded.classification, Classification.FACT)  # untouched

    def test_update_content_item_field_rejects_status(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        with self.assertRaises(PermissionError):
            update_content_item_field(content_item.path, "status", "`PUBLISHED`")

    def test_update_content_item_field_rejects_owner_approval(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        with self.assertRaises(PermissionError):
            update_content_item_field(content_item.path, "Owner approval state", "`PASS`")

    def test_append_notes_log_is_append_only(self):
        content_item = load_content_item(self.root / "CONTENT_ITEM.md")
        before = content_item.path.read_text(encoding="utf-8")
        append_notes_log(content_item.path, "test entry")
        after = content_item.path.read_text(encoding="utf-8")
        self.assertTrue(after.startswith(before.rstrip("\n")))
        self.assertIn("test entry", after)


if __name__ == "__main__":
    unittest.main()
