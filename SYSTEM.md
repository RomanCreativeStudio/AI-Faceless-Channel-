# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**Foundational documentation & directory structure only.** No implementation
code, no scripts, no automation, no dependencies. Nothing here executes.

## Directory structure

```
/
├── README.md            Project overview, entry point
├── SYSTEM.md             This file — architecture
├── CONSTITUTION.md        Non-negotiable governing rules
├── STATE.md               Living project status
└── content/                Content pillar folders (structure only, no code)
    ├── business-stories/
    ├── history/
    ├── technology/
    └── what-if/
```

Each `content/<pillar>/` folder holds a `README.md` describing that pillar's
scope and conventions. Actual episode/content files are added in a later
phase, not this one.

## Content pillars

| Pillar | Folder | Notes |
|---|---|---|
| Business Stories / Case Studies | `content/business-stories/` | Real companies/events, sourced |
| History | `content/history/` | Established historical fact, sourced |
| Technology | `content/technology/` | How things work / technical explainers |
| What If? | `content/what-if/` | Fact vs. hypothetical must be labeled (see CONSTITUTION.md rule 4) |

## Planned content lifecycle (not yet implemented)

Idea → Research → Draft → Human Review → Human Approval → Production →
Publish. Every stage from Draft onward is human-gated. No stage in this
lifecycle is automated yet, and publishing will never be automated per
`CONSTITUTION.md` rule 2.

## Out of scope for this phase

- No scripts, no dependency installation, no code of any kind.
- No automation or scheduling.
- No production or publishing pipeline.
