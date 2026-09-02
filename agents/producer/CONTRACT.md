# Contract: Producer

Specification only — **not implemented this phase.** Governs the
transition from an approved script to a structured production plan: the
first step of the production stack (Phase 7), distinct in kind from the
three review agents (Phase 6) — it doesn't judge content, it structures
already-approved content for production.

Subordinate to `CONSTITUTION.md` and to `templates/PRODUCTION.md`/
`SCENE.md` (the schema it produces against). Where anything below
conflicts with those, they win.

## Purpose

Transform an approved `SCRIPT.md` into `templates/PRODUCTION.md` (the
production record) and an ordered set of `templates/SCENE.md` records —
decomposing narration into scenes, assigning estimated durations, and
carrying forward claim references — so that Voice, Visual Planner, and
future asset/assembly tooling have machine-readable input instead of
prose to reinterpret. It does not generate audio, images, or video
itself.

## Preconditions

The Producer may only create or update a `PRODUCTION.md` for a content
item whose `CONTENT_ITEM.md` `status` is `APPROVED`. This is deliberately
the strictest gate available — not merely "automated review passed"
(`FACT_CHECK`/`SAFETY_REVIEW`/`ORIGINALITY_REVIEW` all `PASS`, which
`APPROVED` already presupposes) but the full human sign-off. Running
against anything earlier is a contract violation, not a judgment call the
Producer gets to make.

## Inputs

- `CONTENT_ITEM.md` (status, pillar — read-only)
- `SCRIPT.md` (hook, premise, narrative beats, conclusion — read-only,
  the source of truth for narration text and claim references)
- `claims/*.md` (`Classification` only, to carry forward into scenes —
  read-only)

## Outputs

- `PRODUCTION.md` (new, or updated if re-run against a changed script —
  see "Re-running")
- `scenes/scene-<n>.md`, one per scene

## Allowed actions

- Read `CONTENT_ITEM.md`, `SCRIPT.md`, `claims/*.md`
- Create/update `PRODUCTION.md`'s own fields (Identity, Production
  status, Scene list rollup, Linked records, Notes/history log) and the
  rollup sections it owns (Visual requirements rollup, Music/audio
  rollup, Transitions rollup, Asset references rollup) — not the
  sections owned by later stages (Voiceover information beyond linking
  to a not-yet-created voice record, Captions, Thumbnail, Title/
  description, Production QA state, Human review state all start
  `NOT_STARTED` and are never populated by the Producer)
- Create `scenes/scene-<n>.md` files: Scene ID, Order, Duration
  (estimated), Narration (verbatim from `SCRIPT.md`), Visual type/
  description (a first-pass proposal — Visual Planner's job to finalize),
  Source/claim references, all statuses set to `NOT_STARTED`

## Forbidden actions

The Producer must **never**:

- Change a factual claim, its classification, or any `research/*.md`
  evidence — it only *references* claim IDs, verbatim, never edits them
- Change a `FACT_CHECK`/`SAFETY_REVIEW`/`ORIGINALITY_REVIEW` result, or
  any `REVIEW.md` file
- Bypass or shortcut human approval — see "Preconditions"; there is no
  emergency path around the `APPROVED` gate
- Publish anything, anywhere, under any condition
- Write to `CONTENT_ITEM.md` at all (not even `Production state`/`QA
  state` — those remain a human/editorial update once real production
  work, tracked entirely in `PRODUCTION.md`, is complete)
- Invent narration text not present in `SCRIPT.md`, or paraphrase it —
  scene narration must be verbatim
- Assign a final `Visual type`/asset — that's `agents/visual-planner/`'s
  job; the Producer's visual fields are an initial proposal only, always
  subject to revision downstream

## Re-running

If `SCRIPT.md` changes after `PRODUCTION.md` was created (detectable via
`Script content hash` mismatch, the same pattern the three review agents
use for `PASS` staleness), the existing production plan is stale. The
Producer does not silently patch it — it creates a new `Production ID`
(incrementing the suffix) and a fresh scene set, leaving the prior
`PRODUCTION.md`/`scenes/` in place as a historical record, mirroring
`templates/CLAIM.md`'s immutable-claim/supersession convention rather
than in-place editing.

## Handoff

On completion, `Production status` is `PRODUCTION_PLANNING` (the
Producer's own output state — it does not advance further; `VOICE` is
`agents/voice/`'s stage to start, not the Producer's to trigger). The
Producer does not touch `status` on `CONTENT_ITEM.md` in either
direction.
