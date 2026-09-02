# AI Faceless Channel

A faceless content channel project built around four equal content pillars:

- **Business Stories / Case Studies**
- **History**
- **Technology**
- **What If?** — hypothetical/speculative content that always distinguishes
  established fact from inference (see `CONSTITUTION.md`)

## Project docs

- [`CONSTITUTION.md`](./CONSTITUTION.md) — non-negotiable governing rules
  (human authority, no automated publishing, content standards)
- [`SYSTEM.md`](./SYSTEM.md) — architecture, directory structure, content
  lifecycle
- [`STATE.md`](./STATE.md) — current project status and next task
- [`templates/`](./templates/) — the content-item schema every piece of
  content is built from (idea → research → script → review → QA →
  publication → learning), plus the production-record schema
  (`PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md`)
- [`agents/`](./agents/) — agent contracts and working MVP
  implementations: three independent review agents (Research/Fact-Check,
  Safety Reviewer, Originality Reviewer) plus a thin orchestrator that
  runs them in order; and three production agent contracts (Producer,
  Voice, Visual Planner) with no implementation yet

## Current phase

**Phase 6 complete: MVP automated review layer.** Three independent,
tested review agents (`agents/researcher/`, `agents/safety/`,
`agents/originality/`) plus `agents/orchestrator/`, which runs
`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW` in order and stops at
the first stage that doesn't pass — it makes no review judgment itself.
Stdlib Python, no dependencies, no scheduling — everything runs only when
explicitly invoked, dry run by default.

**Phase 7 foundation laid: production stack contracts.** A production
record schema now exists (`templates/PRODUCTION.md`/`SCENE.md`/
`ASSET.md`/`VOICE.md`) describing a video as structured data — scenes,
narration, visual/asset requirements, claim references — plus contracts
for the agents that will eventually populate it
(`agents/producer/`, `agents/voice/`, `agents/visual-planner/`). No media
generation, no TTS/image/video integration, and no implementation of any
of the three exists yet — see `STATE.md` for what's next. Production
remains a separate lifecycle from content review and can never publish;
publishing is, and will remain, entirely human-gated — see
`CONSTITUTION.md`.
