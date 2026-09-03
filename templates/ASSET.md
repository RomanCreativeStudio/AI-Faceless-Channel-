# Asset Template

One copy per production asset (image, video clip, audio, music, graphic),
store under `content/<pillar>/<content-id>/assets/asset-<n>.md`.
Referenced by `templates/SCENE.md`'s "Asset requirement" field and rolled
up in `templates/PRODUCTION.md`.

**An asset existing is never evidence it is safe to use.** Every field
below must be filled honestly at the asset's current state — `NOT_STARTED`/
`UNVERIFIED` are valid, expected values before real work has happened, and
are not weaker than filling in a guess. Never mark `Verification status`
or `Licensing/provenance status` as cleared just to unblock a scene.

| Field | Value |
|---|---|
| Asset ID | `<content-id>-asset-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Asset type | `<IMAGE \| VIDEO_CLIP \| AUDIO \| MUSIC \| GRAPHIC>` |
| Intended scene | `<scenes/scene-<n>.md path(s) that use this asset>` |
| Scene/visual content hash | `<sha256 of the scene's narration + claim references + visual type/description at generation time — same staleness-detection pattern as templates/PRODUCTION.md/REVIEW.md/VOICE.md; added Phase 7C-2, see agents/assets/CONTRACT.md's "Schema changes" note. "N/A" until an asset agent has actually run>` |

## Provenance

| Field | Value |
|---|---|
| Generated vs. retrieved | `GENERATED` \| `RETRIEVED` \| `HUMAN_PROVIDED` — the third value added Phase 7C-2 for a human-supplied asset; see agents/assets/CONTRACT.md |
| Source | `<where this came from: archive name, stock library, generation tool, or the human provider's own description — "TBD" if not yet sourced. Never a fabricated URL or invented organization name.>` |
| Source URL / reference | `<url, archive ID, or "N/A">` |
| Generation prompt/reference | `<the exact prompt/parameters used, if GENERATED — "N/A" if RETRIEVED or HUMAN_PROVIDED>` |

## Historical authenticity classification

**Required whenever this asset depicts, or could be read as depicting, a
real historical event, person, place, or artifact.** Use `NOT_APPLICABLE`
only for non-representational assets (on-screen text graphics, generic
diagrams, music). No default — pick explicitly:

- `AUTHENTIC_HISTORICAL_MEDIA` — a real historical artifact/document/
  image/recording, or a direct, unaltered reproduction of one.
- `GENERATED_RECONSTRUCTION` — AI-generated, illustrated, or otherwise
  synthesized imagery depicting a historical (or hypothetical/`what-if`)
  scene, even if based on real research. **Must never be presented in the
  video as if it were `AUTHENTIC_HISTORICAL_MEDIA`** — see
  `agents/safety/CONTRACT.md`'s `SYNTHETIC_MEDIA`/`DECEPTION` signals,
  which this classification feeds.
- `NOT_APPLICABLE` — not a representational depiction (text graphic,
  abstract diagram, music, generic B-roll with no historical claim).

| Field | Value |
|---|---|
| Classification | `AUTHENTIC_HISTORICAL_MEDIA` \| `GENERATED_RECONSTRUCTION` \| `NOT_APPLICABLE` |
| Basis for classification | `<why — e.g. "period woodcut, public domain archive" or "AI-generated illustration, no real photographic/documentary source exists">` |

## Licensing / copyright

| Field | Value |
|---|---|
| Licensing/provenance status | `UNVERIFIED` \| `PUBLIC_DOMAIN` \| `LICENSED` \| `RIGHTS_UNCLEAR` \| `DO_NOT_USE` |
| Copyright/provenance notes | `<license terms, attribution requirements, why status was set — "not yet checked" is honest and acceptable pre-verification>` |

## Technical

| Field | Value |
|---|---|
| Dimensions / aspect ratio | `<e.g. 1920x1080, 16:9 — "N/A" for audio> ` |
| File reference | `<path once generated/retrieved — "not yet produced" until then>` |

## Generation/retrieval status

Added Phase 7C-2 (`agents/assets/CONTRACT.md`) — mirrors
`templates/SCENE.md`'s field of the same name, extended with
`HUMAN_PROVIDED`:

`NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `RETRIEVED` \|
`HUMAN_PROVIDED` \| `REVISION_REQUIRED`

**`RETRIEVED` may only be used once a real retrieval has actually
happened** — a placeholder/not-yet-implemented retrieval strategy stays
`NOT_STARTED`, never `RETRIEVED`, so this field can never falsely claim
an asset was sourced when it wasn't.

## Verification status

`NOT_STARTED` \| `IN_PROGRESS` \| `VERIFIED` \| `DISPUTED` \|
`REVIEW_REQUIRED` — the last value added Phase 7C-2: a human must confirm
this specific asset (e.g. a `HUMAN_PROVIDED` asset with no stated source)
before it may be used; distinct from `DISPUTED` (an active
authenticity/licensing conflict) and `NOT_STARTED` (nothing checked yet).

`<what was checked, by whom/what, and when — "not yet verified" is the honest default>`
