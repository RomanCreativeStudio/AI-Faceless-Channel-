"""Builds minimal, isolated content-item directories for originality
tests. Never touches the real golden sample or any committed fixture —
each caller passes a fresh tempfile directory (see test files' setUp).
"""
from __future__ import annotations

from pathlib import Path


def write_content_item(
    root: Path,
    content_id: str = "test-item",
    pillar: str = "business-stories",
    title: str = "How a Small Bakery Chain Expanded Regionally",
    premise: str = "A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
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

- 2026-09-02 — fixture created for agents/originality/tests.
""",
        encoding="utf-8",
    )


def write_claim(
    root: Path,
    short_id: str,
    content_id: str = "test-item",
    classification: str = "FACT",
    exact_claim: str = "A fixture claim with a single checkable assertion.",
    supporting_sources: str = "`N/A`",
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
| Evidence | `N/A` |
| Confidence level | `MEDIUM` |
| Classification | `{classification}` |
| Contradictory evidence | `N/A` |
| Fact-check status | `NOT_APPLICABLE` |
""",
        encoding="utf-8",
    )


def write_script(
    root: Path,
    content_id: str = "test-item",
    ai_disclosure: str = '`NO` — no AI-generated content requiring disclosure',
    hook: str = "A regional chain's forty-store expansion started with one "
                 "surprising ingredient decision.",
    beats: list[str] | None = None,
    conclusion: str = "The expansion's real driver was a supply-chain choice, "
                       "not marketing — a lesson other small chains overlook.",
    verified_claims_rows: list[str] | None = None,
) -> None:
    beats = beats or [
        "1. Why the chain's early growth stalled, and how a single sourcing "
        "decision changed the trajectory. — claims: `c1`"
    ]
    verified_claims_rows = verified_claims_rows or ["| `c1` | `FACT` | `NOT_APPLICABLE` | 1 |"]

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

{conclusion}

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


def build_minimal_item(
    root: Path,
    content_id: str = "test-item",
    pillar: str = "business-stories",
    title: str = "How a Small Bakery Chain Expanded Regionally",
    premise: str = "A regional bakery chain grew from one shop to forty "
                    "locations by focusing on a single distinctive product line.",
    **script_kwargs,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_content_item(root, content_id=content_id, pillar=pillar, title=title, premise=premise)
    write_claim(root, "c1", content_id=content_id, classification="FACT",
                supporting_sources="`research/01-source.md`")
    write_script(root, content_id=content_id, **script_kwargs)
