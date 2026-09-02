# Golden Sample Audit — Phase 3

Content ID: `wi-20260902-black-death-modern-medicine`. This audits the
`templates/` schema against a realistic `what-if` item and actively tries
to break it, per the Phase 3 task. Not a review of the sample's content
quality — a review of whether the schema holds up.

## Checklist results

**1. Can every claim be traced to evidence?**
Yes, but the original `CLAIM.md` didn't say *how* for non-`FACT` claims.
`FACT` claims (`c1`–`c3`) cite `Supporting sources` → `research/*.md`.
`INFERENCE`/`SPECULATION` claims (`c6`–`c9`) aren't independently sourced
by definition — they trace through a new `Derived from` field to the
claim IDs they're built on, which was missing before this sample. Fixed
(see below).

**2. Can fact be distinguished from inference?**
Yes. `c1`–`c3` (`FACT`) vs. `c6`/`c7` (`INFERENCE`) are structurally
distinct in the sample and the script's "What If? fact/hypothesis
separation" section keeps them in separate labeled buckets.

**3. Can assumptions be identified?**
Yes — `c4`/`c5` (`ASSUMPTION`), explicitly split into "granted" and
"withheld" elements. This was necessary to satisfy the task's requirement
to name specific technologies rather than "modern medicine" as a
monolith; the schema didn't force this split, so it's a content-authoring
discipline, not a schema guarantee. Noted as a soft risk below.

**4. Can speculation be identified?**
Yes — `c8`/`c9` (`SPECULATION`), each citing what they speculate from via
`Derived from`.

**5. Can the content item move through the defined statuses?**
IDEA → RESEARCH → SCRIPT worked cleanly for this sample. Stress-testing
the parts of the pipeline this sample doesn't reach surfaced a real gap:
the status diagram only shows a forward path, with no notation for what
happens on a `REVISION_REQUIRED` verdict at a gate stage. Fixed (see
below).

**6. Can the review structure handle this content?**
Reasoned through without instantiating (this sample stops at `SCRIPT` per
scope): `REVIEW.md`'s five reviewer roles map cleanly onto this item —
a fact checker would work through the `Verified claims` table in
`SCRIPT.md`, a safety reviewer would check the conclusion doesn't overstate
certainty (it doesn't — see `c8`/`c9`), an originality reviewer has
nothing what-if-specific to check. No gap found here.

**7. Does anything in the schema create ambiguity?**
Three found and fixed:
- `CLAIM.md`'s `Supporting sources` field read as required for every
  claim, but `ASSUMPTION`/`INFERENCE`/`SPECULATION` aren't sourced the
  same way `FACT` is.
- `CLAIM.md`'s `Fact-check status` enum (`UNVERIFIED`/`VERIFIED`/
  `DISPUTED`/`FALSE`) has no way to express "this isn't a factual claim to
  verify" for `ASSUMPTION`/`SPECULATION` — forcing e.g. `c4` into
  `UNVERIFIED` would misleadingly imply it's an unverified fact rather
  than a stipulated premise.
- `CONTENT_ITEM.md` gave one example content-ID prefix (`hist-`) but never
  defined the mapping for all four pillars, which this sample needed
  immediately (`wi-` for `what-if`).

One more found, not yet fixed (deferred, see Next task): no registry or
uniqueness check exists for content IDs across `content/`. At the current
scale (two items total) this is low risk; it becomes a real collision risk
once many items exist, and is naturally solved once any tooling/automation
exists to enumerate content items — premature to build by hand now.

**8. Does anything need to change before agents are implemented?**
Yes — the five fixes below should land before any agent is built to
produce/consume these files, since agents will rely on exactly the fields
this sample exposed as ambiguous or missing.

## Template changes made, and why

1. **`templates/CLAIM.md`** — added a `Derived from` field (claim IDs a
   claim is built on); clarified `Supporting sources` is required for
   `FACT` and `N/A` otherwise; added `NOT_APPLICABLE` to `Fact-check
   status` for claims that aren't factual assertions; added `N/A` to
   `Confidence level` for `ASSUMPTION`. Without these, every
   `INFERENCE`/`SPECULATION`/`ASSUMPTION` claim in this sample would have
   had to leave required-looking fields blank with no defined meaning.
2. **`templates/SCRIPT.md`** — added a `Verified claims` roll-up table.
   Without it, a fact-checker reviewing a real script would have to
   manually extract claim IDs from prose beats; the table makes
   `REVIEW.md`'s fact-checker pass mechanically checkable against
   `CLAIM.md`.
3. **`templates/CONTENT_ITEM.md`** — added the pillar → content-ID-prefix
   mapping (`bs`/`hist`/`tech`/`wi`) and a note on how `REVISION_REQUIRED`
   at a gate stage moves `status` back to the preceding work stage. Both
   were genuine ambiguities this sample hit directly, not hypothetical
   ones.

No structural/field changes were needed in `templates/RESEARCH.md` or
`templates/VIDEO_QA.md` — this sample didn't stress `VIDEO_QA.md` at all
(no production), and `RESEARCH.md`'s fields mapped cleanly onto all three
real sources used.

## Soft risks noted, not fixed (schema is adequate, discipline-dependent)

- Nothing enforces that a claim is atomic (single classification). This
  sample manually split compound statements (e.g. mortality figures vs.
  the reasoning built on them) into separate claims; a careless author
  could write a compound claim that blends `FACT` and `INFERENCE`. Worth
  a lint rule once automation exists; not a documentation-phase fix.
- No defined rule for how multiple `REVIEW.md` passes of the *same* role
  (e.g. two fact-checker attempts) resolve into the single `CONTENT_ITEM.md`
  fact-check state — presumably "latest attempt wins," but this is
  implicit. Left for the agent-implementation phase, where review
  sequencing will be defined in code/process anyway.

## Sources used (real, verified, not invented)

- World Health Organization, "Plague" fact sheet — https://www.who.int/news-room/fact-sheets/detail/plague
- University of Oxford, Faculty of History, "The Black Death and European Expansion" — https://www.history.ox.ac.uk/black-death-and-european-expansion
- Encyclopaedia Britannica, "Germ theory" — https://www.britannica.com/science/germ-theory

## Conclusion

The schema handles a realistic `what-if` item end-to-end through `SCRIPT`
once the three ambiguities above are fixed. It was not merely exercised —
five separate breakage points were found (three fixed as template
ambiguities, one fixed as a template gap, one deferred as low-risk at
current scale) rather than zero.

## Phase 4 addendum

Both soft risks deferred above were resolved in Phase 4 as the two
deferred-schema-question objectives:

- **Claim atomicity** — `templates/CLAIM.md` now has a deterministic
  Atomicity rule (one sentence, no causal connectors, one classification).
  Re-running this sample against it found `c3` was itself a compound
  claim (see `claims/c3.md`'s revision note) — split into `c3`/`c10`/`c11`.
  This is direct evidence the rule catches real, not just hypothetical,
  violations.
- **Multi-pass review resolution** — `templates/REVIEW.md` now has a
  Multi-pass resolution rule (sequential numbering, latest-attempt-wins,
  `REJECT` terminal without human reopening, `PASS` scoped/staleness on
  artifact change). Not exercised by this sample (no `REVIEW.md` created
  yet — it stops before `FACT_CHECK`), but consistent with everything
  else in this item.

See `agents/researcher/CONTRACT.md` for the first agent contract, which
this sample's structure (research → claims → script → pending fact-check)
was designed to exercise once that agent exists.
