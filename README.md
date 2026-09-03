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
  runs them in order; and three production agents (Producer, Voice,
  Visual Planner) that turn an approved script into structured scenes, a
  voiceover record, and visual requirements — no *real* media generation
  yet (Voice's only provider is a deterministic placeholder).

## Current phase

**Phase 6 complete: MVP automated review layer.** Three independent,
tested review agents (`agents/researcher/`, `agents/safety/`,
`agents/originality/`) plus `agents/orchestrator/`, which runs
`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW` in order and stops at
the first stage that doesn't pass — it makes no review judgment itself.
Stdlib Python, no dependencies, no scheduling — everything runs only when
explicitly invoked, dry run by default.

**Phase 7C-1 complete: Voice Generation MVP.** A production record schema
(`templates/PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md`) describes a
video as structured data — scenes, narration, a voiceover track,
visual/asset requirements, claim references. `agents/producer/` turns an
`APPROVED` script into that structure deterministically (word-count/WPM
duration, verbatim narration, no invented content); `agents/voice/` then
converts the narration into a voiceover-audio *record* through a
provider-agnostic adapter interface — this phase's only implementation
produces a deterministic, permanently-labeled `TEST / PLACEHOLDER AUDIO`
artifact, never real speech; `agents/visual_planner/` finalizes each
scene's visual requirement via a deterministic Visual Safety Rule that
classifies every representational asset as `AUTHENTIC_HISTORICAL_MEDIA`
(sourcing intent only) or `GENERATED_RECONSTRUCTION` — never ambiguous,
never presenting generated content as real. None of the three generates
or retrieves any real media — see `STATE.md` for what's next
(asset generation/retrieval). Production remains a separate lifecycle
from content review and can never publish; publishing is, and will
remain, entirely human-gated — see `CONSTITUTION.md`.
