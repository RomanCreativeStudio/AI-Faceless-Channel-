# Content Item Template

The master record for one piece of content, from idea through
post-publication learning. One copy of this file per content item
(suggested path: `content/<pillar>/<content-id>/CONTENT_ITEM.md`).

This is a documentation contract, not code. Future agents read and write
these fields instead of passing arbitrary text to each other.

## Identity

| Field | Value |
|---|---|
| Content ID | `<pillar-prefix>-<YYYYMMDD>-<slug>` e.g. `hist-20260902-rome-fire` |
| ↳ pillar prefixes | `business-stories`→`bs` · `history`→`hist` · `technology`→`tech` · `what-if`→`wi` |
| Working title | `<draft title>` |
| Final title | `<set at APPROVED>` |
| Content pillar | `business-stories` \| `history` \| `technology` \| `what-if` |
| Premise | `<1-3 sentence description of what this piece is about>` |
| Target audience | `<who this is for>` |
| Intended format | `<e.g. short-form, long-form, series episode>` |
| Priority | `LOW` \| `MEDIUM` \| `HIGH` |
| Creation date | `<YYYY-MM-DD>` |
| Owner | `<human owner name/handle>` |

## Pipeline status

`status` is the single source of truth for where this item sits in the
pipeline. Must be exactly one of:

```
IDEA → RESEARCH → SCRIPT → FACT_CHECK → SAFETY_REVIEW →
ORIGINALITY_REVIEW → PRODUCTION → QA → HUMAN_REVIEW → APPROVED →
PUBLISHED → ANALYZING → LEARNING → ARCHIVED

REJECTED (may occur from any stage)
```

Current status: `IDEA`

A `REVISION_REQUIRED` verdict at any gate stage (fact-check, safety,
originality, QA, human review) moves `status` back to the nearest
preceding work stage (e.g. a failed `FACT_CHECK` moves `status` back to
`SCRIPT`) for rework, and the item re-enters the pipeline forward from
there. The diagram above shows the forward path only; it does not imply
gates are one-shot.

## Stage states

Each stage tracks its own state independently of the overall `status`, so
an item's history stays visible even after `status` has moved on. Allowed
values per state family (see `templates/REVIEW.md` for reviewer detail).
When a gate state is backed by multiple review attempts (e.g. a
fact-checker retry), `templates/REVIEW.md`'s "Multi-pass resolution"
section is the authoritative rule for which attempt's verdict the gate
state reflects — always the latest, never an average.

- **Approval / gate states** (owner approval, fact-check, safety,
  originality, QA): `NOT_STARTED` \| `IN_PROGRESS` \| `PASS` \|
  `REVISION_REQUIRED` \| `REJECT`
- **Work states** (research, script, production): `NOT_STARTED` \|
  `IN_PROGRESS` \| `COMPLETE` \| `REVISION_REQUIRED`
- **Post-publication states** (publication, analytics, learning):
  `NOT_STARTED` \| `IN_PROGRESS` \| `COMPLETE`

| State | Value |
|---|---|
| Owner approval state | `NOT_STARTED` |
| Research state | `NOT_STARTED` |
| Script state | `NOT_STARTED` |
| Fact-check state | `NOT_STARTED` |
| Safety state | `NOT_STARTED` |
| Originality state | `NOT_STARTED` |
| Production state | `NOT_STARTED` |
| QA state | `NOT_STARTED` |
| Publication state | `NOT_STARTED` |
| Analytics state | `NOT_STARTED` |
| Learning state | `NOT_STARTED` |

## Linked records

- Research: `templates/RESEARCH.md` copies, one per source
- Claims: `templates/CLAIM.md` copies, one per claim
- Script: `templates/SCRIPT.md` copy
- Reviews: `templates/REVIEW.md` copies, one per reviewer pass
- Video QA: `templates/VIDEO_QA.md` copy (post-production only)

## What If? requirement

If `content pillar == what-if`, this item's research and script MUST
separate KNOWN FACT / ASSUMPTION / INFERENCE / SPECULATION per
`CONSTITUTION.md` rule 4. Hypothetical conclusions must never be presented
as established fact. See `templates/CLAIM.md` and `templates/SCRIPT.md`.

## Notes / history log

`<append-only log of major decisions, revisions, and state transitions>`
