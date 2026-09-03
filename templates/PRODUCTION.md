# Production Template

The master production record for one approved content item — the
production-side counterpart to `templates/CONTENT_ITEM.md`. One copy per
content item, store under `content/<pillar>/<content-id>/PRODUCTION.md`.

**Production is a separate lifecycle from content review.** This record
only exists to connect an *already-approved* script to its production
assets. It never substitutes for, overrides, or shortcuts
`CONTENT_ITEM.md`'s own `status`/stage-state fields — see "Separation
from content lifecycle" below.

## Identity

| Field | Value |
|---|---|
| Content ID | `<matches CONTENT_ITEM.md>` |
| Production ID | `<content-id>-prod-01` (increment the suffix if a production is redone from scratch) |
| Script version | `<SCRIPT.md path this production is built from>` |
| Script content hash | `<sha256 of SCRIPT.md at the time this production plan was created>` |
| Production status | see "Production status" below |
| Total target duration | `<sum of scene durations, e.g. "46s">` |

## Production status

Must be exactly one of, in this order:

```
PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING → ASSET_COLLECTION →
ASSEMBLY → CAPTIONS → THUMBNAIL → METADATA → PRODUCTION_QA →
HUMAN_REVIEW → APPROVED → READY_TO_PUBLISH
```

`READY_TO_PUBLISH` is the last state this record or any production agent
may ever set. Nothing in `templates/PRODUCTION.md`, `SCENE.md`,
`ASSET.md`, or `VOICE.md`, and no agent under `agents/producer/`,
`agents/voice/`, or `agents/visual_planner/`, may publish, or move a
content item to `PUBLISHED` — that remains outside this entire phase, per
`CONSTITUTION.md` rule 2. Publishing off the back of `READY_TO_PUBLISH`
is a separate, human-driven action with its own (not yet built) system.

## Separation from content lifecycle

`CONTENT_ITEM.md`'s `status` and stage states (`Fact-check state`,
`Safety state`, `Originality state`, `Production state`, `QA state`, ...)
are the content-review lifecycle and are owned exclusively by the
agents/humans already documented for them (`agents/researcher/`,
`agents/safety/`, `agents/originality/`, human editorial/QA review). This
file's `Production status` above is a *different*, more granular
lifecycle that only starts once a script is approved. No production
agent may write to `CONTENT_ITEM.md` at all — not even the coarse
`Production state`/`QA state` fields there, which remain a human/
editorial update once real production work (tracked here) is complete.

## Linked records

- Script: `<SCRIPT.md path>`
- Scenes: `templates/SCENE.md` copies, one per scene — `scenes/scene-<n>.md`
- Assets: `templates/ASSET.md` copies, referenced by scenes — `assets/asset-<n>.md`
- Voiceover: `templates/VOICE.md` copies — `voice/voice-<n>.md`
- Final QA/publication gate: `templates/VIDEO_QA.md` (unchanged by this
  phase — `PRODUCTION_QA` here feeds into it, it doesn't replace it)

## Scene list

| Scene ID | Duration | Visual type | Claims referenced | Status |
|---|---|---|---|---|
| `<scene-01>` | `<Ns>` | `<visual type>` | `<claim IDs, if any>` | `<generation/retrieval + QA status>` |

## Voiceover information

| Field | Value |
|---|---|
| Voice record | `<voice/voice-<n>.md path>` |
| Narration source | `<SCRIPT.md section(s) the narration is drawn from>` |
| Generation status | `NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `REVISION_REQUIRED` |

## Visual requirements (rollup)

`<one line per distinct visual need across all scenes, or "see scenes/ for detail">`

## Captions

| Field | Value |
|---|---|
| Source | `<derived from narration text — never a separate hand-written script>` |
| Status | `NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `QA_PASS` \| `QA_FAIL` |

## Music / audio

`<mood/cues rollup, or "see scenes/ for per-scene detail"; licensing status is tracked per-asset in ASSET.md, never assumed here>`

## Transitions

`<rollup of transition style between scenes, if consistent; otherwise "see scenes/">`

## Asset references (rollup)

`<list of assets/asset-<n>.md files this production uses>`

## Assembly / Output

Added Phase 7D (`agents/assembler/CONTRACT.md`) — this section didn't
exist before there was an agent to populate it; documented here rather
than left implicit, mirroring every other rollup section's shape.

| Field | Value |
|---|---|
| Timeline reference | `<timeline/timeline-<n>.md path, or "not yet produced">` |
| Video output reference | `<output/video-<n>.<ext> path, or "not yet produced">` |
| Assembly status | `NOT_STARTED` \| `IN_PROGRESS` \| `ASSEMBLED` \| `REVISION_REQUIRED` |

## Thumbnail

| Field | Value |
|---|---|
| Asset reference | `<assets/asset-<n>.md, or "not yet produced">` |
| Status | `NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `QA_PASS` \| `QA_FAIL` |

Thumbnail/title consistency is verified in `templates/VIDEO_QA.md`, not
re-defined here.

## Title / description

| Field | Value |
|---|---|
| Working title | `<may match CONTENT_ITEM.md's Working title, or be a production-optimized variant>` |
| Description | `<platform video description text>` |

Final title/thumbnail deception checks are `agents/safety/`'s job
(`TITLE_THUMBNAIL_MISREPRESENTATION`) and `templates/VIDEO_QA.md`'s job
downstream — this section only records the current draft.

## Production QA state

| Field | Value |
|---|---|
| State | `NOT_STARTED` \| `IN_PROGRESS` \| `PASS` \| `REVISION_REQUIRED` |
| Notes | `<summary; full checklist lives in templates/VIDEO_QA.md once production is complete>` |

## Human review state

| Field | Value |
|---|---|
| State | `NOT_STARTED` \| `IN_PROGRESS` \| `APPROVED` \| `REVISION_REQUIRED` |
| Reviewer | `<human name/handle — never an agent>` |
| Notes | `<...>` |

No production may reach `READY_TO_PUBLISH` without a human `APPROVED`
here, mirroring `templates/VIDEO_QA.md`'s existing final-approval gate
(`CONSTITUTION.md` rules 1-2).

## Notes / history log

`<append-only log of major decisions, revisions, and state transitions>`
