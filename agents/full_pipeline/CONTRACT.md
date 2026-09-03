# Contract: Full Pipeline Orchestrator

Specification for Phase 7E's unified production orchestrator. Like
`agents/orchestrator/` (which it wraps rather than duplicates), this
agent makes no editorial, safety, originality, production, or QA
judgment of its own. It coordinates the eleven agents that already exist
— nothing more.

This contract is subordinate to `CONSTITUTION.md` and to every agent's
own contract (`agents/researcher/CONTRACT.md`, `agents/safety/CONTRACT.md`,
`agents/originality/CONTRACT.md`, `agents/orchestrator/CONTRACT.md`,
`agents/producer/CONTRACT.md`, `agents/voice/CONTRACT.md`,
`agents/visual_planner/CONTRACT.md`, `agents/assets/CONTRACT.md`,
`agents/assembler/CONTRACT.md`, `agents/captions/CONTRACT.md`,
`agents/thumbnail/CONTRACT.md`, `agents/production_qa/CONTRACT.md`). It
does not restate what those agents decide or how. Where anything below
could be read as expanding an individual agent's authority, that agent's
own contract wins.

## Important distinction

**This orchestrator does not decide whether content is safe, factual,
original, production-ready, or QA-clean. The individual agents decide
that.** It only sequences them, stops at the first stage that doesn't
cleanly succeed, and aggregates their already-structured results into
one report. It contains no fact evaluation, no signal detection, no
narration generation, no visual/asset classification, no timeline
construction, no caption segmentation, no thumbnail framing, and no QA
check of its own.

## Accepted entry conditions

Runs against any content-item directory containing at least
`CONTENT_ITEM.md`. Nothing more is required to *start* a run — the first
two stages (content review, then the approval gate) exist precisely to
determine, without guessing, how far a given item can legitimately go
this call. There is no separate "is this item eligible" precondition
beyond what each invoked agent already independently enforces.

## Stage ordering

```
CONTENT_REVIEW           (agents/orchestrator, run_automated_review:
                           FACT_CHECK -> SAFETY_REVIEW -> ORIGINALITY_REVIEW)
  -> CONTENT_APPROVAL_GATE (read-only: CONTENT_ITEM.md status == APPROVED)
    -> PRODUCER
      -> VOICE
        -> VISUAL_PLANNER
          -> ASSETS
            -> ASSEMBLER
              -> CAPTIONS
                -> THUMBNAIL
                  -> PRODUCTION_QA
                    -> HUMAN_REVIEW  (terminal; human-only beyond this point)
```

