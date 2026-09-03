# Project State

Last updated: 2026-09-03

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE** (unchanged).
**Phase 7C-1 — Voice Generation MVP — COMPLETE** (unchanged).
**Phase 7C-2 — Asset Generation / Retrieval MVP — COMPLETE** (unchanged).
**Phase 7D — Video Assembly + Captions + Thumbnail + Production QA — COMPLETE** (unchanged).
**Phase 7E — Full Pipeline Orchestration + Self-Review Loop — COMPLETE.**

## Completed (Phase 7E)

**Step 1 — Inspection:** re-read `CONSTITUTION.md`, `SYSTEM.md`,
`STATE.md`, `agents/README.md`, every existing agent's `CONTRACT.md`, and
`templates/CONTENT_ITEM.md`/`PRODUCTION.md`/`REVIEW.md`/`PRODUCTION_QA.md`
before writing any code — verified the actual repository rather than
relying on memory, per the task's explicit instruction. Read every
production agent's `src/pipeline.py` and `src/models.py` in full to
confirm the real result-shape convention (`aborted`/`blocked`/`stale`/
`already_up_to_date`, a `produced`/`planned` success property, `reasons`)
before designing a single normalizer for all eight, rather than guessing
from the Phase 7D summary.

**Step 2 — Full Pipeline Orchestrator MVP** (`agents/full_pipeline/src/`):
- `models.py` — stage name constants in the real, verified execution
  order (`CONTENT_REVIEW → CONTENT_APPROVAL_GATE → PRODUCER → VOICE →
  VISUAL_PLANNER → ASSETS → ASSEMBLER → CAPTIONS → THUMBNAIL →
  PRODUCTION_QA`); the six `pipeline_status` values the task requires
  (`PASS`/`REVISION_REQUIRED`/`BLOCKED`/`ESCALATE_TO_HUMAN`/
  `SYSTEM_ERROR`/`COMPLETE`); `MAX_STAGE_ATTEMPTS = 1` (documented as
  permanent, not a placeholder — see "Genuine finding" below);
  `StageRunOutcome` (per-stage normalized result, carrying the real
  underlying agent result for detailed inspection); `PipelineResult`
  (`completed_stages`/`skipped_stages`/`blocked_stages`/`failed_stages`/
  `escalated_stages`/`revision_requests`/`attempt_counts`/
  `stale_artifacts`/`human_action_required`+`reason`/`terminal_reason`/
  `stage_results` — every field the task's Section 2 requires).
- `stages.py` — `normalize_standard_result(result, apply)`: reads the one
  shared result shape every production agent except `production_qa`
  uses, generically, once, for all seven of those agents rather than
  duplicated per agent (`apply` matters because a dry-run success
  legitimately reports `produced=False` by every agent's own design — see
  "Errors and fixes" below); `normalize_qa_result(result, apply)`: reads
  `agents/production_qa/`'s verdict-shaped result instead. Eight
  `ProductionStageAdapter`s, each wiring one agent's real `run_*` entry
  point directly — zero reimplementation of any agent's algorithm,
  hashing, or write path.
- `status_sequence.py` — `PRODUCTION_STATUS_SEQUENCE` (verbatim from
  `templates/PRODUCTION.md`) and `STAGE_COMPLETION_STATUS` (the status
  value each stage's own success sets, read from each agent's own
  `pipeline.py`, never guessed) — enables
  `stage_already_completed_by_a_later_stage`, the fix for a real
  idempotency bug found this phase (see "Errors and fixes").
- `pipeline.py` (`run_full_pipeline(root, apply=False,
  originality_channel_index=None, originality_reference_paths=None)`) —
  the one entry point. Calls `agents.orchestrator.src.pipeline
  .run_automated_review` directly for `CONTENT_REVIEW` (never
  reimplementing its three-stage sequencing, freshness checking, or
  two-consecutive-attempts gating); maps its `OverallResult` to this
  orchestrator's own outcome vocabulary via one small translation table,
  not a new interpretation of what any reviewer's verdict means; performs
  a read-only `CONTENT_APPROVAL_GATE` check
  (`agents.researcher.src.loader.load_content_item`, already-generic
  infrastructure); then walks the eight production adapters in order,
  skipping a stage the status-sequence check finds already superseded,
  invoking every other stage exactly once and stopping at the first
  non-`PASS` outcome. No stage is ever invoked twice in one call.
- `__main__.py` — CLI (`python -m agents.full_pipeline.src <dir>
  [--apply]`), prints a deterministic JSON result. No `--publish` flag;
  none will ever be added.
- **No `mutate.py` exists for this agent** — matching
  `agents/orchestrator/`'s own precedent exactly. Every write under
  `apply=True` happens inside an invoked agent's own existing,
  already-tested path.
- 34 tests (`agents/full_pipeline/tests/`) across 8 files, covering all
  12 required scenarios from the task plus general robustness (dry-run/
  apply behavior, write-boundary/no-mutate proof, CLI JSON output) — see
  "Validation performed" for the full breakdown.

**Step 3 — Documentation:** `agents/full_pipeline/CONTRACT.md`/`README.md`
(new); `SYSTEM.md`, `README.md` (root), `agents/README.md`, `STATE.md`
(this file) — all updated.

## Errors and fixes (this phase)

1. **Dry-run success was misclassified as `SYSTEM_ERROR`.** Every
   production agent's `produced`/`planned` success property is only ever
   `True` once `apply=True` actually wrote something (e.g.
   `agents/producer/src/models.py`'s `produced` property is
   `bool(self.production_path)`, and `production_path` stays `""` on a
   dry run even when nothing failed). `normalize_standard_result`
   initially had no way to distinguish "dry run, would have succeeded"
   from "nothing happened, something's wrong," and fell through to
   `SYSTEM_ERROR` for every dry-run success. **Found** via a test
   asserting a full dry-run chain reaches `COMPLETE`. **Fixed** by
   passing `apply` into the normalizer: once every failure/staleness
   check has cleared and `apply` is `False`, a `produced=False` result is
   correctly a `PASS`, not an anomaly. Re-verified: a dry run immediately
   following a real `apply=True` run now correctly reaches `COMPLETE`
   with zero file changes (`test_dry_run_after_apply_is_side_effect_free`).
2. **A first-time dry run against a completely fresh item cannot reach
   `COMPLETE` — this is correct dry-run semantics, not a bug, and the
   original test's assumption was wrong.** A dry run never writes
   `PRODUCTION.md`, so a downstream stage invoked in the *same* dry run
   genuinely has nothing to read yet and correctly reports
   `SYSTEM_ERROR`/`BLOCKED` (every single agent has this identical
   limitation standalone). **Fixed** by correcting the test's expectation
   rather than the orchestrator: a fresh dry run is only meaningfully
   validated one stage at a time; the useful, tested dry-run guarantee is
   "a dry run after real artifacts already exist changes nothing," not
   "a dry run simulates an entire multi-artifact chain end to end."
3. **A real idempotency bug: re-invoking the pipeline after production
   already advanced past a stage produced a false `BLOCKED`.** Each
   production agent's own `ALLOWED_PRODUCTION_STATUSES` accepts only its
   own narrow re-entry window (e.g. `agents/voice/`'s is exactly
   `{PRODUCTION_PLANNING, VISUAL_PLANNING}`) — correct and sufficient for
   that agent standalone, but this orchestrator calls *every* stage on
   *every* invocation (it keeps no state of its own between calls — see
   "Genuine finding" below for why). Once a later stage genuinely
   advanced `Production status` past an earlier one (e.g. all the way to
   `HUMAN_REVIEW`), re-invoking that earlier stage hit its own
   precondition gate and reported a false `BLOCKED`, even though nothing
   was actually wrong. **Found** via a smoke test calling
   `run_full_pipeline` a third time against an already-`COMPLETE` item —
   `VOICE` came back `BLOCKED` with `"Production status is 'HUMAN_REVIEW'
   ... require ['PRODUCTION_PLANNING', 'VISUAL_PLANNING']"`. **Fixed** by
   adding `status_sequence.py`: before invoking a stage, this
   orchestrator reads (never writes) `PRODUCTION.md`'s current
   `Production status` and compares it against the canonical sequence
   `templates/PRODUCTION.md` already documents (not a new, competing
   source of truth — the same one every agent's own precondition already
   derives from). A stage is skipped, reported as an implicit `PASS`
   ("a later stage already completed this one's job"), only when the
   current status has moved *strictly past* that stage's own completion
   status — never when it merely equals that stage's own accepted
   re-entry window, which stays governed entirely by that agent's own
   logic. Re-verified: a third consecutive call against an already-
   `COMPLETE` item now correctly reports `COMPLETE` again, with every
   already-superseded stage marked `executed=False` and only
   `PRODUCTION_QA` genuinely re-invoked.

Every other module (`models.py`, `stages.py`'s QA normalizer,
`pipeline.py`'s `CONTENT_REVIEW`/`CONTENT_APPROVAL_GATE` handling) passed
its own tests on the first run.

## Genuine finding

**No agent in this codebase — none of the twelve coordinated by
`agents/full_pipeline/` — has authority to autonomously regenerate,
overwrite, or fix an existing artifact once written.** Verified against
every agent's actual `CONTRACT.md` before writing any orchestration code,
not assumed from the task's own description of what a "self-review loop"
should do. Every production agent's own contract documents "no versioned
supersession": a stale or QA-failing artifact is reported and left
untouched, permanently, until a human (or a not-yet-built future agent)
changes the underlying input out of band. `templates/REVIEW.md` rule 5
permits a review agent to "fix and create the next attempt" autonomously
for `REVISION_REQUIRED` — but nothing in `agents/researcher/`,
`agents/safety/`, or `agents/originality/` implements the *fixing* half
of that (no `RESEARCH`-mode implementation exists this phase, per
`SYSTEM.md`'s own "Out of scope"); only a human editing `SCRIPT.md`/
`claims/` and re-invoking the same stage constitutes a fix today.

This makes the task's literal "self-review loop" steps 4-7 (perform the
permitted revision, re-run the affected stage, re-run downstream stages,
run Production QA again) a **provable no-op within a single call** — an
in-process retry with unchanged inputs either wastes a call
(production stages, whose own precondition would report the identical
unresolved issue) or actively harms the system (content-review stages,
where a bare re-invocation with nothing fixed would create a second,
identical-verdict review attempt purely to burn down the
two-consecutive-attempts budget faster, for zero benefit). So
`agents/full_pipeline/` deliberately never loops in-process
(`MAX_STAGE_ATTEMPTS = 1`, enforced, not a placeholder). "Self-review"
instead means: **call `run_full_pipeline` again, later, after something
actually changed.** Because every stage's own freshness/precondition
check is already fully general and reused unmodified, this correctly and
automatically re-runs exactly the affected stage and every downstream
stage whose dependency changed — with zero new invalidation code — while
leaving every unrelated, still-fresh artifact untouched. Proven via
`agents/full_pipeline/tests/test_self_review.py`'s
`test_pipeline_resumes_after_fix_applied_between_calls` (fixes a
`REVISION_REQUIRED` fact-check between two separate calls; the second
call resumes correctly) and
`test_staleness_and_invalidation.py`'s downstream-invalidation tests.

A related, secondary finding, discovered while building the idempotency
fix above: **`agents/safety/`'s and `agents/originality/`'s own
`Reviewed content hash` includes `CONTENT_ITEM.md`'s full raw text**
(the docstring in `agents/safety/src/hashing.py` says "Identity table
text," but the code hashes `bundle.content_item.raw_text` — the whole
file), and **both agents append a Notes/history log entry to
`CONTENT_ITEM.md` as part of the very `apply` call that computed that
hash.** The result: their own just-recorded `PASS` is immediately stale
relative to the note they just appended, so every repeat invocation
regenerates a fresh (still correct, never fabricated) review attempt —
`reviews/safety_reviewer-*.md` and `reviews/originality_reviewer-*.md`
grow by one on every `apply=True` call, unlike `reviews/fact_checker-*.md`
(whose hash does not include `CONTENT_ITEM.md`, so it stays genuinely
stable). This is a pre-existing characteristic of those two agents, not
introduced by this orchestrator, and fixing it is out of this phase's
scope (touching another agent's own hashing/write path is exactly the
sibling-agent boundary this project has maintained since Phase 6). Noted
here, and in `agents/full_pipeline/tests/test_staleness_and_invalidation.py`'s
own test docstring, as an honest observation rather than something
silently routed around.

## A near-miss caught during validation

While writing `agents/full_pipeline/tests/test_integration.py`'s golden-
sample test, an early draft called `run_full_pipeline(GOLDEN_SAMPLE,
apply=True)` — content review is legitimately allowed to write against
non-`APPROVED` content (that's how `agents/researcher/`/`safety/`/
`originality/` are designed to work), so this call genuinely created
`reviews/*.md` files and updated the golden sample's own `CONTENT_ITEM.md`
`Fact-check state` field. **This was caught immediately via `git status
--short -- content/` before committing anything**, and reverted in full
(`git checkout -- content/.../CONTENT_ITEM.md`; `rm -rf
content/.../reviews/`), confirmed clean via a second `git status` check.
The test was then corrected to use `apply=False` — matching
`agents/orchestrator/tests/test_integration.py`'s own established
convention for this exact reason — which still proves the same
zero-mutation guarantee without ever risking a real write. This is
exactly the kind of check-before-you-commit discipline this project's
own constraints require, recorded here rather than left implicit.

## Validation performed

1. `agents/full_pipeline/tests/` — 34/34 pass, covering all 12 required
   scenarios: (1) clean all-pass pipeline reaching `COMPLETE` with every
   artifact produced; (2) safety escalation (impersonation, `HIGH_RISK`)
   stops before any production stage runs; (3) originality escalation
   (ambiguous similarity, `REVIEW_REQUIRED`) likewise; (4) a directly-
   corrupted voice hash is caught (by Production QA's own independent
   re-check, since `VOICE` is correctly skipped once superseded — see
   "Errors and fixes" #3); (5) a directly-corrupted asset hash likewise;
   (6) a genuine Production QA failure (the honest `RETRIEVED`-strategy
   limitation, not fabricated) reported as `REVISION_REQUIRED` with every
   earlier stage still marked complete; (7) the pipeline resumes
   correctly after a real fix is applied between two separate calls; (8)
   two consecutive `REVISION_REQUIRED` verdicts hit the underlying
   agent's own two-consecutive-attempts limit and escalate; (9) human
   escalation is always named explicitly (`human_action_required` +
   `human_action_reason` citing the exact stage); (10) missing/malformed
   content and a structurally-broken `CONTENT_ITEM.md` both produce
   `SYSTEM_ERROR`, never a false `PASS`; (11) a `SCRIPT.md` change is
   caught at the earliest possible point (`PRODUCER`), with every later
   stage correctly skipped and an unrelated asset edit never touching
   voice or fact-check history; (12) no publishing identifier
   (`upload`/`publish`/`post_video`/`youtube`/`schedule_publish`) exists
   anywhere in `agents/full_pipeline/src/` (AST-checked), no `--publish`
   CLI flag, no `mutate.py` at all, and a `COMPLETE` run never sets
   `Production status` beyond `HUMAN_REVIEW` or `CONTENT_ITEM.md`'s
   `status` to `PUBLISHED`.
2. Additional coverage beyond the 12 required scenarios: dry-run-before-
   any-apply behavior (correctly limited, per finding #2 above);
   dry-run-after-apply is fully side-effect-free; `apply` never touches
   `claims/*.md`, `PRODUCTION.md`'s `Human review state`, or
   `CONTENT_ITEM.md`'s `status` itself; `MAX_STAGE_ATTEMPTS` is exactly
   `1` and enforced; a production-stage `REVISION_REQUIRED` is never
   silently converted into a `PASS` on a bare re-run; the CLI prints
   valid, complete JSON and defaults to dry-run.
3. Combined suite — `python3 -m unittest discover -s agents -t . -p
   "test_*.py"` — **357/357 pass, 0 regressions** (323 pre-existing + 34
   Full Pipeline Orchestrator).
4. Every agent's own suite re-run individually and green: researcher 43,
   safety 27, originality 31, orchestrator 30, producer 20, voice 33,
   visual_planner 18, assets 45, assembler 21, captions 17, thumbnail 13,
   production_qa 25, full_pipeline 34.
5. Golden-sample safety: `git status --short -- content/` confirmed empty
   after the full suite; `agents/full_pipeline/tests/test_integration.py`'s
   `test_golden_sample_never_modified` runs a **dry-run-only**
   `run_full_pipeline` against the real golden sample (matching
   `agents/orchestrator/tests/`'s own established convention exactly,
   for the reason recorded in "A near-miss caught during validation"
   above) and confirms zero byte-level changes.
6. No publishing capability anywhere: AST-based scan across
   `agents/full_pipeline/src/` (checking for `upload`/`publish`/
   `post_video`/`youtube`/`schedule_publish` identifiers), confirmation
   that no `--publish` CLI flag exists and no `mutate.py` file exists at
   all, and a behavioral test confirming a full, genuine `COMPLETE` run
   never sets `Production status` beyond `HUMAN_REVIEW`.
7. Manual CLI smoke tests of the full 9-invocation sequence (content
   review pass → simulated human approval → full production run reaching
   `COMPLETE`; a third repeat call confirming idempotency; corrupted-hash
   and `SCRIPT.md`-edit scenarios) against fresh isolated fixtures before
   any test file was written, to validate the design empirically first.

## Known limitations

- No in-process self-fix/retry loop — a deliberate, verified
  architectural finding (see "Genuine finding" above), not a missing
  feature. `MAX_STAGE_ATTEMPTS = 1` is permanent.
- No new persisted artifact type — a full pipeline run's result
  (`PipelineResult`) is never written to disk by this orchestrator; only
  the twelve underlying agents' own existing outputs are.
- `agents/safety/`'s and `agents/originality/`'s own review-attempt
  counts grow by one on every repeat `apply=True` invocation, even with
  nothing substantively changed — a pre-existing characteristic of those
  two agents (see "Errors and fixes" #3's secondary finding), not
  introduced or fixed by this orchestrator, and out of this phase's scope
  to change.
- Inherits every one of the twelve coordinated agents' own documented
  limitations unchanged: no real TTS/rendering/image-generation
  integration, `RETRIEVED`-strategy assets can never pass Production QA
  this phase, no versioned artifact supersession, no editorial-review
  agent, no RESEARCH-mode live retrieval.
- No true rollback — a human-set `CONTENT_ITEM.md status = APPROVED` is
  never automatically reverted by a later production failure; every
  downstream staleness/failure is caught and reported, but nothing in
  this system undoes an earlier human decision.
- Content-review escalation categories (`REJECT` and `HUMAN_ESCALATION`
  from `agents/orchestrator/`) are both folded into this orchestrator's
  own `ESCALATE_TO_HUMAN` outcome for simplicity, matching the task's own
  six-value vocabulary — the finer distinction between them remains fully
  visible in `stage_results[CONTENT_REVIEW].raw_result`
  (the real, unmodified `OrchestratorResult`) for anyone who needs it.

## Next task

No further phase was specified as "exact next task" by this phase's
instructions beyond delivering this report. A natural continuation, not
yet started, would be a genuine autonomous-fix capability for at least
one stage (e.g. a `RESEARCH`-mode implementation that could legitimately
let `agents/researcher/` "fix and create the next attempt" per
`templates/REVIEW.md` rule 5, rather than only re-evaluating unchanged
evidence) — but this remains explicitly unbuilt and unscoped until a
future phase names it. Publishing remains permanently human-gated per
`CONSTITUTION.md` rule 2, regardless of anything built so far.
