# Project State

Last updated: 2026-09-02

## Phase

**Phase 6 (continuation) — Automated Review: Originality Reviewer — complete.**

Phases 1-5 and the Safety Reviewer portion of Phase 6 — complete,
approved.

## Completed (this continuation)

**`agents/originality/`** — third independent agent, ORIGINALITY_REVIEW
stage only:
- `CONTRACT.md` — core principle stated up front (not a plagiarism
  lawyer, never a legal determination, never "100% original"); inputs
  (current item, channel metadata, script, title, hook, source records,
  optional reference material); outputs/allowed/forbidden actions
  (protected fields: claims, classifications, research evidence, owner
  approval, publishing/content status, safety state, fact-check state);
  the eight-signal model; risk levels; verdict derivation (no signal ever
  reaches `REJECT` — reserved for structural failures only, exactly like
  the other two agents); human escalation rules; failure conditions;
  exact handoff; relationship to `agents/researcher`/`agents/safety`.
- `README.md` — how to run it, module map, the eight signals' detection
  method, the "important distinctions" the MVP is built to respect
  (similar topic ≠ copied, common knowledge ≠ copying, etc.), known
  limitations.
- `src/` (`models.py`, `loader.py`, `signals.py`, `review.py`,
  `hashing.py`, `review_writer.py`, `mutate.py`, `pipeline.py`,
  `__main__.py`) — stdlib Python, no dependencies, no external APIs.
  Reuses only `agents/researcher/src`'s generic infrastructure (parsing,
  `ReviewVerdict`/`ReviewRecord`/`ContentItem`/`Classification`,
  `load_claims`/`load_research`/`load_reviews`, multi-pass gating,
  failure exceptions, `append_notes_log`) — nothing from `agents/safety`
  at all (siblings, not dependents).
- `tests/` — 31 tests, all passing (see table below).

**Documentation:** `SYSTEM.md`, `README.md` (root), `agents/README.md`,
`STATE.md` (this file) updated to reflect three working agents. No
template changes were needed — `templates/REVIEW.md`'s
`ORIGINALITY_REVIEWER` role and `templates/CONTENT_ITEM.md`'s
`Originality state` field already existed from Phase 2.

## Architecture notes

- **Signal model:** `INTERNAL_DUPLICATION`, `CONCEPT_DISTINCTIVENESS`,
  `FRAMING_DISTINCTIVENESS`, `SCRIPT_DISTINCTIVENESS`,
  `SOURCE_DEPENDENCE`, `TEMPLATE_REPETITION`,
  `TITLE_HOOK_DISTINCTIVENESS`, `EXTERNAL_SIMILARITY_RISK` — each
  independently `NOT_APPLICABLE`/`LOW_RISK`/`REVIEW_REQUIRED`/`HIGH_RISK`,
  all deterministic/lexical (word-set Jaccard overlap, curated stock-
  phrase lists, source counts) — no semantic embeddings, no NLP, no
  external API, explicitly documented as such.
- **Verdict derivation:** structural failures (missing claim file cited
  by script, invalid classification) → `REJECT`; any signal `HIGH_RISK` →
  `REVISION_REQUIRED` (never `REJECT` — no content-similarity finding
  ever reaches it, by design); any `REVIEW_REQUIRED` → at least
  `REVISION_REQUIRED` plus `escalate_to_human=True`; all clear → `PASS`.
- **Structured inputs:** current content item, auto-discovered or
  explicitly-supplied "channel metadata" (`ChannelItemSummary` list, via
  `discover_channel_index()` scanning sibling `content/<pillar>/*/
  CONTENT_ITEM.md` files or an explicit override), script, claims,
  research, and optional supplied reference files (`--reference` /
  `reference_paths`) — never a live web search.
- **Clean extension seam:** `signals.py` exposes one pure function per
  signal, each taking the same `OriginalityBundle`; a future semantic-
  similarity implementation can replace/augment any one signal without
  touching verdict derivation, orchestration, or the others.

## Tests and results

