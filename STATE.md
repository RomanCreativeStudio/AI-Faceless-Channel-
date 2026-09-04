# Project State

Last updated: 2026-09-03

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE** (unchanged).
**Phase 7C-1 — Voice Generation MVP — COMPLETE** (unchanged).
**Phase 7C-2 — Asset Generation / Retrieval MVP — COMPLETE** (unchanged).
**Phase 7D — Video Assembly + Captions + Thumbnail + Production QA — COMPLETE** (unchanged).
**Phase 7E — Full Pipeline Orchestration + Self-Review Loop — COMPLETE** (unchanged).
**Phase 7F — Autonomous Revision Engine (Research/Fact-Check) — COMPLETE.**

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

## Next task

No further phase was specified as the "exact next task" by this phase's
own instructions beyond delivering this report and, if logically defined,
naming the next one. Two natural, not-yet-scoped continuations exist:
(1) extending Autonomous Revision Mode's evidence-linkage-repair pattern
to `agents/safety/`/`agents/originality/` where a genuinely safe,
narrow, deterministic fix exists for either (none has been identified
yet — this would need its own careful evidence-rules analysis, not a
blind copy of this phase's pattern); (2) a RESEARCH-mode implementation
that would make substantially more `FACT_CHECK` failures genuinely
fixable by giving this phase's revision engine real new evidence to work
with, not just already-existing evidence to re-link. Neither is started.
Publishing remains permanently human-gated per `CONSTITUTION.md` rule 2,
regardless of anything built so far.
