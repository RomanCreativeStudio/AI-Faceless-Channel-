# Contract: Unified Automated Review Orchestrator

Specification for the fourth piece of Phase 6, distinct in kind from the
three review agents: it makes no editorial, safety, or originality
judgment of its own. It coordinates `agents/researcher/`,
`agents/safety/`, and `agents/originality/` — nothing more.

This contract is subordinate to `CONSTITUTION.md` and to each reviewer's
own contract (`agents/researcher/CONTRACT.md`, `agents/safety/CONTRACT.md`,
`agents/originality/CONTRACT.md`). It does not restate what those agents
decide or how — see `agents/README.md` for the shared interface those
contracts already establish. Where anything below could be read as
expanding an individual agent's authority, that agent's own contract
wins.

## Important distinction

**The orchestrator does not decide whether content is safe, factual, or
original. The individual agents decide that. The orchestrator only
coordinates** — it runs the existing reviewers in order, stops at the
first one that doesn't cleanly PASS, and aggregates their already-
structured results into one report. It contains no evidence evaluation,
no signal detection, no verdict-deriving logic of its own.

## Pipeline

```
CONTENT ITEM
  -> FACT_CHECK        (agents/researcher, run_fact_check)
  -> SAFETY_REVIEW      (agents/safety, run_safety_review)
  -> ORIGINALITY_REVIEW  (agents/originality, run_originality_review)
  -> AUTOMATED REVIEW COMPLETE
  -> HUMAN REVIEW
```

`HUMAN REVIEW` is not executed by this orchestrator or any agent — it is
the human-driven pipeline stage that follows a clean
`AUTOMATED_REVIEW_COMPLETE`. The orchestrator never touches the content
item's `status` field, so it never actually advances anything to
`HUMAN_REVIEW` — that remains a human/owner-approval-gated action exactly
as `CONSTITUTION.md` rule 1 and every individual agent contract already
require.

## Execution rules

1. Stages run in this exact order, always: `FACT_CHECK` → `SAFETY_REVIEW`
   → `ORIGINALITY_REVIEW`.
2. A stage must return `PASS` (and not be `blocked` by its own multi-pass
   gating, and not set `escalate_to_human`) before the next stage runs.
3. `REVISION_REQUIRED` → stop; no later stage runs.
4. `REJECT` → stop immediately; no later stage runs.
5. `escalate_to_human = true` on any stage → stop immediately, regardless
   of that stage's verdict.
6. A later stage can never override, soften, or hide an earlier stage's
   failure. If `FACT_CHECK = REVISION_REQUIRED`, `SAFETY_REVIEW` and
   `ORIGINALITY_REVIEW` are `NOT RUN` — the result says so explicitly via
   `stages_skipped`, never by omission.
7. A missing/unloadable content item or a crashing reviewer is a
   **system error**, categorically different from a review verdict — see
   "Error handling."

## Result model

`OrchestratorResult` (see `src/models.py`) carries at minimum:

| Field | Meaning |
|---|---|
| `content_id` | From whichever stage first successfully loaded the item |
| `overall_result` | `PASS` / `REVISION_REQUIRED` / `REJECT` / `HUMAN_ESCALATION` / `SYSTEM_ERROR` |
| `pipeline_status` | `AUTOMATED_REVIEW_COMPLETE` / `BLOCKED_AT_<STAGE>` / `SYSTEM_ERROR` |
| `stages_executed` | Stages actually invoked (including one that errored) |
| `stages_skipped` | Stages never invoked because an earlier one stopped the pipeline |
| `stage_results` | Per-stage `StageOutcome`, keyed by stage name, for every executed stage |
| `first_blocking_stage` | Name of the first stage that wasn't a clean PASS, or `None` |
| `blocking_reason` | Why that stage blocked, in plain text |
| `human_escalation` | `True` whenever any stage flagged it — tracked independently of `overall_result`, never hidden even when `overall_result` is labeled `REJECT` |
| `apply` | Whether this run was in apply mode |
| `timestamp` | When this orchestration run happened |

### `overall_result` derivation (no new interpretation of a reviewer's own verdict)

Only the blocking stage (the first non-PASS one) determines
`overall_result`; every reviewer verdict keeps its existing meaning from
`templates/REVIEW.md`:

1. Any stage failed to load / a reviewer raised an exception →
   `SYSTEM_ERROR`.
2. All three stages `PASS` → `PASS`.
3. The blocking stage's verdict is `REJECT` → `REJECT` (this label wins
   even though such a stage also always sets `escalate_to_human = true`
   — the flag stays visible in `human_escalation` regardless).
4. The blocking stage set `escalate_to_human = true` (and isn't a
   `REJECT`) → `HUMAN_ESCALATION`.
