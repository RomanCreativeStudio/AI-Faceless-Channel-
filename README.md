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
  (`PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md`/`TIMELINE.md`/
  `CAPTIONS.md`/`THUMBNAIL.md`/`PRODUCTION_QA.md`)
- [`agents/`](./agents/) — agent contracts and working MVP
  implementations: three independent review agents (Research/Fact-Check,
  Safety Reviewer, Originality Reviewer) plus a thin orchestrator that
  runs them in order; and eight production agents (Producer, Voice,
  Visual Planner, Assets, Assembler, Captions, Thumbnail, Production QA)
  that turn an approved script all the way through to a human-review-ready
  production package — no *real* media generation yet (every provider is
  a deterministic placeholder).

## Current phase

**Phase 6 complete: MVP automated review layer.** Three independent,
tested review agents (`agents/researcher/`, `agents/safety/`,
`agents/originality/`) plus `agents/orchestrator/`, which runs
`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW` in order and stops at
the first stage that doesn't pass — it makes no review judgment itself.
Stdlib Python, no dependencies, no scheduling — everything runs only when
explicitly invoked, dry run by default.

**Phase 7D complete: Video Assembly + Captions + Thumbnail + Production
QA.** The full production pipeline now runs end to end, from an
`APPROVED` script through to `Production status = HUMAN_REVIEW`:
`agents/producer/` → `agents/voice/` → `agents/visual_planner/` →
`agents/assets/` → `agents/assembler/` → `agents/captions/` →
`agents/thumbnail/` → `agents/production_qa/`. `agents/assembler/`
derives a deterministic, non-overlapping timeline from scene records and
hands it to a swappable `VideoRenderer` provider (a placeholder manifest
this phase — no video-encoding tool is installed); `agents/captions/`
deterministically segments narration into timed caption chunks that are
always a verbatim substring of the source narration, never paraphrased,
and never drop safety-critical qualifiers like "may"/"could"/
"hypothetical"/"we cannot know"; `agents/thumbnail/` produces a
deterministic thumbnail *specification* via a swappable
`ThumbnailProvider` (placeholder text this phase, no real image
generation), hedging `what-if` titles (`"What if: ...?"`) rather than
implying a hypothetical premise happened; `agents/production_qa/` is the
final automated gate, independently re-verifying every upstream claim and
reporting `PASS`/`REVISION_REQUIRED`/`BLOCKED`/`SYSTEM_ERROR` — it can
advance `Production status` to `HUMAN_REVIEW` at most, on `PASS` only,
and can never approve or publish anything. Every provider across all
eight agents is a deterministic placeholder, permanently labeled as such
— none generates or retrieves any real media. See `STATE.md` for what's
next (Phase 7E: full pipeline orchestration + self-review loop).
Production remains a separate lifecycle from content review and can never
publish; publishing is, and will remain, entirely human-gated — see
`CONSTITUTION.md`.
