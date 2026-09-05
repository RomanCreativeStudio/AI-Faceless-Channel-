# Project State

Last updated: 2026-09-04

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE** (unchanged).
**Phase 7C-1 — Voice Generation MVP — COMPLETE** (unchanged).
**Phase 7C-2 — Asset Generation / Retrieval MVP — COMPLETE** (unchanged).
**Phase 7D — Video Assembly + Captions + Thumbnail + Production QA — COMPLETE** (unchanged).
**Phase 7E — Full Pipeline Orchestration + Self-Review Loop — COMPLETE** (unchanged).
**Phase 7F — Autonomous Revision Engine (Research/Fact-Check) — COMPLETE** (unchanged this phase).
**Phase 7G — Bounded Research Retrieval + Evidence Expansion — COMPLETE** (unchanged this phase).
**Phase 8 — Real Episode 1 Production — COMPLETE.**

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

## Completed (Phase 7F)

**Step 1 — Inspection:** re-read `CONSTITUTION.md`, `SYSTEM.md`,
`STATE.md`, `templates/CLAIM.md`, `templates/RESEARCH.md`,
`templates/REVIEW.md`, `agents/researcher/CONTRACT.md`/`README.md`, every
Researcher source file, `agents/orchestrator/`, and `agents/full_pipeline/`
before writing any code — verified the actual repository rather than
relying on Phase 7E's own summary. Two significant findings from this
step alone, both verified against real code, not assumed:

1. **`templates/CLAIM.md` and `agents/researcher/src/mutate.py` already
   define and test the exact supersession primitive this phase needed**
   (`supersede_claim`: creates a new claim file, appends an immutable
   trailing note to the old one, never edits the old table) — built in
   Phase 5, fully unit-tested, but never actually *invoked* by
   `run_fact_check`'s own `_apply_result`. This phase's job was to build
   the missing *diagnosis-and-invocation* layer around already-solid,
   already-tested infrastructure, not to invent supersession from
   scratch.
