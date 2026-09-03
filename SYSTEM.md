# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**Phase 6 complete (automated review layer); Phase 7D complete (Video
Assembly + Captions + Thumbnail + Production QA).** Twelve agents have
working, tested implementations, stdlib Python, no dependencies: the
Research / Fact-Check Agent (`agents/researcher/src/`, FACT_CHECK mode
only), the Safety Reviewer (`agents/safety/src/`, SAFETY_REVIEW only),
the Originality Reviewer (`agents/originality/src/`, ORIGINALITY_REVIEW
only), the Unified Automated Review Orchestrator
(`agents/orchestrator/src/`, which runs the three in order and
aggregates their results — it makes no safety/factual/originality
judgment of its own), the Producer (`agents/producer/src/`, turns an
`APPROVED` script into `PRODUCTION.md` + `scenes/*.md`, deterministically),
the Voice agent (`agents/voice/src/`, converts narration into a
voiceover-audio record via a provider-agnostic adapter — output always
labeled `TEST / PLACEHOLDER AUDIO`, never real speech), the Visual
Planner (`agents/visual_planner/src/`, finalizes each scene's visual
requirement with an explicit authenticity classification via the
deterministic Visual Safety Rule), the Assets agent
(`agents/assets/src/`, completes each scene's asset record with a
strategy — `GENERATED`/`RETRIEVED`/`HUMAN_PROVIDED` — honest provenance,
and a QA pass), the Assembler (`agents/assembler/src/`, combines scenes/
voice/assets into a deterministic `templates/TIMELINE.md` schedule and a
video artifact — a permanently-labeled placeholder manifest, since no
video-encoding tool exists in this environment), the Captions agent
(`agents/captions/src/`, deterministic narration segmentation into
`templates/CAPTIONS.md`, every caption a verbatim substring of its
source narration), the Thumbnail agent (`agents/thumbnail/src/`, a
thumbnail *specification* — never a generated image — that hedges a
`what-if` premise's title concept rather than asserting it as fact), and
Production QA (`agents/production_qa/src/`, an automated structural
readiness check across all of the above — `PASS`/`REVISION_REQUIRED`/
`BLOCKED`/`SYSTEM_ERROR` — that can advance `Production status` to
`HUMAN_REVIEW` at most, never further). None of these agents generates
or retrieves any *real* media, and none can publish, approve, or
schedule anything — see "Production layer" below. Everything else
remains documentation/templates only: no RESEARCH-mode live retrieval,
no editorial-review agent, no real TTS/image/video generation or
retrieval integration, no YouTube/publishing integration, no analytics,
no learning engine. Nothing outside the twelve agent directories above
executes.

## Directory structure

```
/
├── README.md            Project overview, entry point
├── SYSTEM.md             This file — architecture
├── CONSTITUTION.md        Non-negotiable governing rules
├── STATE.md               Living project status
├── templates/              Content-item schema (see below)
│   ├── CONTENT_ITEM.md
│   ├── RESEARCH.md
│   ├── CLAIM.md
│   ├── SCRIPT.md
│   ├── REVIEW.md
│   ├── VIDEO_QA.md
│   ├── PRODUCTION.md         Production record (Phase 7)
│   ├── SCENE.md               Per-scene record (Phase 7)
│   ├── ASSET.md                Per-asset record + provenance (Phase 7)
│   ├── VOICE.md                Voiceover record, provider-agnostic (Phase 7)
│   ├── TIMELINE.md             Assembly timeline + output record (Phase 7D)
│   ├── CAPTIONS.md             Caption chunks + timing (Phase 7D)
│   ├── THUMBNAIL.md            Thumbnail specification (Phase 7D)
│   └── PRODUCTION_QA.md        Structural readiness verdict (Phase 7D)
├── agents/                  Agent contracts + implementations
│   ├── researcher/            Research / Fact-Check Agent
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (FACT_CHECK mode only)
│   │   └── tests/                Unit + integration tests
│   ├── safety/                  Safety Reviewer
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (SAFETY_REVIEW only)
│   │   └── tests/                Unit + integration tests
│   ├── originality/            Originality Reviewer
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (ORIGINALITY_REVIEW only)
│   │   └── tests/                Unit + integration tests
│   ├── orchestrator/           Unified Automated Review Orchestrator
│   │   ├── CONTRACT.md           Design contract (coordination only)
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  Runs the three agents in order, aggregates results
│   │   └── tests/                Unit + integration tests
│   ├── producer/               Producer
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7B)
│   │   └── tests/                Unit + integration tests
│   ├── voice/                   Voice
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7C-1)
│   │   └── tests/                Unit + integration tests
│   ├── visual_planner/          Visual Planner
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7B)
│   │   └── tests/                Unit + integration tests
│   ├── assets/                  Assets
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7C-2)
│   │   └── tests/                Unit + integration tests
│   ├── assembler/               Assembler
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7D)
│   │   └── tests/                Unit + integration tests
│   ├── captions/                Captions
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7D)
│   │   └── tests/                Unit + integration tests
│   ├── thumbnail/               Thumbnail
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (Phase 7D)
│   │   └── tests/                Unit + integration tests
│   └── production_qa/           Production QA
│       ├── CONTRACT.md           Design contract
│       ├── README.md             How to run it, module map, limitations
│       ├── src/                  MVP implementation (Phase 7D)
│       └── tests/                Unit + integration tests
└── content/                Content pillar folders (structure only, no code)
    ├── business-stories/
    ├── history/
    ├── technology/
    └── what-if/
```

Each `content/<pillar>/` folder holds a `README.md` describing that pillar's
scope and conventions. Actual episode/content files, built from the
`templates/` schema, are added in a later phase, not this one.

## Content-item architecture

`templates/CONTENT_ITEM.md` is the master record for a single piece of
content and the contract between future agents: agents are intended to
consume and produce structured content items (and their linked
`RESEARCH.md` / `CLAIM.md` / `SCRIPT.md` / `REVIEW.md` / `VIDEO_QA.md`
records) rather than pass arbitrary text between one another. This applies
once agents exist — none are implemented yet.

Each content item tracks an overall pipeline `status` plus independent
per-stage states (research, script, fact-check, safety, originality,
production, QA, publication, analytics, learning) — see
`templates/CONTENT_ITEM.md` for the full field list and allowed values.

## Content pillars

| Pillar | Folder | Notes |
|---|---|---|
| Business Stories / Case Studies | `content/business-stories/` | Real companies/events, sourced |
| History | `content/history/` | Established historical fact, sourced |
| Technology | `content/technology/` | How things work / technical explainers |
| What If? | `content/what-if/` | Fact vs. hypothetical must be labeled (see CONSTITUTION.md rule 4) |

## Pipeline status

```
IDEA → RESEARCH → SCRIPT → FACT_CHECK → SAFETY_REVIEW →
ORIGINALITY_REVIEW → PRODUCTION → QA → HUMAN_REVIEW → APPROVED →
PUBLISHED → ANALYZING → LEARNING → ARCHIVED

REJECTED (may occur from any stage)
```

The `FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW` span is now the
**automated review layer**: `agents/orchestrator/` runs those three
stages via the existing agents and stops at the first one that doesn't
`PASS` — see `agents/orchestrator/CONTRACT.md`'s pipeline diagram. A
clean run of all three reaches `AUTOMATED_REVIEW_COMPLETE`, which is not
itself a `status` value — it only means the content item is ready for the
still fully human-driven `HUMAN_REVIEW` stage. The `PRODUCTION` stage now
has a schema (see "Production layer" below) but no implementation.
`APPROVED` requires human sign-off (`templates/VIDEO_QA.md` final
approval) and precedes `PUBLISHED`; publishing will never be automated
per `CONSTITUTION.md` rule 2.

## Production layer (Phase 7D — full pipeline through Production QA)

Once a content item reaches `status = APPROVED`, `templates/PRODUCTION.md`
defines a **separate, more granular lifecycle** for turning its script
into an actual video — separate on purpose, so production work never
has authority over content review/approval or publishing:

```
PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING → ASSET_COLLECTION →
ASSEMBLY → CAPTIONS → THUMBNAIL → METADATA → PRODUCTION_QA →
HUMAN_REVIEW → APPROVED → READY_TO_PUBLISH
```

`READY_TO_PUBLISH` is the last state any production agent may ever set —
actual publishing is a separate, human-driven action with its own
(not yet built) system, outside this entire phase. `HUMAN_REVIEW` is the
highest state any agent this phase actually reaches (Production QA's own
terminal output, and only on `PASS`) — `APPROVED` and `READY_TO_PUBLISH`
remain exclusively human-set. A content item's own `HUMAN_REVIEW`/
`APPROVED` `status` values and this production lifecycle's same-named
states are deliberately distinct — see `templates/PRODUCTION.md`'s
"Separation from content lifecycle."

`templates/SCENE.md` records the video as data; `templates/ASSET.md`
requires every representational asset to be classified
`AUTHENTIC_HISTORICAL_MEDIA` or `GENERATED_RECONSTRUCTION` (never left
implicit); `templates/VOICE.md` is provider-agnostic. Phase 7D adds four
more schemas following the identical pattern: `templates/TIMELINE.md`
(the assembled scene-by-scene schedule plus the output artifact record),
`templates/CAPTIONS.md` (caption chunks and timing, every chunk a
verbatim substring of its source narration), `templates/THUMBNAIL.md` (a
specification, never a generated image, with an explicit "must never
imply something happened if hypothetical" rule), and
`templates/PRODUCTION_QA.md` (a structural verdict —
`PASS`/`REVISION_REQUIRED`/`BLOCKED`/`SYSTEM_ERROR` — never an approval).

All eight production agents now have working MVPs, covering the full
sequence from `PRODUCTION_PLANNING` through `HUMAN_REVIEW` — see "Agent
contracts" below. None generates or retrieves any *real* media: every
provider (`VoiceProvider`, `GeneratedAssetProvider`,
`AssetRetrievalProvider`, `VideoRenderer`, `ThumbnailProvider`) has only
a deterministic local-test implementation this phase, and every one of
their outputs is permanently, honestly labeled as a placeholder. No
video-encoding tool exists in this environment, so `agents/assembler/`
produces a manifest describing what a real renderer would assemble, not
an actual video file — see `agents/assembler/README.md`'s "Actual video
artifact status". `agents/production_qa/` is the last automated gate: it
can report a production ready for human review (`Production status =
HUMAN_REVIEW`) but can never approve, schedule, or publish anything —
see `agents/production_qa/CONTRACT.md`'s "Verdict states".

## Agent contracts

`agents/` holds specifications for agents — what each is allowed and
forbidden to do, and its exact handoff back into the pipeline. An agent
may only be implemented once its contract exists and has been reviewed.
See `agents/README.md`, including its shared result-shape convention for
how a future orchestrator would run every stage in sequence.

- `agents/researcher/CONTRACT.md` — Research / Fact-Check Agent (RESEARCH
  and FACT_CHECK stages). FACT_CHECK has a working MVP
  (`agents/researcher/src/`). Touches only `reviews/*.md` and two
  whitelisted `CONTENT_ITEM.md` fields (`Research state`, `Fact-check
  state`).
- `agents/safety/CONTRACT.md` — Safety Reviewer (SAFETY_REVIEW stage).
  Has a working MVP (`agents/safety/src/`). Touches only `reviews/*.md`
  and one whitelisted `CONTENT_ITEM.md` field (`Safety state`); never
  writes to a `claims/*.md` file.
- `agents/originality/CONTRACT.md` — Originality Reviewer
  (ORIGINALITY_REVIEW stage): editorial originality and similarity
  *risk* only — never a plagiarism/legal determination, never "100%
  original." Has a working MVP (`agents/originality/src/`). Touches only
  `reviews/*.md` and one whitelisted `CONTENT_ITEM.md` field
  (`Originality state`); never writes to `claims/*.md` or `research/*.md`.
- `agents/orchestrator/CONTRACT.md` — Unified Automated Review
  Orchestrator: runs the three agents above in order
  (`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW`), stopping at the
  first stage that doesn't `PASS`. Makes no review judgment of its own,
  has no `mutate.py`/field whitelist of its own — every mutation under
  `--apply` happens through the invoked agent's own existing write path.
  Reuses (never duplicates) each agent's own hashing to skip re-running a
  stage that already has a fresh, unstale `PASS` on file.
- `agents/producer/CONTRACT.md` — Producer (Phase 7B). Has a working MVP
  (`agents/producer/src/`): turns an `APPROVED` script into
  `PRODUCTION.md` + `scenes/*.md`, deterministically (word-count/WPM
  duration, verbatim narration, no invented content). Requires content
  `status = APPROVED`; refuses (structured `blocked` result, no
  mutation) rather than bypassing. Never writes to `CONTENT_ITEM.md`,
  changes a claim, or bypasses human approval. A changed `SCRIPT.md`
  after production makes the plan `stale` — refuses to silently
  regenerate rather than overwriting production history.
- `agents/voice/CONTRACT.md` — Voice (Phase 7C-1). Has a working MVP
  (`agents/voice/src/`): narration → voiceover-audio record, via a
  provider-agnostic `VoiceProvider` adapter interface (this phase's only
  implementation, `LocalTestVoiceProvider`, produces a deterministic
  placeholder, always labeled `TEST / PLACEHOLDER AUDIO`, never real
  speech). Requires content `status = APPROVED` (checked independently of
  `PRODUCTION.md`); never alters narration meaning or inserts unsupported
  claims. A changed `SCRIPT.md` after generation makes the voice result
  `stale` — refuses to silently reuse or regenerate it.
- `agents/visual_planner/CONTRACT.md` — Visual Planner (Phase 7B). Has a
  working MVP (`agents/visual_planner/src/`): finalizes each scene's
  visual requirement and creates `assets/*.md` skeleton records via the
  deterministic Visual Safety Rule (claim `Classification` -> visual
  type/authenticity — see `agents/visual_planner/README.md`). Never
  presents generated media as authentic, never invents historical
  evidence beyond what claims establish; blocks (never guesses) if a
  scene's claim provenance is missing.
- `agents/assets/CONTRACT.md` — Assets (Phase 7C-2). Has a working MVP
  (`agents/assets/src/`): completes each scene's asset record with a
  strategy (`GENERATED`/`RETRIEVED`/`HUMAN_PROVIDED`), a deterministic
  placeholder artifact or structured retrieval requirement, and honest
  provenance — reimplementing the identical Visual Safety Rule (never
  importing Visual Planner's own code) so authenticity is always derived
  from claims, never from strategy or filename. Preserves (never
  recomputes) Visual Planner's existing classification when completing
  its skeleton. Requires content `status = APPROVED` (checked
  independently); never invents a claim, a source URL, or a source
  organization; an unprovenanced `HUMAN_PROVIDED` asset is flagged
  `REVIEW_REQUIRED`, never silently trusted. A changed scene after asset
  generation makes that asset `STALE` — refuses to silently regenerate.
- `agents/assembler/CONTRACT.md` — Assembler (Phase 7D). Has a working
  MVP (`agents/assembler/src/`): derives a deterministic, non-overlapping
  `TIMELINE.md` from `SCENE.md` records and hands it to a swappable
  `VideoRenderer` provider (this phase's only implementation,
  `LocalTestVideoRenderer`, writes a placeholder manifest text file, never
  a real video — no video-encoding tool exists in this environment).
  Requires content `status = APPROVED`; reuses (never regenerates)
  existing Voice and Asset output, blocking as `STALE` on any script/asset
  hash mismatch rather than silently reusing outdated input; never
  substitutes an unrelated asset for a missing one. Advances `Production
  status` to `CAPTIONS`.
- `agents/captions/CONTRACT.md` — Captions (Phase 7D). Has a working MVP
  (`agents/captions/src/`): deterministically segments each scene's
  narration into caption chunks (documented defaults: 40 characters/line
  x 2 lines/caption) with proportional timing. Captions are always a
  verbatim substring of the source narration — never paraphrased,
  rewritten, or grammar-"fixed" — and never drop safety-critical
  qualifiers (`may`, `could`, `likely`, `hypothetical`, `we cannot know`).
  Advances `Production status` to `THUMBNAIL`.
- `agents/thumbnail/CONTRACT.md` — Thumbnail (Phase 7D). Has a working
  MVP (`agents/thumbnail/src/`): produces a deterministic thumbnail
  *specification* (concept, text overlay, focal subject, authenticity
  considerations) via a swappable `ThumbnailProvider` (this phase's only
  implementation, `LocalTestThumbnailProvider`, a placeholder — no real
  image-generation integration). Never invents a sensational claim or
  implies a hypothetical premise happened; a `what-if` pillar's title is
  hedged (`"What if: ...?"`) unless already phrased as a question. Also
  populates `PRODUCTION.md`'s `Title / description` section verbatim from
  `CONTENT_ITEM.md`'s own working title — never synthesized copy.
  Advances `Production status` to `METADATA`.
- `agents/production_qa/CONTRACT.md` — Production QA (Phase 7D). Has a
  working MVP (`agents/production_qa/src/`): the final automated gate —
  independently re-verifies every upstream claim (content, voice, assets,
  timeline, captions, thumbnail, output) rather than trusting it, and
  reports a structured verdict (`PASS` / `REVISION_REQUIRED` / `BLOCKED` /
  `SYSTEM_ERROR`). Staleness in any upstream input is always a hard
  `BLOCKED` gate, never a soft check. **Never** sets `Production status`
  to anything beyond `HUMAN_REVIEW`, and only on `PASS` — `APPROVED` and
  `READY_TO_PUBLISH` remain exclusively human-set; never touches `Human
  review state` or `CONTENT_ITEM.md`'s own `status`.

All agents: never run unless explicitly invoked (no scheduling, no
triggers); `--apply` is opt-in, a dry run is the default; never touch
`status` or `Owner approval state`; never publish anything.

## Out of scope for this phase

- No dependency installation (all eight MVPs are stdlib Python only), no
  frameworks.
- No automation or scheduling — agents only run when explicitly invoked
  by a human.
- No RESEARCH-mode implementation (source collection/live retrieval) —
  FACT_CHECK mode only for the Research/Fact-Check Agent.
- No internet-wide plagiarism/similarity search — the Originality
  Reviewer only compares against explicitly supplied channel metadata
  and reference material.
- The automated-review orchestrator only coordinates the three review
  stages that exist (`FACT_CHECK`, `SAFETY_REVIEW`, `ORIGINALITY_REVIEW`)
  — production QA (`agents/production_qa/`) is a separate, later gate in
  the production lifecycle, not part of that orchestrator.
- No real TTS integration — `agents/voice/`'s only provider
  (`LocalTestVoiceProvider`) produces a deterministic, clearly-labeled
  placeholder text artifact, never real speech; no vendor is named
  anywhere in the schema or code.
- No actual media generation or retrieval — `agents/producer/`,
  `agents/voice/`, `agents/visual_planner/`, and `agents/assets/` produce
  structured *requirements*/*records* only (scenes, a voice-record
  referencing placeholder audio, visual/asset specifications, an
  asset-record referencing a placeholder artifact or an unimplemented
  retrieval requirement); no real audio synthesis, no image/video
  generation integration, no stock-media crawler.
- No real video rendering — `agents/assembler/`'s only provider
  (`LocalTestVideoRenderer`) writes a deterministic placeholder manifest
  text file, never a playable video file; no FFmpeg or other
  video-encoding tool is installed or invoked anywhere in this phase. No
  real thumbnail image generation either — `agents/thumbnail/`'s only
  provider (`LocalTestThumbnailProvider`) produces a text specification,
  never a generated image.
- `RETRIEVED`-strategy assets can never reach a genuine `PASS` in
  Production QA this phase, since no real asset-retrieval integration
  exists (`agents/assets/`'s `LocalTestAssetRetrievalProvider` always
  returns `RETRIEVAL_NOT_IMPLEMENTED`) — documented as an intentional,
  honest limitation, not a bug, in `agents/production_qa/CONTRACT.md` and
  `README.md`.
- No sophisticated editing intelligence, cinematic pacing optimization,
  computer vision, or thumbnail A/B testing/optimization.
- No external API integration (e.g. YouTube), no analytics, no
  recommendation/audience-prediction system, no learning engine.
- No autonomous publishing or approval pipeline. `agents/production_qa/`
  can advance `Production status` to `HUMAN_REVIEW` at most, only on
  `PASS` — it can never set `APPROVED` or `READY_TO_PUBLISH`, and never
  touches `CONTENT_ITEM.md`'s own `status` or `Human review state`. Those
  remain exclusively human/owner-set, with no automated path around them.
- No full pipeline orchestration across all eight production agents yet
  (each is invoked individually) and no self-review/revision loop — see
  "Exact next task" in `STATE.md` (Phase 7E).
