"""Builds isolated, all-three-agents-passing content items for
orchestrator tests, plus a couple of deliberately-failing variants.
Never touches the real golden sample — every caller passes a fresh
tempfile directory.
"""
from __future__ import annotations

from pathlib import Path


def write_content_item(
    root: Path,
    content_id: str = "test-item",
    pillar: str = "business-stories",
    title: str = "How a Regional Hardware Store Chain Cut Delivery Costs",
    premise: str = "A regional hardware chain rerouted its delivery network "
                    "and cut costs without slowing down customer orders at all.",
) -> None:
    (root / "CONTENT_ITEM.md").write_text(
        f"""# Content Item: {title} (test fixture)

## Identity

| Field | Value |
|---|---|
| Content ID | `{content_id}` |
| Working title | {title} |
| Content pillar | `{pillar}` |
| Premise | {premise} |

## Pipeline status

Current status: `SCRIPT`

## Stage states

| State | Value |
|---|---|
| Owner approval state | `NOT_STARTED` |
| Research state | `COMPLETE` |
| Script state | `COMPLETE` |
| Fact-check state | `NOT_STARTED` |
| Safety state | `NOT_STARTED` |
| Originality state | `NOT_STARTED` |

## Notes / history log

- 2026-09-02 — fixture created for agents/orchestrator/tests.
""",
        encoding="utf-8",
    )


def write_research(
    root: Path,
    content_id: str = "test-item",
    related_claims: str = "`c1`",
) -> None:
    (root / "research").mkdir(exist_ok=True)
    (root / "research" / "01-source.md").write_text(
        f"""# Research Entry: Fixture Source (test)

| Field | Value |
|---|---|
| Content ID | `{content_id}` |
| Source | Fixture Source |
| Source type | `SECONDARY` |
| Source URL / reference | https://example.invalid/fixture-source |
| Publication date | unknown |
| Retrieved date | 2026-09-02 |
| Source reliability | `HIGH` (fixture) |

## Relevant evidence

Fixture evidence text.

## Related claims

{related_claims}

## Conflicting evidence

None found.

## Researcher notes

Fixture only.
""",
        encoding="utf-8",
    )


def write_claim(
    root: Path,
    short_id: str,
    content_id: str = "test-item",
    classification: str = "FACT",
    exact_claim: str = "Fixture source establishes a single checkable fact.",
    supporting_sources: str = "`research/01-source.md`",
) -> None:
    (root / "claims").mkdir(exist_ok=True)
    (root / "claims" / f"{short_id}.md").write_text(
        f"""# Claim {short_id} (fixture)

| Field | Value |
|---|---|
| Claim ID | `{content_id}-{short_id}` |
| Content ID | `{content_id}` |
| Exact claim | {exact_claim} |
| Supporting sources | {supporting_sources} |
| Derived from | `N/A` |
| Evidence | Fixture evidence summary. |
| Confidence level | `HIGH` |
| Classification | `{classification}` |
| Contradictory evidence | None found. |
| Fact-check status | `UNVERIFIED` |
""",
        encoding="utf-8",
    )


def write_script(
    root: Path,
    content_id: str = "test-item",
    ai_disclosure: str = '`NO` — no AI-generated content requiring disclosure',
    hook: str = "One rerouted delivery truck route quietly cut this chain's costs in half.",
    beats: list[str] | None = None,
    verified_claims_rows: list[str] | None = None,
) -> None:
    beats = beats or [
        "1. Why the old delivery routes cost so much, and how rerouting "
        "changed the math. — claims: `c1`"
    ]
    verified_claims_rows = verified_claims_rows or ["| `c1` | `FACT` | `UNVERIFIED` | 1 |"]

    (root / "SCRIPT.md").write_text(
        f"""# Script (test fixture)

| Field | Value |
|---|---|
| Content ID | `{content_id}` |
| AI disclosure required | {ai_disclosure} |

## Hook

{hook}

## Premise

An ordinary premise restated for the script.

## Narrative beats

{chr(10).join(beats)}

## Verified claims

| Claim ID | Classification | Fact-check status | Beat(s) |
|---|---|---|---|
{chr(10).join(verified_claims_rows)}

## Transitions

N/A.

## Conclusion

The real driver was the route change, not headcount — a lesson other chains overlook.

## CTA

Like and subscribe.

## Visual requirements

Standard b-roll and on-screen text.

## Music / SFX requirements

Neutral background music, no specific third-party works referenced.

## Uncertainty notes

None.
""",
        encoding="utf-8",
    )


def build_all_pass_item(root: Path, content_id: str = "test-item") -> None:
    """A content item designed so FACT_CHECK, SAFETY_REVIEW, and
    ORIGINALITY_REVIEW all independently PASS with zero shared setup
    between the three agents beyond this one fixture."""
    root.mkdir(parents=True, exist_ok=True)
    write_content_item(root, content_id=content_id)
    write_research(root, content_id=content_id)
    write_claim(root, "c1", content_id=content_id)
    write_script(root, content_id=content_id)


def build_fact_check_blocked_item(root: Path, content_id: str = "test-item") -> None:
    """Same shape, but c1 has no supporting source, so FACT_CHECK comes
    back REVISION_REQUIRED (UNRESOLVED evidence) and later stages must
    never run."""
    root.mkdir(parents=True, exist_ok=True)
    write_content_item(root, content_id=content_id)
    write_claim(root, "c1", content_id=content_id, supporting_sources="`N/A`")
    write_script(root, content_id=content_id)