**Stage order deviates from a literal reading of the task brief in one
place, deliberately and for the same reason Phase 7C-2 already
established:** the brief's flow lists `VISUAL PLANNER` before `VOICE`.
The real, working precondition chain — verified against every agent's
actual `CONTRACT.md` and `pipeline.py` this phase, not assumed from
memory — is `PRODUCER -> VOICE -> VISUAL_PLANNER -> ASSETS`
(`templates/PRODUCTION.md`'s own `Production status` sequence:
`PRODUCTION_PLANNING -> VOICE -> VISUAL_PLANNING -> ASSET_COLLECTION`).
Voice's own `CONTRACT.md` requires `Production status ==
PRODUCTION_PLANNING`; Visual Planner requires `VISUAL_PLANNING` (or the
still-undocumented-away Phase 7B interim allowance). Running Visual
Planner before Voice would either be blocked by Visual Planner's own
precondition or silently exploit that interim allowance — this
orchestrator uses the real, documented order instead of inventing a
second one. See `agents/README.md`'s "Genuine finding" (Phase 7C-2) for
the original discovery.

**No Script Agent exists, and none is invented here.** The brief's `SCRIPT`
stage is a human/owner-authored (or otherwise already-produced)
`SCRIPT.md` file — this orchestrator treats its existence and content as
an input, exactly as every production agent already does independently.
Building a script-generation agent is out of scope for this phase and is
not attempted.

## Two-phase structure (the real architectural shape)

Because `CONTENT_ITEM.md`'s `status` field may only ever be set to
`APPROVED` by a human (`CONSTITUTION.md` rule 1; every agent's own
Forbidden actions independently forbid touching it), this orchestrator's
stage list is **not actually one continuous automatable chain** — it is
two automatable phases separated by a hard, human-only gate:

1. **Content review** (`CONTENT_REVIEW`): fully automatable, reuses
   `agents/orchestrator/` entirely.
2. **`CONTENT_APPROVAL_GATE`**: a read-only check, not a stage this
   orchestrator can pass on its own — it can only observe that a human
   already did.
3. **Production** (`PRODUCER` through `PRODUCTION_QA`): fully automatable
   *once* phase 2 has been satisfied by a human.

A run that reaches the approval gate with `CONTENT_ITEM.md status !=
APPROVED` is not a failure — the content review chain worked exactly as
designed. It is reported as `pipeline_status = PASS`, `human_action_required
= True`, with a `human_action_reason` naming the approval gate explicitly
— mirroring how `agents/orchestrator/` itself reports a clean
`AUTOMATED_REVIEW_COMPLETE` as `PASS`, not as a blocking failure.

## Stage adapters

Reuses each agent's real public entry point directly — no reimplementation
of any agent's algorithm, hashing, or write path:

| Stage | Reused entry point |
|---|---|
| `CONTENT_REVIEW` | `agents.orchestrator.src.pipeline.run_automated_review` |
| `PRODUCER` | `agents.producer.src.pipeline.run_producer` |
| `VOICE` | `agents.voice.src.pipeline.run_voice_generation` |
| `VISUAL_PLANNER` | `agents.visual_planner.src.pipeline.run_visual_planner` |
| `ASSETS` | `agents.assets.src.pipeline.run_asset_generation` |
| `ASSEMBLER` | `agents.assembler.src.pipeline.run_video_assembly` |
| `CAPTIONS` | `agents.captions.src.pipeline.run_caption_generation` |
| `THUMBNAIL` | `agents.thumbnail.src.pipeline.run_thumbnail_generation` |
| `PRODUCTION_QA` | `agents.production_qa.src.pipeline.run_production_qa` |

`CONTENT_APPROVAL_GATE` has no agent of its own — it reuses
`agents.researcher.src.loader.load_content_item` (already-generic
infrastructure every agent already depends on) purely to read `status`.
It never writes anything.

Every production-stage result shares one structural shape across all
eight agents (`aborted`/`abort_reason`, `blocked`/`blocked_reason`,
`stale`/`stale_reason`, `already_up_to_date`, a `produced`/`planned`
success property, `reasons: list[str]`) — see `agents/README.md`'s shared
result-shape convention. `src/stages.py`'s `normalize_standard_result`
reads that shared shape generically, once, for all eight. Only
`agents/production_qa/`'s result is structurally different (`verdict` is
already one of `PASS`/`REVISION_REQUIRED`/`BLOCKED`/`SYSTEM_ERROR` instead
of separate booleans) and gets its own small `normalize_qa_result`
adapter — still zero domain logic, just reading an existing field.

## Dependency graph

Two distinct graphs matter here and are kept explicit rather than
conflated:

**1. The state-machine-enforced *execution* order** (what actually gates
whether a stage may run at all — `templates/PRODUCTION.md`'s
`Production status` sequence): strictly linear, `PRODUCER -> VOICE ->
VISUAL_PLANNER -> ASSETS -> ASSEMBLER -> CAPTIONS -> THUMBNAIL ->
PRODUCTION_QA`. This orchestrator's stage list follows this order exactly.

**2. The true *data* dependency graph** (what each stage actually reads):

```
CONTENT_ITEM.md (status, pillar, working title)
  + SCRIPT.md (human-authored/approved — an input, not an output of this system)
    -> PRODUCER reads SCRIPT.md, claims/*.md
       writes PRODUCTION.md, scenes/scene-<n>.md
         -> VOICE reads scenes/ narration, PRODUCTION.md's script hash
            writes voice/voice-01.md
         -> VISUAL_PLANNER reads scenes/, claims/
            writes scenes/*.md visual fields, assets/asset-<n>.md skeletons
              -> ASSETS reads scenes/, claims/, assets/ skeletons
                 completes assets/asset-<n>.md
                   -> ASSEMBLER reads scenes/, voice/voice-01.md, assets/*.md
                      writes timeline/timeline-01.md, output/video-01.manifest.txt
                        -> CAPTIONS reads scenes/ narration, timeline/'s scene timing
                           writes captions/captions-01.md
                             -> THUMBNAIL reads CONTENT_ITEM.md, claims/, assets/ authenticity
                                writes thumbnail/thumbnail-01.md
                                  -> PRODUCTION_QA reads everything above, independently
                                     writes qa/production-qa-01.md
                                       -> HUMAN_REVIEW (human-only beyond here)
```

`SCRIPT.md` is a genuinely **shared** root of both the content-review
chain (via each reviewer's own `Reviewed content hash`, which covers
`SCRIPT.md` + cited claims) and the entire production chain (via
`compute_script_content_hash`, reused unmodified by every production
agent). Editing `SCRIPT.md` after review correctly invalidates *both*
independently — this orchestrator does not need to propagate that
itself; each agent's own hash check already does, on its own, every time
it runs. See "Freshness and invalidation" below.

## Freshness and invalidation — no second hash system

**This orchestrator computes no hash of its own and maintains no central
staleness table.** Every one of the eleven coordinated stages already,
independently, verifies its own inputs are current before doing anything
(`agents/orchestrator/`'s `find_fresh_pass` for the three review stages;
each production agent's own stored-hash-vs-current-hash comparison for
its stage). This orchestrator relies on that existing, already-tested
machinery entirely:

- A stage that is already satisfied and unstale reports success with
  nothing written (`already_up_to_date` / `reused_existing_pass`) —
  cheap, correct, and exactly what a naive "just re-run everything"
  script would get wrong.
- A stage whose input changed reports `stale`/executes fresh, exactly
  scoped to what actually changed — never a blanket "start over."
- Because each stage's freshness check only ever looks at *its own*
  direct inputs, invalidation is naturally scoped: changing `SCRIPT.md`
  makes `VOICE`, `VISUAL_PLANNER`/`ASSETS`, `ASSEMBLER`, `CAPTIONS`,
  `THUMBNAIL`, and `PRODUCTION_QA` all detect staleness (each depends on
  it, directly or transitively through a stored hash chain) but never
  touches `CONTENT_REVIEW`'s own review-attempt files beyond the fact
  that the *same* `SCRIPT.md` hash change also independently invalidates
  those (a real, correct dependency — not an accident of this
  orchestrator's design). Changing an `assets/asset-<n>.md` artifact by
  hand invalidates only `ASSEMBLER`, `PRODUCTION_QA` — never `VOICE` or
  the content-review chain, which never read it.

Building a second, orchestrator-owned hash/invalidation system would
duplicate this exactly, be a second source of truth to keep in sync, and
contradict "reuse the existing hash infrastructure wherever possible" —
so this orchestrator deliberately has none.

## Self-review behavior

**Genuine finding, verified against every agent's actual contract before
writing any code (not assumed): no agent in this codebase — none of the
eleven coordinated here — has authority to autonomously regenerate,
overwrite, or fix an existing artifact once written.** Every production
agent's own `CONTRACT.md` documents this as "no versioned supersession":
a stale or QA-failing artifact is reported and left untouched,
permanently, until a human (or a not-yet-built future agent) changes the
underlying input out of band. `templates/REVIEW.md` rule 5 permits an
agent to "fix and create the next attempt" autonomously for
`REVISION_REQUIRED` — but nothing in `agents/researcher/`,
`agents/safety/`, or `agents/originality/` implements the "fix" half of
that (no `RESEARCH`-mode implementation exists this phase per
`SYSTEM.md`'s "Out of scope"); only a human editing `SCRIPT.md`/`claims/`
and re-invoking the same stage constitutes a "fix" today.

Given that, **this orchestrator invokes every stage's own `run_*` at most
once per call, and never loops in-process.** Immediately re-invoking a
stage with unchanged inputs would either be a wasted no-op (production
stages, whose own precondition would just report `already_up_to_date`
with the *same* unresolved issue still blocking `Production status`), or
actively harmful for the three review stages (creating a second,
identical-verdict `reviews/<role>-2.md` attempt purely to burn down the
two-consecutive-attempts budget faster, with no actual fix behind it —
exactly the kind of fabricated, valueless action `CONTRACT.md`'s
Forbidden-actions list below rules out in spirit even where not named
explicitly). So the self-review loop this phase is:

1. Run the next stage (`adapter.run(root, apply)`).
2. Inspect its normalized outcome.
3. `PASS` (fresh or already-up-to-date) -> continue to the next stage.
4. `REVISION_REQUIRED` / `BLOCKED` / `STALE` -> check whether *this
   orchestrator* has any explicitly permitted autonomous fix for it. It
   never does, this phase (see finding above) — the permitted-fix table
   this orchestrator consults is deliberately empty. Stop.
5. Report `human_action_required = True` with the exact stage and reason.
6. **The loop resumes correctly on the *next separate call*** to
   `run_full_pipeline`, once a human (or a future agent) has actually
   changed something: each stage's own freshness/precondition check
   (never this orchestrator's own logic) determines, correctly and for
   free, exactly which stages need to re-run and which are already
   satisfied — see "Freshness and invalidation" above. This *is* "re-run
   the affected stage, re-run all downstream stages whose dependencies
   changed, run Production QA again" — implemented as an emergent
   property of each stage's existing precondition, not as new
   orchestrator-level invalidation code.

`MAX_STAGE_ATTEMPTS = 1` is documented in `src/pipeline.py` as an
explicit, enforced constant for exactly this reason — not a placeholder
for a future in-process retry loop, a permanent architectural fact about
what this codebase's agents can and cannot do autonomously.

## Retry / escalation policy

- **Content review** (`CONTENT_REVIEW`): retry/escalation is entirely
  `agents/orchestrator/`'s and, beneath it, each of the three review
  agents' own already-implemented two-consecutive-`REVISION_REQUIRED`
  rule (`templates/REVIEW.md` Multi-pass resolution rule 5) and
  REJECT-is-terminal rule (rule 3). This orchestrator surfaces whatever
  `OrchestratorResult` it gets back; it does not reimplement or extend
  either rule.
- **Production stages**: exactly one attempt per call
  (`MAX_STAGE_ATTEMPTS = 1`), for the reasons above. A `BLOCKED`/`STALE`
  result is immediately terminal for this call and reported as requiring
  human action.
- **Two-consecutive-attempt rule, at this orchestrator's own level**: not
  reimplemented — it already exists one layer down, inside
  `agents/orchestrator/`, and this orchestrator would only ever
  duplicate it if it tried to loop internally (which it deliberately does
  not — see "Self-review behavior").

## Human escalation

`ESCALATE_TO_HUMAN` is reported whenever:

- `CONTENT_REVIEW`'s own `OrchestratorResult.human_escalation` is `True`
  (a review stage flagged `escalate_to_human`, or reached `REJECT`), or
- `CONTENT_REVIEW`'s two-consecutive-attempts gate already fired
  (surfaced via that stage's own `blocked=True`).

A production stage's `BLOCKED`/`REVISION_REQUIRED` result is reported as
`pipeline_status = BLOCKED` / `REVISION_REQUIRED` with `human_action_required
= True` — a genuine escalation in effect, but not labeled
`ESCALATE_TO_HUMAN` specifically, since no production agent has its own
`escalate_to_human` concept (none needed one — `BLOCKED` already means
"a human must act," per every production `CONTRACT.md`'s Preconditions).
Reserving `ESCALATE_TO_HUMAN` for the content-review stage's own explicit
flag keeps this orchestrator from inventing a new escalation category
that doesn't already exist in an underlying agent's own vocabulary.

## Protected fields

This orchestrator has **no field whitelist of its own** — it has no
`mutate.py` at all (matching `agents/orchestrator/`'s own precedent
exactly: "The orchestrator has no `mutate.py` and no field whitelist of
its own — every mutation that happens under `apply=True` is performed by
the invoked agent through its own existing, already-tested write path").
Every byte written to disk under `apply=True` is written by one of the
eleven coordinated agents, through a path that agent's own `CONTRACT.md`
already documents and tests independently protect. This orchestrator
writes **nothing** — not even a new "pipeline run" artifact — by design
(see "Artifact ownership" below).

## Artifact ownership

No new artifact type is introduced. `PipelineResult` (the structured
in-memory/CLI-JSON result — see `src/models.py`) is coordination
*metadata*: it exists only for the duration of one call and is never
persisted to disk by this orchestrator. Every actual production/review
artifact (`REVIEW.md`, `PRODUCTION.md`, `scenes/*.md`, `voice/*.md`,
`assets/*.md`, `timeline/*.md`, `captions/*.md`, `thumbnail/*.md`,
`qa/*.md`) is owned exactly as documented in the owning agent's own
`CONTRACT.md` — this orchestrator neither creates a new artifact type nor
gains write access to any existing one.

## Terminal states

| `pipeline_status` | Meaning |
|---|---|
| `PASS` | Every stage run this call succeeded, but a human checkpoint stands between here and further progress (the approval gate, most commonly) — not a failure. |
| `REVISION_REQUIRED` | A stage reported `REVISION_REQUIRED` with no autonomous fix available. Human action needed. |
| `BLOCKED` | A stage's precondition wasn't met, or an upstream artifact is stale. Human action needed. |
| `ESCALATE_TO_HUMAN` | The content-review chain itself flagged escalation (a `REJECT`, a `HIGH_RISK`/`REVIEW_REQUIRED` signal, or its own two-consecutive-attempts limit). |
| `SYSTEM_ERROR` | A stage's content couldn't be loaded, or a coordinated agent raised an exception (caught at this orchestrator's boundary, never mistaken for success). |
| `COMPLETE` | `PRODUCTION_QA` reached `PASS`; `Production status` is now `HUMAN_REVIEW`. The highest automated outcome this system may ever reach. |

`COMPLETE` is the ceiling. Nothing in this orchestrator, or any agent it
coordinates, may ever report or cause `APPROVED` or `READY_TO_PUBLISH`.

## Handoff behavior

On `COMPLETE`, the item sits at `Production status = HUMAN_REVIEW` —
exactly where `agents/production_qa/` itself already leaves it. This
orchestrator does nothing further; a human reviewer takes it from there
via `PRODUCTION.md`'s `Human review state` section, which no agent,
including this one, has ever been permitted to touch.

## What this orchestrator is forbidden from doing

- Change a claim's classification or wording, or fabricate evidence.
- Override, soften, reinterpret, or hide a safety or originality
  decision.
- Override a human decision, or a `BLOCKED`/`stale` refusal from any
  invoked agent.
- Convert `REVISION_REQUIRED`, `REJECT`, or `BLOCKED` into `PASS`.
- Set `CONTENT_ITEM.md`'s `status` to `APPROVED`, or touch it at all.
- Set `PRODUCTION.md`'s `Production status` beyond what
  `agents/production_qa/` itself is permitted to set (`HUMAN_REVIEW`,
  only on `PASS`) — this orchestrator never writes that field directly;
  it only ever happens via the invoked agent's own existing path.
- Touch `PRODUCTION.md`'s `Human review state` — human-only.
- Publish, upload, schedule, or otherwise transmit anything to any
  external platform, under any condition.
- Regenerate, overwrite, or delete any existing artifact any invoked
  agent has already written — see "Self-review behavior."
- Retry a stage more than `MAX_STAGE_ATTEMPTS` (1) times within a single
  call, or loop indefinitely under any circumstance.
- Reimplement any agent's own domain logic (evidence evaluation, signal
  detection, scene/timeline construction, caption segmentation,
  thumbnail framing, QA checks) — it only ever calls the real function.
- Gain any write authority beyond what invoking the eleven existing
  agents already grants them individually.

## Apply / dry-run

Same convention as every other agent: dry run by default, `apply=True` is
explicit and opt-in, passed straight through unmodified to every invoked
stage's own `run_*` call. This orchestrator does not intercept, batch,
reorder, or alter what any invoked call does with `apply`.

## Idempotency

Running this orchestrator repeatedly against an unchanged content item
must not create duplicate artifacts, must not manufacture a new success
where none is warranted, and must not overwrite any agent's existing
history — guaranteed entirely by delegation (see "Self-review behavior"
and "Freshness and invalidation"): every invoked agent already guarantees
this for its own artifacts, and this orchestrator adds no state of its
own that could violate it.

## Golden sample

Never mutated by this orchestrator or any test — the golden sample's
`CONTENT_ITEM.md status` is (and must remain) `SCRIPT`, never `APPROVED`,
so `CONTENT_APPROVAL_GATE` refuses before any production stage could ever
run `--apply` against it, exactly as every individual production agent's
own precondition already guarantees independently. See
`tests/test_integration.py`'s `test_golden_sample_never_modified`.

## CLI

```
python3 -m agents.full_pipeline.src <content-item-dir> [--apply]
```

No `--publish` flag exists, and none will ever be added to this or any
agent in this system.
