# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**MVP automated review layer.** Three independent agents have working,
tested implementations, stdlib Python, no dependencies: the Research /
Fact-Check Agent (`agents/researcher/src/`, FACT_CHECK mode only), the
Safety Reviewer (`agents/safety/src/`, SAFETY_REVIEW only), and the
Originality Reviewer (`agents/originality/src/`, ORIGINALITY_REVIEW
only). No orchestrator runs them in sequence yet — see
`agents/README.md`'s shared interface convention. Everything else remains
documentation/templates only: no RESEARCH-mode live retrieval, no
editorial/production-QA agents, no video generation, no automation/
scheduling, no publishing, no external API integration. Nothing outside
`agents/researcher/`, `agents/safety/`, and `agents/originality/` executes.

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
│   └── VIDEO_QA.md
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
│   └── originality/            Originality Reviewer
│       ├── CONTRACT.md           Design contract
│       ├── README.md             How to run it, module map, limitations
│       ├── src/                  MVP implementation (ORIGINALITY_REVIEW only)
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

## Pipeline status (not yet implemented — schema only)

```
IDEA → RESEARCH → SCRIPT → FACT_CHECK → SAFETY_REVIEW →
ORIGINALITY_REVIEW → PRODUCTION → QA → HUMAN_REVIEW → APPROVED →
PUBLISHED → ANALYZING → LEARNING → ARCHIVED

REJECTED (may occur from any stage)
```

`APPROVED` requires human sign-off (`templates/VIDEO_QA.md` final
approval) and precedes `PUBLISHED`. No stage is automated yet, and
publishing will never be automated per `CONSTITUTION.md` rule 2.

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

All three agents: never run unless explicitly invoked (no scheduling, no
triggers); `--apply` is opt-in, a dry run is the default; never touch
`status` or `Owner approval state`; never publish anything.

## Out of scope for this phase

- No dependency installation (all three MVPs are stdlib Python only), no
  frameworks.
- No automation or scheduling — agents only run when explicitly invoked
  by a human.
- No RESEARCH-mode implementation (source collection/live retrieval) —
  FACT_CHECK mode only for the Research/Fact-Check Agent.
- No internet-wide plagiarism/similarity search — the Originality
  Reviewer only compares against explicitly supplied channel metadata
  and reference material.
- No orchestrator running the pipeline stages automatically in sequence
  — each agent is invoked independently.
- No editorial/production-QA agents yet, no video generation, no
  external API integration (e.g. YouTube).
- No production or publishing pipeline.
