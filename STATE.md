# Project State

Last updated: 2026-09-02

## Phase

**Phase 6 — Automated Review: Safety Reviewer — complete.**

Phases 1-5 (foundational docs, content-item schema, golden sample
validation, agent contracts, MVP Research/Fact-Check pipeline) —
complete, approved.

## Completed (Phase 6)

**Step 0 — Golden sample `c5` correction**, via the established
immutable-claim/supersession mechanism (not a silent edit):
- `claims/c5.md` — table left byte-identical; trailing "Superseded" note
  appended pointing to `c12` (violation: two sentences, confirmed via
  `agents/researcher/src/atomicity.py`).
- `claims/c12.md` — new atomic successor: same `ASSUMPTION`, same
  exclusion list, one sentence. `c5`'s redundant second sentence was not
  carried forward as its own claim (documented reasoning in `c12.md` and
  `AUDIT.md`'s Phase 6 addendum: it asserted nothing beyond what `c2`/`c11`
  already establish as `FACT`).
- References updated: `claims/c6.md`'s `Derived from` field (c5→c12; its
  `Exact claim`/`Evidence` prose deliberately left untouched — `c5.md`
  still resolves via its Superseded note); `claims/c3.md`/`c2.md`'s
  trailing commentary; `SCRIPT.md`'s `Verified claims` table and
  ASSUMPTION bullet; `CONTENT_ITEM.md`'s linked-records list and
  Notes/history log; `AUDIT.md`'s new Phase 6 addendum.
