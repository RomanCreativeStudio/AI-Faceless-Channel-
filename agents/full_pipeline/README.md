# Full Pipeline Orchestrator

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7E MVP — `src/`/`tests/`
exist and are stdlib-only.

## Responsibility

Sequences all eleven agents that already exist — `agents/orchestrator/`
(itself a coordinator of `researcher`/`safety`/`originality`), then the
eight production agents in their real, verified precondition order — into
one call, stopping at the first stage that doesn't cleanly succeed. Makes
**no** review, production, or QA judgment of its own — see `CONTRACT.md`'s
"Important distinction."

```
CONTENT_REVIEW -> CONTENT_APPROVAL_GATE -> PRODUCER -> VOICE ->
VISUAL_PLANNER -> ASSETS -> ASSEMBLER -> CAPTIONS -> THUMBNAIL ->
PRODUCTION_QA -> (human) HUMAN_REVIEW
```

## The two-phase shape

Because only a human may ever set `CONTENT_ITEM.md status = APPROVED`,
this orchestrator cannot itself bridge `CONTENT_REVIEW` into production —
a clean content-review pass with the item still not `APPROVED` is reported
as `pipeline_status = PASS`, `human_action_required = True`, naming the
approval gate. Once a human approves, the same call proceeds straight
through to `PRODUCTION_QA`.

## Self-review — what it actually is

**No agent in this codebase can autonomously fix a `REVISION_REQUIRED`,
`BLOCKED`, or stale result.** Every production agent's own contract
documents "no versioned supersession"; the three review agents can only
"fix and create the next attempt" if *something upstream actually
changed* — nothing in this phase implements the fixing half. So this
orchestrator never loops in-process; it runs each stage's real `run_*`
exactly once per call (`MAX_STAGE_ATTEMPTS = 1`) and reports
`human_action_required` the moment anything doesn't cleanly pass.

"Self-review" instead means: **call `run_full_pipeline` again, later,
after something actually changed** (a human edit, a future agent). Every
stage's own freshness/precondition check — never new code in this
orchestrator — then determines exactly which stages are already
satisfied (skipped for free) and which need to re-run, fully scoped to
what actually depends on the change. See `CONTRACT.md`'s "Freshness and
invalidation" and "Self-review behavior" for the full reasoning, and
`tests/test_integration.py`'s downstream-invalidation test for proof.

## Result model

`PipelineResult` (`src/models.py`) carries: `pipeline_status` (`PASS` /
`REVISION_REQUIRED` / `BLOCKED` / `ESCALATE_TO_HUMAN` / `SYSTEM_ERROR` /
`COMPLETE`), `current_stage`, `completed_stages`, `skipped_stages`,
`blocked_stages`, `failed_stages`, `escalated_stages`,
`revision_requests` (stage -> reasons), `attempt_counts`,
`stale_artifacts`, `human_action_required`/`human_action_reason`,
`terminal_reason`, and `stage_results` (per-stage `StageRunOutcome`,
carrying the real underlying agent result for detailed inspection).

## Stage adapters

Every production-stage result shares one shape (`aborted`, `blocked`,
`stale`, `already_up_to_date`, a `produced`/`planned` property, `reasons`)
— `src/stages.py`'s `normalize_standard_result` reads it generically for
all eight production agents. `agents/production_qa/`'s result is
verdict-shaped instead (`PASS`/`REVISION_REQUIRED`/`BLOCKED`/
`SYSTEM_ERROR` directly) and gets its own small `normalize_qa_result`.
`CONTENT_REVIEW` reuses `agents.orchestrator.src.pipeline.run_automated_review`
wholesale — its own three-stage sequencing, freshness checking, and
two-consecutive-attempts gating are never reimplemented here.

## Write boundary

**None.** This orchestrator has no `mutate.py`, matching
`agents/orchestrator/`'s own precedent exactly. Every write under
`--apply` happens inside an invoked agent's own existing, already-tested
path. `PipelineResult` is in-memory/CLI-output coordination metadata only
— never persisted to disk.

## Relationship to other agents

Imports and calls `agents.orchestrator.src.pipeline.run_automated_review`
and every production agent's real `run_*` entry point directly — never
reimplements any of their algorithms, hashing, or write paths. Reuses
`agents.researcher.src.loader.load_content_item` for the read-only
approval-gate check (already-generic infrastructure, not new domain
logic). No agent requires this orchestrator to exist; each remains fully
usable standalone, exactly as before this phase.

## Running it

```
python3 -m agents.full_pipeline.src <content-item-dir> [--apply]
```

```
python3 -m unittest discover -s agents/full_pipeline/tests -t .
```

## Known limitations

- No in-process retry loop — see "Self-review — what it actually is."
  This is a deliberate architectural finding, not an oversight: looping
  with unchanged inputs would either no-op or actively burn down a review
  agent's two-consecutive-attempts budget for no benefit.
- No new persisted artifact type — a full pipeline run's result is never
  written to disk by this orchestrator; only the underlying agents'
  existing outputs are.
- Production stages allow exactly one attempt per call
  (`MAX_STAGE_ATTEMPTS = 1`) — permanent, not a placeholder, since no
  production agent has autonomous-fix authority this phase.
- Inherits every underlying agent's own documented limitations
  unchanged (no real TTS/rendering/image-generation, `RETRIEVED`-strategy
  assets can never pass Production QA this phase, no versioned
  supersession, etc. — see each agent's own README.md).
