# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**Content intelligence architecture.** Documentation and templates only.
No implementation code, no scripts, no automation, no dependencies, no
external API integration. Nothing here executes.

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

## Out of scope for this phase

- No scripts, no dependency installation, no code of any kind.
- No automation or scheduling.
- No agents, no video generation, no external API integration (e.g. YouTube).
- No production or publishing pipeline.
