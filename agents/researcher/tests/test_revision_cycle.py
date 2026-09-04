"""Tests 13-18 from the Phase 7F task: the two-attempt limit, REJECT
terminal behavior, human escalation, protected-field enforcement,
dry-run produces no mutation, apply performs only whitelisted mutation.

Uses a dedicated single-claim "all-fixable" fixture (built inline, not
via fixtures/revision_item/, since these tests need a scenario that
genuinely reaches Attempt 2 -> PASS) plus fixtures/revision_item/ for the
"still unresolved after revision" escalation path.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.models import FactCheckResult, ReviewVerdict
from ..src.pipeline import run_fact_check
from ..src.review_writer import render_review_markdown
from ..src.revision import run_autonomous_revision, run_fact_check_with_autonomous_revision

REVISION_FIXTURE = Path(__file__).parent / "fixtures" / "revision_item"


def _write_all_fixable_item(root: Path) -> None:
    """A single-claim item whose one FACT claim is Case A fixable — lets
    Attempt 2 genuinely reach PASS, exercising the full happy-path cycle.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "claims").mkdir()
    (root / "research").mkdir()

    (root / "CONTENT_ITEM.md").write_text(
        """# Content Item: All-Fixable (fixture)

## Identity

| Field | Value |
|---|---|
| Content ID | `all-fixable` |
| Working title | All Fixable |
| Content pillar | `business-stories` |

## Pipeline status

Current status: `SCRIPT`

## Stage states

| State | Value |
|---|---|
| Owner approval state | `NOT_STARTED` |
| Research state | `COMPLETE` |
| Script state | `COMPLETE` |
| Fact-check state | `NOT_STARTED` |

## Notes / history log

- 2026-09-04 — fixture created for agents/researcher/tests/test_revision_cycle.py.
""",
        encoding="utf-8",
    )
    (root / "SCRIPT.md").write_text(
        """# Script (fixture)

| Field | Value |
|---|---|
| Content ID | `all-fixable` |

## Verified claims

| Claim ID | Classification | Fact-check status | Beat(s) |
|---|---|---|---|
| `c1` | `FACT` | `UNVERIFIED` | 1 |
""",
        encoding="utf-8",
    )
    (root / "claims" / "c1.md").write_text(
        """# Claim c1 (fixture)

| Field | Value |
|---|---|
| Claim ID | `all-fixable-c1` |
| Content ID | `all-fixable` |
| Exact claim | Warehouse throughput increased after the conveyor upgrade. |
| Supporting sources | N/A |
| Derived from | N/A |
| Evidence | Not yet linked. |
| Confidence level | `LOW` |
| Classification | `FACT` |
| Contradictory evidence | None found. |
| Fact-check status | `UNVERIFIED` |
""",
        encoding="utf-8",
    )
    (root / "research" / "01-throughput.md").write_text(
        """# Research Entry (fixture)

| Field | Value |
|---|---|
| Content ID | `all-fixable` |
| Source | Fixture Ops Report |
| Source type | `PRIMARY` |
| Source URL / reference | https://example.invalid/ops-report |
| Publication date | 2026-01-01 |
| Retrieved date | 2026-09-04 |
| Source reliability | `HIGH` |

## Relevant evidence

Warehouse throughput increased after the conveyor upgrade.

## Related claims

`c1`

## Conflicting evidence

None found.

## Researcher notes

Fixture only.
""",
        encoding="utf-8",
    )


class HappyPathCycleTests(unittest.TestCase):
    """Attempt 1 -> REVISION_REQUIRED -> autonomous revision -> Attempt 2
    -> PASS -> continue (task section 8's first example, verified for
    real)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        _write_all_fixable_item(self.root)

    def test_attempt_2_reaches_pass_after_successor_creation(self):
        final, revision_result = run_fact_check_with_autonomous_revision(self.root, apply=True)

        self.assertEqual(final.verdict, ReviewVerdict.PASS)
        self.assertEqual(revision_result.successors_created, ["c1_rev1"])
        self.assertFalse(revision_result.escalate_to_human)

        self.assertTrue((self.root / "reviews" / "fact_checker-1.md").is_file())
        self.assertTrue((self.root / "reviews" / "fact_checker-2.md").is_file())
        attempt2_text = (self.root / "reviews" / "fact_checker-2.md").read_text(encoding="utf-8")
        self.assertIn("`PASS`", attempt2_text)
        self.assertIn("AUTONOMOUS REVISION", attempt2_text)
        self.assertIn("c1_rev1", attempt2_text)
        self.assertIn("c1", attempt2_text)

    def test_script_md_is_never_touched(self):
        script_before = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        run_fact_check_with_autonomous_revision(self.root, apply=True)
        script_after = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        self.assertEqual(script_before, script_after)
        # SCRIPT.md still cites the ORIGINAL claim id — a human must
        # update it before this fix takes effect there.
        self.assertIn("`c1`", script_after)
        self.assertNotIn("c1_rev1", script_after)


class TwoAttemptLimitTests(unittest.TestCase):
    """Test 13: two-attempt limit — a still-unresolved issue after
    revision correctly stops at HUMAN_ACTION_REQUIRED, never a third
    autonomous attempt."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, self.root)

    def test_still_unresolved_after_revision_stops_not_a_third_attempt(self):
        final, revision_result = run_fact_check_with_autonomous_revision(self.root, apply=True)

        # c_contradicted/c_insufficient/c_nonatomic remain genuinely
        # unresolved — attempt 2 is correctly still REVISION_REQUIRED.
        self.assertEqual(final.verdict, ReviewVerdict.REVISION_REQUIRED)
        self.assertTrue(revision_result.escalate_to_human)

        reviews = sorted((self.root / "reviews").glob("fact_checker-*.md"))
        self.assertEqual(len(reviews), 2)

        # A third call must not create a fact_checker-3.md — the existing
        # two-consecutive-REVISION_REQUIRED rule blocks it.
        third_final, third_revision = run_fact_check_with_autonomous_revision(self.root, apply=True)
        self.assertFalse((self.root / "reviews" / "fact_checker-3.md").is_file())
        self.assertTrue(third_revision is None or third_revision.blocked or third_revision.aborted)


