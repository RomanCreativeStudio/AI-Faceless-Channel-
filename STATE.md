# Project State

Last updated: 2026-09-03

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE** (unchanged).
**Phase 7C-1 — Voice Generation MVP — COMPLETE** (unchanged).
**Phase 7C-2 — Asset Generation / Retrieval MVP — COMPLETE.**

## Completed (Phase 7C-2)

**Step 1 — Inspection:** re-read `CONSTITUTION.md`, `SYSTEM.md`,
`STATE.md`, `templates/ASSET.md`/`SCENE.md`/`PRODUCTION.md`,
`agents/visual_planner/CONTRACT.md`, `agents/voice/CONTRACT.md`,
`agents/producer/CONTRACT.md`, and the existing Producer/Visual
Planner/Voice implementations before writing any code. Found and
resolved one genuine architectural question before implementation
started: `agents/visual_planner/CONTRACT.md` already gives Visual
Planner authority to create `assets/asset-<n>.md` (a Phase 7B decision).
Rather than edit Visual Planner (out of this phase's stated scope) or
silently let two agents fight over the same file, `agents/assets/`
treats an existing Visual-Planner-created file as an intentionally
incomplete skeleton: it reads and *preserves verbatim* the one thing
Visual Planner already decided (`Historical authenticity
classification`), then performs one full rewrite to complete every
other field — the same "placeholder → populated by the next agent"
pattern already established between `agents/producer/` and
`agents/visual_planner/` for `PRODUCTION.md`'s rollups. For a scene
Visual Planner left with no asset record at all (no claim references),
this agent creates one from scratch, independently reaching the
identical `NOT_APPLICABLE` classification. Documented in full in
`agents/assets/CONTRACT.md`'s "Relationship to `agents/visual_planner/`".

**Step 2 — Assets MVP** (`agents/assets/src/`):
- `provider.py` / `test_providers.py` — two provider interfaces:
  `GeneratedAssetProvider` (`generate(...) -> GeneratedArtifact`) and
  `AssetRetrievalProvider` (`retrieve(...) -> RetrievalResult`);
  `pipeline.py` depends only on these. `LocalTestGeneratedAssetProvider`
  writes a deterministic, permanently-labeled `TEST / PLACEHOLDER
  GENERATED ASSET` text artifact. `LocalTestAssetRetrievalProvider`
  never contacts any service and never fabricates a source/URL/
  organization — it returns a structured `RETRIEVAL_NOT_IMPLEMENTED`
  requirement.
- `classification.py` — the Visual Safety Rule, reimplemented (not
  imported from `agents/visual_planner/`) per this repo's sibling-agent
  boundary: no claims → `NOT_APPLICABLE`; all `FACT` →
  `AUTHENTIC_HISTORICAL_MEDIA` (sourcing intent only); any
  `ASSUMPTION`/`INFERENCE`/`SPECULATION` → `GENERATED_RECONSTRUCTION`
  unconditionally. **Authenticity is always derived from claims, never
  from strategy or filename** — an unprovenanced `HUMAN_PROVIDED` asset
  changes `Verification status` to `REVIEW_REQUIRED`, never the
  authenticity classification itself.
- `scene_reader.py` — its own small scene-field reader (order, claim
  references, narration, and the `Visual type`/`Visual description`
  Visual Planner wrote) — reuses `agents/researcher/src.parsing`
  directly; doesn't reuse Visual Planner's `SceneRecord` since that model
  doesn't carry the visual fields this agent needs.
- `hashing.py` — `Scene/visual content hash` (new field, see "Schema
  changes" below): sha256 of narration + visual type/description + sorted
  claim IDs — what makes per-asset staleness detection possible.
- `qa.py` — deterministic, structural checks only (asset/scene IDs
  present, strategy and authenticity values recognized, claim references
  resolve, a `GENERATED` asset has a real artifact, a `RETRIEVED` asset
  never claims `Generation/retrieval status = RETRIEVED` or carries a
  fabricated URL, an unprovenanced `HUMAN_PROVIDED` asset is
  `REVIEW_REQUIRED`) — explicitly **not** a visual-quality judgment.
- `mutate.py` — hard-coded whitelist: `assets/asset-<n>.md` +
  `assets/asset-<n>.generated.txt`, and `PRODUCTION.md`'s `Asset
  references (rollup)` section + (only once every scene's asset is
  current) `Production status`.
- `pipeline.py` (`run_asset_generation(root, apply=False,
  generated_provider=None, retrieval_provider=None,
  human_provided=None)`) — gates on `CONTENT_ITEM.md status ==
  APPROVED` (independent of `PRODUCTION.md`) and `PRODUCTION.md
  Production status` in `{ASSET_COLLECTION, ASSEMBLY}` (the second
  accepted for the same re-run reason `agents/voice/` accepts its own
  terminal state — found and documented during Step 1, not a new gap
  discovered mid-implementation this time, since Visual Planner reliably
  sets `ASSET_COLLECTION`). Re-verifies `SCRIPT.md`'s hash against
  `PRODUCTION.md`'s stored one. Per scene: completes or creates the
  asset (see Step 1), defaults strategy from authenticity
  (`AUTHENTIC_HISTORICAL_MEDIA` → `RETRIEVED`, otherwise `GENERATED`)
  unless the caller explicitly opts a scene into `HUMAN_PROVIDED`. A
  matching existing hash is a no-op; a mismatched one is `STALE`
  (existing files untouched); a hash field present but blank is
  malformed and aborts safely.
- 45 tests (`agents/assets/tests/`), all isolated fixtures built via the
  real Producer/Visual Planner/Voice, real golden sample confirmed
  untouched.

**Step 3 — Schema changes** (`templates/ASSET.md`, all additive,
backward-compatible — the Phase 7A golden `asset-01.md`–`asset-03.md`
fixture remains valid as-is):
1. `Scene/visual content hash` (identity table) — staleness detection,
   mirroring `PRODUCTION.md`/`REVIEW.md`/`VOICE.md`'s identical pattern.
2. `Generated vs. retrieved` gains a third value, `HUMAN_PROVIDED` — the
   field name kept (not renamed) so existing `GENERATED`/`RETRIEVED`
   values need no change.
3. New `## Generation/retrieval status` section, mirroring
   `templates/SCENE.md`'s field of the same name, extended with
   `HUMAN_PROVIDED` — explicitly documented that `RETRIEVED` may only be
   set once a real retrieval has actually happened.
4. `Verification status` gains a fifth value, `REVIEW_REQUIRED` — for an
   unprovenanced human-provided asset that must never be silently
   trusted as authentic.

`related claims` was deliberately **not** added as a new field — already
reachable transitively via `Intended scene` → that scene's claim
references. Full reasoning for all four changes is in
`agents/assets/CONTRACT.md`'s "Schema changes".

**Step 4 — Isolated test fixtures:** every test builds its own fresh,
isolated, `status = APPROVED` content item in a
`tempfile.TemporaryDirectory()` (`agents/assets/tests/builders.py`,
reusing `agents/producer/`'s, `agents/visual_planner/`'s, and
`agents/voice/`'s real pipelines — never hand-rolled `PRODUCTION.md`/
scene/asset files). The real golden sample's `CONTENT_ITEM.md status`
remains `SCRIPT`, untouched.

**Step 5 — Documentation:** `agents/assets/CONTRACT.md`,
`agents/assets/README.md` (new), `SYSTEM.md`, `README.md` (root),
`agents/README.md`, `STATE.md` (this file).

## Validation performed

1. `agents/assets/tests/` — 45/45 pass: approved fixture produces asset
   records, unapproved content blocked (no mutation), golden sample never
   modified, all three strategies work (`GENERATED`/`RETRIEVED`/
   `HUMAN_PROVIDED`), `AUTHENTIC_HISTORICAL_MEDIA`/
   `GENERATED_RECONSTRUCTION`/`NOT_APPLICABLE` classifications all work,
   a What If?/`SPECULATION` claim forces `GENERATED_RECONSTRUCTION`,
   unknown human-provided provenance becomes `REVIEW_REQUIRED` without
   changing the authenticity field, a generated placeholder explicitly
   labels itself (never as real media), a retrieval placeholder never
   invents a source/URL, a missing claim reference blocks rather than
   inventing one, claim references are traceable end to end, asset IDs
   are stable and scene IDs preserved across re-runs, the scene/visual
   hash is recorded and correct, a scene change produces a `STALE`
   result and the prior asset is never overwritten, dry-run makes zero
   mutation, apply writes only asset-owned files/fields, `mutate.py`
   rejects non-whitelisted filenames, a malformed existing record and a
   missing `PRODUCTION.md` both fail safely, QA unit tests catch an
   invalid strategy/authenticity value, an unresolved claim reference, a
   `GENERATED` asset with no artifact, a `RETRIEVED` asset falsely
   claiming retrieval or carrying a fabricated URL, and an unprovenanced
   `HUMAN_PROVIDED` asset not flagged `REVIEW_REQUIRED`; claims,
   reviewer/review-history state, and voice records are never touched;
   no publishing-like identifier appears anywhere in `agents/assets/src/`
   (AST-checked); a full Producer→Visual Planner→Assets integration test
   (scene/visual/claim references all preserved, both default strategies
   exercised, generated placeholders labeled, no protected field
   changes); a Producer→Voice→Visual Planner→Assets test confirming
   Voice's and the Asset agent's outputs never overwrite one another.
2. Voice (33), Producer (20), Visual Planner (18), Researcher (43),
   Safety (27), Originality (31), Orchestrator (30) — all still pass
   individually, re-run this phase.
3. Combined suite — `python3 -m unittest discover -s agents -t . -p
   "test_*.py"` — **247/247 pass, 0 regressions** (202 pre-existing + 45
   Assets).
4. Manual CLI smoke test (`producer` → `visual_planner` → `assets`
   `--apply`, isolated scratch fixture with one `FACT` and one
   `ASSUMPTION` beat, deleted after): confirmed the completed-skeleton
   path (`asset-02.md`, `AUTHENTIC_HISTORICAL_MEDIA`, `RETRIEVED`), the
   fresh-classification path (`asset-01.md`, hook scene,
   `NOT_APPLICABLE`, `GENERATED`), and the reconstruction path
   (`asset-03.md`, `GENERATED_RECONSTRUCTION`, `GENERATED`), each
   inspected by hand against `templates/ASSET.md` and
   `agents/assets/CONTRACT.md`.
5. `git status --short` confirms zero modified files under
   `content/what-if/wi-20260902-black-death-modern-medicine/` — only
   `templates/ASSET.md` and the new `agents/assets/` files changed.
6. No existing agent implementation touched this phase — Producer's,
   Voice's, and Visual Planner's `src/`/`tests/` are all untouched; only
   their already-established, reused modules (`hashing.py`,
   `parsing.py`) were imported, never modified.

## Genuine finding

Task Step 18's "APPROVED CONTENT → Producer → Visual Planner → Voice →
Asset Agent" scenario, read literally, is unreachable: `agents/voice/`'s
own contract requires `Production status` in `{PRODUCTION_PLANNING,
VISUAL_PLANNING}`, but Visual Planner already advances status past both
of those (to `ASSET_COLLECTION`) before Voice would get a turn. The
established, working production-lifecycle order is Producer → **Voice**
→ Visual Planner → Assets (`PRODUCTION_PLANNING → VOICE →
VISUAL_PLANNING → ASSET_COLLECTION`, per `templates/PRODUCTION.md` and
every prior phase's documentation) — not the order the task listed. This
phase's integration tests and `agents/assets/tests/builders.py`'s
`build_full_pipeline_item` use the canonical order; the task's stated
intent (Voice's and Assets' outputs must not overwrite each other) is
fully verified either way, since neither ordering changes what files
each agent touches.

## Known limitations

- No versioned asset supersession (`asset-01` attempt 1 → attempt 2) — a
  stale asset is reported and left untouched; regenerating after a scene
  change is a human/operator decision this MVP surfaces, matching
  `agents/producer/`'s and `agents/voice/`'s identical documented
  limitation.
- Placeholder assets only — no real image/video/audio generation or
  retrieval integration exists; adding one is a future
  `GeneratedAssetProvider`/`AssetRetrievalProvider` implementation, not
  built this phase.
- One asset per scene, keyed to the scene's order number.
- QA is structural only — no visual-quality/historical-accuracy
  evaluation exists or is claimed.
- `agents/visual_planner/`'s Phase 7B interim allowance (accepting
  `Production status = PRODUCTION_PLANNING`) remains unremoved, same
  documented limitation carried over from Phase 7C-1 — out of this
  phase's scope too.
- No actual video assembly, captions, thumbnails, or publishing exists
  anywhere — `ASSEMBLY` and every stage after it in
  `templates/PRODUCTION.md`'s `Production status` sequence remain
  unbuilt.

## Next task

**Phase 7D — Video Assembly + Captions + Thumbnail + Production QA**:
combine scenes, the voice track, and asset records into an actual
rendered video, plus caption rendering, thumbnail generation, and a real
Production QA pass. Still no YouTube publishing, no analytics, no
learning systems — publishing remains permanently human-gated per
`CONSTITUTION.md` rule 2. Not started yet.
