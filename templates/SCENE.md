# Scene Template

One copy per scene, store under
`content/<pillar>/<content-id>/scenes/scene-<n>.md`. A production's scene
list (`templates/PRODUCTION.md`) is an ordered sequence of these.

**Design goal: the video is described as data.** A scene record must
contain everything a future renderer needs to turn it into seconds of
video — narration, timing, what's on screen, what it needs, and where it
came from — without inventing anything the record doesn't already state.

| Field | Value |
|---|---|
| Scene ID | `<content-id>-scene-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Order | `<n>` |
| Duration | `<seconds, e.g. "12s">` |

## Narration

| Field | Value |
|---|---|
| Script reference | `<SCRIPT.md section/beat this narration is drawn from>` |
| Narration text | `<the exact text to be spoken, verbatim — never paraphrased from the script by the renderer>` |

## Visual

| Field | Value |
|---|---|
| Visual type | `<e.g. HISTORICAL_MAP, ARCHIVAL_IMAGE, GENERATED_RECONSTRUCTION, ON_SCREEN_TEXT_GRAPHIC, B_ROLL, DIAGRAM>` |
| Visual description | `<what should be on screen, concretely enough to brief a generator or a stock search>` |
| Asset requirement | `<assets/asset-<n>.md path, or "N/A — produced directly at assembly, no discrete asset record">` |

## Caption text

`<on-screen caption/subtitle text for this scene — derived from Narration text, never independently authored>`

## Music / audio requirement

`<mood, cue, or "continues previous scene's track">`

## Transition

| Field | Value |
|---|---|
| In | `<e.g. cut, fade, match-cut — or "N/A" for scene 1>` |
| Out | `<e.g. cut, fade — or "N/A" for the last scene>` |

## Source / claim references

`<claim IDs (templates/CLAIM.md) this scene's narration/visual depends on, if any — "N/A" for a purely transitional or framing scene>`

## Generation/retrieval status

`NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `RETRIEVED` \| `REVISION_REQUIRED`

## QA status

`NOT_STARTED` \| `IN_PROGRESS` \| `PASS` \| `REVISION_REQUIRED`

`<notes on what failed, if not PASS>`
