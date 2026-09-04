# Thumbnail Template

One copy per thumbnail attempt, store under
`content/<pillar>/<content-id>/thumbnail/thumbnail-<n>.md`. Produced by
`agents/thumbnail/` — a **specification** for what a thumbnail should
show, not a generated image (no external image-generation integration
exists this phase). See `agents/thumbnail/CONTRACT.md`.

**Must never imply something happened if the content is hypothetical.**
See `agents/thumbnail/CONTRACT.md`'s "Fact / What If? framing" for the
deterministic rule that keeps a `what-if` premise's thumbnail concept
hedged (e.g. "Could modern medicine have stopped it?") rather than
assertive (e.g. "It was stopped!").

| Field | Value |
|---|---|
| Thumbnail ID | `<content-id>-thumbnail-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Production ID | `<matches PRODUCTION.md>` |
| Thumbnail content hash | `<sha256 of the inputs this spec is built from — see agents/thumbnail/CONTRACT.md>` |

## Concept

| Field | Value |
|---|---|
| Title concept | `<on-thumbnail text concept — hedged if the content pillar is what-if>` |
| Visual concept | `<what should be depicted, concretely enough to brief a generator>` |
| Text overlay | `<exact on-image text, if any — "N/A" if none>` |
| Focal subject | `<the single subject the eye should land on>` |
| Composition | `<layout notes>` |

## Claim / theme relationship

`<which claim(s)/theme this thumbnail represents, and why>`

## Authenticity considerations

`<whether the visual concept depicts something real (must reflect
AUTHENTIC_HISTORICAL_MEDIA) or hypothetical/generated (must reflect
GENERATED_RECONSTRUCTION) — never blurred; mirrors templates/ASSET.md's
Historical authenticity classification>`

## Generation strategy

`<provider used, and an explicit note that output is a placeholder
specification, not a real generated image>`

## Rendered image

Added Phase 8 — optional, additive: a thumbnail *specification* remains
this agent's primary output (see above), but a real, deterministically-
rendered illustration may also exist. `NOT_RENDERED` for a spec-only run
(this template's original, pre-Phase-8 behavior — nothing here changes
for that case).

| Field | Value |
|---|---|
| Reference | `<file path once rendered, or "NOT_RENDERED">` |

## Thumbnail status

`NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `REVISION_REQUIRED`
