# Project State

Last updated: 2026-09-02

## Phase

**Phase 2 — Content Intelligence Architecture.** Complete.

Phase 1 (foundational documentation & directory structure) — complete,
approved.

## Completed (Phase 2)

- `templates/CONTENT_ITEM.md` — master record schema: identity fields,
  full `status` pipeline (IDEA → ... → ARCHIVED/REJECTED), and eleven
  independent per-stage states
- `templates/RESEARCH.md` — per-source research entry schema
- `templates/CLAIM.md` — per-claim schema with FACT/INFERENCE/
  SPECULATION/ASSUMPTION classification and fact-check status
- `templates/SCRIPT.md` — script schema including a dedicated What If?
  KNOWN FACT / ASSUMPTION / INFERENCE / SPECULATION section
- `templates/REVIEW.md` — multi-reviewer schema (fact checker, safety,
  originality, editorial, production QA) with PASS/REVISION_REQUIRED/REJECT
- `templates/VIDEO_QA.md` — post-production checklist ending in a
  human-only final approval gate
- `SYSTEM.md` — updated: directory structure now includes `templates/`,
  added "Content-item architecture" section (agents-as-future-consumers
  contract), replaced prose lifecycle with the exact `status` pipeline
- `README.md` — added link to `templates/`, phase description updated
- `STATE.md` — this file

## Verified

- All six template files present under `templates/` with the exact
  filenames specified.
- All four pillars (`business-stories`, `history`, `technology`,
  `what-if`) referenced consistently across `CONTENT_ITEM.md` and
  `SYSTEM.md`; no pillar-specific fork in the schema.
- What If? fact/hypothesis separation: `CLAIM.md` classification field and
  `SCRIPT.md`'s dedicated KNOWN FACT / ASSUMPTION / INFERENCE /
  SPECULATION section both enforce it; `CONTENT_ITEM.md` cross-references
  the requirement. No path allows hypothetical content to be labeled as
  established fact.
- Every pipeline status in the task spec (IDEA, RESEARCH, SCRIPT,
  FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW, PRODUCTION, QA,
  HUMAN_REVIEW, APPROVED, PUBLISHED, ANALYZING, LEARNING, ARCHIVED,
  REJECTED) appears verbatim in both `CONTENT_ITEM.md` and `SYSTEM.md`.
- No contradictions with `CONSTITUTION.md`: `VIDEO_QA.md` final approval
  is explicitly human-only and gates `PUBLISHED`; no automation or agent
  implementation was introduced.
- No contradictions with `SYSTEM.md`'s "out of scope" list: no code,
  scripts, dependencies, agents, or API integration were added — templates
  are markdown documentation only.

## Explicitly not done (by design, this phase)

- No agents implemented (templates are the future contract, not the agents)
- No video generator
- No YouTube or other external API connection
- No implementation code, dependencies, or automation

## Next task

Populate one real, end-to-end example content item under
`content/<pillar>/<content-id>/` using the Phase 2 templates (a "golden
sample" — e.g. one `history` item carried through IDEA → SCRIPT with
2-3 research entries and claims) to validate the schema against real
content before any agent or automation work begins. Still documentation
only, no code. Requires human owner review of the sample before it's
treated as the reference pattern.
