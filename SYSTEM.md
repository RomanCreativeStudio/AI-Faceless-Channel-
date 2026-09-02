# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**MVP Research / Fact-Check pipeline.** The first agent — FACT_CHECK mode
only — has a working, tested implementation (`agents/researcher/src/`,
stdlib Python, no dependencies). Everything else remains
documentation/templates only: no RESEARCH-mode live retrieval, no other
agents, no video generation, no automation/scheduling, no publishing, no
external API integration. Nothing outside `agents/researcher/` executes.

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
│   └── researcher/            Research / Fact-Check Agent
│       ├── CONTRACT.md          Design contract
│       ├── README.md            How to run it, module map, limitations
│       ├── src/                 MVP implementation (FACT_CHECK mode only)
│       └── tests/               Unit + integration tests
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

`agents/` holds specifications for future agents — what each is allowed
and forbidden to do, and its exact handoff back into the pipeline. An
agent may only be implemented once its contract exists and has been
reviewed. See `agents/README.md`. The first contract,
`agents/researcher/CONTRACT.md`, covers the Research / Fact-Check Agent
(RESEARCH and FACT_CHECK stages). Its FACT_CHECK half now has a working
MVP implementation (`agents/researcher/src/`) — see that directory's
README for how to run it. It only ever touches `reviews/*.md` and two
whitelisted `CONTENT_ITEM.md` fields; it never runs unless explicitly
invoked (no scheduling, no triggers), and `--apply` is opt-in — a dry run
is the default.

## Out of scope for this phase

- No dependency installation (the MVP is stdlib Python only), no
  frameworks.
- No automation or scheduling — the agent only runs when explicitly
  invoked by a human.
- No RESEARCH-mode implementation (source collection/live retrieval) —
  FACT_CHECK mode only.
- No other agents (script, safety, originality, production, QA), no video
  generation, no external API integration (e.g. YouTube).
- No production or publishing pipeline.
