"""Phase 7G integration tests: Bounded Research Mode wired into
agents/researcher/src/revision.py's Case C (INSUFFICIENT_EVIDENCE) path.
Covers task areas: research-only-when-permitted (never Case B), a
successful bounded-research pass handing off to the existing Case A
create_successor_claim mechanism unchanged, contradiction/conflict/
still-insufficient escalation, dry-run vs apply, predecessor immutability
continuing to hold, and a real end-to-end fixture (not just
helper-function tests) reaching PASS via bounded research.

Never touches the golden sample — every test builds its own tempdir item.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from ..src.hashing import compute_claim_hash
from ..src.loader import load_bundle, load_claims
from ..src.models import DiscoveryStatus, RevisionCase, RevisionStatus, ReviewVerdict
from ..src.pipeline import run_fact_check
from ..src.research_provider import ResearchProviderResult
from ..src.revision import diagnose_claim, run_autonomous_revision, run_fact_check_with_autonomous_revision
from ..src.test_research_provider import (
    LocalTestResearchProvider,
    conflicting_pair,
    contradiction_result,
    strong_support_result,
)

REVISION_FIXTURE = Path(__file__).parent / "fixtures" / "revision_item"


def _write_insufficient_only_item(root: Path, exact_claim: str = "The supplier contract renewal lowered per-unit costs by twelve percent.") -> None:
    """A single-claim item with genuinely zero research on disk — the one
    scenario Bounded Research Mode's Case C extension exists for.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "claims").mkdir()
    (root / "research").mkdir()

    (root / "CONTENT_ITEM.md").write_text(
        """# Content Item: Insufficient-Only (fixture)

## Identity

| Field | Value |
|---|---|
| Content ID | `insufficient-only` |
| Working title | Insufficient Only |
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

- 2026-09-05 — fixture created for agents/researcher/tests/test_research_cycle.py.
""",
        encoding="utf-8",
    )
    (root / "SCRIPT.md").write_text(
        """# Script (fixture)

| Field | Value |
|---|---|
| Content ID | `insufficient-only` |

## Verified claims

| Claim ID | Classification | Fact-check status | Beat(s) |
|---|---|---|---|
| `c1` | `FACT` | `UNVERIFIED` | 1 |
""",
        encoding="utf-8",
    )
    (root / "claims" / "c1.md").write_text(
        f"""# Claim c1 (fixture)

| Field | Value |
|---|---|
| Claim ID | `insufficient-only-c1` |
| Content ID | `insufficient-only` |
| Exact claim | {exact_claim} |
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


class ResearchOnlyWhenPermittedTests(unittest.TestCase):
    """Bounded research is only ever reachable through Case C — Case B
    (CONTRADICTED) must never invoke a provider search."""

    def test_contradicted_claim_never_triggers_a_provider_search(self):
        calls = []

        class _TrackingProvider:
            label = "tracking"

            def search(self, query):
                calls.append(query)
                return ResearchProviderResult(query=query, results=[])

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, root)

        run_fact_check(root, apply=True)
        run_autonomous_revision(root, apply=True, research_provider=_TrackingProvider())

        # c_contradicted is in this fixture and must never reach the
        # provider; c_insufficient IS expected to (that's the point of
        # Case C's extension) — so calls should name only c_insufficient.
        self.assertTrue(all(q.claim_short_id != "c_contradicted" for q in calls))


class SupportedResearchCreatesSuccessorTests(unittest.TestCase):
    """A SUPPORTED bounded-research outcome hands off to the SAME
    create_successor_claim mechanism Case A already uses — no new,
    competing claim-creation path exists."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        _write_insufficient_only_item(self.root)

    def _provider(self):
        return LocalTestResearchProvider({"c1": [strong_support_result("c1")]})

    def test_apply_true_creates_a_research_record_and_a_successor_claim(self):
        run_fact_check(self.root, apply=True)
        result = run_autonomous_revision(self.root, apply=True, research_provider=self._provider())

        outcome = result.claim_outcomes[0]
        self.assertEqual(outcome.case, RevisionCase.FIXABLE)
        self.assertEqual(outcome.successor_short_id, "c1_rev1")
        self.assertFalse(result.escalate_to_human)

        research_files = sorted((self.root / "research").glob("*.md"))
        self.assertEqual(len(research_files), 1)
        successor = load_claims(self.root / "claims")["c1_rev1"]
        self.assertIn(f"research/{research_files[0].stem}.md", successor.supporting_sources)

    def test_predecessor_remains_byte_prefix_identical_after_research_driven_revision(self):
        run_fact_check(self.root, apply=True)
        predecessor_path = self.root / "claims" / "c1.md"
        before = predecessor_path.read_bytes()

        run_autonomous_revision(self.root, apply=True, research_provider=self._provider())

        after = predecessor_path.read_bytes()
        self.assertTrue(after.startswith(before.rstrip(b"\n")))

    def test_full_re_fact_check_via_run_fact_check_with_autonomous_revision_reaches_pass(self):
        """The real end-to-end fixture: attempt 1 REVISION_REQUIRED (no
        evidence at all) -> Case C -> bounded research finds support ->
        research record + successor claim -> attempt 2 -> PASS.
        """
        final, revision_result = run_fact_check_with_autonomous_revision(
            self.root, apply=True, research_provider=self._provider(),
        )
        self.assertEqual(final.verdict, ReviewVerdict.PASS)
        self.assertEqual(revision_result.successors_created, ["c1_rev1"])
        self.assertFalse(revision_result.escalate_to_human)
        self.assertTrue((self.root / "reviews" / "fact_checker-2.md").is_file())
        # SCRIPT.md still names the original claim — a human closes the loop.
        script_text = (self.root / "SCRIPT.md").read_text(encoding="utf-8")
        self.assertIn("`c1`", script_text)
        self.assertNotIn("c1_rev1", script_text)

    def test_dry_run_finds_support_but_writes_nothing_and_still_escalates(self):
        run_fact_check(self.root, apply=True)
        files_before = sorted(self.root.rglob("*"))

        result = run_autonomous_revision(self.root, apply=False, research_provider=self._provider())

        files_after = sorted(self.root.rglob("*"))
        self.assertEqual(files_before, files_after)
        self.assertTrue(result.escalate_to_human)
        outcome = result.claim_outcomes[0]
        self.assertEqual(outcome.successor_short_id, "")
        self.assertIn("dry run", outcome.reason.lower())


class ContradictedByResearchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        _write_insufficient_only_item(self.root)

    def test_contradicting_source_escalates_never_rewrites(self):
        run_fact_check(self.root, apply=True)
        provider = LocalTestResearchProvider({"c1": [contradiction_result("c1")]})
        result = run_autonomous_revision(self.root, apply=True, research_provider=provider)

        outcome = result.claim_outcomes[0]
        self.assertEqual(outcome.case, RevisionCase.CONTRADICTED)
        self.assertEqual(outcome.successor_short_id, "")
        self.assertTrue(result.escalate_to_human)
        self.assertFalse((self.root / "claims" / "c1_rev1.md").exists())

        text = Path(outcome.revision_path).read_text(encoding="utf-8")
        self.assertIn(RevisionStatus.ESCALATED_CONTRADICTORY_EVIDENCE.value, text)


class ConflictByResearchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        _write_insufficient_only_item(self.root)

    def test_disagreeing_sources_escalate_as_explicit_conflict_never_silently_picked(self):
        run_fact_check(self.root, apply=True)
        provider = LocalTestResearchProvider({"c1": conflicting_pair("c1")})
        result = run_autonomous_revision(self.root, apply=True, research_provider=provider)

        outcome = result.claim_outcomes[0]
        self.assertEqual(outcome.case, RevisionCase.RESEARCH_CONFLICT)
        self.assertEqual(outcome.successor_short_id, "")
        self.assertTrue(result.escalate_to_human)

        text = Path(outcome.revision_path).read_text(encoding="utf-8")
        self.assertIn(RevisionStatus.ESCALATED_RESEARCH_CONFLICT.value, text)


class StillInsufficientAfterResearchTests(unittest.TestCase):
    def test_no_provider_data_still_escalates_as_insufficient(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name) / "item"
        _write_insufficient_only_item(root)

        run_fact_check(root, apply=True)
        # Default provider (LocalTestResearchProvider with no fixture data)
        # — bounded research runs, finds nothing, still escalates.
        result = run_autonomous_revision(root, apply=True)

        outcome = result.claim_outcomes[0]
        self.assertEqual(outcome.case, RevisionCase.INSUFFICIENT_EVIDENCE)
        self.assertTrue(result.escalate_to_human)
        self.assertIn("bounded research", outcome.reason.lower())


class RejectedResearchEntryNeverTreatedAsReciprocalTests(unittest.TestCase):
    """The safety fix this integration required: a research entry this
    engine itself marked REJECTED must never be picked up by Case A's
    reciprocal-evidence detector on a later run, even though it names the
    claim in its own Related claims field (full-auditability, not tacit
    endorsement).
    """

    def test_a_rejected_entry_naming_the_claim_does_not_make_it_fixable(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name) / "item"
        _write_insufficient_only_item(root)

        (root / "research" / "01-rejected.md").write_text(
            """# Research Entry (fixture — deliberately REJECTED)

| Field | Value |
|---|---|
| Content ID | `insufficient-only` |
| Source | Fixture Rejected Source |
| Source type | `OTHER` |
| Source URL / reference | https://example.invalid/rejected |
| Publication date | unknown |
| Retrieved date | 2026-09-05 |
| Source reliability | `UNVERIFIED` |
| Discovery status | `REJECTED` |
| Provider result ID | `N/A` |
| Retrieval verified | `NO` |

## Relevant evidence

Fixture excerpt.

## Related claims

`c1`

## Claim support relationship

`SUPPORTS`

## Conflicting evidence

N/A

## Rejection reason

fixture: deliberately rejected, never real evidence.

## Researcher notes

Fixture only.
""",
            encoding="utf-8",
        )

        bundle = load_bundle(root)
        entry = bundle.research["01-rejected"]
        self.assertEqual(entry.discovery_status, DiscoveryStatus.REJECTED)
        self.assertIn("c1", entry.related_claims)

        case, reason, reciprocal = diagnose_claim(bundle.claims["c1"], bundle)
        self.assertEqual(case, RevisionCase.INSUFFICIENT_EVIDENCE)
        self.assertIsNone(reciprocal)


if __name__ == "__main__":
    unittest.main()
