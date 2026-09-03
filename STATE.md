# Project State

Last updated: 2026-09-03

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged this
phase; contracts + schema + golden fixture, no implementation).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE.**

## Completed (Phase 7B)

**Step 1 — Inspection:** re-read `CONSTITUTION.md`, `templates/PRODUCTION.md`/
`SCENE.md`/`ASSET.md`/`VOICE.md`, `agents/producer/CONTRACT.md`,
`agents/visual-planner/CONTRACT.md`, the existing Researcher/Safety/
Originality/Orchestrator implementations, and the Phase 7A golden
production fixture before writing any code. Found and fixed three
genuine gaps before implementation started, all documented in place
rather than silently worked around:
- `agents/visual-planner/` is an invalid Python package name (hyphens
  aren't legal in module identifiers) — renamed to `agents/visual_planner/`
  via `git mv`, then every markdown reference to the old path (9 files)
  updated via a verified `sed` pass that touched only path/directory
  references, never the prose name "Visual Planner."
- The Visual Planner's contract required `Production status =
  VISUAL_PLANNING`, reachable only after `agents/voice/` (no
  implementation, Phase 7C) — which would make it permanently unrunnable
  and contradict this phase's own required Producer→Visual Planner
  integration test. Fixed with an explicitly-labeled Phase 7B interim
  allowance permitting `PRODUCTION_PLANNING` too, to be removed once
  `agents/voice/` exists.
- Producer's and Visual Planner's contracts both claimed ownership of
  `PRODUCTION.md`'s Visual requirements/Asset references rollups.
  Resolved: Producer only initializes them as placeholders; Visual
  Planner is the one that populates real content — documented in both
  `CONTRACT.md` files.

**Step 2 — Producer MVP** (`agents/producer/src/`):
- `duration.py` — deterministic `estimate_duration_seconds(text,
  words_per_minute)`; `words_per_minute` is always an explicit parameter
  (`run_producer(..., words_per_minute=...)`, CLI `--wpm`) —
  `DEFAULT_WORDS_PER_MINUTE = 150` is only the fallback.
- `scene_builder.py` — Hook (if present) becomes scene 1; each
  `## Narrative beats` numbered item becomes its own scene, in order, no
  condensation. A beat's trailing `` — claims: `c1`, `c2` `` suffix is
  parsed for claim references, cross-validated against `claims/*.md`
  (missing claim → `StructuralFailure`, reused directly from
  `agents/researcher/src/errors.py` — never invents a claim). No
  `## Narrative beats` section at all → `NoLoadableContent` (also
  reused, never researcher's fact-check domain logic).
- `hashing.py` — `sha256(SCRIPT.md)`, reused directly by Visual Planner.
- `mutate.py` — hard-coded path whitelist: `PRODUCTION.md` (root) and
  `scenes/scene-<n>.md` only, and only ever as fresh files.
- `pipeline.py` (`run_producer(root, apply=False, words_per_minute=150)`)
  — gates on `CONTENT_ITEM.md` `status == APPROVED` (structured `blocked`
  result otherwise, no mutation); if `PRODUCTION.md` already exists, a
  matching `Script content hash` is a no-op, a mismatched one returns a
  structured `stale` result and leaves existing files untouched — no
  versioned supersession built (see "Known limitations").
- 20 tests (`agents/producer/tests/`), all isolated fixtures, real golden
  sample confirmed untouched.

**Step 3 — Visual Planner MVP** (`agents/visual_planner/src/`):
- `classification.py` — the Visual Safety Rule, deterministic from claim
  `Classification` alone: no claim references → `ON_SCREEN_TEXT_GRAPHIC`/
  `NOT_APPLICABLE`; all claims `FACT` → `ARCHIVAL_IMAGE`/
  `AUTHENTIC_HISTORICAL_MEDIA` (sourcing intent only — `Verification
  status` stays `NOT_STARTED`, mirroring the Phase 7A golden fixture's
  `asset-02.md` pattern); any `ASSUMPTION`/`INFERENCE`/`SPECULATION` claim
  → `GENERATED_RECONSTRUCTION` unconditionally, never
  `AUTHENTIC_HISTORICAL_MEDIA`.
- `pipeline.py` (`run_visual_planner(root, apply=False)`) — requires
  `PRODUCTION.md` `Production status` in `{VISUAL_PLANNING,
  PRODUCTION_PLANNING}` (the interim allowance); re-verifies `SCRIPT.md`'s
  hash against `PRODUCTION.md`'s stored one (reusing Producer's
  `hashing.py` directly) and blocks if stale; blocks (never guesses) if a
  scene cites a claim with no `claims/*.md` file ("missing provenance").
  **Defense-in-depth found during implementation:** the interim allowance
  means `Production status` alone can't tell a real approved production
  apart from a hand-built schema fixture with a matching status/hash —
  exactly the Phase 7A golden `PRODUCTION.md` fixture's situation (its
  `CONTENT_ITEM.md` status is `SCRIPT`, never `APPROVED`). Added a second
  check requiring `CONTENT_ITEM.md`'s own status to be `APPROVED`
  whenever that file is present, closing the gap rather than relying on
  the interim allowance alone — documented in `CONTRACT.md`.
