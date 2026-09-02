# Project State

Last updated: 2026-09-02

## Phase

**Phase 5 — MVP Research / Fact-Check Pipeline: complete.**

Phases 1-4 (foundational docs, content-item schema, golden sample
validation, agent contracts) — complete, approved.

## Completed (Phase 5)

**Template changes (made and documented before implementing, per the task
instructions):**
- `templates/REVIEW.md` — added `Reviewed content hash` field, closing
  the hashing gap Phase 4 explicitly deferred to "agent implementation."
  Multi-pass resolution rule 4 (PASS staleness) now names the exact hash
  algorithm and points at `agents/researcher/src/hashing.py`.
- `agents/researcher/CONTRACT.md` — added an "Implementation notes (Phase
  5)" section: the `EvidenceSupport` vocabulary (`SUPPORTED` /
  `PARTIALLY_SUPPORTED` / `UNSUPPORTED` / `CONTRADICTED` / `UNRESOLVED`)
  the task asked for is computed, not a new persisted `CLAIM.md` field —
  it's compatible with the existing templates without a schema change
  (surfaced in `REVIEW.md`'s `Reasons`/JSON output instead); and the exact
  verdict-derivation order the implementation follows.
- `templates/CLAIM.md`/`CONTENT_ITEM.md` — **not** changed further; Phase
  4's Atomicity and Multi-pass rules already covered what Phase 5 needed
  to implement against.

**Implementation** (`agents/researcher/src/`, stdlib Python, no
dependencies): `models.py`, `parsing.py`, `loader.py`, `atomicity.py`,
`evidence.py`, `factcheck.py`, `multipass.py`, `hashing.py`,
`review_writer.py`, `mutate.py`, `pipeline.py`, `__main__.py`, `errors.py`.
Implements `CONTRACT.md`'s FACT_CHECK mode end-to-end: load a content
item -> load research/claims -> validate structure (Atomicity rule) ->
evaluate evidence (separated from fact-check status per the task's
explicit design rule) -> derive a verdict -> write a `REVIEW.md` ->
update only `Fact-check state` + Notes/history log. RESEARCH mode
(source collection) is **not** implemented — out of scope per the task.

**Tests** (`agents/researcher/tests/`, 43 tests, all passing): covers all
15 required cases plus structural-failure and apply-mode integration
coverage — see below.

**Documentation:** `agents/researcher/README.md` (how to run it, module
map, design decisions, known limitations); `SYSTEM.md` updated (directory
structure, current phase, out-of-scope list); `STATE.md` (this file).

## Tests created (all 15 required cases, plus extras)

| # | Case | Test |
|---|---|---|
| 1-4 | Valid FACT/ASSUMPTION/INFERENCE/SPECULATION claims | `test_atomicity.py` |
| 5 | Compound claim rejection | `test_atomicity.py` (uses the real pre-split `c3` text as a regression fixture) |
| 6 | Missing source detection | `test_evidence.py` |
| 7 | Unsupported claim detection | `test_evidence.py` |
| 8 | Contradictory evidence detection | `test_evidence.py` |
| 9 | Classification preservation | `test_evidence.py` |
| 10 | Immutable claim correction/supersession | `test_mutate.py` |
| 11 | REVISION_REQUIRED behavior | `test_multipass.py`, `test_pipeline_apply.py` |
| 12 | Two autonomous attempts -> human escalation | `test_multipass.py`, `test_pipeline_apply.py` (end-to-end) |
| 13 | REJECT terminal behavior | `test_multipass.py` |
| 14 | PASS staleness on artifact change | `test_multipass.py` |
| 15 | C11 unresolved, no fabricated evidence | `test_pipeline.py` (against the real golden sample) |

Extra coverage: field-writer whitelist enforcement (`test_mutate.py`),
structural failures — missing claim file, invalid classification, total
retrieval failure (`test_structural_failures.py`), determinism and
dry-run-doesn't-touch-disk (`test_pipeline.py`).

Run: `python3 -m unittest discover -s agents/researcher/tests -t .`

## Test results

43/43 passing. Verified: fixture and golden-sample directories are
byte-unchanged after the full suite runs (`git status --short content/`
clean) — all mutation tests operate on `tempfile`/`shutil.copytree`
copies, never the real fixture or golden sample.

## Safety boundaries verified

- **Never fabricates evidence.** Running against the real golden sample,
  `c11` (no dedicated source, per the C11 sourcing rule in this phase's
  instructions) evaluates to `UNRESOLVED` / `UNVERIFIED`, named explicitly
  in `Reasons`, with `Supporting sources` left `N/A` — confirmed by test
  and by manual inspection of the rendered `REVIEW.md`.
- **Never silently changes a claim's classification.** `evidence.py`
  never writes to `claim.classification`; `mutate.py`'s
  `update_claim_field` structurally refuses (`PermissionError`) any field
  outside `{Fact-check status, Evidence, Contradictory evidence,
  Confidence level}` — `Classification` and `Exact claim` are not in that
  set, so writing them is a programming error, not a runtime choice.
  Correcting a claim only works via `supersede_claim`, which creates a new
  file and leaves the old claim's table byte-identical.
- **Never publishes, never touches Owner approval or `status`.**
  `mutate.py`'s `CONTENT_ITEM_WRITABLE_FIELDS` whitelist is
  `{Research state, Fact-check state}` only — `status` and `Owner approval
  state` cannot be written through this codebase at all. No code path
  contains the word "publish" in an executable sense.
  `CONTENT_ITEM_WRITABLE_FIELDS`/`CLAIM_WRITABLE_FIELDS` are the same set
  named in `CONTRACT.md`'s Allowed actions.
- **Multi-pass rules enforced, not just documented.** `REJECT` blocks any
  new attempt until `HUMAN_REOPEN: <ROLE>` appears in Notes/history log;
  two consecutive `REVISION_REQUIRED` verdicts block a third automated
  attempt (`can_run_new_attempt`); a stale `PASS` (content hash mismatch)
  reads back as `REVISION_REQUIRED` (`effective_stage_state`).
- **Never auto-`FALSE`, never clears a prior `FALSE`.** Contradicted
  evidence resolves to `DISPUTED`; a claim already marked `FALSE` stays
  `FALSE` regardless of what re-evaluation would otherwise compute.

## Schema changes made this phase

- `templates/REVIEW.md`: new `Reviewed content hash` field (see above).
- `agents/researcher/CONTRACT.md`: new "Implementation notes (Phase 5)"
  section (see above). No changes to `templates/CLAIM.md`,
  `templates/CONTENT_ITEM.md`, `templates/RESEARCH.md`,
  `templates/SCRIPT.md`, or `CONSTITUTION.md`.

## Known limitations

- FACT_CHECK mode only — RESEARCH mode (source collection/live retrieval)
  is not implemented; `loader.load_research()` reads local files, and the
  seam for a future live-retrieval implementation is documented but not
  built (no crawler, per the task's explicit instruction).
- No semantic/NLP comparison of claim text to source text — evaluation is
  structural-signal only (source existence, reciprocal citation, source
  reliability, presence of contradictory evidence, `Derived from` chain
  integrity). Documented as a deliberate MVP boundary in
  `agents/researcher/README.md`, not a bug.
- `INFERENCE`/`SPECULATION` claims always resolve to `Fact-check status:
  NOT_APPLICABLE`, even when their evidence support is computed as
  `CONTRADICTED` — allowed by `CONTRACT.md` but a future version could be
  more precise.
- The two-consecutive-`REVISION_REQUIRED` cap counts verdicts, not
  "same underlying issue" as `CONTRACT.md` phrases it — distinguishing
  which issue would need comparing `Reasons` text across attempts.
- Markdown table parser assumes no cell value contains a literal `|`
  (true of every file in this repo today).
- Running the MVP (dry run) against the real golden sample surfaced a
  genuine, previously-unnoticed Atomicity rule violation in `claims/c5.md`
  (two sentences) — left as-is deliberately; that is what
  `REVISION_REQUIRED` is for, not something to patch mid-implementation.
  The golden sample itself was **not** modified by this phase — it was
  only read (dry run) and, separately, exercised via `--apply` against
  disposable copies in tests. A real `--apply` run against the committed
  golden sample (which would update its `Fact-check state` and its
  Phase-3-era "stops before FACT_CHECK" status commentary) is left for a
  deliberate follow-up, not a side effect of building the agent.

## Next task

**Phase 6 — Automated Review**, per the roadmap. Likely scope: run the
Phase 5 agent for real (`--apply`) against the golden sample as its first
production use, reconcile the resulting `Fact-check state`/Notes-log
change with the sample's Phase 3/4 documentation ("stops before
FACT_CHECK"), and design/implement the next reviewer role's contract
(most plausibly `SAFETY_REVIEWER`, since `FACT_CHECK` -> `SAFETY_REVIEW`
is the next pipeline handoff with no agent contract yet). Still bounded by
`CONSTITUTION.md`: no automated publishing, no `status`/`Owner approval`
authority for any agent, human sign-off remains required before any
verdict this system produces reaches `APPROVED`.