2. **`run_fact_check`'s `_apply_result` never writes back a per-claim
   `Fact-check status`/`Evidence`/`Confidence level`** despite
   `CONTRACT.md`'s own "Outputs" section describing this — a pre-existing
   gap, confirmed by grepping for `update_claim_field` call sites (only
   test files, never `pipeline.py`). Left unfixed for ordinary claims
   (out of this phase's stated scope — a separate, distinct feature from
   autonomous revision); this phase's own `_apply_result` extension
   writes back `Fact-check status` **only** for claims a
   `claim_substitutions` mapping actually touched (i.e., only successor
   claims this phase's own revision engine created), never widening the
   fix to every ordinary claim.

**Step 2 — Autonomous Revision contract** (`agents/researcher/CONTRACT.md`'s
new "Autonomous Revision Mode" section): defines exactly what the agent
MAY (inspect its own `FACT_CHECKER` result and existing `research/*.md`
evidence, create a new successor claim ID, preserve the original
unchanged, mark it superseded via the established pattern, cite only
already-real evidence, create one revision record per diagnosed claim,
re-verify and update the successor's own `Fact-check status`, trigger a
new `FACT_CHECKER` attempt, stop at the retry limit) and MUST NOT (edit
an old claim's wording/classification, erase evidence, fabricate a
citation/source, upgrade confidence without evidence, turn `FALSE` into
`PASS`, override a human/Safety/Originality decision, touch
`CONTENT_ITEM.md` approval, mark anything `APPROVED`/`READY_TO_PUBLISH`,
publish, or delete history) — the exact task-specified list, verified
against every downstream implementation choice rather than written
speculatively first.

**Step 3 — Revision record** (`templates/REVISION.md`, new): identity
table (Revision ID, Original/Successor claim ID, Triggering review
attempt, Reason, Original/New claim hash, Evidence used, Changes made,
Revision author/timestamp, Revision status, Verification result, Human
escalation state) plus a "What this record does NOT do" section making
the approval boundary explicit on every single record. `Revision status`
covers both outcomes — `SUCCESSOR_CREATED` and three escalation variants
(`ESCALATED_INSUFFICIENT_EVIDENCE`/`ESCALATED_CONTRADICTORY_EVIDENCE`/
`ESCALATED_ATOMICITY_VIOLATION`) — so a revision record exists and is
inspectable even when nothing could be fixed, not only on success.

**Step 4 — Revision engine** (`agents/researcher/src/revision.py`, new,
~350 lines — a narrow component, not a rewrite of the Researcher):
- `diagnose_claim(claim, bundle)` — the three-case evidence diagnosis
  (see "Evidence rules" below), mechanical and deterministic, reusing
  `atomicity.check_atomicity` directly for the fourth (structural) case.
- `_find_reciprocal_uncited_source(claim, bundle)` — Case A's exact
  mechanical detector: a `research/*.md` entry that already, reciprocally
  names this claim in its own `Related claims` field but isn't yet cited
  in the claim's own `Supporting sources`.
- `create_successor_claim(root, old_claim, reciprocal_entry, apply,
  bundle)` — builds (and, if `apply`, writes via `mutate.supersede_claim`)
  a successor whose `Exact claim`/`Classification`/`Derived from` are
  byte-identical to the predecessor's; only `Supporting sources` (gains
  the reciprocal entry) and `Confidence level` (deterministically derived
  from that entry's own `Source reliability`) change. Immediately
  re-verifies the successor via `evidence.evaluate_claim` (reused, not
  duplicated — see "Errors and fixes" #1 below for why this needed one
  small extension) and writes its `Fact-check status` back via the
  existing `mutate.update_claim_field` whitelist.
- `run_autonomous_revision(root, apply, fact_check_result)` — the
  top-level diagnosis pass: checks the latest `FACT_CHECKER` attempt is
  `REVISION_REQUIRED` (not `PASS`, not `REJECT`), reuses
  `multipass.can_run_new_attempt` for the retry gate (no second retry
  system), diagnoses every flagged `FACT` claim, creates successors for
  every `FIXABLE` one, and writes one `revisions/revision-<n>.md` per
  claim diagnosed (fixed or escalated).
- `run_fact_check_with_autonomous_revision(root, apply)` — the full
  narrow-component cycle: attempt 1 -> diagnose -> permitted successor
  creation -> attempt 2 (`run_fact_check(..., claim_substitutions=...)`).
- `mutate.write_revision_file` (new, in the existing `mutate.py`, not a
  separate module) — the one new whitelisted write path, filename-pattern
  gated (`revision-<n>.md`), fails closed with `PermissionError`
  otherwise, matching every other agent's established writer pattern.
- `hashing.compute_claim_hash` (new, in the existing `hashing.py`) —
  sha256 of one claim file's raw content, the mechanical predecessor/
  successor-immutability proof this phase's own tests rely on.

**Step 5 — Atomic successor creation:** enforced by construction, not a
separate check — a successor's `Exact claim`/`Classification` are always
copied verbatim from an already-atomic predecessor (a claim that already
fails `check_atomicity` is routed to `ESCALATED_ATOMICITY_VIOLATION`
instead and never gets a successor at all), so the successor is
trivially atomic too.

**Step 6 — Full-pipeline integration** (`agents/full_pipeline/src/pipeline.py`,
extended, only after Step 4 was independently tested and stable):
`_attempt_researcher_revision` — when `CONTENT_REVIEW` blocks specifically
at `FACT_CHECK` with `REVISION_REQUIRED`, invokes
`agents.researcher.src.revision.run_autonomous_revision` against the
attempt `agents/orchestrator/` already produced (never a redundant
re-run); if it produces at least one successor, runs one more
`FACT_CHECKER` attempt, then re-runs the whole content-review chain once
more — reusing `agents/orchestrator/`'s own freshness check to let
`SAFETY_REVIEW`/`ORIGINALITY_REVIEW` run for the first time only if
`FACT_CHECK` now genuinely passes. Never continues downstream with an
unresolved factual issue: if the retry is still `REVISION_REQUIRED` or
escalates, the pipeline reports exactly that and stops.

**Step 7 — Documentation:** `agents/researcher/CONTRACT.md` (new
"Autonomous Revision Mode" section, ~180 lines) and `README.md` (new
section); `agents/full_pipeline/CONTRACT.md`/`README.md` (Self-review
behavior, Retry/escalation policy, and Forbidden-actions sections
updated to describe the one bounded exception); `SYSTEM.md`, root
`README.md`, `agents/README.md` (all updated, including a new "Three
concepts" explainer distinguishing automated review / autonomous
revision / human approval in `SYSTEM.md`); `STATE.md` (this file).

## Errors and fixes (this phase)

1. **A successor claim's own re-verification initially, wrongly, stayed
   `UNVERIFIED`.** The reciprocal research entry a successor cites still,
   correctly, names the *predecessor*'s short id in its own `Related
   claims` field (research entries are immutable too — this agent may
   never edit them, only create new ones) — but `evidence.evaluate_claim`'s
   general-purpose reciprocal check only ever recognized the *current*
   claim's own short id, so it correctly-by-its-own-rules, but wrongly for
   this new case, reported `UNSUPPORTED`. **Found** via manual smoke
   testing (a successor with a `HIGH`-reliability source still came back
   `UNVERIFIED`). **Fixed** by adding one optional, backward-compatible
   parameter — `predecessor_short_id` — to `evidence.evaluate_claim`/
   `_evaluate_fact` and `factcheck.evaluate_all` (threaded from
   `claim_substitutions`'s reverse mapping), accepting a reciprocal match
   against either id: since the successor's `Exact claim` text is
   byte-identical to the predecessor's, a source that already, truthfully
   confirmed the predecessor's assertion is equally valid evidence for
   the successor. This single fix also let a first draft's separate,
   duplicate `_verify_successor` function in `revision.py` be deleted
   entirely — one shared implementation, not two.
2. **`_claims_needing_revision` initially read a claim's stale on-disk
   `Fact-check status` instead of the just-computed evaluation.** Because
   ordinary `FACT_CHECK` never writes that field back (see Step 1
   finding #2), an already-fine claim (already `VERIFIED`-eligible, e.g.
   the fixture's own `c_ok`) was wrongly re-diagnosed every time, since
   its file still said `UNVERIFIED`. **Found** via the dedicated
   multi-claim fixture (`tests/fixtures/revision_item/`), where `c_ok`
   incorrectly appeared in the diagnosis output. **Fixed** by changing
   `_claims_needing_revision` to take the freshly-computed
   `ClaimEvaluation` list (from the triggering `FactCheckResult`, or
   computed fresh via `factcheck.evaluate_all` if none was supplied)
   rather than trusting any on-disk field.
3. **The item-level `Reviewed content hash` initially reflected the
   substituted (successor) claim's content, breaking
   `agents/orchestrator/`'s own freshness re-check.** A first design
   computed `content_hash` from whichever claims were actually
   evaluated — correct-sounding ("hash what was reviewed"), but wrong in
   effect: `agents/orchestrator/`'s `find_fresh_pass` always recomputes
   plainly, with zero knowledge of any substitution, so it would compute
   a *different* hash (from the *original*, unsubstituted claim) and
   treat the just-written `PASS` as stale, triggering a pointless
   re-fact-check that would recreate the identical problem attempt 2 just
   solved. **Found** by reasoning through the full-pipeline integration
   design before writing it, not by a failing test. **Fixed** by always
   computing `content_hash` from the *original*, unsubstituted claim ids
   (`factcheck.claims_under_review(bundle)` with no substitutions) —
   safe and stable forever, since a superseded claim's own content never
   changes again once superseded.
4. **Three Phase-7E-era `agents/full_pipeline/tests/` fixtures
   accidentally became "Case A fixable" under this phase's own new
   capability, changing their outcome from `REVISION_REQUIRED` to
   `ESCALATE_TO_HUMAN`.** `write_claim(root, "c1",
   supporting_sources="\`N/A\`")` combined with a default `write_research(root)`
   call (which reciprocally names `c1` by default) is now a genuine,
   real, fixable evidence gap — exactly the kind of thing Phase 7F exists
   to fix, so the *new* behavior is correct, not a regression, but it
   broke three Phase 7E tests whose entire point was "nothing can fix
   this automatically." **Found** by the combined test suite going from
   391 (expected) to 388 pass / 3 fail after wiring the full-pipeline
   integration. **Fixed** by updating those three fixtures
   (`test_self_review.py`'s two tests, `test_integration.py`'s one) to
   remove the upfront `write_research` call, making the claim genuinely
   Case C (insufficient evidence — no research exists anywhere yet, the
   same shape `agents/orchestrator/tests/builders.build_fact_check_blocked_item`
   already uses) so their original intent (idempotent-safe re-invocation
   when nothing is fixable; a truly stuck item escalates after two
   attempts) is preserved and still true under Phase 7F. `test_self_review.py`'s
   own "resumes after fix" test now adds `write_research` as part of the
   simulated human fix step instead of upfront, which is a more accurate
   simulation of a real out-of-band fix besides.

Every other module (`models.py`'s new dataclasses, `mutate.py`'s
`write_revision_file`, `revision_writer.py`, the CLAIM.md template) passed
its own tests on the first run.

## A near-miss caught during validation

An early draft of the golden-sample safety test for this phase called
`run_fact_check(GOLDEN_SAMPLE, apply=True)` directly — content review is
legitimately allowed to write against non-`APPROVED` content (that's how
`agents/researcher/` is designed to work; this is not new to Phase 7F),
so this call would have genuinely created a `reviews/fact_checker-1.md`
file and updated the golden sample's own `Fact-check state` field. This
was caught *before* running it — by re-reading Phase 7E's own STATE.md
entry, which records the identical mistake being made and reverted during
that phase's own validation — and the test was written `apply=False`
from the start instead, matching `agents/orchestrator/tests/`'s and
Phase 7E's own established convention. `git status --short -- content/`
was still run after every test suite pass this phase, as a second,
independent check; it reported clean every time.

## Validation performed

1. `agents/researcher/tests/test_revision.py` (13 tests),
   `test_revision_cycle.py` (7 tests), `test_revision_write_boundary.py`
   (11 tests) — 31/31 pass, covering all 22 required test areas: valid
   successor creation, predecessor immutability, successor immutability
   (going forward — the same rules apply to it as any claim),
   revision-record creation (both `SUCCESSOR_CREATED` and escalated
   outcomes), evidence preservation, no fabricated evidence, insufficient-
   evidence escalation, contradictory-evidence handling, atomicity
   enforcement, classification handling (always retained verbatim), claim
   hash changes (successor differs, predecessor's own stays traceable to
   its pre-revision value), old hash preservation, the two-attempt limit,
   `REJECT` terminal behavior, human escalation (every unresolved case
   named explicitly), protected-field enforcement (structural
   `PermissionError`s, not just documentation, plus an AST scan of
   `revision.py` for forbidden imports/field-name string literals/
   publishing identifiers), dry-run produces no mutation, apply performs
   only whitelisted mutation (every new file under `reviews/`,
   `revisions/`, or a `claims/*_rev*.md` successor — nothing else),
   downstream stale detection (the *existing* `agents/producer/` staleness
   check, not new code, correctly fires once a human completes the loop),
   golden sample untouched, no publishing capability.
2. The task's own "important architectural test" (section 13): a
   dedicated `ArchitecturalImmutabilityProofTests` class snapshots the
   predecessor's exact bytes/hash, runs a full revision cycle, and
   asserts the predecessor's table content is still byte-identical (the
   file grows by exactly one appended, documented note — verified via
   `str.startswith`, not just inequality), the successor has a different
   ID and a different hash, and the revision record's own text contains
   both hashes — plus a direct inspection of
   `mutate.CLAIM_WRITABLE_FIELDS` itself (not just a passing happy-path
   test) confirming `Exact claim`/`Classification`/`Supporting sources`
   are absent from it.
3. `agents/full_pipeline/tests/test_researcher_revision_integration.py`
   (3 tests) — full-pipeline integration: a `REVISION_REQUIRED` at
   `FACT_CHECK` is resolved via a real successor claim and the pipeline
   proceeds to run `SAFETY_REVIEW`/`ORIGINALITY_REVIEW` for the first
   time (never skipped, never bypassed); after simulated human approval,
   the fix carries all the way through to `PRODUCTION_QA` (the very last
   stage) without being blocked anywhere revision itself resolved,
   correctly still blocking at the separate, already-documented Phase 7D
   `RETRIEVED`-strategy limitation (this fixture's claims are
   `FACT`-classified, so this is expected, not a bug); a safety-escalating
   beat alongside an otherwise-fixable fact-check issue still correctly
   escalates rather than letting revision paper over a genuine safety
   problem.
4. Combined suite — `python3 -m unittest discover -s agents -t . -p
   "test_*.py"` — **391/391 pass, 0 regressions** (357 pre-existing + 31
   Researcher revision + 3 full-pipeline revision integration).
5. Every agent's own suite re-run individually and green: researcher 74
   (43 pre-existing + 31 new), safety 27, originality 31, orchestrator 30,
   producer 20, voice 33, visual_planner 18, assets 45, assembler 21,
   captions 17, thumbnail 13, production_qa 25, full_pipeline 37 (34
   pre-existing + 3 new).
6. Golden-sample safety: `git status --short -- content/` confirmed empty
   after every test run this phase; a dedicated
   `test_golden_sample_never_modified_by_revision_engine` runs both
   `run_fact_check` and `run_autonomous_revision` against the real golden
   sample with `apply=False` (matching the established convention — see
   "A near-miss" above) and confirms zero byte-level changes, no
   `revisions/` directory created, and no `*_rev*.md` successor claim
   file anywhere under it.
7. No publishing capability: an AST-based scan of `revision.py` (checking
   for `upload`/`publish`/`post_video`/`youtube`/`schedule_publish`
   identifiers) plus a source-text scan for protected field-name string
   literals (`Production status`, `Safety state`, `Originality state`,
   `Production QA state`, `Owner approval state`, `READY_TO_PUBLISH`,
   `"APPROVED"`) — all absent, and a module-import scan confirming
   `revision.py` never imports from any sibling production/review agent's
   own module.
8. No approval bypass: a full-pipeline-level test confirms a genuine
   revision-resolved `FACT_CHECK` `PASS` never sets `CONTENT_ITEM.md`'s
   `status`, and production continuing afterward still requires the same
   human-set `APPROVED` the approval gate has always required — revision
   `PASS` is never conflated with human approval, anywhere.
9. Predecessor immutability, review-history immutability, the two-attempt
   cap, `REJECT`-remains-terminal, insufficient-evidence escalation, and
   downstream stale detection are each covered by a dedicated test (see
   items 1-3 above) — verified structurally (byte/hash comparison,
   `PermissionError` assertions), not only by a passing happy path.

## Genuine finding

**Two evidence-linkage-repair capabilities already existed as tested,
unused primitives before this phase began** (`mutate.supersede_claim`,
`mutate.update_claim_field`) — Phase 7F's actual work was building the
*diagnosis and invocation* layer that decides *when* and *how* to use
them safely, not inventing new low-level write mechanics. This is worth
recording plainly: the codebase's own established immutability/
supersession convention (`templates/CLAIM.md`'s Atomicity rule, written
in Phase 4-5) was designed with exactly this kind of future capability in
mind, and it held up completely unmodified.

**A second, narrower finding, discovered while making the successor's
own re-verification work correctly** (see "Errors and fixes" #1):
`evidence.py`'s reciprocal-evidence check is fundamentally built around
"does this exact claim id appear in the source's own declaration" — a
reasonable, sufficient rule for ordinary fact-check, but one that has no
way to express "this is the same assertion under a new id" without an
explicit extension. The `predecessor_short_id` parameter this phase added
is the minimum such extension, applied nowhere except this one revision
path (`None` everywhere else, reproducing prior behavior exactly) — but
it is a real, permanent addition to `evidence.py`'s public surface, not
purely internal to `revision.py`, and is documented as such in both
modules' docstrings.

## Known limitations

- Autonomous Revision Mode only ever closes an evidence-*linkage* gap (an
  already-existing, already-recorded, reciprocally-confirming source not
  yet cited) — it never rewords a claim, never reclassifies one, and
  never helps a claim whose problem is genuinely contradictory or wholly
  absent evidence (Cases B/C always escalate). This is intentional and
  documented, not a shortcut — see `agents/researcher/CONTRACT.md`'s
  "Evidence requirements".
- No RESEARCH-mode implementation still — this phase's revision engine
  can only re-link to research that already exists on disk; it can never
  retrieve or generate new source material. A future RESEARCH-mode
  implementation (still unbuilt, still unscoped) would make more claims
  genuinely fixable, but that is a different, larger capability than this
  phase's own deliberately narrow scope.
- No in-process retry loop, same as every other phase's agents — one
  diagnose-and-revise cycle per call; "self-review" across separate calls
  is what makes repeated invocation safe and correct.
- A revision-fixed `FACT_CHECK` `PASS` only takes effect at the
  `SCRIPT.md`/production level once a human updates `SCRIPT.md`'s
  `Verified claims` table to cite the successor — this agent never edits
  `SCRIPT.md` (Forbidden actions, unchanged from Phase 5). Until that
  happens, `agents/producer/` and everything downstream of it keep
  building from the *predecessor's* content, which is fine (it's
  unchanged and still real) but means the successor's improved evidence
  isn't yet reflected anywhere `SCRIPT.md` is read from directly.
- `agents/safety/` and `agents/originality/` still have zero autonomous-
  fix capability — this phase adds one narrow capability to
  `agents/researcher/` only, exactly as scoped ("First implementation:
  Research / Fact-Check Revision").
- The pre-existing gap found in Step 1 (ordinary `FACT_CHECK` never
  writes a claim's own `Fact-check status` back to disk, for claims that
  aren't part of a revision cycle) remains unfixed — out of this phase's
  scope, and touching it more broadly risks changing established Phase 5
  behavior no other phase's tests currently depend on.
- Inherits every agent's own previously-documented limitations unchanged
  (no real TTS/rendering/image-generation, `RETRIEVED`-strategy assets
  can never pass Production QA this phase, no versioned supersession for
  production artifacts, etc.).

## Completed (Phase 7G)

**Bounded Research Retrieval + Evidence Expansion.** Extends Autonomous
Revision Mode's Case C (`INSUFFICIENT_EVIDENCE`) — the one case Phase 7F
left as a pure escalation — with one narrow, deterministic, auditable
research operation, per this phase's own instructions: continue directly
from the current repo state, no redesign, preserve every existing
contract/safety boundary/immutable history/human approval gate/full-
pipeline behavior.

```
FACT-CHECK RESULT (REVISION_REQUIRED)
  -> REVISION DIAGNOSIS       (revision.diagnose_claim, unchanged)
  -> EXISTING-EVIDENCE REPAIR (Case A, unchanged — always tried first)
  -> BOUNDED RESEARCH         (research.run_bounded_research — Case C only)
  -> NEW RESEARCH RECORD      (research/<n>-<slug>.md, one per evaluated source)
  -> RE-DIAGNOSIS             (either now Case A-eligible, or it isn't)
  -> PASS / REVISION_REQUIRED / ESCALATE
```

**Files created:**
- `agents/researcher/src/research_provider.py` — the `ResearchProvider`
  Protocol + `ResearchQuery`/`ProviderSourceResult`/`ResearchProviderResult`
  dataclasses (mirrors `agents/voice/src/provider.py`'s established
  shape). No vendor named or assumed anywhere.
- `agents/researcher/src/source_policy.py` — deterministic, conservative
  reliability model (`check_malformed`, `evaluate_source_reliability`).
  Not a per-domain authority list; caps a provider's claimed reliability
  down using only structural signals (retrieval independently verified,
  publisher present, publication date present) — never up.
- `agents/researcher/src/test_research_provider.py` —
  `LocalTestResearchProvider` (deterministic, no network) plus factory
  functions for CONTRACT.md's six required fixture cases (A strong
  support, B contradiction, C weak/insufficient, D unverified, E
  malformed, F conflicting pair).
- `agents/researcher/src/research.py` — the provider-independent engine:
  `build_research_request`, `evaluate_provider_result`,
  `_enforce_accepted_source_limit`, `run_bounded_research` (the one entry
  point), `_apply_outcome`. Hard-coded limits in one place:
  `MAX_QUERIES_PER_CLAIM=1`, `MAX_PROVIDER_RESULTS_PER_QUERY=5`,
  `MAX_ACCEPTED_SOURCES_PER_CLAIM=2`, `MAX_RESEARCH_ATTEMPTS_PER_REVISION=1`,
  `RELIABILITY_THRESHOLD=MEDIUM`. A limit reached always means
  `ESCALATE_TO_HUMAN`, never "keep searching."
- `agents/researcher/src/research_writer.py` — renders one evaluated
  source (accepted *or* rejected) as a `RESEARCH.md`-formatted file.
- Four new test files (`agents/researcher/tests/test_source_policy.py`,
  `test_research.py`, `test_research_cycle.py`,
  `test_research_write_boundary.py`) plus
  `agents/full_pipeline/tests/test_bounded_research_integration.py` — 55
  new tests total.

**Files modified:**
- `templates/RESEARCH.md` — additive only: `Discovery status`, `Provider
  result ID`, `Retrieval verified` fields, plus `## Claim support
  relationship` and `## Rejection reason` sections. Pre-Phase-7G entries
  have no value for these and default safely (`DiscoveryStatus.ACCEPTED`,
  `RetrievalVerified.UNVERIFIED`, `ClaimSupportRelationship.NOT_APPLICABLE`).
- `agents/researcher/src/models.py` — three new enums
  (`DiscoveryStatus`, `RetrievalVerified`, `ClaimSupportRelationship`),
  five new defaulted `ResearchEntry` fields, and `RevisionCase.RESEARCH_CONFLICT`
  / `RevisionStatus.ESCALATED_RESEARCH_CONFLICT` — Case F's ("source
  disagreement") own escalation state, since neither existing
  `RevisionCase` value fit an *explicit conflict* between accepted
  sources.
- `agents/researcher/src/loader.py` — parses the five new fields,
  defaulting gracefully (try/except) for any file that predates them;
  verified directly against the real golden sample's existing research
  entries.
- `agents/researcher/src/mutate.py` — `write_research_file()`: the one
  new write path, filename-whitelisted (`^\d+-[a-z0-9][a-z0-9-]*\.md$`),
  fails closed (`PermissionError`) on any other name, refuses
  (`FileExistsError`) to overwrite — append-only, matching every other
  writer in this module exactly.
- `agents/researcher/src/revision.py` — Case C in the diagnosis loop now
  calls a new `_diagnose_with_bounded_research` helper before escalating;
  `run_autonomous_revision`/`run_fact_check_with_autonomous_revision`
  gained an optional `research_provider` parameter (defaults to `None`
  -> `research.py`'s own default). **One real, pre-existing safety gap
  this integration required fixing**: `_find_reciprocal_uncited_source`
  (Case A's detector) did not previously check a research entry's
  `Discovery status` at all — since Phase 7G now writes `REJECTED`
  entries to disk for full auditability, and those entries' `Related
  claims` field legitimately names the claim they were evaluated for, an
  unpatched detector would have treated a source this engine itself
  rejected as valid Case A evidence on a later run. Fixed by excluding
  `DiscoveryStatus.REJECTED` entries from reciprocal-evidence candidacy;
  covered by a dedicated test
  (`RejectedResearchEntryNeverTreatedAsReciprocalTests`).
- `agents/researcher/CONTRACT.md` — new "Bounded Research Mode" section
  (full flow, provider abstraction, source policy, limits, evaluation/
  verdicts, structured research record, MAY/MUST NOT lists, write
  whitelist, the six test-provider cases, human escalation conditions)
  plus an added summary bullet.
- `agents/full_pipeline/src/pipeline.py` — `research_provider` parameter
  threaded from `run_full_pipeline` through `_attempt_researcher_revision`
  to `run_autonomous_revision`, unmodified otherwise; the existing call
  site already invoked the function bounded research now lives inside,
  so no control-flow change was needed.
- Documentation: `agents/researcher/README.md`, `agents/full_pipeline/README.md`,
  `agents/README.md`, `SYSTEM.md`, root `README.md` — all updated to
  document Bounded Research Mode's scope, provider abstraction, source
  policy, limits, escalation behavior, provenance guarantees, and why
  this is not general autonomous browsing.

**Architecture / safety boundaries (unchanged, extended, never
loosened):**
- Bounded research is reachable **only** from Case C
  (`INSUFFICIENT_EVIDENCE`) — Case B (`CONTRADICTED`) never triggers a
  provider search, proven by a dedicated test tracking every query issued
  during a mixed-case revision run.
- Exactly one query per claim, built from the claim's own `Exact claim`
  text verbatim — never reworded, never broadened.
- A `SUPPORTED` verdict never creates a claim itself — it only writes a
  research record and hands off to Case A's *existing, unmodified*
  `create_successor_claim`. No second, competing claim-creation path
  exists.
- A source's reliability can only ever be capped down from a provider's
  own claim, never up; `retrieval_verified=False` always hard-caps a
  source at `UNVERIFIED` regardless of any other claimed quality.
- Every evaluated source — accepted *or* rejected — gets a written
  `research/*.md` record for full auditability; every rejected source
  carries a concrete `Rejection reason`, never `"N/A"`.
- `CONFLICT` (accepted sources both support and contradict) is an
  explicit, always-escalated verdict — never silently resolved by picking
  a side.
- No new retry counter anywhere: bounded research runs at most once per
  revision cycle by construction (one call, no loop), and that cycle is
  still governed entirely by the pre-existing two-consecutive-
  `REVISION_REQUIRED` gate.
- `REJECT` is still never autonomously reopened — bounded research is
  only reachable through `run_autonomous_revision`'s existing REJECT
  check, unchanged.
- Predecessor claims remain byte-prefix-identical after a bounded-
  research-driven revision, exactly as Phase 7F already proved for
  Case A — verified again end-to-end for the bounded-research path
  specifically.
- Dry run (`apply=False`) performs full diagnosis and verdict computation
  but writes zero files anywhere; `apply=True` writes only through
  `mutate.write_research_file`'s filename whitelist.
- No import from `agents/safety/`, `agents/originality/`, or any
  production agent's own module anywhere in `research.py` — verified by
  an AST-based test, not just documented.
- Golden sample never mutated — verified via a dedicated dry-run test
  against the real content item, and via `git status` showing zero
  `content/` changes after the full test run.

**Tests: 55 new (14 source-policy, 21 research-engine, 9 revision-
integration, 9 write-boundary/golden-sample, 2 full-pipeline
integration), all passing. Full repo suite: 446/446 passing (391 baseline
+ 55 new), zero regressions.** Includes real end-to-end fixtures (not
just helper-function tests): `test_research_cycle.py`'s
`test_full_re_fact_check_via_run_fact_check_with_autonomous_revision_reaches_pass`
(attempt 1 `REVISION_REQUIRED` with zero evidence -> bounded research
finds support -> successor claim -> attempt 2 `PASS`) and
`test_bounded_research_integration.py`'s two `run_full_pipeline` tests
(one reaching `PASS` via bounded research with a supporting provider, one
correctly still escalating with the default no-data provider).

**Known limitations:**
- No real research provider exists — `LocalTestResearchProvider` is
  permanently a deterministic, no-network test double. A real provider
  (a distinct, deliberate follow-up) would satisfy the same `Protocol`
  unchanged.
- `MAX_ACCEPTED_SOURCES_PER_CLAIM` enforcement was added during this
  phase (the constant existed in an early draft of `research.py` but
  wasn't yet wired into `run_bounded_research`) — caught and fixed before
  writing tests for it, not left as a silent gap.
- `research_writer.py` always renders `Source type` as `OTHER` — nothing
  in `ProviderSourceResult` lets this MVP determine
  `PRIMARY`/`SECONDARY`/`TERTIARY`/`EXPERT_COMMENTARY` without guessing.
- Bounded Research Mode only ever helps `FACT`-classified claims in
  exactly the same way Case A already did — it does not extend autonomous
  revision to `ASSUMPTION`/`INFERENCE`/`SPECULATION` claims, and it does
  not help a claim whose problem is wording/classification (still
  `ATOMICITY_VIOLATION`, still escalates).
- General RESEARCH mode (open-ended source collection for a whole content
  item, independent of any single claim's evidence gap) remains
  unimplemented — Bounded Research Mode is deliberately narrower and was
  never meant to substitute for it.
- Inherits every prior phase's own documented limitations unchanged.

**Genuine findings:**
1. The Case A reciprocal-evidence detector's missing `Discovery status`
   check, described above under "Files modified" — a real gap this
   integration surfaced and fixed, not a hypothetical.
2. `MAX_ACCEPTED_SOURCES_PER_CLAIM` was present as a constant before it
   was actually enforced — caught while writing the accepted-source-limit
   test, fixed immediately (`_enforce_accepted_source_limit`), not
   deferred.
3. `run_bounded_research`'s original draft accepted an unused `bundle`
   parameter (a leftover from an earlier design where the request builder
   consulted the whole `ContentBundle`); removed once nothing in the
   function actually used it, keeping the signature honest.

## Completed (Phase 8)

**Real Episode 1 Production.** Moved from "production pipeline
architecture" to "first real episode": four production agents gained a
real, non-placeholder provider, and Episode 1 ("What If Modern Medicine
Existed During the Black Death?") was produced end to end with real
audio, real visuals, a real captioned MP4, and a real thumbnail, then
manually inspected. The Learning Engine, autonomous publishing, and
unrestricted browsing were explicitly not built, per this phase's own
scope limit.

### Real provider status

| Agent | Real provider | What it actually does | Network / credentials |
|---|---|---|---|
| `agents/voice/` | `FliteVoiceProvider` (`real_provider.py`) | Real speech via ffmpeg's built-in `flite` filter | None — fully offline |
| `agents/assets/` (GENERATED) | `GeneratedAssetProviderReal` | Real, deterministic, non-photorealistic illustration (Pillow) | None — fully offline |
| `agents/assets/` (RETRIEVED) | `WikimediaCommonsRetrievalProvider` | Real image search + download, real license/provenance recorded | Public Wikimedia API, no API key |
| `agents/assembler/` | `FFmpegVideoRenderer` (`real_provider.py`) | Real H.264/AAC MP4, real captions burned in, `ffprobe`-verified playable | None — fully offline |
| `agents/thumbnail/` | `render_thumbnail_image` (`real_provider.py`, opt-in) | Real PNG rendered from the existing spec (reuses the assets illustration renderer) | None — fully offline |

No cloud/paid TTS or image-generation vendor is integrated anywhere — the
environment had no such credentials configured (checked directly, e.g.
`env | grep -i api_key`/`token` — none found beyond this platform's own
session tokens and unrelated AWS credentials, which were deliberately
**not** repurposed for a new paid service without explicit authorization
for that specific purpose). Every real provider's own CLI/test default
remains the original placeholder/test provider, unchanged.

### Renderer status

`agents/assembler/src/real_provider.py`'s `FFmpegVideoRenderer`: resolves
real narration audio and real per-scene visual assets from disk, holds
each scene's image for exactly its `templates/TIMELINE.md` duration,
concatenates (stream-copy), muxes in the real audio, burns in captions
built from `agents/captions/`'s own per-scene timings plus each scene's
timeline `start` offset (`captions_reader.py` — no `templates/CAPTIONS.md`
schema change), and independently verifies the output via `ffprobe`
before ever reporting `Playable = YES`. `VideoRenderer.render()` gained
one additive parameter (`root: Path`) for this — the placeholder renderer
ignores it.

### Episode 1 content path

`content/what-if/wi-20260904-black-death-modern-medicine-ep1/` — a real,
independent content item, never the schema/engineering golden sample at
`content/what-if/wi-20260902-black-death-modern-medicine/` (confirmed
untouched: `git status --porcelain -- content/what-if/wi-20260902-...`
returns nothing). Research (`research/`) and claims (`claims/`) are
carried over in substance from that already-reviewed fixture (only
`Claim ID`/`Content ID` fields updated); `SCRIPT.md` is a full rewrite —
the fixture's beat-level *descriptions* replaced with genuine full-
sentence spoken narration for the Hook and all six beats (7 scenes once
`agents/producer/` runs: Hook + one scene per beat), since
`agents/producer/`'s real scene-builder lifts each beat's text verbatim
into a scene's spoken narration.

### Actual output artifacts (from an isolated technical-validation copy)

Produced and manually inspected (frames extracted and viewed, audio
duration cross-checked, thumbnail viewed): a ~188s WAV narration track
(`voice/voice-01.wav`, QA `PASS`), 5 real generated illustrations + 2
scene visuals (see "Known limitations" — Wikimedia retrieval was rate-
limited during this session for those 2), a ~188s H.264/AAC MP4 with
burned-in captions (`ffprobe`-verified `Playable = YES`, audio/video
duration matched to within fractions of a second), and a real 1280×720
thumbnail PNG. All three were sent to the user directly for review. The
canonical episode directory itself was never mutated by this validation
run — see "Human approval / production gate," below.

### Human approval / production gate

**Never bypassed.** The canonical Episode 1 `CONTENT_ITEM.md` status
remains whatever the automated pipeline naturally left it at — this
system never set it to `APPROVED`. Real production (Producer onward)
structurally requires `APPROVED`, so validating the real providers
required a separate, isolated, throwaway copy (under this session's own
scratch directory, never committed, never part of the repository) with
`APPROVED` set only in that copy — the exact same test-only pattern this
codebase's own `agents/full_pipeline/tests/builders.py:simulate_human_approval`
already establishes and documents ("the one action no agent in this
system may ever perform... never called by any agent's own code").

Content review (`agents/orchestrator/`, real, against the canonical
episode, `apply=False`) currently returns `REVISION_REQUIRED`:
`claims/c11.md` ("antibiotics were not developed until the 20th century")
has `Supporting sources = N/A` — a real, pre-existing evidence gap
(already flagged as needing "a future research pass" back in Phase 4 of
the original fixture) that this phase could not close without
fabricating a citation. Five real, distinct external sources were checked
this phase (WHO's live plague fact sheet, Wikipedia's API, Britannica,
NLM, a PMC article) — none confirmed the specific claim; Wikipedia's API
was also repeatedly rate-limited. No `ResearchProvider` capable of live
citation-finding exists yet (Phase 7G explicitly deferred that as future
work) building one is out of Phase 8's own scope (real media production,
not research retrieval). **Exact human action needed:** either supply a
real source for `claims/c11.md` (a research pass), or make an editorial
call to soften/remove that specific claim, before `FACT_CHECK` can
genuinely `PASS` and a human can consider setting `status = APPROVED`. A
separate, smaller fix (`claims/c1.md`'s `Contradictory evidence` field
was miscategorized — a methodology-range note, not a genuine dispute) was
identified and corrected this phase.

### Tests / full-suite result

55 new tests across `agents/voice/tests/test_real_provider.py` (10),
`agents/assets/tests/test_real_providers.py` (23),
`agents/assembler/tests/test_real_provider.py` (8),
`agents/thumbnail/tests/test_real_provider.py` (5) +
`test_pipeline.py` (2 new), plus one regression test in
`agents/producer/tests/test_scene_generation.py` for the whitespace/
table-corruption bug below. All Wikimedia calls in the automated suite
are mocked (deterministic local fixtures, no live network call) per this
phase's own instruction; every ffmpeg-dependent test runs the real
binary (skipped automatically if ffmpeg isn't installed). **Full repo
suite: 496/496 passing, zero regressions** (447 baseline + 49 new).

### Production QA result

Run for real (`apply=True`) against the isolated validation copy:
`REVISION_REQUIRED` — correctly. Two assets (the two Case A/FACT-only
scenes needing `RETRIEVED` media) never achieved genuine retrieval
evidence in that run (Wikimedia rate-limited; a manual, clearly-labeled
GENERATED substitution was used only so the manual video inspection had
a complete, watchable render — recorded honestly, `generation_status`
left as `NOT_STARTED`, never marked `RETRIEVED`). `agents/production_qa/`
correctly flagged both — proof the QA layer does not rubber-stamp a
substitution it wasn't told is real. Every other check passed.

### Human-review state

The highest automated state remains `HUMAN_REVIEW` (unreachable this
phase for the canonical episode, since `FACT_CHECK` hasn't passed and
`status` was never set to `APPROVED`) — nothing in this system moved, or
can move, anything to `PUBLISHED`. `CONSTITUTION.md` rule 2 (no automated
publishing authority) is untouched.

### Known limitations

- **`claims/c11.md`'s evidence gap is still open** — see "Human approval
  / production gate" above; this is the one thing genuinely blocking a
  full automated `FACT_CHECK` `PASS` for Episode 1 right now.
- **No real `ResearchProvider`** (live citation-finding) — Phase 7G's
  abstraction exists; nothing implements it yet. Out of Phase 8's own
  scope (real media production).
- **Wikimedia Commons retrieval is realistically rate-limited** in this
  shared sandboxed environment — the provider itself retries 429/5xx with
  backoff and fails closed (never fabricates), but a real production run
  here should expect some `RETRIEVED`-strategy scenes to need a retry on
  a later, less-contended run.
- **Assembler/Captions stage-order friction** — `agents/full_pipeline/`
  runs `ASSEMBLER` before `CAPTIONS` (captions structurally cannot run
  first — its own precondition is `Production status == CAPTIONS`, which
  only a successful assembler run sets), so the first, in-sequence
  assembler pass has no captions to burn in yet. `FFmpegVideoRenderer`
  degrades gracefully (silent video, no crash) rather than blocking. A
  genuinely captioned cut currently needs a second, explicit render pass
  after `agents/captions/` runs — not yet automated by any agent (this
  phase produced one manually, for inspection). Reordering the two stages
  would fix this properly but is a bigger change than "swap in a real
  provider" and was left as a documented follow-up rather than done under
  this phase's explicit "do not redesign the pipeline" instruction.
- **No transitions beyond hard cuts** — `templates/TIMELINE.md`'s
  `Transition in/out` fields are read and recorded, but only "cut" is
  actually implemented by the renderer; anything else silently falls back
  to a hard cut. Deliberately minimal, per this phase's own "clean,
  watchable baseline, not complicated cinematic effects" instruction.
  Episode 1 itself only ever uses "cut," so this never mattered in
  practice this phase.
- **Illustration renderer is deliberately abstract** — gradient +
  concentric-ring motif + caption, never an attempt at a photorealistic
  or period-accurate scene. This is an honest, explicit design choice
  (see `agents/assets/src/illustration.py`'s own docstring), not a bug —
  it keeps every `GENERATED_RECONSTRUCTION` asset unmistakably non-
  photographic without needing a real image-generation model this phase
  has no credentials for anyway.
- **Thumbnail image rendering is opt-in** (`render_image=True`), not the
  pipeline default — `agents/full_pipeline/` was not modified to always
  request one; a caller (or a future small change) must ask for it.
- **`Pillow` and `ffmpeg` are now real dependencies** (`requirements.txt`)
  — every phase before 8 was stdlib-only; this is a deliberate,
  documented departure, not an oversight.

### Genuine findings

1. **A real, latent bug in `agents/producer/src/scene_builder.py`**,
   found and fixed with a regression test: a SCRIPT.md author hard-
   wrapping a long Hook across multiple source lines (this repo's own
   established prose style) survived, with embedded newlines intact,
   into the written `scenes/scene-01.md`'s own `| Narration text | ... |`
   table cell — corrupting that markdown table and silently truncating
   `narration_text` to empty once re-read. Numbered beats were already
   protected (`_extract_beats` joins wrapped lines before use); the Hook
   path was not. This had never been exercised before, because no prior
   phase had actually run `agents/producer/` against a real, hand-authored
   SCRIPT.md with a wrapped Hook — Phase 8 was the first real run. Fixed
   by collapsing whitespace at the source (the same "formatting only,
   never content" transformation `agents/voice/src/narration.py` already
   applies one stage later, for the identical reason).
2. **A real visual defect, found and fixed**: `illustration.py`'s own
   burned-in caption text and the video renderer's separately burned-in,
   timed SRT captions occupy the same lower-third screen area — playing
   together, they produced illegible, overlapping text. Fixed by adding
   `draw_caption` (default `True`, for `agents/thumbnail/`'s use, which
   has no separate caption track) and having
   `GeneratedAssetProviderReal` pass `draw_caption=False` for scene
   assets specifically, since a scene's real narration is already
   captioned, in sync, by the renderer.
3. **A stale assumption in `agents/assets/src/qa.py`**, found and fixed:
   its structural check unconditionally flagged any `RETRIEVED` asset
   with a source URL as suspicious — correct before Phase 8 (no real
   retrieval existed, so a URL there could only mean an error), actively
   wrong now that a real retrieval provider exists and URLs are expected.
   Corrected to require a URL *and* a retrieved artifact file
   specifically when `generation_status == RETRIEVED`; a regression test
   (`test_catches_retrieved_asset_with_fabricated_url`, updated) still
   catches a URL recorded *without* genuine `RETRIEVED` status.
4. **`agents/visual_planner/`'s `visual_description` is fixed boilerplate
   per authenticity bucket, never scene-specific** — harmless pre-Phase-8
   (a placeholder provider never acted on it meaningfully), a real defect
   now. Fixed in `agents/assets/src/pipeline.py` by preferring the
   scene's own narration text as the prompt handed to a real provider —
   narrower and more defensible than editing `agents/visual_planner/`'s
   own domain logic, and consistent with this codebase's established
   "reuse generic data, never cross-import another agent's judgment"
   boundary.
5. **The AWS credentials present in this environment were deliberately
   not used** for any Phase 8 provider (e.g. AWS Polly for real cloud
   TTS) — they were not confirmed to be provisioned for that specific
   purpose, and using found infrastructure credentials for a new, paid,
   external-facing service without explicit authorization is a real risk
   this phase declined to take. `flite`'s complete lack of any
   credential requirement was the deciding factor in choosing it.

## Completed (Phase 8 follow-up: Episode 1 evidence closure + validation)

**`claims/c11.md`'s evidence gap is closed — honestly, with a real
source, using the existing immutable-claim/supersession mechanism.**
Five real, live sources were checked; this time Wikipedia's "Antibiotic"
article's History section directly corroborated the exact claim
("Antibiotics were not developed until the 20th century") with specific,
uncontested dates (Fleming's 1928 penicillin discovery, Domagk's 1932/33
Prontosil) and its own "revolutionized medicine in the 20th century"
framing. Recorded as a new, permanent research entry,
`research/04-wikipedia-antibiotic-history.md`. `agents/researcher/src/
revision.py`'s `run_fact_check_with_autonomous_revision` — already built
in Phase 7F, never exercised end-to-end on a real gap until now — was run
live against the canonical episode (fact-check/revision are independent
of, and prior to, the human-approval gate) and correctly diagnosed this
as `RevisionCase.FIXABLE` (an existing research entry already
reciprocally cited `c11` in its own `Related claims`, just not yet cited
back). It created a successor claim, `claims/c11_rev1.md`
(`Fact-check status = VERIFIED`, exact original claim wording preserved
unchanged — the evidence supported the claim as originally written, so
no rewording was needed or made), and left `claims/c11.md` itself
byte-identical apart from one appended, trailing "Superseded" note — its
`Exact claim`/`Classification`/original table are untouched, per
`templates/CLAIM.md`'s Atomicity rule. `SCRIPT.md`'s own "Verified
claims" table still cites `c11` by name (the revision engine never
rewrites `SCRIPT.md`), which is expected and correct — `c11_rev1` is
resolved by content hash lookup, not by the script's own claim ID text.

**A genuine, previously-latent bug was found and fixed along the way**:
`agents/researcher/src/loader.py`'s `normalize_claim_ref` and
`normalize_research_ref` both used `token.rsplit("/", 1)[-1]` to extract
a claim/research basename from a path-like reference — which silently
corrupted the literal placeholder `"N/A"` into `"A"` when backtick-
wrapped (e.g. a real successor claim's own `Derived from | \`N/A\` |`
table cell). Never triggered before because nothing had exercised a real
autonomous-revision successor claim end-to-end until this session. Fixed
with an explicit guard in both functions (`if token.upper() == "N/A":
return token`, before any path-splitting); regression test added,
`agents/researcher/tests/test_loader_ref_normalization.py` (5 cases).
Confirmed `claims/c11_rev1.md`'s `Derived from` field now correctly reads
`N/A`.

**Content review re-run for real, via `agents/orchestrator/`'s
`run_automated_review` (FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW,
stopping at the first blocking stage — never bypassed, nothing manually
marked `PASS`):**

| Stage | Verdict | Notes |
|---|---|---|
| `FACT_CHECK` | `PASS` (attempt #2; attempt #1 was `REVISION_REQUIRED` before `c11_rev1` existed) | All 11 claims `VERIFIED`/`NOT_APPLICABLE`, no unresolved contradictions; autonomous revision correctly evaluated successor `c11_rev1` in place of superseded `c11`. |
| `SAFETY_REVIEW` | `REVISION_REQUIRED` (attempt #1) | Every signal `LOW_RISK`/`NOT_APPLICABLE` except `SENSITIVE_CONTENT: REVIEW_REQUIRED` — the keyword `'plague'` (real mass-casualty tragedy content) triggers this system's deliberate, permanent human-escalation gate. This is working as designed, not a defect, and was correctly left unresolved rather than auto-cleared. (`AI_DISCLOSURE` is now `LOW_RISK` — a real "AI disclosure plan" section was added to `SCRIPT.md`, giving `check_ai_disclosure()`'s substring search a genuine match; this was a real fix, not a keyword hack, since the disclosure plan itself describes real on-screen/description text.) |
| `ORIGINALITY_REVIEW` | `NOT_STARTED` | Never reached — the orchestrator correctly stops at the first blocking stage (`SAFETY_REVIEW`). |

**Content review has not reached full `PASS`.** The remaining blocker is
`SENSITIVE_CONTENT`'s human-judgment escalation — by design, this system
cannot and must not resolve it automatically. This is a separate gate
from, and prior to, human approval of `status = APPROVED` itself.

**Human approval was never touched.** Canonical
`CONTENT_ITEM.md`'s `Current status:` remains `SCRIPT`; `Owner approval
state` remains `NOT_STARTED`. Nothing in this session set or simulated
`APPROVED` on the canonical episode.

**Real production pipeline validated end to end**, again on a fresh,
isolated, throwaway copy (this session's own scratch directory, never
committed) with `APPROVED` set only in that copy — Producer → Voice
(`FliteVoiceProvider`) → Visual Planner → Assets → Assembler
(`FFmpegVideoRenderer`) → Captions → a second, manual Assembler render
pass (captions burned in) → Thumbnail (`render_image=True`) →
`agents/production_qa/`:

- Assets: real Wikimedia retrieval was attempted for both `RETRIEVED`-
  strategy scenes and genuinely failed — this time confirmed as a
  query-specificity issue rather than primarily rate-limiting (a short,
  generic query succeeded but surfaced a real, topically-unrelated,
  sensitive image; the actual narration-derived queries returned no
  usable result). Deliberately did not loosen the query just to force a
  match — an honest `RETRIEVAL_FAILED` was judged safer than a
  "successful" but mismatched/sensitive retrieval. Real Pillow
  illustrations were substituted for validation only, with
  `Generation/retrieval status` left honestly `NOT_STARTED` (never
  marked `RETRIEVED`) — no fabricated provenance.
- Both known Phase 8 production limitations were checked against this
  real run and confirmed **not** to block a watchable result: the
  Assembler-before-Captions ordering still requires the documented
  two-pass workaround (render once without captions, run Captions, then
  re-invoke the same real renderer directly to burn captions into a
  fresh `output/video-01.mp4`) — done here, producing a real,
  `ffprobe`-verified `Playable = YES` H.264/AAC MP4 with captions
  correctly burned in; hard-cut-only transitions were a non-issue since
  Episode 1 only ever uses cuts. Neither was redesigned, per this
  phase's explicit instruction not to.
- `agents/production_qa/` verdict: `REVISION_REQUIRED` — exactly the two
  expected, honest flags (`scene-02.md`/`scene-03.md`: "retrieved asset
  has real retrieval evidence" fails because `Generation/retrieval
  status` is `NOT_STARTED`, not `RETRIEVED`) and nothing else. Every
  other check passed (Content, Voice, Timeline, Captions, Thumbnail,
  Output/playability). This is the QA layer correctly refusing to
  rubber-stamp a substitution it wasn't told is a real retrieval — proof
  the check works, not a pipeline defect.
- Thumbnail: a real 1280×720 PNG rendered successfully from the existing
  spec.

**Full test suite: 501/501 passing** (496 baseline + 5 new — the
`test_loader_ref_normalization.py` regression tests for the bug above).
Zero regressions, zero new skips.

**Golden sample confirmed untouched**:
`git status --porcelain -- content/what-if/wi-20260902-black-death-modern-medicine/`
returns nothing.

**No new production limitations were found.** All limitations already
listed under Phase 8's "Known limitations" above still apply as
documented (Wikimedia rate-limiting/query-specificity, Assembler/Captions
ordering, hard-cut-only transitions, the deliberately abstract
illustration renderer, opt-in thumbnail rendering).

### Exact next human action

Two separate, sequential decisions remain — neither can be made by this
system:

1. **A human must review the tone/framing of this episode's real
   mass-casualty subject matter** (the Black Death, flagged via the
   `'plague'` keyword) before `SAFETY_REVIEW` can genuinely clear. This
   is the one concrete blocker on `agents/orchestrator/`'s automated
   review pipeline right now. `ORIGINALITY_REVIEW` has not yet run and
   its outcome is unknown until Safety clears.
2. Only after content review reaches a genuine `PASS`, the human owner
   may consider setting the canonical `CONTENT_ITEM.md`'s
   `status = APPROVED` — a decision this system will never make or
   simulate on its own authority. The episode is **not** published and
   is **not** human-approved; nothing in this session changed that.

## Completed (Phase 8 follow-up 2: Safety escalation inspection + human-review package)

**Inspected the `SENSITIVE_CONTENT` escalation directly against the real
script rather than assuming the keyword itself means the episode is
unsafe.** `agents/safety/src/signals.py`'s `check_sensitive_content` is a
plain keyword match (`plague`, among a small curated tragedy/mass-
casualty list) against `SCRIPT.md` + `CONTENT_ITEM.md` text — it cannot
and does not evaluate tone or framing, by design. The script was read in
full and searched for graphic, exploitative, or sensational language
(gore, suffering, exaggerated-casualty framing): none found. Every
mortality figure is a sourced, hedged statistic; the Conclusion
explicitly rejects a "modern medicine saves the day" framing. **No
editorial revision was made** — rewriting to avoid the word "plague"
(the historical disease this episode is about) would not change the
episode's substance, only defeat the keyword detector. The
`SENSITIVE_CONTENT` signal, the `agents/safety/` keyword list, and the
orchestrator's stop-at-first-blocker behavior were none of them touched,
weakened, or bypassed.

**Re-ran content review via the real orchestrator** (`run_automated_review`,
dry-run first, then `apply=True`): `FACT_CHECK` correctly reused its
existing `PASS` (attempt #2 — hash unchanged, since Researcher's
`Reviewed content hash` never includes `CONTENT_ITEM.md`).
`SAFETY_REVIEW` genuinely re-ran as a fresh attempt
(`reviews/safety_reviewer-2.md`) because adding `HUMAN_REVIEW.md`'s
reference to `CONTENT_ITEM.md`'s own Linked records/Notes sections
changed the *Safety* role's `Reviewed content hash` specifically (its own
`compute_reviewed_content_hash` hashes all of `CONTENT_ITEM.md`, unlike
Researcher's) — correctly detected as stale and re-evaluated rather than
assumed still valid. Attempt #2 reached the identical verdict and reason
as attempt #1 (`REVISION_REQUIRED` — `SENSITIVE_CONTENT` only; every
other signal `LOW_RISK`/`NOT_APPLICABLE`, including `AI_DISCLOSURE`).
`ORIGINALITY_REVIEW` still not reached — the orchestrator still correctly
stops at Safety. Overall content review remains
`HUMAN_ESCALATION`/`BLOCKED_AT_SAFETY_REVIEW` — genuinely, not by
omission.

**Re-attempted real Wikimedia retrieval for the two previously-failed
assets** (mortality timeline scene; absence-of-germ-theory scene), using
several honest, still-topically-faithful queries — not to force a match,
but to check whether a legitimate real asset now exists. Findings: for
the mortality-timeline scene, no safe/accurate result exists (candidates
were a real-but-unrelated 1930s political cartoon and an unrelated
Renoir painting); `SCRIPT.md`'s own Visual requirements already call for
a "map graphic" there, which is structurally a diagram, not an archival
photograph (none exists from 1347) — so `GENERATED_RECONSTRUCTION` is
arguably the correct asset type for this scene, not really a retrieval
gap. For the absence-of-germ-theory scene, a real, safe, on-topic,
public-domain candidate was found (a portrait of Louis Pasteur, whom the
script names directly) — recorded as a finding for a future production
run; not written into any file, since the canonical episode has no
`assets/` directory yet (Producer has never run against it). No asset
anywhere in this repository is, or has been, labeled `RETRIEVED` without
real, verifiable provenance.

**Created `content/what-if/wi-20260904-black-death-modern-medicine-ep1/
HUMAN_REVIEW.md`** — a plain-language human-review package (not part of
the automated review chain; never read by any agent) covering: the
episode's editorial fact/assumption/inference/speculation breakdown, the
exact Safety trigger and why no rewrite was made, visual treatment per
scene, AI disclosure status, production/QA results, the Wikimedia
findings above, and the two sequential human decisions still required
(Safety tone/framing sign-off, then — only afterward — `status =
APPROVED`). Linked from `CONTENT_ITEM.md`'s Linked records and logged in
its Notes/history log.

**Full test suite: 501/501 passing** — unchanged (no source-code changes
this round, only content/documentation and a fresh Safety review
attempt).

**Golden sample confirmed untouched.**

### Exact next human action (unchanged in substance, now documented for the owner directly in `HUMAN_REVIEW.md`)

1. A human reviews this episode's tone/framing of real historical
   mass-casualty content (`HUMAN_REVIEW.md` Section 2) and decides
   whether `SAFETY_REVIEW` may be recorded as cleared — this system
   cannot make this decision.
2. Only after content review reaches a genuine `PASS` (Fact Check +
   Safety + Originality — Originality has not yet run), the human owner
   may consider `CONTENT_ITEM.md`'s `status = APPROVED`. Not done, and
   not simulated, this round either.

The episode is **not** published and **not** approved.

## Completed (Phase 8 follow-up 3: explicit human Safety signoff mechanism)

**Built the smallest clean mechanism for recording a human Safety
decision, reusing existing architecture rather than redesigning the
pipeline.** New pieces, all additive:

- `templates/HUMAN_SAFETY_SIGNOFF.md` — schema for one human decision
  record: reviewer, `CLEARED`/`NOT_CLEARED`, timestamp, the exact content
  hash reviewed, which Safety signal(s) it addresses, confirmation the
  flagged subject matter was read in context, review scope, and optional
  notes. Same numbered-attempt, never-overwritten convention as
  `templates/REVIEW.md`.
- `agents/safety/src/human_signoff.py` — the record model, a loader
  (`load_human_safety_signoffs`, fails closed on a malformed file rather
  than silently ignoring or trusting it), and
  `record_human_safety_decision()` (the only function that writes one;
  requires every field explicitly, refuses `NOT_CLEARED` without notes,
  never called automatically by any agent).
- `agents/safety/src/human_signoff_cli.py` — `python -m
  agents.safety.src.human_signoff_cli <dir> --reviewer ... --decision
  CLEARED|NOT_CLEARED --signals ... --scope ... [--historical-context-
  reviewed] [--notes ...]`. `--decision` has no default — the only way to
  record a decision is to type one. The reviewed-content hash and the
  triggering review attempt are computed automatically from current
  on-disk state at the moment the command runs, never typed by hand.
- `agents/orchestrator/src/human_safety_continuation.py` —
  `continue_after_human_safety_review()`, the one function that lets a
  content item move past a `SAFETY_REVIEW` human escalation into
  `ORIGINALITY_REVIEW`. In order: (1) an automated Safety review must
  have run at least once; (2) a human signoff must exist and be
  `CLEARED`; (3) the signoff's own recorded hash must still match the
  content's *current* hash (otherwise `STALE_SIGNOFF` — the script/
  content changed since clearance, and a new human review is required);
  (4) re-evaluating Safety's real signals live right now must show no
  blocking finding (`HIGH_RISK` or `REVIEW_REQUIRED`) outside exactly
  what the signoff declares it covers (`BLOCKED_OTHER_SAFETY_FINDING`
  otherwise — a clearance for `SENSITIVE_CONTENT` never overrides an
  unrelated `DANGEROUS_INSTRUCTION` finding, now or later). Only once all
  four hold does it call the real `run_originality_review`. It never
  runs Safety itself, never writes to `reviews/safety_reviewer-*.md`, and
  never touches `CONTENT_ITEM.md`'s `status`.

**A `NOT_CLEARED` decision leaves the item at `EDITORIAL_REVISION_
REQUIRED`** — no automatic retry, script rewrite, or Originality run.
**No signoff at all** reports `WAITING_FOR_HUMAN_SAFETY_REVIEW`.

**A genuine, previously-latent bug was found and fixed along the way**:
`agents/safety/src/hashing.py`'s `compute_reviewed_content_hash` hashed
the *entire* `CONTENT_ITEM.md` file — including the `Safety state` field
and `Notes / history log` line that this very agent's own `_apply_result`
writes *immediately after* computing that hash. That made every freshly-
applied Safety review's own stored hash mismatch the content on disk the
instant you checked it again, silently defeating
`agents/orchestrator/src/freshness.py`'s PASS-reuse check for Safety
specifically (discovered only because the new continuation mechanism
actually exercises this path for the first time — Researcher's
equivalent hash never includes `CONTENT_ITEM.md` at all, so it never hit
this). Fixed by scoping the hash to `CONTENT_ITEM.md`'s Identity section
only (title/premise) — matching the function's own docstring, which
already said "Identity table text," and the one part of the file this
role actually needs to care about and never itself writes to.

**Demonstrated against the real Episode 1**, with no fabricated
decision: `continue_after_human_safety_review()` correctly reports
`WAITING_FOR_HUMAN_SAFETY_REVIEW` — no `human_safety_signoffs/` directory
exists yet. `HUMAN_REVIEW.md` gained a "Human Safety Decision Required"
section with the exact CLI command the human owner runs, what `CLEARED`
vs. `NOT_CLEARED` means, and an explicit reminder that clearing Safety
does not approve the episode. Canonical `CONTENT_ITEM.md`'s `status`
remains `SCRIPT`; `Fact-check state`/`Safety state` are unchanged in
substance (`PASS` / `REVISION_REQUIRED`).

**31 new regression tests** (`agents/safety/tests/test_human_signoff.py`,
15; `agents/orchestrator/tests/test_human_safety_continuation.py`, 16):
valid clearance (correct hash, only-intended-signal coverage, a stale
*automated review record* alone does not block a fresh valid signoff);
invalid clearance (missing signoff, no automated review ever run,
`NOT_CLEARED`, wrong/fabricated hash, script changed after signoff,
`CONTENT_ITEM.md` changed after signoff, an unrelated `HIGH_RISK`/
`REJECT`-tier finding never overridden, a malformed signoff file);
security/integrity (tampering with a review's `Verdict` text cannot
manufacture clearance since live signals are always re-evaluated
independently of any stored verdict text; a `CLEARED` continuation never
sets `status = APPROVED`; a stale clearance never lets Originality run;
running Safety alone never creates a signoff). **Full suite: 532/532
passing** (501 baseline + 31 new; zero regressions, zero skips).

**Golden sample confirmed untouched.**

### Exact next human action (unchanged)

1. Read `HUMAN_REVIEW.md`'s "Human Safety Decision Required" section and
   run the `human_signoff_cli` command with `--decision CLEARED` or
   `--decision NOT_CLEARED`. This system will not infer or simulate this
   decision.
2. If `CLEARED` and no other Safety blocker exists,
   `continue_after_human_safety_review()` will run `ORIGINALITY_REVIEW`
   for real on the next invocation — the next Claude session/prompt
   should do exactly that, and no more, once this decision actually
   exists. If Originality then passes, content review reaches `PASS` and
   human content approval (`status = APPROVED`) becomes the next and
   final gate — still a separate, later, human-only decision.

## Completed (Phase 8 follow-up 4: owner-voice provider architecture)

**Owner-voice requirement**: the channel's narration should eventually
use the human owner's own voice identity, not the generic offline Flite
voice — `Owner records/teaches voice → voice system generates narration
in owner's voice → AI handles repetitive narration production → human
reviews final audio`. This follow-up builds the provider architecture
for that goal; it does **not** generate any owner-voice audio, since no
real voice-cloning engine or credentials are configured in this
environment (checked directly, not assumed — see below).

**Implementation status: architecture and tests complete; provider not
yet operational.**

- `agents/voice/src/owner_voice.py` — `OwnerVoiceConfig` (reads
  `OWNER_VOICE_ID`/`OWNER_VOICE_SAMPLE_PATH`/`OWNER_VOICE_ENGINE`/
  `OWNER_VOICE_MODEL`/`OWNER_VOICE_LANGUAGE`/`OWNER_VOICE_STYLE`/
  `OWNER_VOICE_STABILITY`/`OWNER_VOICE_CONSISTENCY`/
  `OWNER_VOICE_PRONUNCIATION` from the environment; carries no credential
  fields at all and never exposes the sample's path or contents in any
  summary/log/persisted string — verified by dedicated tests);
  `OwnerVoiceEngine` protocol + an empty-by-default registry (no vendor
  chosen or hard-coded); `check_owner_voice_availability()` returning
  `OWNER_VOICE_AVAILABLE`/`OWNER_VOICE_NOT_CONFIGURED` with a precise,
  non-secret reason; `OwnerVoiceProvider` (a third `VoiceProvider`
  implementation, alongside the existing test and Flite providers) whose
  `generate()` raises `OwnerVoiceNotConfiguredError` — never falls back
  to a different voice — whenever availability isn't genuinely met.
  Every `GeneratedAudio` it could ever return carries an explicit
  `OWNER_AUTHORIZED_VOICE` marker; there is no code path for cloning
  anyone else's voice.
- `agents/voice/src/provider_selection.py` — `resolve_voice_provider(name,
  ...)`, supporting `local-test`, `local-fallback`, and `owner-voice` by
  name; rejects any unrecognized name rather than silently defaulting.
- `agents/voice/src/real_provider.py`'s `FliteVoiceProvider` gained a
  second export name, `LocalFallbackVoiceProvider` — the same class,
  never deleted or rewritten, named for its actual role now that an
  owner-voice provider exists (dev/test/explicit-fallback only, never a
  stand-in for the owner's voice).
- `agents/voice/src/owner_voice_cli.py` — `python -m
  agents.voice.src.owner_voice_cli` reports current availability and a
  redacted configuration summary; never generates audio, never prints a
  credential value or the sample's path/contents.
- `.gitignore` gained `/owner_voice_samples/`, `/.private/`, and
  `*.owner-voice-sample.*` so a locally-placed sample can never be
  committed by accident.

**Provider selection (this environment, checked directly, not
assumed):** no TTS/voice-cloning Python package is installed, no
`piper`/`espeak`/`festival` binary exists on `PATH`, and no
voice/speech-related API key or credential environment variable is
present. No commercial vendor was chosen — per this task's own
instruction not to pick one "merely because it is popular," and per
`agents/voice/CONTRACT.md`'s existing rule against committing this
codebase to a specific provider. The engine registry is empty;
`OWNER_VOICE_AVAILABLE` cannot be true here until a real engine is
selected, implemented against the `OwnerVoiceEngine` protocol, and
registered — a distinct, later, separately-validated step.

**A real owner voice sample was provided this session** (an ~18s video
of the owner speaking, uploaded to this conversation). It was **not**
copied into this repository at any point — its audio was extracted only
into this session's own scratch directory (outside the repo, outside
git, never referenced by literal path in any committed file) purely to
prove `check_owner_voice_availability()` correctly recognizes a real,
non-empty sample file when `OWNER_VOICE_SAMPLE_PATH` points at it — it
still, correctly, reports `OWNER_VOICE_NOT_CONFIGURED` (reason: no
engine configured), since a sample alone is not a working provider. No
owner-voice audio was fabricated, and Flite's output was never relabeled
as the owner's voice.

**Narration integrity preserved**: `OwnerVoiceProvider` receives the
same PROVIDER-READY NARRATION every provider does and cannot alter it;
existing structural QA (`qa.py`) applies unchanged; regression tests
confirm script hash and narration text are preserved verbatim in
`voice/voice-<n>.md` when generated via a (test-only, fake) owner-voice
engine.

**Human approval boundary preserved**: regression tests confirm voice
generation via `OwnerVoiceProvider` never touches `CONTENT_ITEM.md`,
never advances `Production status` beyond what QA passing already
allows, and never approves/publishes anything — identical to every
other provider.

**35 new tests** (`agents/voice/tests/test_owner_voice.py`, 29;
`agents/voice/tests/test_provider_selection.py`, 6): configuration
(valid/missing/malformed, privacy of the redacted summary and
configuration string), availability (every individual missing
precondition, a registered fake engine reporting itself unavailable,
missing/present credential *environment variable names*, full
availability), generation (raises when unconfigured, never falls back,
rejects empty narration, succeeds with a fake engine, fails on an engine
producing no audio, two different `voice_id`s never collapse to the same
label), provider selection (each of the three names, an unknown name
rejected), and the pipeline-integration set described above. **Full
suite: 567/567 passing** (532 baseline + 35 new; zero regressions, zero
skips; the existing Flite/local-test providers, real FFmpeg renderer,
captions, and Production QA are all untouched and still pass).

**Golden sample confirmed untouched. Episode 1 unaffected**: still
`WAITING_FOR_HUMAN_SAFETY_REVIEW` (from the prior follow-up); this work
never touched Episode 1's `CONTENT_ITEM.md`, `SCRIPT.md`, reviews, or
signoffs, and no production artifacts were regenerated for it.

### Remaining setup requirement

Real owner-voice narration requires, in order: (1) a human decision on
which voice-generation approach to use (a specific local model or a
specific paid cloud service), weighed against this task's own priorities
(owner-authorized cloning, quality, privacy, cost, accessibility,
cross-episode consistency) — this system deliberately did not make that
choice; (2) implementing and registering one `OwnerVoiceEngine` adapter
for that choice (a small, isolated addition — nothing else in
`agents/voice/` needs to change); (3) the owner's actual consented voice
sample and any required credentials supplied via the environment
(`OWNER_VOICE_SAMPLE_PATH`, `OWNER_VOICE_ID`, `OWNER_VOICE_ENGINE`, plus
whatever that engine's own `required_credential_env_vars` name); (4)
only then, a real, explicit owner-voice generation as its own validation
step — never claimed operational before that actually succeeds.

## Completed (Phase 8 follow-up 5: owner-voice provider readiness evaluation)

**Research-only** — no code changed, no account created, no purchase
made, no credential added, and the owner's private voice sample was not
uploaded to, or referenced by path/content to, any external service.
Full write-up: `agents/voice/PROVIDER_EVALUATION.md`.

Evaluated five real options against the existing, unmodified
`OwnerVoiceEngine` protocol: **ElevenLabs**, **PlayHT**, **Resemble AI**
(commercial cloud APIs), **Azure AI Speech "Personal Voice"** (gated,
consent-first enterprise feature), and **OpenVoice V2** (MyShell, MIT
license, self-hosted). Coqui XTTS-v2 was checked and explicitly *not*
shortlisted as a primary recommendation: its model weights are licensed
under CPML 1.0.0, non-commercial use only — a real, easy-to-miss legal
trap for a channel that publishes commercially.

`INITIAL_SAMPLE_STATUS = TECHNICALLY_USABLE_FOR_TEST` — the existing
~18s sample is technically clean but below the recommended minimum for
several reputable options (ElevenLabs recommends 1–2 minutes; Azure
requires 1 minute); Resemble AI (~10s floor) and OpenVoice V2 (1–5s
floor) comfortably support it. A longer 2–5 minute sample is
recommended before any production commitment, independent of which
provider is eventually chosen — not concluded to be production-quality
merely because it is technically clean.

Non-binding recommendations (final choice remains
`HUMAN_OWNER_DECISION`): best overall — ElevenLabs; best low-cost —
Resemble AI (hosted) or OpenVoice V2 (self-hosted, free); best
privacy/local — OpenVoice V2 (MIT-licensed, sample never leaves
owner-controlled infrastructure); best expressive-narration candidate —
ElevenLabs, reputationally (not independently verified — no provider's
raw voice-clone quality was tested in this evaluation; every "quality"
cell in the comparison matrix is marked `UNKNOWN` for that reason).

**No real adapter can be implemented yet** — that requires the owner to
first pick a provider, weighing the cloud-upload-vs-self-hosted privacy
tradeoff and cost, then supply real, owner-obtained credentials via the
environment. Once that happens, exactly one new, isolated module
implementing the existing `OwnerVoiceEngine` protocol is the only code
change needed — `owner_voice.py`, `pipeline.py`, `mutate.py`, and
`templates/VOICE.md` all stay unchanged.

**Full suite: 567/567 passing, unchanged** (no source code was
modified this round). Golden sample and Episode 1 (still
`WAITING_FOR_HUMAN_SAFETY_REVIEW`) both confirmed untouched.

## Completed (Phase 8 follow-up 6: owner-voice readiness — adapter contract + authorization-boundary tests)

**No new provider, no code behavior change** — the `OwnerVoiceEngine`
protocol built in follow-up 4 was preserved exactly as-is, per this
round's own explicit instruction not to redesign it. This round adds
documentation and tests only.

- `agents/voice/CONTRACT.md` gained an "Owner-voice adapter contract"
  section: a written MUST/MUST-NOT list any future adapter is judged
  against (accepting the authorized config and provider-ready
  narration, generating audio, returning deterministic provider/model/
  voice-ID metadata and duration, preserving the narration/script-hash
  relationship, failing explicitly when unavailable — and never
  rewriting/summarizing narration, never silently falling back, never
  approving or publishing content).
- `agents/voice/PROVIDER_EVALUATION.md` gained: an explicit
  `RECOMMENDED_PRODUCTION_SAMPLE = 2-5 minutes...` constant alongside
  the existing `INITIAL_SAMPLE_STATUS = TECHNICALLY_USABLE_FOR_TEST`; a
  "Human authorization boundary" section spelling out the two
  independent human decisions (provider authorization vs. episode
  editorial approval) and why neither can satisfy the other; and a
  machine-readable decision block (`OWNER_DECISION_REQUIRED`,
  `SELECTED_PROVIDER = UNSELECTED`, `SAMPLE_STATUS =
  TECHNICALLY_USABLE_FOR_TEST`, `PRODUCTION_SAMPLE_RECOMMENDATION =
  2-5 MINUTES`, `EXTERNAL_UPLOAD_AUTHORIZED = FALSE`) — descriptive only,
  never read by any code, never auto-updated.
- `agents/voice/tests/test_owner_voice_authorization_boundary.py`
  (12 new tests, all using a clearly-labeled fake test engine — no real
  provider registered or contacted): an unselected/unregistered engine
  name fails safely and by name; `resolve_voice_provider("owner-voice")`
  never hands back `LocalFallbackVoiceProvider`/`LocalTestVoiceProvider`
  even when unconfigured; the module has no network-capable imports at
  all; a private sample's filename and a fake credential's value never
  appear in any file `run_voice_generation(apply=True)` writes to disk,
  nor in the returned result's own string fields; a fully-available
  owner-voice provider still cannot bypass the pre-existing content-
  approval gate on an unapproved item; and registering/configuring a
  provider never touches `CONTENT_ITEM.md` at all.

**Full suite: 579/579 passing** (567 baseline + 12 new; zero
regressions). No external voice service was contacted at any point —
confirmed no network-capable code path exists in `owner_voice.py` and
no engine is registered. Golden sample and Episode 1 (still
`WAITING_FOR_HUMAN_SAFETY_REVIEW`, re-verified live via
`continue_after_human_safety_review()`) both confirmed untouched. No
private sample path, filename, or content appears anywhere in this
round's diff.

## Completed (Phase 8 follow-up 7: OpenVoice V2 — first real owner-voice engine)

**Implemented `agents/voice/src/engines/openvoice_v2_engine.py`** — the
first real `OwnerVoiceEngine`: OpenVoice V2 (MyShell, MIT license),
fully local, no cloud API, no account, no credentials
(`required_credential_env_vars = []`). Conforms exactly to the existing,
unmodified `OwnerVoiceEngine` protocol; never registered automatically
(registers only when explicitly imported), so `agents/voice/`'s provider
registry stays empty for every normal test/CI run — the same guarantee
every prior follow-up already established.

**A real, isolated local environment was actually built and exercised**
(`.voice-experiments/`, fully gitignored, never touches this
repository's own `requirements.txt`): torch/torchaudio, the `openvoice`
package, MeloTTS, and OpenVoice V2's checkpoints. Two genuine
environment blockers were hit and resolved, both documented in
`agents/voice/src/engines/README.md` for reproducibility:

1. The officially-documented checkpoint host
   (`myshell-public-repo-host` on S3) returned `NoSuchBucket` — retired
   since the docs were written. Used the maintained Hugging Face mirror
   (`myshell-ai/OpenVoiceV2`) instead — same files, same license.
2. `faster-whisper==0.9.0`'s pinned `av==10.*` dependency has no
   prebuilt wheel for Python 3.11 and fails to compile (missing FFmpeg
   *development* headers — only the runtime `.so` files are present in
   this environment). An unpinned, current `faster-whisper` resolves a
   newer `av` with a prebuilt wheel instead, with no behavior difference
   relevant to this use case.

**A genuine privacy bug was found and fixed during real testing**:
OpenVoice's own `se_extractor.get_se()` defaults to writing derived
audio segments extracted from *the owner's actual sample* into a
`processed/` directory relative to the current working directory —
which landed inside this repository's own working tree during a real
test run (never committed; caught and deleted immediately). Fixed by
pinning `target_dir` to the adapter's own ephemeral
`tempfile.TemporaryDirectory()` for every call, so no derived sample
data can ever land anywhere persistent, let alone inside the repo.
`.gitignore` also gained `/processed/` as defense in depth.

**20 new tests** (`agents/voice/tests/test_openvoice_v2_engine.py`):
language/speaker-mapping logic, the engine's real identity/protocol
conformance, its genuine `is_available()`/`synthesize()` failure
behavior in this test environment (which does not have the heavy ML
deps installed — an honest test of what happens on any machine that
hasn't set up the isolated environment, not a mock), registration,
no-network-imports, the content-approval boundary (a fully-available
OpenVoice engine still cannot bypass the pre-existing `APPROVED` gate),
and — via a separate, clearly-labeled fake test double, never claimed
to be OpenVoice — narration/script-hash/metadata pipeline guarantees.
**Full suite: 599/599 passing** (579 baseline + 20 new; zero
regressions).

**A real local synthesis test completed successfully** against the
owner's existing ~18-second sample (`INITIAL_SAMPLE_STATUS =
TECHNICALLY_USABLE_FOR_TEST`, unchanged recommendation: 2–5 minutes for
real production use) with a representative ~98-word test narration —
full write-up in `agents/voice/OPENVOICE_V2_TEST_REPORT.md`. Genuine,
non-placeholder audio was produced: 416.4s synthesis time (CPU-only —
MeloTTS + BERT prosody + tone-color conversion, no GPU in this
environment), 1,527,340 bytes, 34.63s duration, WAV/PCM 16-bit mono
22,050Hz (independently verified via `ffprobe`/`ffmpeg` — not
self-reported), peak volume −7.1dB (no clipping), no silence gaps
≥0.5s. Replayed through the real `run_voice_generation()` pipeline
against an isolated throwaway test item (never Episode 1): **Voice QA
= `PASS`**, `generation_status = GENERATED`, correct
`OWNER_AUTHORIZED_VOICE` provider metadata, no trace of the private
sample's path in any written record. The 18-second sample was
sufficient to produce a complete, structurally valid synthesis — this
is **not** evidence of production-quality fidelity; only human
listening can determine that. The report's "Human evaluation" fields
(voice similarity, naturalness, pronunciation, narration suitability,
overall decision) are deliberately left blank for the owner — nothing
here fabricates that judgment. Nothing about this experiment touches
Episode 1, Safety, Originality, or any approval state.

## Completed (Phase 8 follow-up 9: OpenVoice V2 activated for production; VOICE_DECISION = USE_FOR_PRODUCTION)

**The owner recorded a real decision** after listening to the previous
follow-up's test clip: the voice is recognizable as their own and
acceptable for production, while acknowledging the clone can be
improved later. Recorded as `CURRENT_OWNER_VOICE = OpenVoice V2`,
`VOICE_QUALITY_STATUS = ACCEPTABLE_FOR_PRODUCTION`, `VOICE_IMPROVEMENT =
FUTURE_ITERATION` in `agents/voice/PROVIDER_EVALUATION.md`'s Section 10
and `agents/voice/OPENVOICE_V2_TEST_REPORT.md`'s new "Production-use
evaluation" section — not fabricated: fields the owner didn't
individually rate are marked as such, not guessed. This decision does
not reopen or restate — it authorizes using OpenVoice V2 going forward.

**No architecture was redesigned.** `OwnerVoiceEngine`,
`OwnerVoiceProvider`, and `provider_selection.resolve_voice_provider()`
are exactly as Phase 8 follow-up 7 left them. Selecting `"owner-voice"`
already routed to whatever engine `OwnerVoiceConfig` names; the only
thing that changed this round is that an operator can now genuinely
complete the three-step activation (isolated environment set up +
explicit `from agents.voice.src.engines import openvoice_v2_engine`
import + `OWNER_VOICE_ENGINE=openvoice-v2` and related env vars) and
have it actually work — verified end to end, not just asserted. The
registry still starts empty in every normal test/CI run; nothing
auto-imports the engine module.

**7 new regression tests** (`agents/voice/tests/test_openvoice_v2_production_activation.py`):
`resolve_voice_provider("owner-voice", ...)` genuinely routes to a
provider bound to the registered OpenVoice V2 engine; the selection
layer never bypasses the engine's own real failure behavior (still no
silent fallback); no publish-shaped attribute is reachable from the
resolved provider; invalid-checkpoint and missing-checkpoint-dir
scenarios are reported precisely (verified for real inside the isolated
venv, where torch/openvoice/melo are actually importable — skipped, not
faked, in the normal test environment that lacks them); and the
pre-existing content-approval gate still blocks a fully-configured
OpenVoice V2 provider from generating against an unapproved item, now
reached through the production selection path rather than only the
provider's own direct constructor.

**Isolated Episode 1 production validation** (never the canonical
episode — a fresh copy under this session's own scratch directory,
`APPROVED` flipped only in that copy, confirmed via `git status
--porcelain` that the canonical `content/what-if/wi-20260904-...-ep1/`
directory was never touched): the real `run_producer()` ran first
(7 scenes produced), then the real, registered OpenVoice V2 engine was
invoked through the real `run_voice_generation()` pipeline against the
full Episode 1 script (~479 words, all 6 beats + Hook, not just a short
test clip).

**First attempt genuinely OOM-killed** — reported honestly rather than
hidden: synthesizing + tone-converting the entire script in one pass
reached ~13.9GB resident memory against this sandboxed session's
~14.3GB cgroup limit and was killed by the kernel (confirmed via
`dmesg`'s `oom-kill` log entry), right as MeloTTS's own synthesis phase
finished and tone-color conversion began on the full combined audio. No
audio was produced or reported as a result of that attempt. **Root-caused
and fixed**: `openvoice_v2_engine.py`'s `synthesize()` now chunks
narration into ~100-word, sentence-boundary-respecting pieces
(`_chunk_narration`), synthesizes/converts each independently, and
concatenates the resulting PCM audio — bounding peak memory regardless
of script length, with zero effect on the narration text the engine
receives or on what the pipeline records about it (5 new tests verify
exact-reconstruction, no mid-sentence splits, and that realistic-length
scripts actually produce multiple chunks).

**A second attempt, chunked, was also genuinely OOM-killed** — at
essentially the same ~13.9GB ceiling, though after completing noticeably
more work first (5 of ~6-7 chunks fully synthesized+converted, versus
zero completed conversions in the first attempt). Reported honestly,
same as the first. Memory scaling with total text/forward-passes
processed rather than any one call's audio size pointed to PyTorch
autograd graphs accumulating across inference calls that neither
MeloTTS's nor OpenVoice's own code wraps in `no_grad`/`inference_mode`
internally. **Fixed** by wrapping the per-chunk synthesis/conversion
loop in `torch.inference_mode()` — a second, independent fix layered on
top of chunking, again with no effect on narration content or recorded
pipeline fields.

**A third attempt, with both fixes applied, was ALSO genuinely
OOM-killed** — at essentially the identical ~13.9GB ceiling and stopping
point (5 chunks in) as the second attempt. `inference_mode()` did not
fix it, ruling out autograd-graph retention as the (sole) cause and
pointing to memory retained inside PyTorch's/MeloTTS's/OpenVoice's own
native/allocator internals across repeated in-process calls — not
forceable free from within the same process. **Fixed conclusively** by
running each chunk's synthesis/conversion in its own **subprocess**
(`_openvoice_v2_chunk_worker.py`, invoked via `subprocess.run`) — a
subprocess's memory is unconditionally reclaimed by the OS on exit,
regardless of the exact internal cause. The worker receives only a
checkpoint dir, device, language/speaker identifiers, chunk text, and an
already-computed target-embedding path — never the owner's raw sample
path (verified by a dedicated test). Verified standalone first: the
worker was invoked directly against a smoke-test sentence and the
owner's real sample-derived embedding, producing a valid 120,364-byte
WAV with exit code 0, before relying on it for the full run. 4 new tests
cover the worker's existence, no network-capable imports, no
sample-path argument, and that `synthesize()` genuinely delegates to it.
**A fourth attempt, with subprocess isolation applied, SUCCEEDED — no
OOM** (confirmed via `dmesg`: no new `oom-kill` entries since the third,
pre-fix attempt). Real, complete Episode 1 narration: 415.9s (~6m56s)
CPU-only synthesis across 6 subprocess-isolated chunks, 7,122,988 bytes,
161.52s duration (`ffprobe`-verified WAV/PCM 16-bit mono 22,050Hz, mean
volume −32.1dB, peak −4.4dB — no clipping, 5 natural pause gaps of
0.55–0.66s each, no dead air). Replayed through the real
`run_voice_generation()` pipeline (not a second synthesis — the actual
generated bytes): **Voice QA = `PASS`**, `generation_status = GENERATED`,
provider-ready narration measured at 2,930 characters — matching the
independently-computed value exactly (narration integrity confirmed).
`PRODUCTION.md`'s `Production status` correctly advanced
`PRODUCTION_PLANNING` → `VISUAL_PLANNING`.

**The isolated production pipeline (Visual Planner → Assets → Assembler
→ Captions → Thumbnail → Production QA) was then run for real**, directly
(not through `run_full_pipeline()`, which re-runs `CONTENT_REVIEW` —
including the real, still-open Safety escalation — from scratch and
would stop there before ever reaching production; direct-stage calls
are the same pattern Phase 8 itself established). Real providers
throughout: `GeneratedAssetProviderReal` + `WikimediaCommonsRetrievalProvider`
for Assets, `FFmpegVideoRenderer` for Assembler, real Pillow thumbnail
rendering. Result: Assembler produced a real, playable H.264/AAC MP4
(1920×1080, 161.52s, 3,803,778 bytes); Captions and Thumbnail both
genuinely `GENERATED`; **Production QA correctly returned
`REVISION_REQUIRED`** — exactly 2 of ~45 checks failed
(`scene-02.md`/`scene-03.md`: "retrieved asset has real retrieval
evidence"), both for the same pre-existing, already-documented reason
("no real retrieval integration exists this phase"), never a new
regression. The live Wikimedia Commons API genuinely returned "no
usable result found" for both queries this run (a real no-match, not a
rate limit this time) — recorded exactly as returned, neither ever
marked `RETRIEVED`. To produce a complete watchable render for
inspection (mirroring Phase 8's own precedent), a clearly-labeled
`VALIDATION_SUBSTITUTE` illustration was manually attached to those two
scenes' `File reference` field only — their `Generated vs. retrieved`
and `Generation/retrieval status` fields were left exactly as `RETRIEVED`/
`NOT_STARTED`, which is precisely why Production QA still correctly
failed those checks rather than being fooled by the substitute's mere
presence.

**A genuine, honest finding, not fixed (out of this task's scope)**: the
scene timeline's planned total duration (191s, from Producer's own
word-count-based estimate) doesn't match the real OpenVoice V2 audio's
actual duration (161.5s) — the owner's real speaking pace differs from
the planning-time estimate. The final render's length follows the real
audio, not the original plan. No agent currently reconciles this
automatically; noted here rather than hidden.

The canonical Episode 1 directory was confirmed untouched
(`git status --porcelain`) throughout every step of this section.

**Full test suite: 615/615 passing** (599 baseline + 7 provider-routing
+ 5 chunking + 4 subprocess-worker; 2 skipped — the two
checkpoint-specific scenarios that require the isolated venv, same
honest skip pattern already used for ffmpeg-dependent tests elsewhere in
this repository).

## Next task

1. **Content review**: Episode 1 still needs the human owner to read
   `HUMAN_REVIEW.md` and record a Safety `CLEARED`/`NOT_CLEARED` decision
   (`agents/safety/src/human_signoff_cli.py`). Once recorded, the next
   session should run `continue_after_human_safety_review()` (Originality
   on `CLEARED`, nothing further on `NOT_CLEARED`) and go no further.
   **Unchanged by anything in this follow-up** — the owner's voice
   decision above is a completely separate authorization from content
   approval, exactly as `PROVIDER_EVALUATION.md`'s "Human authorization
   boundary" requires.
2. **Owner voice**: provider selected, activated, and validated end to
   end (`VOICE_DECISION = USE_FOR_PRODUCTION`) — full Episode 1
   narration and the full isolated production pipeline both ran for real
   this follow-up (see above). Remaining, not yet done: two RETRIEVED-
   strategy assets (scenes 2–3) still have no real retrieval integration
   (`agents/production_qa/CONTRACT.md`'s own documented, pre-existing
   limitation) — unrelated to voice — and, only once Episode 1's own
   content review independently reaches human approval, producing
   Episode 1's real, canonical production artifacts in the owner's
   voice. Nothing in this follow-up regenerated Episode 1's actual
   canonical production artifacts, approved its content, or authorized
   publishing — everything above ran only against the isolated,
   throwaway validation copy.

Beyond those two: (1) a real `ResearchProvider` implementation (Phase
7G's own deferred follow-up) would give future evidence gaps an
automated closure path; (2) per repeated explicit instruction, observe
what a real, human-reviewed Episode 1 actually needs before building the
Learning Engine, analytics, or any further automation — none of that is
started, and none should be until there is real production experience to
learn from. Publishing remains permanently human-gated per
`CONSTITUTION.md` rule 2, regardless of anything built so far.
