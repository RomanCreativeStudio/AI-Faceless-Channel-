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

**No *production* agent in this codebase can autonomously fix a
`REVISION_REQUIRED`, `BLOCKED`, or stale result.** Every production
agent's own contract documents "no versioned supersession." So this
orchestrator invokes every stage's real `run_*` at most once per call
(`MAX_STAGE_ATTEMPTS = 1`) and reports `human_action_required` the moment
anything doesn't cleanly pass — with **one exception, added Phase 7F**:
when `CONTENT_REVIEW` fails specifically at `FACT_CHECK`, this
orchestrator invokes `agents/researcher/`'s Autonomous Revision Mode,
which can genuinely close a real, already-existing evidence gap and
create a corrected successor claim (never inventing anything — see
`agents/researcher/CONTRACT.md`'s "Evidence requirements"). If that
produces a fix, one more `FACT_CHECKER` attempt runs against the
successor, and — only if that reaches `PASS` — the whole content-review
chain re-runs once more so `SAFETY_REVIEW`/`ORIGINALITY_REVIEW` get their
turn. This is still bounded, still not a loop: it is governed entirely by
`agents/researcher/`'s own existing two-consecutive-attempts gate, not a
new counter here.

For every other stage, "self-review" still means: **call
`run_full_pipeline` again, later, after something actually changed** (a
human edit, a future agent). Every stage's own freshness/precondition
check — never new code in this orchestrator — then determines exactly
which stages are already satisfied (skipped for free) and which need to
re-run, fully scoped to what actually depends on the change. See
`CONTRACT.md`'s "Freshness and invalidation" and "Self-review behavior"
for the full reasoning, and `tests/test_integration.py`'s
downstream-invalidation test for proof.

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
logic). Also calls `agents.researcher.src.pipeline.run_fact_check` and
`agents.researcher.src.revision.run_autonomous_revision` directly (Phase
7F) for the one bounded revision-and-recheck extension described above —
never reimplements either. No agent requires this orchestrator to exist;
each remains fully usable standalone, exactly as before this phase.

## Running it

```
python3 -m agents.full_pipeline.src <content-item-dir> [--apply]
```

```
python3 -m unittest discover -s agents/full_pipeline/tests -t .
```

## Known limitations

- No in-process retry loop for production stages, `SAFETY_REVIEW`, or
  `ORIGINALITY_REVIEW` — see "Self-review — what it actually is." This is
  a deliberate architectural finding, not an oversight: looping with
  unchanged inputs would either no-op or actively burn down a review
  agent's two-consecutive-attempts budget for no benefit.
- Autonomous revision (Phase 7F) only ever applies to `FACT_CHECK`, and
  only ever closes a real, already-existing evidence-linkage gap — never
  a wording or classification correction, and never anything for
  `SAFETY_REVIEW`/`ORIGINALITY_REVIEW`. See
  `agents/researcher/CONTRACT.md`'s "Autonomous Revision Mode".
- No new persisted artifact type — a full pipeline run's result is never
  written to disk by this orchestrator; only the underlying agents'
  existing outputs are.
- Production stages allow exactly one attempt per call
  (`MAX_STAGE_ATTEMPTS = 1`) — permanent, not a placeholder, since no
  production agent has autonomous-fix authority this phase.
- Inherits every underlying agent's own documented limitations
  unchanged (no real TTS/rendering/image-generation, `RETRIEVED`-strategy
  assets can never pass Production QA this phase, no versioned
  supersession for production artifacts, etc. — see each agent's own
  README.md).
