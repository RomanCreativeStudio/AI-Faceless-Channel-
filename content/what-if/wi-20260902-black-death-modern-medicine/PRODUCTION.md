# Production: What If Modern Medicine Existed During the Black Death?

Golden fixture per `templates/PRODUCTION.md`. **Schema validation
exercise, not a real production.** See `PRODUCTION_AUDIT.md` in this
folder for why, and for the validation findings.

## Identity

| Field | Value |
|---|---|
| Content ID | `wi-20260902-black-death-modern-medicine` |
| Production ID | `wi-20260902-black-death-modern-medicine-prod-01` |
| Script version | `SCRIPT.md` |
| Script content hash | `ae2b03dcb7f626253f3b883f94935919805ea6f0cdd64dc2c3239543966f9c3c` |
| Production status | `PRODUCTION_PLANNING` |
| Total target duration | `46s` |

## Production status

Current: `PRODUCTION_PLANNING`. Per `PRODUCTION_AUDIT.md`, this fixture
stops here deliberately — it does not progress through `VOICE`,
`VISUAL_PLANNING`, or beyond, since no agent exists yet to do that work
for real, and this content item has not actually reached `APPROVED`.

## Separation from content lifecycle

`CONTENT_ITEM.md`'s `status` for this item is `SCRIPT` (unchanged by this
fixture — see `PRODUCTION_AUDIT.md`). This file exists purely to validate
`templates/PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md` against real
content; it does not assert or require that the content item has been
approved.

## Linked records

- Script: `SCRIPT.md`
- Scenes: `scenes/scene-01.md`, `scene-02.md`, `scene-03.md`, `scene-04.md`
- Assets: `assets/asset-01.md`, `asset-02.md`, `asset-03.md`
- Voiceover: `voice/voice-01.md`
- Final QA/publication gate: `templates/VIDEO_QA.md` (not started — no
  production has actually happened)

## Scene list

| Scene ID | Duration | Visual type | Claims referenced | Status |
|---|---|---|---|---|
| `scene-01` | `12s` | `GENERATED_RECONSTRUCTION` (infographic map) | `c1` | `NOT_STARTED` |
| `scene-02` | `10s` | `ARCHIVAL_IMAGE` | `c2` | `NOT_STARTED` |
| `scene-03` | `14s` | `GENERATED_RECONSTRUCTION` | `c4`, `c12`, `c3`, `c10`, `c11`, `c6` | `NOT_STARTED` |
| `scene-04` | `10s` | `ON_SCREEN_TEXT_GRAPHIC` | `c7`, `c8`, `c9` | `NOT_STARTED` |

## Voiceover information

| Field | Value |
|---|---|
| Voice record | `voice/voice-01.md` |
| Narration source | `SCRIPT.md` Hook + Narrative beats 1-6 (Conclusion excluded from this 4-scene condensation — see `PRODUCTION_AUDIT.md`) |
| Generation status | `NOT_STARTED` |

## Visual requirements (rollup)

One infographic-style map of plague spread (scene 1); one genuine
period/archival image of plague-era medicine or mortality (scene 2, not
yet sourced); one illustrative "what if" reconstruction of the
hypothetical scenario (scene 3); one text-graphic callout for the
uncertainty framing (scene 4, no photographic asset needed).

## Captions

| Field | Value |
|---|---|
| Source | Derived from each scene's Narration text |
| Status | `NOT_STARTED` |

## Music / audio

Somber/restrained under scenes 1-2 and 3's back half; neutral/curious
under scene 3's front half and scene 4 — matches `SCRIPT.md`'s Music/SFX
requirements section. No specific third-party track identified; licensing
status to be set on any music asset once one exists.

## Transitions

Cut between all scenes; no fades or match-cuts specified — see individual
`scenes/scene-<n>.md` files.

## Asset references (rollup)

`assets/asset-01.md` (scene 1), `assets/asset-02.md` (scene 2),
`assets/asset-03.md` (scene 3). Scene 4 uses no discrete asset record
(text graphic, produced at assembly).

## Thumbnail

| Field | Value |
|---|---|
| Asset reference | not yet produced |
| Status | `NOT_STARTED` |

## Title / description

| Field | Value |
|---|---|
| Working title | "What If Modern Medicine Existed During the Black Death?" (matches `CONTENT_ITEM.md`) |
| Description | Not yet drafted. |

## Production QA state

| Field | Value |
|---|---|
| State | `NOT_STARTED` |
| Notes | No production work has happened; nothing to QA yet. |

## Human review state

| Field | Value |
|---|---|
| State | `NOT_STARTED` |
| Reviewer | N/A |
| Notes | N/A |

## Notes / history log

- 2026-09-02 — Created as the Phase 7 golden production fixture, built
  from the existing Black Death What If? golden sample
  (`CONTENT_ITEM.md`, `SCRIPT.md`, `claims/`) to validate
  `templates/PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md` against
  real content before any production agent is implemented. See
  `PRODUCTION_AUDIT.md` for the validation report and why this fixture
  intentionally stops at `PRODUCTION_PLANNING`.
