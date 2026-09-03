# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**Phase 6 complete (automated review layer); Phase 7B complete (Producer
+ Visual Planner MVP).** Six agents have working, tested implementations,
stdlib Python, no dependencies: the Research / Fact-Check Agent
(`agents/researcher/src/`, FACT_CHECK mode only), the Safety Reviewer
(`agents/safety/src/`, SAFETY_REVIEW only), the Originality Reviewer
(`agents/originality/src/`, ORIGINALITY_REVIEW only), the Unified
Automated Review Orchestrator (`agents/orchestrator/src/`, which runs the
three in order and aggregates their results — it makes no
safety/factual/originality judgment of its own; see
`agents/orchestrator/CONTRACT.md`), the Producer
(`agents/producer/src/`, turns an `APPROVED` script into
`PRODUCTION.md` + `scenes/*.md`, deterministically — no AI creativity
yet), and the Visual Planner (`agents/visual_planner/src/`, finalizes
each scene's `Visual type`/`Visual description` and creates
`assets/*.md` records via the deterministic Visual Safety Rule). Neither
Producer nor Visual Planner generates or retrieves any actual media —
see "Production layer" below. `agents/voice/` remains a **contract only,
no implementation** (Phase 7C). Everything else remains
documentation/templates only: no RESEARCH-mode live retrieval, no
editorial/production-QA agents, no voice/TTS integration, no image/video
generation or asset retrieval, no FFmpeg/assembly, no automation/
scheduling, no publishing, no external API integration. Nothing outside
`agents/researcher/`, `agents/safety/`, `agents/originality/`,
`agents/orchestrator/`, `agents/producer/`, and `agents/visual_planner/`
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
│   └── VOICE.md                Voiceover record, provider-agnostic (Phase 7)
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
│   ├── voice/                   Voice (Phase 7C — contract only, no src/)
│   └── visual_planner/          Visual Planner
│       ├── CONTRACT.md           Design contract
│       ├── README.md             How to run it, module map, limitations
│       ├── src/                  MVP implementation (Phase 7B)
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

## Production layer (Phase 7B — Producer + Visual Planner MVP)

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
(not yet built) system, outside this entire phase. A content item's own
`HUMAN_REVIEW`/`APPROVED` `status` values and this production lifecycle's
same-named states are deliberately distinct — see `templates/PRODUCTION.md`'s
"Separation from content lifecycle."

`templates/SCENE.md` records the video as data — narration, timing,
visual type/description, asset requirement, captions, transitions, and
claim references per scene — so a future renderer can assemble a video
from structured records rather than reinterpreting prose.
`templates/ASSET.md` requires every representational asset to be
classified `AUTHENTIC_HISTORICAL_MEDIA` or `GENERATED_RECONSTRUCTION`
(never left implicit), so generated imagery can never be silently
presented as real historical footage. `templates/VOICE.md` is
provider-agnostic — no TTS/voice vendor is named anywhere in the schema.

`agents/producer/` and `agents/visual_planner/` have working MVPs for the
first two stages (`PRODUCTION_PLANNING`, then visual planning);
`agents/voice/` remains a contract only — see "Agent contracts" below.
Neither MVP generates or retrieves any real media: Producer decomposes an
approved script into structured scenes with placeholder visual/asset
fields, and Visual Planner turns those placeholders into a structured,
explicit visual *requirement* (deterministically classified
`AUTHENTIC_HISTORICAL_MEDIA`/`GENERATED_RECONSTRUCTION`/`NOT_APPLICABLE`)
— actually sourcing or generating that asset is later, unbuilt tooling
(`ASSET_COLLECTION`).

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
- `agents/voice/CONTRACT.md` — Voice (Phase 7C, **not implemented**):
  narration → voiceover audio, provider-agnostic. Never alters narration
  meaning or inserts unsupported claims.
- `agents/visual_planner/CONTRACT.md` — Visual Planner (Phase 7B). Has a
  working MVP (`agents/visual_planner/src/`): finalizes each scene's
  visual requirement and creates `assets/*.md` records via the
  deterministic Visual Safety Rule (claim `Classification` -> visual
  type/authenticity — see `agents/visual_planner/README.md`). Never
  presents generated media as authentic, never invents historical
  evidence beyond what claims establish; blocks (never guesses) if a
  scene's claim provenance is missing.

All agents: never run unless explicitly invoked (no scheduling, no
triggers); `--apply` is opt-in, a dry run is the default; never touch
`status` or `Owner approval state`; never publish anything.

## Out of scope for this phase

- No dependency installation (all six MVPs are stdlib Python only), no
  frameworks.
- No automation or scheduling — agents only run when explicitly invoked
  by a human.
- No RESEARCH-mode implementation (source collection/live retrieval) —
  FACT_CHECK mode only for the Research/Fact-Check Agent.
- No internet-wide plagiarism/similarity search — the Originality
  Reviewer only compares against explicitly supplied channel metadata
  and reference material.
- No editorial/production-QA agents yet, so the orchestrator only
  coordinates the three stages that exist.
- No voice/TTS implementation yet (`agents/voice/` is a contract only —
  Phase 7C) — Producer's `Voiceover information` fields stay
  `NOT_STARTED`/placeholder.
- No actual media generation or retrieval — `agents/producer/` and
  `agents/visual_planner/` produce structured *requirements* only
  (scenes, visual/asset specifications); no TTS integration, no
  image/video generation integration, no stock-media crawler, no
  FFmpeg/assembly infrastructure. `ASSET_COLLECTION` and beyond in
  `templates/PRODUCTION.md`'s `Production status` sequence remain
  unbuilt.
- No external API integration (e.g. YouTube), no analytics, no learning
  engine.
- No production or publishing pipeline. Reaching
  `AUTOMATED_REVIEW_COMPLETE` or `READY_TO_PUBLISH` never advances
  `status` or publishes anything — both stay human/owner-approval-gated.
