# Project State

Last updated: 2026-09-02

## Phase

**Phase 6 — COMPLETE.** (Automated Review: Fact-Check + Safety +
Originality + Unified Orchestrator.)

Phases 1-5 and every prior Phase 6 component — complete, approved.

## Completed (this final Phase 6 component)

**`agents/orchestrator/`** — thin coordination layer, no review judgment
of its own:
- `CONTRACT.md` — "Important distinction" stated up front (the
  orchestrator decides nothing about safety/factuality/originality, it
  only coordinates); pipeline diagram
  (`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW → AUTOMATED REVIEW
  COMPLETE → HUMAN REVIEW`); execution/stop rules; result model with
  `overall_result` derivation (`PASS`/`REVISION_REQUIRED`/`REJECT`/
  `HUMAN_ESCALATION`/`SYSTEM_ERROR` — the last one justified as an
  infrastructure category, not a sixth reviewer-verdict interpretation);
  what it must never do; apply/dry-run; idempotency (reuse a fresh `PASS`,
  never duplicate attempts, never clear a `REJECT`); error handling
  (review result vs. system error); relationship to the three review
  agents.
- `README.md` — how to run it, module map, how a run works step by step,
  known limitations.
- `src/` (`models.py`, `stages.py`, `freshness.py`, `pipeline.py`,
  `__main__.py`) — stdlib Python, no dependencies. **No `mutate.py`, no
  field whitelist of its own** — it calls
  `agents.researcher.src.pipeline.run_fact_check`,
  `agents.safety.src.pipeline.run_safety_review`, and
  `agents.originality.src.pipeline.run_originality_review` directly, and
  every write under `--apply` happens inside one of those three agents'
  own existing, already-tested path.
- `tests/` — 30 tests, all passing (see table below).

**Documentation:** `SYSTEM.md` (directory structure, pipeline-status
section now explains the automated-review-layer handoff, agent
contracts, out-of-scope list), `README.md` (root), `agents/README.md`
(pipeline sequence updated to show the orchestrator now runs three of the
five stages), `STATE.md` (this file). No template changes were needed —
nothing about the orchestrator required a new template field; it reuses
each agent's existing `REVIEW.md`/`CONTENT_ITEM.md` fields exclusively
through that agent's own code.

## Architecture notes

- **Thin coordination, not a fourth intelligence engine.** `stages.py`
  defines three `StageAdapter`s, each wiring an existing agent's real
  `run_*` function plus its own loader/hashing functions — no evidence,
  signal, or originality logic is reimplemented anywhere in this package.
