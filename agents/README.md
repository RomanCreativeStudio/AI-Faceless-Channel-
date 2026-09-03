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

None of `producer/`, `voice/`, `visual_planner/`, or `assets/` generates
or retrieves any *real* media — all four produce structured
*requirements*/*records* (scenes, a voice record referencing a
placeholder audio artifact, visual/asset specifications, an asset record
referencing a placeholder artifact or an unimplemented retrieval
requirement) for later, unbuilt tooling (or a real TTS/generation/
retrieval provider) to fulfill.

## Not yet specified

Editorial review and production QA remain fully human-driven until a
contract is written and approved here (the orchestrator's pipeline stops
before them). Publication remains human-gated permanently, by
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

## The production lifecycle (Phase 7C-2 — Producer + Voice + Visual Planner + Assets MVP)

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
current. Visual Planner's own Phase 7B interim allowance (also accepting
`PRODUCTION_PLANNING`, not just `VISUAL_PLANNING`) still exists in code —
unneeded on the real path now that `voice/` genuinely sets
`VISUAL_PLANNING`, but left in place rather than touched, out of each of
Phase 7C-1's and 7C-2's stated scope; see `STATE.md`'s Known limitations.
The rest of the sequence has neither an agent nor an implementation yet.
`READY_TO_PUBLISH` is the last state any of this may ever reach — actual
publishing is a separate, human-driven system, not built in this phase or
any so far.

All four agents share `agents/producer/src/hashing.py`
(`compute_script_content_hash`) directly rather than duplicating it —
`voice/`, `visual_planner/`, and `assets/` each reuse it to re-verify
`SCRIPT.md` hasn't changed since `producer/` ran, refusing to act on a
stale production. `voice/` also reuses `visual_planner/src/loader.load_scenes`
directly (generic scene-file reading, not visual-planning domain logic)
rather than re-parsing scene files a third time; `assets/` has its own,
similarly generic scene-field reader (it needs `Visual type`/`Visual
description` too, which that loader doesn't carry). `assets/`
deliberately does **not** import `visual_planner/`'s classification
logic — it reimplements the identical Visual Safety Rule independently,
preserving the sibling-agent boundary every production agent maintains
(reuse generic infrastructure across agents, never another agent's own
domain judgment) — see `agents/assets/CONTRACT.md`'s "Authenticity
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
(only once every scene's asset is current) `Production status`.

See `content/what-if/wi-20260902-black-death-modern-medicine/PRODUCTION.md`
for the Phase 7A golden fixture demonstrating the schema against real
content (hand-built, not agent-generated — that content item's `status`
is intentionally never `APPROVED`, so no agent will ever run `--apply`
against it; see each agent's `tests/test_approval_gate.py` /
`test_authenticity_classification.py`).
