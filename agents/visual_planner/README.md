# Visual Planner

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7B MVP — `src/`/`tests/`
exist and are stdlib-only, matching the shape of the other agents in this
repo.

## Responsibility

Finalizes each scene's visual requirement and specifies the corresponding
`templates/ASSET.md` record — what's needed, generated vs. retrieved, and
(the critical part) whether it will be `AUTHENTIC_HISTORICAL_MEDIA` or
`GENERATED_RECONSTRUCTION`. Never generates or retrieves the asset itself,
never presents generated media as authentic, never invents historical
evidence beyond what the content item's claims establish.

## The Visual Safety Rule

Deterministic, driven only by the `Classification` of a scene's
referenced claims (`classification.py`) — no NLP, no creativity:

| Scene's claim references | `Visual type` | `Historical authenticity classification` |
|---|---|---|
| none (e.g. a modern infographic/framing scene) | `ON_SCREEN_TEXT_GRAPHIC` | `NOT_APPLICABLE` |
| all `FACT` | `ARCHIVAL_IMAGE` | `AUTHENTIC_HISTORICAL_MEDIA` (**sourcing intent only** — `Verification status` stays `NOT_STARTED` until a specific, provenanced item is confirmed) |
| any `ASSUMPTION`/`INFERENCE`/`SPECULATION` | `GENERATED_RECONSTRUCTION` | `GENERATED_RECONSTRUCTION` (unconditional — a "what if"/hypothetical scene can never be classified as authentic) |

A scene referencing a claim with no corresponding `claims/*.md` file
blocks the whole run with a "missing provenance" reason rather than
guessing at a classification.

## Write boundary

`mutate.py`'s hard-coded whitelist: a scene's `Visual type`/`Visual
description`/`Asset requirement` fields only (never `Narration text`,
`Caption text`, `Source/claim references`, or any status field); new
`assets/asset-<n>.md` files; and `PRODUCTION.md`'s `Visual requirements
(rollup)`/`Asset references (rollup)` sections plus `Production status`
(advanced to `ASSET_COLLECTION` once every scene is planned). No generic
"write anything" helper.

## Preconditions (and a defense-in-depth beyond the literal contract)

Requires `PRODUCTION.md`'s `Production status` to be `VISUAL_PLANNING`
or, as an explicitly-labeled Phase 7B interim allowance (no
`agents/voice/` implementation exists yet), `PRODUCTION_PLANNING`. It also
re-verifies `SCRIPT.md`'s content hash against `PRODUCTION.md`'s stored
`Script content hash` (reusing `agents/producer/src/hashing.py` directly)
and blocks if they've diverged — a stale production plan is never
silently planned against.

Because the interim allowance means `Production status` alone can't
distinguish a real, approved production from a hand-built schema
fixture, this agent **also** requires `CONTENT_ITEM.md`'s own `status` to
be `APPROVED` whenever that file is present — closing the exact gap that
would otherwise let `--apply` run against the Phase 7A golden
`PRODUCTION.md` fixture (whose `CONTENT_ITEM.md` status is `SCRIPT`, never
`APPROVED`). See CONTRACT.md's Preconditions.

## Relationship to other agents

Reuses `agents/researcher/src`'s generic infrastructure (`parsing`,
`loader.load_claims`/`load_content_item`) and
`agents/producer/src.hashing.compute_script_content_hash` directly —
never duplicates either. Runs after `agents/producer/` (which produces
the scenes this agent reads) and, in the full sequence,
`agents/voice/` (`Production status = VISUAL_PLANNING`); hands off to the
still-unbuilt `ASSET_COLLECTION` stage — see `templates/PRODUCTION.md`'s
`Production status` sequence.

## Running it

```
python3 -m agents.visual_planner.src <content-item-dir> [--apply]
```

Prints a JSON result (`aborted`/`blocked`/`planned`, one plan summary per
scene). Without `--apply`, nothing on disk changes.

```
python3 -m unittest discover -s agents/visual_planner/tests -t .
```

## Known limitations

- **Asset requirement is one asset per scene**, keyed to the scene's
  order number (`asset-<scene-order>.md`) — a scene needing multiple
  distinct assets isn't modeled yet.
- **No real sourcing/generation happens here** — `assets/asset-<n>.md`
  records specify a requirement, they don't fulfill it. That's later,
  unbuilt tooling (asset collection).
