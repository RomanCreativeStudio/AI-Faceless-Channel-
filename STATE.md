# Project State

Last updated: 2026-09-02

## Phase

**Phase 3 — Golden Sample Validation.** Complete.

Phase 1 (foundational docs/structure) and Phase 2 (content-item schema) —
complete, approved.

## Completed (Phase 3)

- `content/what-if/wi-20260902-black-death-modern-medicine/` — golden
  sample content item ("What If Modern Medicine Existed During the Black
  Death?"), taken through `IDEA → RESEARCH → SCRIPT`:
  - `CONTENT_ITEM.md` — master record, status `SCRIPT`
  - `research/01-who-plague-fact-sheet.md`, `02-oxford-black-death-history.md`,
    `03-britannica-germ-theory.md` — 3 real, verified sources (WHO,
    University of Oxford Faculty of History, Encyclopaedia Britannica); no
    invented sources or URLs
  - `claims/c1.md`–`c9.md` — 9 claims: 3 `FACT`, 2 `ASSUMPTION`, 2
    `INFERENCE`, 2 `SPECULATION`
  - `SCRIPT.md` — hook through conclusion, with a `Verified claims`
    roll-up and explicit KNOWN FACT / ASSUMPTION / INFERENCE / SPECULATION
    separation
  - `AUDIT.md` — the schema-validation report (see Schema findings below)
- `content/what-if/README.md` — one-line pointer to the golden sample
- `templates/CLAIM.md` — fixed: added `Derived from` field; clarified
  `Supporting sources` applies fully only to `FACT`; added
  `NOT_APPLICABLE` to `Fact-check status`; added `N/A` to `Confidence
  level` for `ASSUMPTION`
- `templates/SCRIPT.md` — fixed: added a `Verified claims` roll-up table
- `templates/CONTENT_ITEM.md` — fixed: added the pillar→ID-prefix mapping
  (`bs`/`hist`/`tech`/`wi`); clarified that `REVISION_REQUIRED` at a gate
  moves `status` back to the preceding work stage
- `STATE.md` — this file

## Schema findings (from actively trying to break it — see AUDIT.md for full detail)

Fixed (5): `CLAIM.md`'s `Supporting sources`/`Fact-check status`/
`Confidence level` didn't accommodate non-`FACT` claims; `SCRIPT.md` had
no consolidated claim list for fact-checkers; `CONTENT_ITEM.md` didn't
define ID prefixes for 3 of 4 pillars or how failed gate reviews loop
back. All fixed in the templates above and re-validated against the
sample.

Deferred, not fixed (2, both low-risk at current scale, both naturally
resolved once agents/tooling exist): no enforcement that a claim is
atomic (single classification) — currently author discipline; no defined
rule for how repeated `REVIEW.md` passes of the same reviewer role
resolve into one `CONTENT_ITEM.md` stage state.

## Verified

- Directory/file structure matches `SYSTEM.md`.
- All 9 sample claims trace to real evidence: `FACT` claims cite
  `research/*.md`; `INFERENCE`/`SPECULATION` cite parent claim IDs via
  `Derived from`.
- All four claim classifications (FACT/ASSUMPTION/INFERENCE/SPECULATION)
  demonstrated with 2+ examples each.
- Sample does not claim modern medicine would have prevented the Black
  Death — `claims/c8.md`/`c9.md` and the script's beat 6 exist
  specifically to preserve that uncertainty.
- "Modern medicine" is decomposed into named, granted-vs-withheld
  elements (`claims/c4.md`, `c5.md`), not treated as one technology.
- All pipeline statuses from the spec still appear identically in both
  `templates/CONTENT_ITEM.md` and `SYSTEM.md` (diffed, no drift).
- No contradictions with `CONSTITUTION.md`: no automated publishing
  claims introduced; human-only approval language unchanged.
- All 3 external URLs in the sample were fetched and verified live during
  this phase, not invented.

## Explicitly not done (by design, this phase)

- Sample does not proceed into `FACT_CHECK`/production/publishing/analytics
- No agents, automation, or external API integration
- No `REVIEW.md`/`VIDEO_QA.md` instances created (reasoned through in
  `AUDIT.md` instead, since this sample doesn't reach those stages)

## Next task

Two deferred schema findings (claim atomicity, multi-pass review
resolution) should be resolved as part of designing the first agent
(likely a research/fact-check agent), since both are workflow-semantics
questions that only need answers once something automated consumes these
files. Requires human owner review of `AUDIT.md` and sign-off before any
agent implementation begins — still no code this phase.
