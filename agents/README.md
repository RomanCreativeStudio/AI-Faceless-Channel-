# Agents

Contracts and MVP implementations for the automated review pipeline —
what each is allowed and forbidden to do, and how it hands off to the
next stage.

Every agent contract here is subordinate to `CONSTITUTION.md`. Where
anything in an agent contract could be read as conflicting with
`CONSTITUTION.md`, the constitution wins — a contract is never grounds to
override it. No agent has publishing authority, ever, at any stage.

## Agents specified so far

- [`researcher/`](./researcher/) — Research / Fact-Check Agent:
  populates `RESEARCH.md`/`CLAIM.md` during `RESEARCH`, verifies claims
  during `FACT_CHECK`. FACT_CHECK mode has a working MVP
  (`researcher/src/`, `researcher/README.md`).
- [`safety/`](./safety/) — Safety Reviewer: evaluates `SCRIPT.md` for
  safety/policy risk during `SAFETY_REVIEW`. Has a working MVP
  (`safety/src/`, `safety/README.md`).
- [`originality/`](./originality/) — Originality Reviewer: evaluates
  editorial originality and similarity *risk* during
  `ORIGINALITY_REVIEW` — never a plagiarism/legal determination, never
  "100% original." Has a working MVP (`originality/src/`,
  `originality/README.md`).
- [`orchestrator/`](./orchestrator/) — Unified Automated Review
  Orchestrator: runs the three agents above in order and aggregates
  their results. Makes **no** review judgment of its own — see
  `orchestrator/CONTRACT.md`'s "Important distinction." Has a working
  MVP (`orchestrator/src/`, `orchestrator/README.md`).

Four more have **working MVPs** (Phase 7B/7C-1/7C-2) — the production
stack, which begins once a content item reaches `status = APPROVED` and
is a separate lifecycle from everything above (see
`templates/PRODUCTION.md`):

- [`producer/`](./producer/) — turns an approved script into
  `PRODUCTION.md` + `scenes/*.md`, deterministically (word-count/WPM
  duration, verbatim narration decomposed into scenes, no invented
  content). Never writes to `CONTENT_ITEM.md`, changes a claim, or
  bypasses human approval. Has a working MVP (`producer/src/`,
  `producer/README.md`).
- [`voice/`](./voice/) — converts a production's narration into a
  voiceover-audio record, via a provider-agnostic `VoiceProvider` adapter
  interface (no vendor named anywhere in the contract or code). This
  phase's only implementation is a deterministic local test provider —
  its output is always labeled `TEST / PLACEHOLDER AUDIO`, never real
  speech. Never alters narration meaning or inserts unsupported claims.
  Has a working MVP (`voice/src/`, `voice/README.md`).
- [`visual_planner/`](./visual_planner/) — finalizes each scene's visual
  requirement and creates an `assets/*.md` skeleton via a deterministic
  Visual Safety Rule (a scene's claim `Classification` drives its visual
  type and authenticity classification). Never presents generated media
  as authentic, never invents historical evidence. Has a working MVP
  (`visual_planner/src/`, `visual_planner/README.md`).
