# Content Item: What If Modern Medicine Existed During the Black Death?

Episode 1 — the channel's first real production item (Phase 8). Adapts
the editorial content originally developed and reviewed as the Phase 3-6
schema/engineering fixture at
`content/what-if/wi-20260902-black-death-modern-medicine/` (which remains
untouched as an engineering fixture) into a standalone, independently
produced content item, with a full spoken-narration pass (see
`SCRIPT.md`'s Narrative beats) replacing that fixture's beat-level
descriptions.

## Identity

| Field | Value |
|---|---|
| Content ID | `wi-20260904-black-death-modern-medicine-ep1` |
| Working title | What If Modern Medicine Existed During the Black Death? |
| Final title | *(not set — status has not reached APPROVED)* |
| Content pillar | `what-if` |
| Premise | How might the Black Death (1347–1351) have unfolded differently if selected 14th-century European communities possessed germ theory, basic epidemiological surveillance, sanitation practices, and quarantine/isolation capability — but *not* antibiotics, vaccines, modern diagnostics, modern pharmaceutical manufacturing, or modern hospitals? |
| Target audience | History/science-curious general audience, teens–adults |
| Intended format | Short-form explainer |
| Priority | `HIGH` — Episode 1 |
| Creation date | 2026-09-04 |
| Owner | project owner (4kingdomzs@gmail.com) |

## Pipeline status

Current status: `SCRIPT`

## Stage states

| State | Value |
|---|---|
| Owner approval state | `NOT_STARTED` |
| Research state | `COMPLETE` |
| Script state | `COMPLETE` |
| Fact-check state | `PASS` |
| Safety state | `REVISION_REQUIRED` |
| Originality state | `NOT_STARTED` |
| Production state | `NOT_STARTED` |
| QA state | `NOT_STARTED` |
| Publication state | `NOT_STARTED` |
| Analytics state | `NOT_STARTED` |
| Learning state | `NOT_STARTED` |

## Linked records

- Research: `research/01-who-plague-fact-sheet.md`, `research/02-oxford-black-death-history.md`, `research/03-britannica-germ-theory.md`
- Claims: `claims/c1.md` – `claims/c9.md`, `claims/c10.md`, `claims/c11.md`,
  `claims/c12.md` (`c5` is superseded by `c12` — see `c5.md`)
- Script: `SCRIPT.md`
- Reviews: `reviews/fact_checker-1.md`, `reviews/fact_checker-2.md`,
  `reviews/safety_reviewer-1.md`; revisions: `revisions/revision-1.md`
- Human review package: `HUMAN_REVIEW.md` (plain-language summary for
  the content owner — not part of the automated review chain)
- Video QA: none yet (no production against the canonical episode;
  see `HUMAN_REVIEW.md` for isolated-copy validation results)

## What If? requirement

This item explicitly separates KNOWN FACT / ASSUMPTION / INFERENCE /
SPECULATION throughout `claims/` and `SCRIPT.md`. It does **not** claim
modern medicine would have prevented the Black Death — see the premise
above, `SCRIPT.md`'s Conclusion, and `claims/c8.md`, `claims/c9.md` for
the modeled uncertainty.

## Notes / history log

- 2026-09-04 — Created for Phase 8 (Real Episode 1 Production) as a
  standalone content item, independent of the
  `wi-20260902-black-death-modern-medicine` engineering fixture (never
  modified). Research (`research/`) and claims (`claims/`) are carried
  over verbatim in substance — the underlying facts, sourcing, and
  FACT/ASSUMPTION/INFERENCE/SPECULATION classifications were already
  sound and independently reviewed across Phases 3, 4, and 6 (see that
  item's own `AUDIT.md` for the record of that review); only the `Claim
  ID`/`Content ID` fields were updated to this item's own ID. `SCRIPT.md`
  is substantially rewritten: the fixture's beat-level *descriptions*
  ("what actually happened: X, Y, Z") are replaced with genuine
  full-sentence spoken narration for every beat, since
  `agents/producer/`'s real scene-builder lifts each numbered beat's text
  verbatim into a scene's spoken narration — beat-level description text
  was never intended to be spoken aloud as-is.
- 2026-09-05 — [researcher agent] FACT_CHECK attempt #1 -> REVISION_REQUIRED (see reviews/fact_checker-1.md)
- 2026-09-05 — [researcher agent] FACT_CHECK attempt #2 -> PASS (see reviews/fact_checker-2.md)
- 2026-09-05 — [safety agent] SAFETY_REVIEW attempt #1 -> REVISION_REQUIRED (see reviews/safety_reviewer-1.md)
- 2026-09-05 — Inspected the SENSITIVE_CONTENT escalation (keyword
  `'plague'`) against the actual script text: no graphic, exploitative,
  or sensational language found; all mortality figures are sourced,
  hedged statistics. No editorial revision was made, since rewriting to
  avoid the keyword would not change the substance of a historical piece
  about the Black Death. Recorded as an intentional human-review gate,
  not a defect — see `HUMAN_REVIEW.md` for the full human-readable
  package (editorial summary, exact Safety trigger, visual treatment,
  production status, and the two remaining human decisions).
- 2026-09-05 — [safety agent] SAFETY_REVIEW attempt #2 -> REVISION_REQUIRED (see reviews/safety_reviewer-2.md)
