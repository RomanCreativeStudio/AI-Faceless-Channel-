# System Architecture

Operational architecture for the AI Faceless Channel project. Governed by
`CONSTITUTION.md`; current status tracked in `STATE.md`.

## Current phase

**Phase 6 complete: automated review layer.** Three independent review
agents plus a thin orchestrator have working, tested implementations,
stdlib Python, no dependencies: the Research / Fact-Check Agent
(`agents/researcher/src/`, FACT_CHECK mode only), the Safety Reviewer
(`agents/safety/src/`, SAFETY_REVIEW only), the Originality Reviewer
(`agents/originality/src/`, ORIGINALITY_REVIEW only), and the Unified
Automated Review Orchestrator (`agents/orchestrator/src/`), which runs
the three in order and aggregates their results — it makes no
safety/factual/originality judgment of its own; see
`agents/orchestrator/CONTRACT.md`. Everything else remains
documentation/templates only: no RESEARCH-mode live retrieval, no
editorial/production-QA agents, no video generation, no automation/
scheduling, no publishing, no external API integration. Nothing outside
`agents/researcher/`, `agents/safety/`, `agents/originality/`, and
`agents/orchestrator/` executes.

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
│   ├── originality/            Originality Reviewer
│   │   ├── CONTRACT.md           Design contract
│   │   ├── README.md             How to run it, module map, limitations
│   │   ├── src/                  MVP implementation (ORIGINALITY_REVIEW only)
│   │   └── tests/                Unit + integration tests
│   └── orchestrator/           Unified Automated Review Orchestrator
│       ├── CONTRACT.md           Design contract (coordination only)
│       ├── README.md             How to run it, module map, limitations
│       ├── src/                  Runs the three agents in order, aggregates results
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
still fully human-driven `HUMAN_REVIEW` stage. Every stage from
`PRODUCTION` onward remains unimplemented — schema only. `APPROVED`
requires human sign-off (`templates/VIDEO_QA.md` final approval) and
precedes `PUBLISHED`; publishing will never be automated per
`CONSTITUTION.md` rule 2.

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

All agents: never run unless explicitly invoked (no scheduling, no
triggers); `--apply` is opt-in, a dry run is the default; never touch
`status` or `Owner approval state`; never publish anything.

## Out of scope for this phase

- No dependency installation (all four MVPs are stdlib Python only), no
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
- No video generation, no external API integration (e.g. YouTube).
- No production or publishing pipeline. Reaching
  `AUTOMATED_REVIEW_COMPLETE` never advances `status` — that stays
  human/owner-approval-gated.
