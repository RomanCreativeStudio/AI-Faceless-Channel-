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
  publication → learning)
- [`agents/`](./agents/) — agent contracts and, for three agents so far,
  working MVP implementations (Research/Fact-Check, Safety Reviewer,
  Originality Reviewer)

## Current phase

MVP automated review layer: three independent, tested agents
(`agents/researcher/`, `agents/safety/`, `agents/originality/`), stdlib
Python, no dependencies, no scheduling — each runs only when explicitly
invoked, dry run by default. No orchestrator, no other agents, no video
production, no external API integration exist yet. Publishing is, and
will remain, human-gated — see `CONSTITUTION.md`.
