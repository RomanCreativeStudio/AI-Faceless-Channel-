# Revision Record Template

One copy per autonomous revision attempt on a single claim. Store under
`content/<pillar>/<content-id>/revisions/revision-<n>.md`, numbered
sequentially per content item (never per claim), never overwritten.
Produced only by `agents/researcher/src/revision.py`'s Autonomous
Revision Mode — see `agents/researcher/CONTRACT.md`'s "Autonomous
Revision Mode" section.

**This file exists to make it structurally impossible to confuse an
original claim with its corrected successor.** The original claim's own
table is never edited (see `templates/CLAIM.md`'s Atomicity rule); this
record is the only place the two are formally linked.

| Field | Value |
|---|---|
| Revision ID | `<content-id>-revision-<n>` |
| Original claim ID | `<claims/<short-id>.md — the untouched predecessor>` |
| Successor claim ID | `<claims/<short-id>.md — the new claim, or "N/A" if no successor was created>` |
| Triggering review attempt | `<reviews/fact_checker-<n>.md path this revision responds to>` |
| Reason for revision | `<why the original claim's evidence was found insufficient>` |
| Original claim hash | `<sha256 of the original claim's raw file content, unchanged by this revision>` |
| New claim hash | `<sha256 of the successor claim's raw file content, or "N/A">` |
| Evidence used | `<research/*.md entries actually cited — real, already-existing evidence only, never invented>` |
| Changes made | `<exactly what changed between predecessor and successor — see "Changes made" below>` |
| Revision author | `AI-assisted: researcher-agent revision engine (pending human confirmation)` |
| Revision timestamp | `<YYYY-MM-DD>` |
| Revision status | `SUCCESSOR_CREATED` \| `ESCALATED_INSUFFICIENT_EVIDENCE` \| `ESCALATED_CONTRADICTORY_EVIDENCE` \| `ESCALATED_ATOMICITY_VIOLATION` |
| Verification result | `<the successor's re-evaluated Fact-check status, or "N/A" if no successor was created>` |
| Human escalation state | `NOT_REQUIRED` \| `REQUIRED` |

## Changes made

`<precise diff-style summary — e.g. "Supporting sources: N/A -> research/03-new-source.md; all other fields unchanged." Never "Exact claim" or "Classification," since the revision engine never touches either — see CONTRACT.md's Autonomous Revision Mode>`

## Notes

`<additional context — e.g. why evidence was judged insufficient rather than manufactured>`

## What this record does NOT do

This record never grants approval of any kind. A `SUCCESSOR_CREATED`
status means a corrected, evidence-complete claim now exists — it does
**not** mean `CONTENT_ITEM.md` is `APPROVED`, does not advance
`Production status`, and does not itself change `SCRIPT.md`. If
`SCRIPT.md` still cites the original claim ID, a human must update it to
reference the successor before the fix takes effect at the script level
— this revision engine never edits `SCRIPT.md` (see
`agents/researcher/CONTRACT.md`'s Forbidden actions).