5. Otherwise (a plain `REVISION_REQUIRED` with no escalation flagged) →
   `REVISION_REQUIRED`.

`SYSTEM_ERROR` is the one addition beyond the four review-outcome
categories the task requires — justified because it is not a reviewer
verdict at all, it's an infrastructure-failure category (see "Error
handling"). No other new outcome category exists.

## What the orchestrator must NOT do

- Modify a claim, its classification, or `research/*.md` evidence.
- Modify any reviewer's findings, verdict, or `REVIEW.md` file.
- Modify `Owner approval state`, `status`, or `Publication state`.
- Override, soften, or reinterpret a reviewer's result.
- Invent reasons not produced by the reviewer itself.
- Convert a `REVISION_REQUIRED`/`REJECT`/escalation into a `PASS`.
- Publish anything, anywhere, under any condition.
- Gain any write authority beyond what invoking the three existing
  agents already grants them individually. **The orchestrator has no
  `mutate.py` and no field whitelist of its own** — every mutation that
  happens under `apply=True` is performed by the invoked agent through
  its own existing, already-tested write path (`Fact-check state`,
  `Safety state`, or `Originality state`, each written only by its owner).

## Apply / dry-run

Same convention as all three agents: dry run by default, `apply=True` is
explicit and opt-in. `apply` is passed straight through to whichever
stage's `run_*` function is invoked — the orchestrator does not
intercept, batch, or alter what that call does. If a stage is blocked by
its own multi-pass gating (a prior `REJECT` not reopened, or two
consecutive `REVISION_REQUIRED`s), that agent's own `run_*` already
returns `blocked=True` and writes nothing — the orchestrator surfaces
that, it doesn't work around it.

## Idempotency

Running the orchestrator repeatedly against an unchanged content item
must not create duplicate review attempts, must not manufacture a new
`PASS` where none is warranted, must not clear a `REJECT`, and must not
overwrite review history. Before invoking a stage, the orchestrator
checks whether that stage's *latest* attempt is already `PASS` **and**
its stored `Reviewed content hash` still matches the content's current
hash (recomputed via that agent's own hashing function). If so, the
stage is treated as already satisfied and its `run_*` is not invoked at
all this call (`reused_existing_pass = True`, `executed = False`) — no
new attempt file is written even under `apply=True`. If the content
changed since that `PASS` (hash mismatch), the check reports "not fresh"
and the stage runs for real, producing a new numbered attempt exactly as
that agent's own `Multi-pass resolution` rules already require. See
`src/freshness.py`.

This reuse check runs regardless of `apply`, since it's a read-only
comparison — a dry run correctly reports `reused_existing_pass = True`
too when applicable, it just still writes nothing.

## Error handling

Distinguished explicitly, per stage:

- **Review result** (normal): the stage ran and returned a verdict —
  `PASS`, `REVISION_REQUIRED`, or `REJECT`. Not an error.
- **System error**: the stage's content couldn't be loaded at all (e.g.
  no `SCRIPT.md` yet — the stage's own `aborted=True` path), or the
  stage's `run_*` function raised an exception. Recorded as
  `system_error=True` on that stage's outcome, and `overall_result` is
  forced to `SYSTEM_ERROR` — **never** silently treated as `PASS`, and
  the pipeline stops there (later stages are skipped, not attempted).

A reviewer's own crash is caught at the orchestrator boundary (one
`try/except` around each stage invocation) specifically so it can be
reported as a system error rather than propagating as an unhandled
exception or, worse, being misread as a clean pass by a naive caller
that only checks "did it raise."

## Failure conditions

- No `CONTENT_ITEM.md` under the given root → `SYSTEM_ERROR` at
  `FACT_CHECK` (the first stage to attempt loading it).
- Any stage's own structural failure (e.g. `SCRIPT.md` cites a claim ID
  with no file) → that stage returns its own `REJECT` per its contract;
  the orchestrator reports `overall_result = REJECT`, not a system error
  — a structural failure inside an agent is that agent's own reviewable
  outcome, not an orchestrator-level fault.

## Relationship to the three review agents

The orchestrator imports and calls `agents.researcher.src.pipeline
.run_fact_check`, `agents.safety.src.pipeline.run_safety_review`, and
`agents.originality.src.pipeline.run_originality_review` directly — it
does not reimplement any part of what they do. It also reuses each
agent's own hashing function (for the freshness check) and
`agents.researcher.src.loader.load_reviews`/`.models.ReviewVerdict`
(already generic, used by all three agents). See `README.md`'s module
map for the exact reuse list. Each of the three agents remains fully
usable with the orchestrator entirely absent, exactly as before this
phase.
