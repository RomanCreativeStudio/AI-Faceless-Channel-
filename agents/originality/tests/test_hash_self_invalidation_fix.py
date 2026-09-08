"""Regression test for a real, previously-latent bug found via direct
verification against Episode 1's own already-`PASS`ed review: Originality's
`compute_reviewed_content_hash()` used to hash the *entire*
CONTENT_ITEM.md file, including the `Originality state` field and
Notes/history-log line this agent's own `_apply_result` writes
*immediately after* computing that hash — so every freshly-applied
`PASS`'s own stored hash mismatched the content on disk the instant you
re-checked it, defeating `agents/orchestrator/src/freshness.py`'s
generic PASS-reuse check for Originality specifically. Mirrors the
identical bug/fix `agents/safety/src/hashing.py` already documents for
Safety.
"""
import tempfile
import unittest
from pathlib import Path

from ..src.hashing import compute_reviewed_content_hash
from ..src.loader import load_originality_bundle
from ..src.pipeline import run_originality_review
from .builders import build_minimal_item


class HashSelfInvalidationFixTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        build_minimal_item(self.root)

    def test_stored_hash_still_matches_a_fresh_rehash_after_apply(self):
        # This is exactly the check agents/orchestrator/src/freshness.py's
        # find_fresh_pass() performs before deciding whether to reuse a
        # PASS instead of re-running -- proving it here at the hash level
        # is the direct regression test for the bug.
        result = run_originality_review(self.root, apply=True, channel_index=[])
        self.assertTrue(result.review_path)

        reloaded = load_originality_bundle(self.root, channel_index=[])
        fresh_hash = compute_reviewed_content_hash(reloaded)
        self.assertEqual(fresh_hash, result.content_hash)

    def test_hash_is_stable_across_repeated_apply_writes_to_other_agents_fields(self):
        # Simulates another agent (e.g. Safety) writing its own state/
        # notes-log line to the same CONTENT_ITEM.md afterward --
        # Originality's hash must be indifferent to that too, since it
        # never reads Stage states or Notes/history log at all.
        result = run_originality_review(self.root, apply=True, channel_index=[])
        content_item_path = self.root / "CONTENT_ITEM.md"
        text = content_item_path.read_text(encoding="utf-8")
        content_item_path.write_text(
            text.replace(
                "| Safety state | `NOT_STARTED` |",
                "| Safety state | `REVISION_REQUIRED` |",
            ) + "\n- some other agent's unrelated notes-log line\n",
            encoding="utf-8",
        )
        reloaded = load_originality_bundle(self.root, channel_index=[])
        fresh_hash = compute_reviewed_content_hash(reloaded)
        self.assertEqual(fresh_hash, result.content_hash)

    def test_hash_still_changes_when_identity_genuinely_changes(self):
        # The fix must not make the hash blind to real changes -- only to
        # the fields this role itself writes to.
        bundle_before = load_originality_bundle(self.root, channel_index=[])
        hash_before = compute_reviewed_content_hash(bundle_before)

        content_item_path = self.root / "CONTENT_ITEM.md"
        text = content_item_path.read_text(encoding="utf-8")
        content_item_path.write_text(
            text.replace(
                "How a Small Bakery Chain Expanded Regionally",
                "How a Small Bakery Chain Expanded Regionally, Revised",
            ),
            encoding="utf-8",
        )
        bundle_after = load_originality_bundle(self.root, channel_index=[])
        hash_after = compute_reviewed_content_hash(bundle_after)
        self.assertNotEqual(hash_before, hash_after)

    def test_hash_still_changes_when_acknowledged_fixture_declaration_changes(self):
        bundle_before = load_originality_bundle(self.root, channel_index=[])
        hash_before = compute_reviewed_content_hash(bundle_before)

        content_item_path = self.root / "CONTENT_ITEM.md"
        text = content_item_path.read_text(encoding="utf-8")
        content_item_path.write_text(
            text.replace(
                "| Acknowledged internal fixture | `N/A` |",
                "| Acknowledged internal fixture | `some-fixture-id` |",
            ),
            encoding="utf-8",
        )
        bundle_after = load_originality_bundle(self.root, channel_index=[])
        hash_after = compute_reviewed_content_hash(bundle_after)
        self.assertNotEqual(hash_before, hash_after)


if __name__ == "__main__":
    unittest.main()
