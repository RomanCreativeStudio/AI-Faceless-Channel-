# Human Safety Signoff Template

One copy per human Safety decision. Store under
`content/<pillar>/<content-id>/human_safety_signoffs/signoff-<n>.md`,
numbered sequentially per content item, never overwritten — same
Multi-pass resolution convention as `templates/REVIEW.md` (latest
attempt wins; nothing is ever deleted or edited after the fact).

**This file exists to make a human Safety decision explicit and
auditable — never inferred.** It records only the answer to one
question: does the human owner clear this content item's *currently
outstanding* `SAFETY_REVIEW` human-escalation signal(s), after reviewing
the actual script and visual treatment in context? It never overrides an
automated Safety `HIGH_RISK`/`REJECT`-tier finding, never edits or
replaces `reviews/safety_reviewer-<n>.md`, and never sets
`CONTENT_ITEM.md`'s `status` to `APPROVED` — that is a separate, later,
human content-approval decision. See
`agents/orchestrator/src/human_safety_continuation.py`'s
`continue_after_human_safety_review()` for the only code path that reads
this file to decide whether `ORIGINALITY_REVIEW` may run.

| Field | Value |
|---|---|
| Signoff ID | `<content-id>-human-safety-signoff-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Reviewer | `<name or handle of the human owner who made this decision>` |
| Decision | `CLEARED` \| `NOT_CLEARED` |
| Decided at | `<RFC3339 timestamp>` |
| Reviewed content hash | `<sha256 — must equal agents/safety/src/hashing.compute_reviewed_content_hash's current output for this item, exactly what the triggering reviews/safety_reviewer-<n>.md attempt itself hashed>` |
| Triggering review attempt | `<reviews/safety_reviewer-<n>.md path this signoff responds to>` |
| Signals covered | `<comma-separated SafetySignal names this decision addresses, e.g. SENSITIVE_CONTENT — must be every signal the triggering review flagged HIGH_RISK/REVIEW_REQUIRED>` |
| Historical/sensitive context reviewed | `YES` \| `NO` — confirms the reviewer actually read the flagged subject matter in context (script + `HUMAN_REVIEW.md`), not just the keyword |

## Review scope

`<what was actually reviewed to reach this decision — e.g. "Full SCRIPT.md, HUMAN_REVIEW.md's Safety section, and the per-scene visual treatment description" — enough for a future reader to know this wasn't a rubber stamp>`

## Notes / reasoning (optional)

`<free-text — why CLEARED or NOT_CLEARED; required if NOT_CLEARED, since "EDITORIAL REVISION REQUIRED" needs something to act on>`

## What this record does NOT do

A `CLEARED` decision here resolves only the specific Safety signal(s)
named in "Signals covered," and only for the exact "Reviewed content
hash" above — if the reviewed script or `CONTENT_ITEM.md` changes at
all afterward, this signoff becomes stale immediately and a new one is
required (mechanically checked, the same way `templates/REVIEW.md`
Multi-pass resolution rule 4 makes `PASS` staleness checkable for
automated reviews). It does not: override any `HIGH_RISK` or
`REJECT`-tier automated Safety finding; skip, delete, or rewrite the
automated `SAFETY_REVIEW` history; advance `Originality state` itself
(that still requires `agents/originality/` to actually run and record
its own result); or set `CONTENT_ITEM.md`'s `status` to `APPROVED`.

A `NOT_CLEARED` decision leaves the content item blocked
(`EDITORIAL_REVISION_REQUIRED`). Nothing in this system may retry
automatically, rewrite the script to remove the trigger, or proceed to
`ORIGINALITY_REVIEW` after a `NOT_CLEARED` decision. A later script
revision followed by a fresh automated `SAFETY_REVIEW` attempt and a new
signoff is the only way forward.