- `mutate.py` — hard-coded whitelist: a scene's `Visual type`/`Visual
  description`/`Asset requirement` only, new `assets/asset-<n>.md` files,
  and `PRODUCTION.md`'s two rollup sections + `Production status`
  (advanced to `ASSET_COLLECTION` once every scene is planned).
- 18 tests (`agents/visual_planner/tests/`), all isolated fixtures built
  by running the real Producer first (never hand-rolled), real golden
  sample confirmed untouched (dry-run only, for the reason below).

**Step 4 — Isolated test fixtures:** no committed "TEST FIXTURE — APPROVED"
file was needed — every test builds its own fresh, isolated, `status =
APPROVED` content item in a `tempfile.TemporaryDirectory()`
(`agents/producer/tests/builders.py`, reused by
`agents/visual_planner/tests/builders.py` via the real `run_producer()`
call rather than hand-rolled `PRODUCTION.md`/scene files). The real
golden sample's `status` remains `SCRIPT`, untouched.

**Step 5 — Documentation:** `agents/producer/README.md`,
`agents/visual_planner/README.md` (rewritten from Phase 7A's
"not implemented yet" stubs to describe the real MVP architecture,
CLI usage, and known limitations), `SYSTEM.md`, `README.md` (root),
`agents/README.md`, `STATE.md` (this file).

## Validation performed

1. `agents/producer/tests/` — 20/20 pass: approved→plan, unapproved→
   blocked (no mutation), golden sample never modified, script hash
   recorded, script change→stale (existing files untouched), unchanged
   script re-run is a no-op, stable/ordered scene IDs, narration
   preserved verbatim, claim references carried into scenes, What If?
   classification rollup preserved, deterministic WPM-driven duration,
   dry-run makes zero mutation, apply writes only `PRODUCTION.md`+
   `scenes/*.md`, `mutate.py` rejects a non-whitelisted filename, apply
   never touches `CONTENT_ITEM.md`, malformed script (no Narrative beats)
   fails safely, missing claim reference fails safely, claims are never
   invented or altered.
2. `agents/visual_planner/tests/` — 18/18 pass: every scene gets an
   explicit classification, `ASSUMPTION`→`GENERATED_RECONSTRUCTION`,
   all-`FACT`→`AUTHENTIC_HISTORICAL_MEDIA` (intent only, `Verification
   status` still `NOT_STARTED`), no-claim scene→`NOT_APPLICABLE`,
   `SPECULATION`→`GENERATED_RECONSTRUCTION`, missing claim provenance
   blocks rather than guessing, non-`APPROVED` `CONTENT_ITEM.md` blocks
   even when `PRODUCTION.md`'s own status would otherwise allow it, claim
   relationship preserved, protected scene fields (identity, narration,
   caption, status) byte-identical after apply, dry-run makes zero
   mutation, apply touches only the whitelisted fields/files, narration
   and claims are never altered, full Producer→Visual Planner
   integration (5 scenarios: end-to-end plan, valid handoff, consistent
   script hash, a blocked Producer leaves nothing for the Visual Planner
   to act on, golden sample untouched end-to-end).
3. Combined suite — `python3 -m unittest discover -s agents -t . -p
   "test_*.py"` — **169/169 pass, 0 regressions** (131 pre-existing +
   20 Producer + 18 Visual Planner). Discovered and fixed a missing
   top-level `agents/producer/__init__.py` / `agents/visual_planner/__init__.py`
   during this run (present in every other agent directory; without them
   `unittest discover` silently skipped both new suites while still
   reporting success on the rest).
4. Manual CLI smoke test (`python -m agents.producer.src` /
   `python -m agents.visual_planner.src`, isolated scratch fixture,
   deleted after): confirmed the full apply pipeline end-to-end —
   generated `PRODUCTION.md`, both scene files, and one `ASSET.md`
   inspected by hand against `templates/` and the Phase 7A golden
   fixture's shape.
5. `git status --short` confirms zero modified files under
   `content/what-if/wi-20260902-black-death-modern-medicine/` — only the
   pre-existing Phase 7A rename/reference fixes and new `agents/producer/`
   `agents/visual_planner/` files are present.
6. No existing reviewer/orchestrator implementation touched this phase —
   only `agents/producer/CONTRACT.md`, `agents/visual-planner/CONTRACT.md`
   (Phase 7A contract text, amended pre-implementation per Step 1 above)
   were edited outside the two new agent directories.

## Genuine finding, carried over from Phase 7A (still true)

`SCRIPT.md`'s beats are descriptions, not always verbatim spoken lines —
Producer faithfully reproduces whatever is in `SCRIPT.md` (that's its
job), so real production still needs a fully spoken-form script before
Producer output is voice-ready. Not a Producer defect; see
`agents/producer/README.md`'s "Known limitations."

## Known limitations

- No versioned production supersession (`prod-01`→`prod-02`) — a stale
  plan is reported and left untouched, but regenerating it after a script
  change is a human/operator decision this MVP surfaces rather than
  automates, per "don't build unnecessary infrastructure."
- Visual Planner assumes exactly one asset per scene, keyed to the
  scene's order number — a scene needing multiple distinct assets isn't
  modeled yet.
- No actual media generation or retrieval exists anywhere — both agents
  produce structured requirements only. `agents/voice/` (Phase 7C) has no
  implementation. `ASSET_COLLECTION` and every stage after it in
  `templates/PRODUCTION.md`'s `Production status` sequence remain
  unbuilt.
- No publishing capability exists anywhere in this phase or any prior
  one — `READY_TO_PUBLISH` remains the ceiling, per `CONSTITUTION.md`
  rule 2.

## Next task

**Phase 7C — Voice + Asset Generation**: implement `agents/voice/`
(narration → voiceover audio, provider-agnostic — no vendor named in the
schema or contract) and real asset generation/retrieval for the
`ASSET_COLLECTION` stage, against the requirements
`agents/visual_planner/` now produces. Still no video rendering, no
captions rendering, no thumbnail generation, and no publishing — those
remain later, unbuilt stages. Not started yet.
