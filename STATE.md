# Project State

Last updated: 2026-09-02

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7 — Production Stack Foundation — COMPLETE** (contracts only, no
implementation, per explicit instruction).

## Completed (Phase 7 foundation)

**Step 1 — Inspection:** reviewed `CONSTITUTION.md`, `SYSTEM.md`,
`STATE.md`, all of `templates/`, `agents/`, the golden sample, and the
Phase 5/6 review/orchestrator architecture before writing anything.
Identified what production needs from an approved script: verbatim
narration per beat, claim references (to keep production traceable back
to fact-checked content), and an explicit separation from both the
content-review lifecycle and any publishing authority.

**Step 2-5 — Templates** (`templates/`):
- `PRODUCTION.md` — the production record connecting an approved content
  item to its assets: identity/script-hash (staleness detection, same
  pattern as the three review agents' hashing), the
  `PRODUCTION_PLANNING → ... → READY_TO_PUBLISH` state machine, scene
  list, voiceover/visual/caption/music/transition/asset rollups,
  thumbnail, title/description, and its own Production QA + Human review
  gates (mirrors `templates/VIDEO_QA.md`'s existing final-approval
  pattern rather than duplicating it). Explicit "Separation from content
  lifecycle" section.
- `SCENE.md` — one scene = one record: narration (verbatim, never
  paraphrased), visual type/description, asset requirement, caption,
  music, transition, claim references, generation and QA status. "The
  video is described as data" stated as the design goal up front.
- `ASSET.md` — provenance-first: `Generated vs. retrieved`,
  `Licensing/provenance status` (never defaults to "safe"), and a
  required-when-applicable `Historical authenticity classification`
  (`AUTHENTIC_HISTORICAL_MEDIA` / `GENERATED_RECONSTRUCTION` /
  `NOT_APPLICABLE`) with no default value — generated imagery can never
  be silently presented as real historical footage.
- `VOICE.md` — provider-agnostic; `Provider`/`Voice configuration` are
  opaque free-text fields, no vendor named anywhere.

**Step 6 — Production agent contracts** (`agents/producer/`,
`agents/voice/`, `agents/visual-planner/` — `CONTRACT.md` + `README.md`
each, **no `src/`, not implemented**):
- Producer: script → `PRODUCTION.md` + scenes. Gated on content
  `status = APPROVED` (the strictest available gate, not merely
  automated-review-passed). Never writes to `CONTENT_ITEM.md`, never
  touches claims/reviews, never bypasses approval, never publishes.
- Voice: narration → voiceover, provider-agnostic. Never alters narration
  meaning or inserts unsupported claims.
- Visual Planner: scenes → finalized visual requirement + `ASSET.md`
  records. Never presents generated media as authentic, never invents
  historical evidence beyond what claims establish, never clears
  provenance itself (that's downstream work).

**Step 7-8 — State machine + human gate:** defined in `PRODUCTION.md`
exactly as specified (`PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING →
ASSET_COLLECTION → ASSEMBLY → CAPTIONS → THUMBNAIL → METADATA →
PRODUCTION_QA → HUMAN_REVIEW → APPROVED → READY_TO_PUBLISH`).
`READY_TO_PUBLISH` is the explicit ceiling — no template or contract this
phase grants publishing authority to anything.

**Step 9 — Golden production fixture** (additive only —
`content/what-if/wi-20260902-black-death-modern-medicine/`):
`PRODUCTION.md`, `scenes/scene-01.md`–`scene-04.md` (4 scenes, 46s,
condensed from `SCRIPT.md`'s 6 beats), `assets/asset-01.md`–`asset-03.md`
(2 `GENERATED_RECONSTRUCTION`, 1 intended `AUTHENTIC_HISTORICAL_MEDIA`),
`voice/voice-01.md`, and `PRODUCTION_AUDIT.md` (the validation report).
Zero existing golden-sample files modified — confirmed via `git status`.

**Step 10 — Documentation:** `SYSTEM.md` (directory structure, new
"Production layer" section, agent contracts list, out-of-scope list),
`README.md` (root), `agents/README.md` (production agents +
"The production lifecycle" section), `STATE.md` (this file).

## Validation performed (Step 9 checklist + Final Validation)

1. Every production field has a clear purpose — confirmed while building
   the fixture; none unused. See `PRODUCTION_AUDIT.md`.
2. Scene records can represent a complete video — 4 ordered, timed scenes
   with narration/visual/caption/music/transition cover all of
   `SCRIPT.md`'s content.
3. Scene records can reference claims — all 11 active claims (`c1`-`c4`,
   `c6`-`c12`; `c5` correctly excluded as superseded, matching
   `SCRIPT.md`'s own Verified claims table) are covered across the 4
   scenes.
4. Assets have provenance — all three fixture assets have honest,
   unresolved (`UNVERIFIED`/`not yet sourced`) provenance fields; none
   defaults to a reassuring value it hasn't earned.
5. Generated historical imagery cannot be confused with authentic media
   — demonstrated directly: 2 assets `GENERATED_RECONSTRUCTION` (each
   with a stated "why"), 1 intended `AUTHENTIC_HISTORICAL_MEDIA` with its
   `Basis for classification` field explicitly flagging that this is
   intent, not a verified claim yet.
6. Voice provider is abstracted — `voice-01.md`'s `Provider`/`Voice
   configuration` are `TBD`, no vendor named anywhere in template or
   fixture.
7. Production is separate from content status — `PRODUCTION.md`'s
   "Separation from content lifecycle" section states it; confirmed in
   practice, `CONTENT_ITEM.md` untouched.
8. Human approval remains mandatory — `PRODUCTION.md`'s Human review
   state is `NOT_STARTED` with an explicit note that `READY_TO_PUBLISH`
   requires human `APPROVED`, mirroring `templates/VIDEO_QA.md`.
9. No publishing capability exists — confirmed via grep across every new
   template and contract; all "publish" mentions are explicit
   prohibitions or the `READY_TO_PUBLISH` state name.
10. Existing 131 tests still pass — 43 (Researcher) + 27 (Safety) + 31
    (Originality) + 30 (Orchestrator), 0 regressions, re-run after every
    new file was added.
11. Existing golden sample remains untouched — `git status --short`
    shows only new (`??`) files under the golden sample's directory,
    zero modified (`M`) files.
12. No existing reviewer contracts weakened — no edits to
    `agents/researcher/`, `agents/safety/`, `agents/originality/`,
    `agents/orchestrator/`, or any of their templates this phase.

## Genuine finding

Building the fixture surfaced that `SCRIPT.md` (explicitly "a
representative structure... not a polished script") contains beat-level
*descriptions* rather than verbatim spoken narration for most beats —
only the Hook is true spoken-form text. `templates/SCENE.md`'s
requirement that narration be verbatim is correct; this is a real gap in
this particular script's current polish, not a template defect, and is
documented in full in `PRODUCTION_AUDIT.md` rather than silently worked
around (each scene quotes `SCRIPT.md`'s actual text and flags that it
isn't final spoken narration yet).

## Known limitations

- No production agent is implemented — `producer/`, `voice/`,
  `visual-planner/` are contracts only, exactly as instructed.
- The golden fixture cannot progress past `PRODUCTION_PLANNING` for two
  honest reasons: no agent exists yet to do the later work, and this
  content item has not actually reached `status = APPROVED` (Researcher's
  own findings show `c1` `DISPUTED`/`c11` `UNRESOLVED` — see
  `PRODUCTION_AUDIT.md`'s "Honesty check").
- `SCRIPT.md` needs a full verbatim-narration pass before a real Producer
  run would produce final (not draft-quality) scene narration — see
  "Genuine finding" above.
- No media generation, TTS, image/video generation, stock-media
  crawling, FFmpeg/assembly, or YouTube integration exists — none was
  built, per explicit instruction.

## Next task

**Phase 7 Implementation** (per the roadmap): build the Producer +
Visual Planner MVP against `agents/producer/CONTRACT.md` and
`agents/visual-planner/CONTRACT.md`, and create the first
machine-readable production plan from the golden sample — following the
same architecture pattern as the three review agents (stdlib only, dry
run by default, whitelisted field writes, immutable/sequential records).
Not full video rendering yet. Given this content item hasn't reached
`APPROVED`, the first real Producer run will need either a different,
genuinely-approved test fixture or an explicit test-only bypass of the
`APPROVED` precondition clearly marked as such — a decision worth
surfacing to the human owner rather than assumed.
