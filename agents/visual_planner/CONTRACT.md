# Contract: Visual Planner

Specification only — **not implemented this phase.** Governs determining
what visual/asset each scene requires — the step between a scene existing
and an asset being sourced or generated for it.

Subordinate to `CONSTITUTION.md` and to `templates/SCENE.md`/`ASSET.md`
(the schema it produces against). Where anything below conflicts with
those, they win.

## Purpose

For each scene in a production, finalize `Visual type` and `Visual
description` (the Producer's versions are a first-pass proposal only —
see `agents/producer/CONTRACT.md`), and create the corresponding
`templates/ASSET.md` record specifying exactly what's needed: generated
or retrieved, and — critically — whether it will depict something as
`AUTHENTIC_HISTORICAL_MEDIA` or `GENERATED_RECONSTRUCTION`. This agent
does **not** generate or retrieve the asset itself (no image-generation
integration, no stock-media crawler — that's later, unbuilt tooling); it
specifies the requirement precisely enough for that tooling to act on.

## Preconditions

Only runs against a `PRODUCTION.md` whose `Production status` is
`VISUAL_PLANNING` (reached after `agents/voice/` completes `VOICE` with
`QA status = PASS`) — **or, as an explicitly-labeled Phase 7B interim
allowance, `PRODUCTION_PLANNING`.** `agents/voice/` has no implementation
yet (Phase 7C), so requiring literal `VISUAL_PLANNING` would make this
agent permanently unrunnable until then. Running against
`PRODUCTION_PLANNING` is not a silent skip of the Voice stage — any
result produced this way must say plainly that Voice has not run. Once
`agents/voice/` exists and can advance `Production status` to
`VISUAL_PLANNING` itself, this interim allowance should be removed rather
than left as a permanent second entry point.

**Defense-in-depth, found during implementation:** `Production status`
alone can't distinguish a real, approved production from a hand-built
schema-validation fixture whose `PRODUCTION.md` happens to carry a
matching status/hash — exactly the situation of the Phase 7A golden
`PRODUCTION.md` fixture, whose `CONTENT_ITEM.md` status is `SCRIPT`,
never `APPROVED`. So when `CONTENT_ITEM.md` is present alongside
`PRODUCTION.md`, this agent also requires its `status` to be `APPROVED`
— mirroring `agents/producer/CONTRACT.md`'s own gate — rather than
relying on the interim allowance alone to keep `--apply` from ever
running against non-approved (including golden-sample) content.

## Inputs

- `PRODUCTION.md` (status — read-only)
- `scenes/scene-<n>.md` (all fields — read-only except as listed below)
- `claims/*.md` (`Classification`/`Exact claim`, for scenes with source/
  claim references — read-only)

## Outputs

- Updated `Visual type`/`Visual description`/`Asset requirement` fields
  on each `scenes/scene-<n>.md`
- New `assets/asset-<n>.md` per distinct asset need

## Allowed actions

- Read `PRODUCTION.md`, every scene, and the claims a scene references
- Update a scene's `Visual type`, `Visual description`, and `Asset
  requirement` fields only (not `Narration text`, `Caption text`,
  `Source/claim references`, or any status field it doesn't own)
- Create `assets/asset-<n>.md` files with every field
  `templates/ASSET.md` requires, including an explicit `Historical
  authenticity classification` for every representational asset — never
  left blank, never defaulted
- Update `PRODUCTION.md`'s `Visual requirements (rollup)` and `Asset
  references (rollup)` sections once real content exists for them.
  `agents/producer/CONTRACT.md` creates these sections as placeholders
  (nothing to roll up yet, since no visual planning has happened) — this
  agent is the one that actually populates them, which is a refinement of
  ownership found while implementing both agents, not a conflict: Producer
  creates the section, Visual Planner is the first agent with real content
  to put in it.
- Advance `PRODUCTION.md`'s `Production status` from `VISUAL_PLANNING` to
  `ASSET_COLLECTION` once every scene has a finalized visual plan

## Forbidden actions

The Visual Planner must **never**:

- Present generated media as authentic. Every asset depicting a
  historical (or hypothetical/`what-if`) event, person, or place must be
  classified `GENERATED_RECONSTRUCTION` unless it is a real, verifiable
  historical artifact/document/recording — in which case
  `AUTHENTIC_HISTORICAL_MEDIA` requires a stated basis (source archive,
  provenance), never just asserted.
- Invent historical evidence. A `Visual description` or generation
  prompt must not introduce specifics (a detail, a quote, an event) that
  isn't supported by the content item's `claims/*.md` — if a visual needs
  a fact the claims don't establish, that's a gap to flag, not fill in.
- Override asset provenance requirements. `Licensing/provenance status`
  and `Verification status` on `assets/asset-<n>.md` start `UNVERIFIED`/
  `NOT_STARTED` and this agent does not clear them — verifying and
  clearing provenance is downstream work (asset collection/QA), not
  planning.
- Publish anything, anywhere, under any condition.
- Modify `SCRIPT.md`, `claims/*.md`, `voice/voice-<n>.md`, or any field
  on a scene/asset outside what's listed in "Allowed actions."

## Handoff

On completion, every scene in the production has a finalized `Visual
type`/`Visual description`/`Asset requirement`, every needed asset has an
`assets/asset-<n>.md` record (still `NOT_STARTED` on generation/
retrieval/verification — this agent specifies, it doesn't produce), and
`Production status` advances to `ASSET_COLLECTION` — the next, still
unbuilt stage where assets actually get generated or retrieved.