- [`assets/`](./assets/) — completes each scene's asset record with an
  explicit strategy (`GENERATED`/`RETRIEVED`/`HUMAN_PROVIDED`), via the
  same provider-agnostic pattern as `voice/` (no vendor named anywhere).
  Reimplements the identical Visual Safety Rule independently (never
  imports `visual_planner/`'s code) so authenticity is always derived
  from claims, never from strategy or filename; preserves — never
  recomputes — Visual Planner's classification when completing its
  skeleton. An unprovenanced `HUMAN_PROVIDED` asset is flagged
  `REVIEW_REQUIRED`, never silently trusted as authentic. Has a working
  MVP (`assets/src/`, `assets/README.md`).

Four more have **working MVPs** (Phase 7D) — the rest of the production
stack, taking a production all the way from `ASSEMBLY` through the final
automated gate before human review:

- [`assembler/`](./assembler/) — derives a deterministic, non-overlapping
  `TIMELINE.md` from `SCENE.md` records and hands it to a swappable
  `VideoRenderer` provider. This phase's only implementation
  (`LocalTestVideoRenderer`) writes a placeholder manifest text file, not
  a real video — no video-encoding tool exists in this environment (see
  `assembler/README.md`'s "Actual video artifact status"). Reuses,
  never regenerates, existing Voice/Asset output; blocks as `STALE` on
  any script/asset hash mismatch. Has a working MVP (`assembler/src/`,
  `assembler/README.md`).
- [`captions/`](./captions/) — deterministically segments each scene's
  narration into caption chunks (documented defaults: 40 characters/line
  x 2 lines/caption) with proportional timing. Every caption is a
  verbatim substring of the source narration — never paraphrased,
  rewritten, or grammar-"fixed" — and never drops safety-critical
  qualifiers (`may`, `could`, `likely`, `hypothetical`, `we cannot know`).
  Has a working MVP (`captions/src/`, `captions/README.md`).
- [`thumbnail/`](./thumbnail/) — produces a deterministic thumbnail
  *specification* (concept, text overlay, focal subject, authenticity
  considerations) via a swappable `ThumbnailProvider`. This phase's only
  implementation (`LocalTestThumbnailProvider`) is a text placeholder, not
  a generated image. Never invents a sensational claim or implies a
  hypothetical premise happened; hedges a `what-if` pillar's title
  (`"What if: ...?"`) unless it's already phrased as a question. Also
  populates `PRODUCTION.md`'s `Title / description` verbatim from
  `CONTENT_ITEM.md`'s working title — never synthesized copy. Has a
  working MVP (`thumbnail/src/`, `thumbnail/README.md`).
- [`production_qa/`](./production_qa/) — the final automated gate:
  independently re-verifies every upstream claim (content, voice, assets,
  timeline, captions, thumbnail, output) rather than trusting it, and
  reports a structured verdict (`PASS`/`REVISION_REQUIRED`/`BLOCKED`/
  `SYSTEM_ERROR`). Staleness anywhere upstream is always a hard `BLOCKED`
  gate, never a soft check. **Never** sets `Production status` beyond
  `HUMAN_REVIEW`, and only on `PASS`; never touches `Human review state`
  or `CONTENT_ITEM.md`. Has a working MVP (`production_qa/src/`,
  `production_qa/README.md`).

None of the eight production agents generates or retrieves any *real*
media — every provider (`VoiceProvider`, `GeneratedAssetProvider`,
`AssetRetrievalProvider`, `VideoRenderer`, `ThumbnailProvider`) has only a
deterministic local-test implementation this phase, permanently labeled
as a placeholder, for later, unbuilt tooling (or a real TTS/generation/
retrieval/rendering provider) to fulfill.

## Not yet specified

Editorial review remains fully human-driven until a contract is written
and approved here (the orchestrator's pipeline stops before it).
Production QA now has a working automated MVP (`production_qa/`), but it
is a **structural** gate only — never a creative/editorial judgment, and
never an approval. Publication remains human-gated permanently, by
`CONSTITUTION.md` rule 2, regardless of what gets automated upstream of
it — see `STATE.md` for what's next.

## The pipeline sequence, and the shared interface shape

```
RESEARCH / FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW →
EDITORIAL_REVIEW → PRODUCTION_QA
```

`agents/orchestrator/` now runs the first three stages
(`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW`) in order, stopping at
the first stage that doesn't cleanly `PASS` — see
`orchestrator/CONTRACT.md`. `EDITORIAL_REVIEW` and `PRODUCTION_QA` have
no agent yet, so the orchestrator's pipeline currently ends at
`ORIGINALITY_REVIEW`; a clean run reaches `AUTOMATED_REVIEW_COMPLETE`,
which hands off to the still fully human-driven `HUMAN_REVIEW` stage (the
orchestrator never touches `status`, so nothing actually advances
automatically).

Each of the four agents remains independently usable — the orchestrator
existing doesn't create any new dependency between `researcher/`,
`safety/`, and `originality/`, and each still has its own CLI and test
suite. This works because every review-stage entry point shares one
result shape:

| Field | Meaning |
|---|---|
| `verdict` | `PASS` / `REVISION_REQUIRED` / `REJECT` (`ReviewVerdict`) |
| `reasons` | Human-readable findings, one per line |
| `required_changes` | What would need to change for a future `PASS` |
| `escalate_to_human` | `True` whenever a human must decide — never silently folded into `PASS` |
| `content_hash` | For staleness detection (`templates/REVIEW.md` Multi-pass resolution rule 4) |
| `aborted` / `abort_reason` | Nothing loadable — no `REVIEW.md` was written |
| `blocked` / `blocked_reason` | Multi-pass gating refused a new attempt (REJECT-terminal or two-consecutive-`REVISION_REQUIRED`) |
| `review_path` | Where the `REVIEW.md` was written, if `apply=True` and not blocked |

All three review agents' entry points — `agents.researcher.src.pipeline
.run_fact_check(root, apply)`, `agents.safety.src.pipeline
.run_safety_review(root, apply)`, and `agents.originality.src.pipeline
.run_originality_review(root, apply, ...)` — return a dataclass with this
shape and share the same `dry-run by default, --apply is opt-in`
behavior. `agents.orchestrator.src.pipeline.run_automated_review(root,
apply, ...)` calls each of those directly, in order, and aggregates their
results into one `OrchestratorResult` (same core fields, plus
`stages_executed`/`stages_skipped`/`first_blocking_stage` — see
`orchestrator/CONTRACT.md`'s Result model) — it doesn't need to know
anything about any stage's internals to do this.

## Shared vs. independent code

`safety/` and `originality/` each reuse `researcher/src`'s generic,
role-agnostic infrastructure (markdown table/section parsing, the
`ReviewVerdict`/`ReviewRecord`/`ContentItem`/`Classification` models, the
`Multi-pass resolution` gating functions, and the two failure-condition
exception types) — never `researcher/`'s fact-check domain logic
(`evidence.py`, `factcheck.py`, `atomicity.py`, or its own field
whitelist/hashing). `safety/` and `originality/` do **not** import from
each other — they are siblings, each depending only on `researcher/`'s
generic base. Each review agent has its own `mutate.py` with its own
hard-coded field whitelist, its own `hashing.py`, and its own
signal/evidence evaluation. `orchestrator/` imports each of the three
agents' real `run_*` pipeline functions directly (never reimplementing
their logic) plus the same generic pieces from `researcher/src`; it has
**no `mutate.py` of its own** — every write under `--apply` happens
inside the invoked agent's own existing path. No agent requires any other
to run first or to exist at all.

## The production lifecycle (Phase 7D — full pipeline through Production QA)

```
PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING → ASSET_COLLECTION →
ASSEMBLY → CAPTIONS → THUMBNAIL → METADATA → PRODUCTION_QA →
HUMAN_REVIEW → APPROVED → READY_TO_PUBLISH
```

Owned by `templates/PRODUCTION.md`, tracked entirely separately from the
content-review `status` above — no production agent writes to
`CONTENT_ITEM.md` at all. `producer/` produces `PRODUCTION_PLANNING`;
`voice/` runs directly against `PRODUCTION_PLANNING` (it *is* the agent
that owns the `VOICE` stage, so it needs no separate hand-off state to
wait for — see `agents/voice/CONTRACT.md`'s Preconditions for why
requiring a literal `Production status = VOICE` would have been
unreachable) and is itself the one that advances status to
`VISUAL_PLANNING`, but only once its own `QA status` is `PASS`;
`visual_planner/` consumes that and advances to `ASSET_COLLECTION` once
every scene has a finalized visual plan; `assets/` consumes *that* and
advances to `ASSEMBLY` once every scene's asset record is complete and
current; `assembler/` consumes `ASSEMBLY` (also idempotently re-runnable
against its own `CAPTIONS` output) and advances to `CAPTIONS` once a
timeline is built and rendered; `captions/` consumes `CAPTIONS` and
advances to `THUMBNAIL`; `thumbnail/` consumes `THUMBNAIL` and advances to
`METADATA` (populating `PRODUCTION.md`'s `Title / description` in the same
run); `production_qa/` consumes `METADATA` and advances to `HUMAN_REVIEW`
**only on a `PASS` verdict** — a `REVISION_REQUIRED`/`BLOCKED`/
`SYSTEM_ERROR` result leaves `Production status` at `METADATA`,
unadvanced. Visual Planner's own Phase 7B interim allowance (also
accepting `PRODUCTION_PLANNING`, not just `VISUAL_PLANNING`) still exists
in code — unneeded on the real path now that `voice/` genuinely sets
`VISUAL_PLANNING`, but left in place rather than touched, out of each of
Phase 7C-1's and 7C-2's stated scope; see `STATE.md`'s Known limitations.
`HUMAN_REVIEW` is the highest state any agent may ever reach this phase —
`APPROVED` and `READY_TO_PUBLISH` remain exclusively human-set, with no
automated path around them; actual publishing is a separate, human-driven
system, not built in this phase or any so far.

All eight agents share `agents/producer/src/hashing.py`
(`compute_script_content_hash`) directly rather than duplicating it — each
downstream agent reuses it to re-verify `SCRIPT.md` hasn't changed since
`producer/` ran, refusing to act on a stale production. `voice/` also
reuses `visual_planner/src/loader.load_scenes` directly (generic
scene-file reading, not visual-planning domain logic) rather than
re-parsing scene files a third time; `assets/`, `assembler/`, and
`captions/` each have their own, similarly generic scene-field readers
(they need fields that loader doesn't carry). `assembler/` reuses
`agents/assets/src/hashing.compute_asset_content_hash` directly to
re-verify each scene's asset is current before building the timeline;
`captions/` reuses `agents/assembler/src/scene_reader.load_scene_timing`
and `agents/assets/src/scene_reader.load_scene_visual_records` directly.
`production_qa/` reuses `agents/producer/src/hashing`,
`agents/assets/src/hashing`, and
`agents/assets/src/scene_reader.load_scene_visual_records` directly, but
otherwise **re-verifies everything independently** rather than trusting
any upstream agent's own claim (e.g. it re-checks caption text against
narration itself, rather than trusting `captions/`'s own record) — the
same sibling-agent boundary every production agent maintains: reuse
generic infrastructure across agents, never another agent's own domain
judgment. `assets/` and `thumbnail/` each independently reimplement the
identical Visual Safety Rule rather than importing `visual_planner/`'s
classification logic — see `agents/assets/CONTRACT.md`'s "Authenticity
classification".

Each agent has its own hard-coded write whitelist (`mutate.py`):
`producer/` may only create fresh `PRODUCTION.md`/`scenes/scene-<n>.md`
files (never overwrites an existing one — a changed script makes the
plan `stale` instead); `voice/` may only create fresh
`voice/voice-<n>.md`/`voice-<n>.audio.txt` files (same never-overwrite
rule) and update `PRODUCTION.md`'s `Voiceover information` section plus
(only once its own QA passes) `Production status`; `visual_planner/` may
only update a scene's `Visual type`/`Visual description`/`Asset
requirement` fields, create `assets/asset-<n>.md` skeleton files, and
update `PRODUCTION.md`'s two rollup sections plus `Production status`;
`assets/` may only create/complete `assets/asset-<n>.md` and
`assets/asset-<n>.generated.txt` files (see
`agents/assets/CONTRACT.md`'s "Relationship to `agents/visual_planner/`"
for exactly how "completing a skeleton" differs from overwriting one) and
update `PRODUCTION.md`'s `Asset references (rollup)` section plus
(only once every scene's asset is current) `Production status`;
`assembler/` may only create fresh `timeline/timeline-<n>.md` and
`output/video-<n>.manifest.txt` files and update `PRODUCTION.md`'s
`Assembly / Output` section plus `Production status`; `captions/` may
only create fresh `captions/captions-<n>.md` files and update
`PRODUCTION.md`'s `Captions` section plus `Production status`;
`thumbnail/` may only create fresh `thumbnail/thumbnail-<n>.md` files and
update `PRODUCTION.md`'s `Thumbnail` and `Title / description` sections
plus `Production status`; `production_qa/` may only create fresh
`qa/production-qa-<n>.md` files and update `PRODUCTION.md`'s `Production
QA state` section plus (only on `PASS`, only to `HUMAN_REVIEW`)
`Production status` — hard-coded in `mutate.py` to raise rather than
accept any other verdict-to-status mapping; it never touches `Human
review state`, which stays exclusively human-owned.

See `content/what-if/wi-20260902-black-death-modern-medicine/PRODUCTION.md`
for the Phase 7A golden fixture demonstrating the schema against real
content (hand-built, not agent-generated — that content item's `status`
is intentionally never `APPROVED`, so no agent will ever run `--apply`
against it; see each agent's `tests/test_approval_gate.py` /
`test_authenticity_classification.py`).
