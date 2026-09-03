# Timeline Template

One copy per assembly attempt, store under
`content/<pillar>/<content-id>/timeline/timeline-<n>.md`. Produced by
`agents/assembler/` from `templates/SCENE.md`/`VOICE.md`/`ASSET.md`
records — the deterministic, reproducible schedule a renderer assembles
into this record's own `Output` section. See `agents/assembler/CONTRACT.md`.

| Field | Value |
|---|---|
| Timeline ID | `<content-id>-timeline-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Production ID | `<matches PRODUCTION.md>` |
| Assembly content hash | `<sha256 of every input this timeline depends on — script, production, voice, and every asset's content hash — see agents/assembler/CONTRACT.md's "Hash / dependency model">` |
| Total duration | `<sum of every scene's duration>` |

## Scene timeline

| Scene ID | Start | End | Duration | Narration/audio reference | Visual asset reference | Captions reference | Transition | Claim references |
|---|---|---|---|---|---|---|---|---|
| `<scene-01>` | `0s` | `<Ns>` | `<Ns>` | `<voice/voice-<n>.md>` | `<assets/asset-<n>.md, or "N/A">` | `<captions/captions-<n>.md, scene section>` | `<in>` / `<out>` | `<claim IDs, or "N/A">` |

**Scenes never overlap:** each row's `Start` equals the previous row's
`End`. `Total duration` above equals the sum of every row's `Duration`
(rounding tolerance: whole seconds, per `agents/producer/`'s existing
duration model).

## Output

| Field | Value |
|---|---|
| Renderer | `<provider label>` |
| Video reference | `<path once rendered, or "not yet produced">` |
| Format | `<file extension / container, or "N/A">` |
| Output hash | `<sha256 of the output artifact, or "N/A">` |
| Playable | `YES` \| `NO` \| `UNVERIFIED` — never `YES` unless independently confirmed by the renderer that produced it |

## Assembly status

`NOT_STARTED` \| `IN_PROGRESS` \| `ASSEMBLED` \| `REVISION_REQUIRED`

`<notes on what failed, if not ASSEMBLED>`