- Re-validated: atomicity is clean for all 11 active claims (only the
  superseded `c5` itself still shows its original violation, correctly,
  since it's out of the active review set); all 43 Researcher tests
  still pass; no claim's `Classification`/`Exact claim` table field was
  altered anywhere in the fix.

**Step 1-6 — Safety Reviewer contract and MVP** (`agents/safety/`):
- `CONTRACT.md` — independent SAFETY_REVIEW-stage contract: purpose,
  inputs/outputs, allowed/forbidden actions (protected fields), the
  twelve-signal model, risk levels, verdict derivation, human escalation
  rules, conservatism principle, failure conditions, exact handoff,
  relationship to `agents/researcher`.
- `README.md` — how to run it, module map, design decisions, known
  limitations.
- `src/` (`models.py`, `loader.py`, `signals.py`, `review.py`,
  `hashing.py`, `review_writer.py`, `mutate.py`, `pipeline.py`,
  `__main__.py`) — stdlib Python, no dependencies. Reuses only
  `agents/researcher/src`'s generic, role-agnostic infrastructure
  (parsing, `ReviewVerdict`/`ReviewRecord`/`ContentItem`/`Classification`
  models, multi-pass gating functions, failure-condition exceptions,
  `append_notes_log`) — never its fact-check domain logic. Each agent
  remains independently runnable.
- `tests/` — 27 tests, all passing (see table below).

**Step 7 — Integration interface** (no orchestrator built): `agents/README.md`
now documents the five-stage pipeline sequence and the shared result
shape (`verdict`/`reasons`/`required_changes`/`escalate_to_human`/
`content_hash`/`aborted`/`blocked`/`review_path`) both `run_fact_check`
and `run_safety_review` already return, so a future orchestrator can
drive any stage without knowing its internals.

**Step 8 — Documentation:** `SYSTEM.md` (directory structure, current
phase, agent contracts section, out-of-scope list), `README.md` (root —
also caught up to reflect Phase 5, which had been missed), `agents/README.md`,
`STATE.md` (this file). No template changes were needed this phase beyond
Step 0's content-only fix — `templates/REVIEW.md`'s `SAFETY_REVIEWER`
role and `templates/CONTENT_ITEM.md`'s `Safety state` field already
existed from Phase 2.

## Tests and results

| # | Case | Test file |
|---|---|---|
| 1-4 | Business/history/technology PASS, labeled What If? PASS | `test_pass_scenarios.py` |
| 5 | Dangerous instruction → REJECT | `test_signal_detection.py` |
| 6 | Illegal facilitation → REJECT | `test_signal_detection.py` |
| 7 | Synthetic media → disclosure/review signal | `test_signal_detection.py` |
| 8 | Impersonation → REVISION_REQUIRED | `test_signal_detection.py` |
| 9 | Misleading what-if title → REVISION_REQUIRED | `test_signal_detection.py` |
| 10 | Unsupported certainty in hypothetical content → REVISION_REQUIRED | `test_signal_detection.py` |
| 11 | Ambiguous (defamation) → escalate, never PASS | `test_signal_detection.py` |
| 12 | Existing failure (REJECT) not silently cleared | `test_multipass.py` |
| 13 | PASS becomes stale on content change | `test_multipass.py` |
| 14 | Review attempts immutable/sequential | `test_multipass.py` |
| 15 | Protected fields cannot be modified | `test_protected_fields.py` |
| 16 | Dry-run does not modify content | `test_pipeline_apply.py` |
| 17 | Apply mode modifies only permitted fields | `test_pipeline_apply.py` |

Researcher: 43/43 passing (unchanged). Safety: 27/27 passing. Run:
`python3 -m unittest discover -s agents/researcher/tests -t .` and
`python3 -m unittest discover -s agents/safety/tests -t .`.

## Safety boundaries verified (Step 9)

1. All 43 Researcher tests pass.
2. All 27 Safety tests pass.
3. Cross-repo consistency: 89 tracked files, no orphaned references
   found (see validation transcript).
4. `c5` correction verified: atomicity clean for all 11 active claims;
   `c5` itself still correctly shows its original violation (superseded,
   not in the active set).
5. No claim's `Classification`/`Exact claim` table field changed anywhere
   — `git diff` on every touched claim file shows only trailing-prose and
   `Derived from` changes.
6. No fabricated sources: the only 3 URLs anywhere in the golden sample
   are the same WHO/Oxford/Britannica ones verified live in Phase 3.
7. No publishing authority: no executable code anywhere in `agents/`
   contains publish-capable logic.
8. Safety's `CONTENT_ITEM_WRITABLE_FIELDS` is exactly `{'Safety state'}`;
   it has no `update_claim_field` function at all — structurally cannot
   write to a claim file.
9. PASS-staleness confirmed end-to-end on a scratch copy: editing
   `SCRIPT.md` after a review changes the recomputed hash, correctly
   diverging from the stored `Reviewed content hash`.
10. Review history confirmed immutable/sequential end-to-end: two
    `--apply` runs on a scratch copy produced `safety_reviewer-1.md` and
    `safety_reviewer-2.md`, with attempt 1's file unchanged after
    attempt 2 ran.

All scratch/tempdir verification used disposable copies — the real
golden sample's only changes this phase are the intentional Step 0
`c5`/`c12` correction (`git status --short content/` confirms nothing
else was touched).

## Known limitations

Researcher: unchanged from Phase 5 (see `agents/researcher/README.md`).

Safety Reviewer (see `agents/safety/README.md` for full detail):
- Pattern/keyword detection only for 8 of 12 signals — not exhaustive,
  will miss subtler real cases; `LOW_RISK` means "no known pattern
  matched," not "confirmed safe."
- `DEFAMATION` and `SENSITIVE_CONTENT` never resolve above
  `REVIEW_REQUIRED` by design — always human judgment, never an automatic
  clearance or automatic reject.
- `TITLE_THUMBNAIL_MISREPRESENTATION` only inspects title text; no
  thumbnail image exists yet at this pipeline stage.
- No orchestrator exists to run RESEARCH→FACT_CHECK→SAFETY_REVIEW→...
  automatically — each agent is invoked independently, by design, this
  phase.
- The Safety Reviewer has not been run with `--apply` against the real
  golden sample (same deliberate deferral as the Researcher in Phase 5,
  to avoid changing its Phase 3-era status commentary as a side effect of
  building the agent).

## Next task

**Phase 6 continuation, per the roadmap:** build the Originality Reviewer
(its own `agents/originality/CONTRACT.md` + MVP, following the same
independent-agent, reused-infrastructure pattern as Safety), then the
unified Automated Review Orchestrator that actually drives
RESEARCH/FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW →
EDITORIAL_REVIEW → PRODUCTION_QA in sequence using the shared interface
`agents/README.md` now documents. Still no video production, no YouTube
publishing, no learning engine. Every stage remains bounded by
`CONSTITUTION.md`: no agent gets `status`/`Owner approval` authority, and
no automated publishing exists at any point in this chain.