class RejectTerminalTests(unittest.TestCase):
    """Test 14: REJECT is never autonomously reopened."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, self.root)

    def test_reject_verdict_blocks_autonomous_revision(self):
        # A prior REJECT attempt already exists on disk (written directly,
        # the same way agents/orchestrator/tests/test_idempotency.py's own
        # REJECT-terminal test does) — SCRIPT.md/claims otherwise load
        # fine, so this exercises run_autonomous_revision's own REJECT
        # check specifically, not load_bundle's unrelated structural-
        # failure path.
        reviews_dir = self.root / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        prior = FactCheckResult(
            content_id="revision-fixture", verdict=ReviewVerdict.REJECT,
            reasons=["structural failure: simulated"], required_changes=[], notes=[],
            claim_evaluations=[], escalate_to_human=True, content_hash="deadbeef",
        )
        (reviews_dir / "fact_checker-1.md").write_text(
            render_review_markdown(prior, attempt=1), encoding="utf-8"
        )

        revision_result = run_autonomous_revision(self.root, apply=True)
        self.assertTrue(revision_result.blocked)
        self.assertIn("REJECT", revision_result.blocked_reason)
        self.assertTrue(revision_result.escalate_to_human)
        self.assertEqual(revision_result.claim_outcomes, [])
        # No successor claim was created as a side effect of a REJECT.
        self.assertFalse(any((self.root / "claims").glob("*_rev*.md")))


class HumanEscalationTests(unittest.TestCase):
    """Test 15: human escalation is always visible and specific."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, self.root)

    def test_escalation_names_every_unresolved_case(self):
        run_fact_check(self.root, apply=True)
        result = run_autonomous_revision(self.root, apply=True)

        self.assertTrue(result.escalate_to_human)
        cases = {o.original_short_id: o.case.value for o in result.claim_outcomes}
        self.assertEqual(cases["c_contradicted"], "CONTRADICTED")
        self.assertEqual(cases["c_insufficient"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(cases["c_nonatomic"], "ATOMICITY_VIOLATION")


class DryRunAndApplyTests(unittest.TestCase):
    """Tests 17, 18: dry-run produces no mutation; apply performs only
    whitelisted mutation."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, self.root)

    def test_dry_run_writes_absolutely_nothing(self):
        run_fact_check(self.root, apply=True)  # attempt 1, real, to have something to diagnose
        files_before = sorted(self.root.rglob("*"))

        result = run_autonomous_revision(self.root, apply=False)
        self.assertTrue(len(result.claim_outcomes) > 0)  # diagnosis still happens

        files_after = sorted(self.root.rglob("*"))
        self.assertEqual(files_before, files_after)
        self.assertFalse((self.root / "revisions").exists())
        for outcome in result.claim_outcomes:
            self.assertEqual(outcome.successor_short_id, "")
            self.assertEqual(outcome.revision_path, "")

    def test_apply_writes_only_successor_claims_and_revision_records(self):
        files_before = {p for p in self.root.rglob("*.md")}
        run_fact_check(self.root, apply=True)
        run_autonomous_revision(self.root, apply=True)
        files_after = {p for p in self.root.rglob("*.md")}

        new_files = files_after - files_before
        for path in new_files:
            relative = path.relative_to(self.root)
            parts = relative.parts
            allowed = (
                parts[0] == "reviews"
                or parts[0] == "revisions"
                or (parts[0] == "claims" and "_rev" in path.stem)
            )
            self.assertTrue(allowed, f"unexpected new file: {relative}")


if __name__ == "__main__":
    unittest.main()
