# Review Template

One copy per reviewer pass. Store under
`content/<pillar>/<content-id>/reviews/<reviewer-type>-<n>.md`. A content
item accumulates one of these per review, per reviewer role, per attempt.

| Field | Value |
|---|---|
| Content ID | `<matches CONTENT_ITEM.md>` |
| Reviewer role | `FACT_CHECKER` \| `SAFETY_REVIEWER` \| `ORIGINALITY_REVIEWER` \| `EDITORIAL_REVIEWER` \| `PRODUCTION_QA` |
| Reviewer | `<name/handle, or "AI-assisted: <agent>" pending human confirmation>` |
| Review date | `<YYYY-MM-DD>` |
| Verdict | `PASS` \| `REVISION_REQUIRED` \| `REJECT` |
| Reviewed content hash | `<sha256 of the exact reviewed artifacts>` \| `N/A` (human reviews may leave this `N/A`; automated reviewers must populate it — see Multi-pass resolution rule 4) |

## Reasons

`<structured, itemized reasons for the verdict — required for REVISION_REQUIRED and REJECT, recommended for PASS>`

1. `<item reviewed>` — `<finding>`
2. `<item reviewed>` — `<finding>`

## Required changes (if REVISION_REQUIRED)

`<specific, actionable list; empty if PASS or REJECT>`

## Notes

`<additional context for the content owner>`

## Multi-pass resolution

A content item can accumulate several review attempts for the same role
(e.g. two fact-checker passes). This is the deterministic rule for how
that resolves into `CONTENT_ITEM.md`'s single stage state for that role:

1. **Number attempts sequentially per role, never overwrite.** Files are
   `reviews/<role>-1.md`, `reviews/<role>-2.md`, etc. Every past attempt
   stays on disk as the audit trail — nothing is deleted or edited after
   the fact.
2. **The stage state equals the verdict of the highest-numbered attempt
   for that role.** No averaging, no "2 out of 3 passed" — latest attempt
   wins, full stop.
3. **`REJECT` is terminal without human action.** No one — human or
   agent — may create a new attempt for that role after a `REJECT` until
   the human owner records an explicit reopen decision in
   `CONTENT_ITEM.md`'s Notes/history log. An agent that reaches a REJECT
   verdict stops; it does not retry itself.
4. **`PASS` is scoped to the exact artifacts reviewed.** If `SCRIPT.md` or
   any `CLAIM.md` file cited by this review changes afterward, the `PASS`
   is stale immediately — the stage state reverts to `REVISION_REQUIRED`
   and this must be logged in Notes/history log by whoever made the
   change. Mechanical detection: `Reviewed content hash` (added Phase 5)
   is the sha256 of the concatenation of `SCRIPT.md`'s content and every
   cited `claims/*.md` file's content, sorted by claim ID for a stable
   order. Recomputing it and comparing against the value stored on the
   latest attempt for a role is how staleness is detected without manual
   tracking — see `agents/researcher/src/hashing.py` for the reference
   implementation. A human review may still leave this `N/A`; in that
   case staleness reverts to the manual process obligation above.
5. **`REVISION_REQUIRED` is the only verdict an agent may act on
   autonomously** (fix and create the next attempt) without additional
   human authorization, since it's the expected, bounded retry loop. Two
   consecutive `REVISION_REQUIRED` verdicts for the same role on the same
   underlying issue is a human escalation trigger, not a third attempt —
   see `agents/researcher/CONTRACT.md`.