- **Idempotency via reuse, not re-derivation.** `freshness.py` checks
  whether a stage's latest attempt is already `PASS` with a matching
  content hash (using that agent's own hashing function) before deciding
  whether to invoke it at all. A fresh `PASS` is reused
  (`reused_existing_pass=True`, `executed=False`, no new attempt file);
  a stale or absent one triggers a real invocation, which itself follows
  that agent's own `Multi-pass resolution` rules unchanged.
- **Blocked-stage handling reads the true recorded state.** When a
  stage's own multi-pass gating refuses a new attempt
  (`blocked=True`), the orchestrator looks up the *actual* last-written
  `ReviewRecord` verdict rather than trusting a freshly-recomputed,
  never-written verdict — so a REJECT-terminal or two-consecutive-cap
  block is reported accurately.
- **`overall_result` priority when a stage blocks:** `REJECT` (if the
  blocking stage's verdict is `REJECT`) > `HUMAN_ESCALATION` (if
  `escalate_to_human` is set) > `REVISION_REQUIRED` (plain). The
  `human_escalation` boolean is tracked independently and stays `True`
  even when `overall_result` is labeled `REJECT` — never hidden.
- **`stage_overrides`** is a test-only seam on `run_automated_review`
  (substitutes a stage's `run` callable) used to construct scenarios the
  real agents don't naturally produce (e.g. a synthetic `REJECT` without
  `escalate_to_human`, or a simulated crash) — documented in both
  `CONTRACT.md` and `README.md` as never used in normal operation.

## Tests and results

| # | Case | Test file |
|---|---|---|
| 1 | All three PASS → overall PASS | `test_pipeline_order.py` |
| 2-4 | Fact Check REVISION_REQUIRED/REJECT/HUMAN_ESCALATION → stop | `test_pipeline_order.py` |
| 5-7 | Safety REVISION_REQUIRED/REJECT/HUMAN_ESCALATION → Originality not run | `test_pipeline_order.py` |
| 8-9 | Originality REVISION_REQUIRED/HUMAN_ESCALATION → overall blocked | `test_pipeline_order.py` |
| 10 | Later stages cannot override earlier failures | `test_pipeline_order.py` |
| 11 | Stage execution order always correct | `test_pipeline_order.py` |
| 12 | Skipped stages explicitly reported | `test_pipeline_order.py` |
| 13 | Existing valid PASS reused (apply and dry-run) | `test_idempotency.py` |
| 14 | Changed content causes stale re-review | `test_idempotency.py` |
| 15 | Existing REJECT remains terminal | `test_idempotency.py` |
| 16 | Existing review history not overwritten | `test_idempotency.py` |
| 17 | Dry-run causes no mutation | `test_apply_and_protected_fields.py` |
| 18 | Apply mode respects each reviewer's field whitelist | `test_apply_and_protected_fields.py` |
| 19 | Missing/malformed content → SYSTEM_ERROR, not PASS | `test_error_handling.py` |
| 20 | Reviewer exception → SYSTEM_ERROR, not PASS | `test_error_handling.py` |
| 21 | Orchestrator cannot modify protected fields (no mutate.py at all) | `test_apply_and_protected_fields.py` |
| 22 | No publishing capability exists | `test_apply_and_protected_fields.py` |
| 23 | Human escalation remains visible in final result | `test_error_handling.py` |
| — | End-to-end: real fixture, all 3 agents, reaches AUTOMATED_REVIEW_COMPLETE | `test_integration.py` |
| — | End-to-end: real fixture, early block, later stages never invoked | `test_integration.py` |
| — | Dry run against the real golden sample never writes | `test_integration.py` |

Orchestrator: 30/30 passing. Researcher: 43/43. Safety: 27/27.
Originality: 31/31. **131 tests total across all four agents, 0
regressions.** Run each with `python3 -m unittest discover -s
agents/<name>/tests -t .`.

## Validation performed

1-4. All four suites run individually and pass (43+27+31+30).
5. 131/131 combined, 0 failures.
6. `git status --short content/` — empty; the golden sample was touched
   only read-only (dry run) this phase.
7. Protected-field whitelists confirmed disjoint across all three review
   agents (`{Research state, Fact-check state}` / `{Safety state}` /
   `{Originality state}`, zero overlap) and the orchestrator confirmed to
   have no `mutate.py` module and no direct `write_text`/field-update
   call anywhere in its own source.
8. No "publish" string anywhere in any agent's `src/*.py`, orchestrator
   included.
9. Review history immutability confirmed end-to-end: editing an
   already-PASSed item's `SCRIPT.md` and re-running under `--apply`
   leaves attempt 1's file byte-identical and adds attempt 2, never
   rewriting the former.
10. Stage ordering confirmed always `FACT_CHECK → SAFETY_REVIEW →
    ORIGINALITY_REVIEW`, including when overrides make later stages
    return PASS while an earlier one fails (test 10) — they still never
    run.
11. Early-stop confirmed for every stage and every verdict category
    (`REVISION_REQUIRED`/`REJECT`/`HUMAN_ESCALATION`) at each of the
    three stages.
12. Stale-review handling confirmed: content hash mismatch after a
    `SCRIPT.md` edit correctly triggers a fresh attempt instead of a
    reuse.
13. Human escalation confirmed to remain visible (`human_escalation`
    field) even when `overall_result` is labeled `REJECT`.
14. Repository consistency: no orphaned references, golden sample intact,
    all four agents' whitelist boundaries hold.

## Known limitations

Researcher, Safety, Originality: unchanged from their respective phases.

Orchestrator (see `agents/orchestrator/README.md` for full detail):
- Freshness checking re-loads and re-hashes each stage's bundle even when
  the result turns out to be reused — cheap at this scale, a known
  inefficiency rather than a correctness issue.
- No persistence of its own between runs — every `OrchestratorResult` is
  computed fresh from the agents' own on-disk state, which is also why
  it's safe to run repeatedly.
- `EDITORIAL_REVIEW` and `PRODUCTION_QA` have no agent yet, so the
  orchestrator's pipeline currently only ever reaches
  `ORIGINALITY_REVIEW`/`AUTOMATED_REVIEW_COMPLETE` — it cannot coordinate
  stages that don't exist.
- Never advances `status` to `HUMAN_REVIEW` or anywhere else — reaching
  `AUTOMATED_REVIEW_COMPLETE` is informational only; a human still drives
  every step from there on, per `CONSTITUTION.md`.
- Not run with `--apply` against the real golden sample as part of this
  phase (same deliberate deferral as every individual agent).

## Next task

**Phase 7 — Production Stack** (per the roadmap), covering
`SCRIPT → VOICE → VISUAL PLAN → ASSETS → VIDEO ASSEMBLY → CAPTIONS →
THUMBNAIL → TITLE/DESCRIPTION → PRODUCTION QA → HUMAN REVIEW`. Not
started this phase, per explicit instruction. Before implementation
begins, Phase 7 will need its own contract(s) — likely starting with
defining what "voice" and "visual plan" mean as structured content-item
records (mirroring how `templates/SCRIPT.md` etc. were defined before any
agent touched them) — and, as with every prior phase, no automated
publishing authority may be introduced at any point in that stack; the
human owner remains the final gate before anything reaches `PUBLISHED`.
