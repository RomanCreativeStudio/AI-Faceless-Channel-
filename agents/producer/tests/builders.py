"""Builds minimal, isolated content-item directories for Producer tests.
Never touches the real golden sample or any committed fixture — each
caller passes a fresh tempfile directory (see test files' setUp). Mirrors
agents/safety/tests/builders.py's shape, adapted for a status the
Producer's gate actually accepts (APPROVED by default).
"""
from __future__ import annotations

from pathlib import Path


def write_content_item(
    root: Path,
    content_id: str = "test-item",
    pillar: str = "business-stories",
    title: str = "An Ordinary Business Story",
    status: str = "APPROVED",
) -> None:
    (root / "CONTENT_ITEM.md").write_text(
        f"""# Content Item: {title} (test fixture)

TEST FIXTURE ONLY — never the real golden sample.

## Identity

| Field | Value |
|---|---|
| Content ID | `{content_id}` |
| Working title | {title} |
| Content pillar | `{pillar}` |

## Pipeline status

Current status: `{status}`

## Stage states

| State | Value |
|---|---|
| Owner approval state | `COMPLETE` |
| Research state | `COMPLETE` |
| Script state | `COMPLETE` |
| Fact-check state | `PASS` |
| Safety state | `PASS` |
| Originality state | `PASS` |
| Production state | `NOT_STARTED` |

## Notes / history log

- 2026-09-02 — fixture created for agents/producer/tests.
""",
        encoding="utf-8",
    )


def write_claim(
    root: Path,
    short_id: str,
    content_id: str = "test-item",
    classification: str = "FACT",
    exact_claim: str = "A fixture claim with a single checkable assertion.",
) -> None:
    (root / "claims").mkdir(exist_ok=True)
    (root / "claims" / f"{short_id}.md").write_text(
        f"""# Claim {short_id} (fixture)

| Field | Value |
|---|---|
| Claim ID | `{content_id}-{short_id}` |
| Content ID | `{content_id}` |
| Exact claim | {exact_claim} |
| Supporting sources | `N/A` |
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
    hook: str = "An ordinary hook line to open the video.",
    beats: list[str] | None = None,
    verified_claims_rows: list[str] | None = None,
) -> None:
    beats = beats if beats is not None else [
        "1. **First beat** — an ordinary first narration beat with enough words to "
        "estimate a duration. — claims: `c1`",
    ]
    verified_claims_rows = verified_claims_rows or ["| `c1` | `FACT` | `NOT_APPLICABLE` | 1 |"]

    (root / "SCRIPT.md").write_text(
        f"""# Script (test fixture)

TEST FIXTURE ONLY.

| Field | Value |
|---|---|
| Content ID | `{content_id}` |
| AI disclosure required | `NO` — no AI-generated content requiring disclosure |

## Hook

{hook}

## Premise

An ordinary premise.

## Narrative beats

{chr(10).join(beats)}

## Verified claims

| Claim ID | Classification | Fact-check status | Beat(s) |
|---|---|---|---|
{chr(10).join(verified_claims_rows)}

## Transitions

N/A.

## Conclusion

An ordinary conclusion.

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
    title: str = "An Ordinary Business Story",
    status: str = "APPROVED",
    **script_kwargs,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_content_item(root, content_id=content_id, pillar=pillar, title=title, status=status)
    write_claim(root, "c1", content_id=content_id, classification="FACT")
    write_script(root, content_id=content_id, **script_kwargs)
