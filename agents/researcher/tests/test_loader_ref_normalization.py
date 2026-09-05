"""Regression test: agents/researcher/src/loader.py's
normalize_claim_ref/normalize_research_ref must never path-split the
literal placeholder "N/A" — found during Episode 1 evidence closure
(Phase 8 follow-up) when a real autonomous-revision successor claim
rendered `Derived from | `N/A` |` as the corrupted `Derived from | `A` |`
(rsplit("/", 1)[-1] on "N/A" strips the "N/" prefix, exactly as it would
for a real path like "claims/c10.md").
"""
from __future__ import annotations

import unittest

from ..src.loader import normalize_claim_ref, normalize_research_ref


class NormalizeClaimRefTests(unittest.TestCase):
    def test_na_placeholder_is_never_path_split(self):
        self.assertEqual(normalize_claim_ref("N/A"), "N/A")

    def test_na_placeholder_case_insensitive(self):
        self.assertEqual(normalize_claim_ref("n/a"), "n/a")

    def test_real_claim_path_still_normalized(self):
        self.assertEqual(normalize_claim_ref("claims/c10.md"), "c10")
        self.assertEqual(normalize_claim_ref("c10.md"), "c10")
        self.assertEqual(normalize_claim_ref("c10"), "c10")


class NormalizeResearchRefTests(unittest.TestCase):
    def test_na_placeholder_is_never_path_split(self):
        self.assertEqual(normalize_research_ref("N/A"), "N/A")

    def test_real_research_path_still_normalized(self):
        self.assertEqual(
            normalize_research_ref("research/01-who-plague-fact-sheet.md"),
            "01-who-plague-fact-sheet",
        )


if __name__ == "__main__":
    unittest.main()