| # | Case | Test file |
|---|---|---|
| 1-4 | Business/history/technology PASS, labeled What If? PASS | `test_pass_scenarios.py` |
| 5 | Duplicate internal topic → REVISION_REQUIRED | `test_signal_detection.py` |
| 6 | Reused hook → REVISION_REQUIRED | `test_signal_detection.py` |
| 7 | Excessive source dependence → REVISION_REQUIRED | `test_signal_detection.py` |
| 8 | Generic AI-style framing → flagged, not PASS/REJECT | `test_signal_detection.py` |
| 9 | High similarity to reference material → REVIEW_REQUIRED/HIGH_RISK | `test_signal_detection.py` |
| 10 | Shared historical facts, distinct angle → NOT auto-fail | `test_signal_detection.py` |
| 11 | Similar format, distinct content → NOT auto-fail | `test_signal_detection.py` |
| 12 | Ambiguous similarity → escalate, never silently PASS | `test_signal_detection.py` |
| 13 | Protected fields cannot be modified | `test_protected_fields.py` |
| 14 | PASS becomes stale on content/reference-material change | `test_multipass.py` |
| 15 | Review attempts immutable/sequential | `test_multipass.py` |
| 16 | Dry-run makes no mutations | `test_pipeline_apply.py` |
| 17 | Apply mode modifies only permitted fields | `test_pipeline_apply.py` |
| 18 | Never claims comprehensive internet-wide detection | `test_signal_detection.py` |

Originality: 31/31 passing. Researcher: 43/43 (unchanged). Safety: 27/27
(unchanged). **101 tests total across all three agents, 0 regressions.**
Run: `python3 -m unittest discover -s agents/originality/tests -t .`
(and the equivalent for `researcher`/`safety`).

## Validation performed

1. All 43 Researcher tests pass.
2. All 27 Safety tests pass.
3. All 31 Originality tests pass.
4. Cross-repo consistency: `git status --short content/` shows zero
   changes — the golden sample was touched only read-only (dry runs) by
   this continuation; the actual `--apply` scratch verification below
   used disposable copies.
5. Protected fields confirmed structurally, not just by test: Originality's
   `CONTENT_ITEM_WRITABLE_FIELDS` is exactly `{'Originality state'}`; it
   has no `update_claim_field`/`update_research_field` function at all.
6. PASS-staleness confirmed end-to-end on a scratch copy: editing
   `SCRIPT.md`, and separately editing supplied reference material,
   both change the recomputed hash.
7. Immutable/sequential review history confirmed end-to-end on a scratch
   copy: two `--apply` runs produced `originality_reviewer-1.md` and
   `-2.md`, attempt 1 unchanged after attempt 2.
8. No publishing authority: no executable code anywhere in `agents/`
   (all three agents) contains publish-capable logic.
9. No unsupported plagiarism-detection claims: `EXTERNAL_SIMILARITY_RISK`
   against the real golden sample (no reference material supplied)
   returns `NOT_APPLICABLE` with the reason stating plainly that no
   internet-wide search was performed — confirmed by test and by direct
   inspection of the live result.
10. Golden sample remains valid: re-ran Researcher's 43 tests (which
    include golden-sample-specific assertions on `c11`/`c5`/`c12`) with
    no changes needed.

## Known limitations

Researcher and Safety: unchanged from their respective phases (see their
own READMEs).

Originality (see `agents/originality/README.md` for full detail):
- All eight signals are lexical/structural (word-set Jaccard, stock
  phrases, source counts) — no semantic understanding. Can miss a close
  paraphrase that avoids shared vocabulary, and can't fully distinguish
  coincidental shared wording from genuine derivation.
- `EXTERNAL_SIMILARITY_RISK` only ever compares against explicitly
  supplied files — never fetches anything, never implies broader
  coverage than what it was actually given.
- `channel_index` auto-discovery only sees content already checked into
  this repo's `content/` tree — no memory of anything else.
- No orchestrator exists yet to run RESEARCH→FACT_CHECK→SAFETY_REVIEW→
  ORIGINALITY_REVIEW→... automatically — each agent still invoked
  independently, by design, this phase.
- Not run with `--apply` against the real golden sample (same deliberate
  deferral as the other two agents).

## Next task

**Phase 6 completion, per the roadmap:** the Unified Automated Review
Orchestrator — a thin driver that calls `run_fact_check` →
`run_safety_review` → `run_originality_review` in sequence against a
content item, using the shared result shape `agents/README.md` documents,
stopping and surfacing `escalate_to_human` at the first stage that isn't
`PASS`. Still no video production, no YouTube publishing, no learning
engine, and no new agent gets `status`/`Owner approval` authority — the
orchestrator only ever reads verdicts and stops; it does not gain any
authority beyond what each individual agent already has.
