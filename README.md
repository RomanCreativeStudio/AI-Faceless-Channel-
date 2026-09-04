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
  `CAPTIONS.md`/`THUMBNAIL.md`/`PRODUCTION_QA.md`) and the claim-revision
  record schema (`REVISION.md`)
- [`agents/`](./agents/) — agent contracts and working MVP
  implementations: three independent review agents (Research/Fact-Check,
  Safety Reviewer, Originality Reviewer — the first also has a narrow
  **Autonomous Revision Mode** and, within it, an even narrower **Bounded
  Research Mode**, see below) plus a thin orchestrator that
  runs them in order; eight production agents (Producer, Voice,
  Visual Planner, Assets, Assembler, Captions, Thumbnail, Production QA)
  that turn an approved script all the way through to a human-review-ready
  production package; and `agents/full_pipeline/`, a thin orchestrator
  sequencing all twelve of the above into one call — no *real* media
  generation yet (every provider is a deterministic placeholder), and
  nothing beyond `Production status = HUMAN_REVIEW` is ever reachable
  automatically.

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
— none generates or retrieves any real media. Production remains a
separate lifecycle from content review and can never publish; publishing
is, and will remain, entirely human-gated — see `CONSTITUTION.md`.

**Phase 7E complete: Full Pipeline Orchestration + Self-Review Loop.**
`agents/full_pipeline/` sequences `agents/orchestrator/`'s own
content-review chain, a read-only approval-gate check, and all eight
production agents into one call, stopping at the first stage that
doesn't cleanly succeed — coordination only, no review/production/QA
judgment of its own, no `mutate.py`. Because only a human may ever set
`CONTENT_ITEM.md status = APPROVED`, this orchestrator's stage list is
really two automatable phases separated by a hard human gate; a clean
content-review pass with the item still unapproved is reported as
success, not a failure, naming exactly what a human needs to do.
**Genuine finding this phase:** no agent in this codebase can
autonomously fix a `REVISION_REQUIRED`/`BLOCKED`/stale result — every
production agent's own contract documents "no versioned supersession" —
so this orchestrator never loops in-process; "self-review" means safely
re-invoking the same call after something changes out of band, relying
entirely on each stage's own already-existing freshness check to
determine exactly what needs to re-run. `COMPLETE` (Production QA
`PASS`, `Production status = HUMAN_REVIEW`) is the highest outcome it may
ever report.

**Phase 7F complete: Autonomous Revision Engine (Research/Fact-Check).**
`agents/researcher/src/revision.py` adds one narrow, deterministically
safe autonomous-fix capability: when a `FACT_CHECKER` attempt is
`REVISION_REQUIRED`, it looks for a `FACT` claim whose evidence gap can
be closed with *already-existing, already-recorded* research — never
invented — and, if one exists, creates a new **successor claim** (never
editing the original, whose table stays byte-identical forever) citing
it. `agents/full_pipeline/` recognizes this and, when it applies, runs
one more `FACT_CHECKER` attempt plus a fresh content-review pass so
`SAFETY_REVIEW`/`ORIGINALITY_REVIEW` get their turn — bounded entirely by
the existing two-consecutive-attempts rule, never a new retry system.
Three concepts stay deliberately separate and always will: **automated
review** (an AI evaluates), **autonomous revision** (an AI may create a
controlled successor artifact when it's safe to), and **human approval**
(a human decides). A revision `PASS` never means `APPROVED`.

**Phase 7G complete: Bounded Research Retrieval + Evidence Expansion.**
`agents/researcher/src/research.py` extends Autonomous Revision Mode's
one remaining gap: when a `FACT` claim's evidence gap can't be closed
with anything already on disk, it now issues **exactly one** bounded,
deterministic query — the claim's own exact text, verbatim, never
reworded or broadened — through a pluggable `ResearchProvider`
abstraction, evaluates every result against a conservative,
never-domain-hardcoded reliability policy, and either produces one new,
genuinely reciprocal `research/*.md` entry that hands off to the *same*
successor-creation mechanism Case A already uses, or escalates. This is
explicitly **not** general autonomous browsing: no retry, no query
rewording, no more than one bounded-research pass per revision cycle, and
a source's reliability can only ever be capped down from what a provider
claims, never up. Only a deterministic, no-network
`LocalTestResearchProvider` exists today; a real provider is a distinct,
deliberate follow-up. `agents/full_pipeline/` needed no control-flow
change — it already called the unmodified function this now lives
inside.

**Phase 8 complete: Real Episode 1 Production.** Four production agents
(`agents/voice/`, `agents/assets/`, `agents/assembler/`,
`agents/thumbnail/`) gained their first real, non-placeholder provider —
real offline speech synthesis (ffmpeg's `flite` filter), a real
deterministic illustration renderer plus real Wikimedia Commons
retrieval, a real ffmpeg H.264/AAC video renderer with burned-in
captions, and an optional real thumbnail image — each a second
implementation of that agent's own pre-existing provider interface, so no
agent's pipeline needed a redesign. `Pillow` and `ffmpeg` are this
project's first non-stdlib dependencies (`requirements.txt`), added only
because Phase 8's actual task — real media production — genuinely needed
them. Episode 1 ("What If Modern Medicine Existed During the Black
Death?") is a real, independent content item at
`content/what-if/wi-20260904-black-death-modern-medicine-ep1/` (never the
schema/engineering golden sample, which remains untouched) — real
narration, real illustrated/retrieved visuals, a real captioned MP4, and
a real thumbnail were produced and manually inspected end to end. The
human approval gate was never bypassed: the canonical episode's
`CONTENT_ITEM.md` status was never set to `APPROVED` by this system, and
production validation used an isolated, throwaway copy — see `STATE.md`
for the full report, what's genuinely still blocking full automated
`FACT_CHECK` `PASS`, and what's next.
