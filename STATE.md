# Project State

Last updated: 2026-09-03

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE** (unchanged).
**Phase 7C-1 — Voice Generation MVP — COMPLETE** (unchanged).
**Phase 7C-2 — Asset Generation / Retrieval MVP — COMPLETE** (unchanged).
**Phase 7D — Video Assembly + Captions + Thumbnail + Production QA — COMPLETE.**

## Completed (Phase 7D)

**Step 1 — Inspection:** re-read `CONSTITUTION.md`, `SYSTEM.md`,
`STATE.md`, `templates/PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md`,
and every existing agent's `CONTRACT.md`/`src/` before writing any code.
Confirmed no `ffmpeg` (or any video-encoding tool) is installed in this
environment (`which ffmpeg` → not found) — treated as an honest MVP
limitation rather than grounds to install a dependency, matching the
stdlib-only constraint every prior phase established. Found one real gap
during inspection: `templates/PRODUCTION.md` had no section to record
assembly/video output at all — fixed by adding one new, minimal `##
Assembly / Output` section (see "Schema changes" below) rather than
inventing a parallel mechanism.

**Step 2 — Assembler MVP** (`agents/assembler/src/`):
- `provider.py` / `test_provider.py` — `VideoRenderer` Protocol
  (`render(scenes, total_duration) -> RenderResult`);
  `LocalTestVideoRenderer` deterministically builds a manifest **text**
  file (scene id/start/end/duration/narration ref/visual ref/transitions,
  plus a truncated sha256 manifest hash) — explicitly, permanently
  labeled `TEST / PLACEHOLDER VIDEO MANIFEST — not a real video file`,
  `Playable` always `NO`.
- `scene_reader.py` — reads each scene's `Duration` and `## Transition`
  in/out fields; reused directly by `agents/captions/`.
- `hashing.py` — `compute_voice_hash_component` /
  `compute_assembly_content_hash` (script hash + voice hash component +
  every scene's asset hash) — the assembly-level staleness key.
- `models.py` — `SceneTimelineEntry` (per-scene start/end/duration/refs/
  transitions/claim ids), `AssemblyResult`.
- `mutate.py` — hard-coded whitelist: `timeline/timeline-<n>.md` +
  `output/video-<n>.manifest.txt`, and `PRODUCTION.md`'s new `Assembly /
  Output` section + `Production status`.
- `timeline_writer.py` — renders `templates/TIMELINE.md`.
- `pipeline.py` (`run_video_assembly(root, apply=False, renderer=None)`)
  — gates on `CONTENT_ITEM.md status == APPROVED` (independent check),
  `PRODUCTION.md Production status` in `{ASSEMBLY, CAPTIONS}`, current
  `SCRIPT.md` hash, `voice/voice-01.md` existing with `Generation status
  == GENERATED` and a matching stored script hash, every scene loading
  with contiguous order and resolving claims, and every scene's
  `assets/asset-<n>.md` matching its current content hash (reusing
  `agents/assets/src/hashing.compute_asset_content_hash` directly — never
  substitutes an unrelated asset for a missing/stale one, refuses
  instead). Builds the timeline (cumulative start/end, total duration ==
  sum of scene durations, no overlaps by construction), calls the
  renderer, writes on `--apply`.
- 21 tests (`agents/assembler/tests/`) — approval/precondition gating (9),
  timeline determinism (6), mutation boundaries (6) — all passed on first
  run.

**Step 3 — Captions MVP** (`agents/captions/src/`):
- `segmentation.py` — deterministic algorithm: sentence-split (`re.split
  (r"(?<=[.!?])\s+", text)`), then word-by-word greedy packing into
  chunks of at most `max_characters_per_line x max_lines_per_caption`
  characters (documented defaults 40 x 2 = 80, never splitting a word),
  timing proportional to each chunk's character-length share of the
  scene's already-established `Duration`.
- `hashing.py` — `compute_captions_content_hash` (narration texts in
  scene order).
- `mutate.py` — whitelist: `captions/captions-<n>.md` +
  `PRODUCTION.md`'s `Captions` section + `Production status`.
- `captions_writer.py` — renders `templates/CAPTIONS.md`, one `### Scene
  \`<id>\`` H3 subsection per scene nested inside the single `## Scene
  captions` H2 section, each with its own `| Caption # | Start | End |
  Text |` table.
- `pipeline.py` (`run_caption_generation(root, apply=False,
  max_characters_per_line=40, max_lines_per_caption=2)`) — gates on
  `Production status` in `{CAPTIONS, THUMBNAIL}`; reuses
  `agents/assembler/src/scene_reader.load_scene_timing` and
  `agents/assets/src/scene_reader.load_scene_visual_records` directly.
  **Caption integrity**: every caption chunk is a verbatim substring of
  the source narration — never paraphrased, rewritten, or
  grammar-"fixed" — and safety-critical qualifiers (`may`, `could`,
  `likely`, `hypothetical`, `we cannot know`) are never dropped, since
  nothing is ever rewritten in the first place.
- 17 tests (`agents/captions/tests/`) — segmentation unit tests (7),
  full-pipeline tests (10) — all passed on first run.

**Step 4 — Thumbnail MVP** (`agents/thumbnail/src/`):
- `provider.py` / `test_provider.py` — `ThumbnailProvider` Protocol
  (`generate_spec(title_source, visual_source, hedge_required,
  authenticity_summary) -> ThumbnailSpec`); `LocalTestThumbnailProvider`
  deterministically builds title concept/visual concept/text overlay/
  focal subject/composition, labeled `placeholder specification only,
  not a real generated image`.
- **Fact / What If? framing rule** (the one place this agent makes a
  judgment call, made fully deterministic): `Title concept` is never
  synthesized prose — built only from `CONTENT_ITEM.md`'s own `Working
  title`, used verbatim if already hedged (contains `"?"` or starts with
  `"what if"`/`"could"`/`"might"`), else wrapped in the one fixed
  template `f"What if: {title}?"` only when `content_pillar ==
  "what-if"`, else used verbatim for any other pillar. Never invents a
  sensational claim (e.g. never produces `"THE BLACK DEATH WAS
  STOPPED!"`); a hypothetical premise is always phrased as a question
  (e.g. `"COULD MODERN MEDICINE HAVE STOPPED IT?"`).
- `hashing.py` — `compute_thumbnail_content_hash` (working title +
  content pillar + every referenced claim's classification, scene
  order).
- `mutate.py` — whitelist: `thumbnail/thumbnail-<n>.md` +
  `PRODUCTION.md`'s `Thumbnail` **and** `Title / description` sections +
  `Production status` (one call updates both, since Thumbnail is also
  this phase's minimal metadata support — working title mirrored
  verbatim, description an explicit placeholder, never synthesized
  copy).
- `pipeline.py` (`run_thumbnail_generation(root, apply=False,
  provider=None)`) — gates on `Production status` in `{THUMBNAIL,
  METADATA}`; aggregates claim classifications and per-scene asset
  authenticity classifications (read, never recomputed, from
  `assets/asset-<n>.md`) into a deterministic `authenticity_considerations`
  note whenever a `GENERATED_RECONSTRUCTION` scene exists, so the
  thumbnail spec can never imply generated content is authentic.
- 13 tests (`agents/thumbnail/tests/`) — all pass (one initial test
  ordering bug fixed, see "Errors and fixes" below).

**Step 5 — Production QA MVP** (`agents/production_qa/src/`), the final
automated gate:
- `models.py` — `VALID_VERDICTS = {PASS, REVISION_REQUIRED, BLOCKED,
  SYSTEM_ERROR}`; `CheckResult`/`ProductionQAResult`.
- `checks.py` — seven independent re-verification functions
  (`check_content`, `check_voice`, `check_assets`, `check_timeline`,
  `check_captions`, `check_thumbnail`, `check_output`), each re-reading
  and re-verifying rather than trusting an upstream agent's own claim
  (e.g. caption text is independently re-checked against narration
  itself, not assumed faithful because `agents/captions/` says so).
- `mutate.py` — whitelist: `qa/production-qa-<n>.md` +
  `PRODUCTION.md`'s `Production QA state` section + (only on `PASS`)
  `Production status`, hard-coded via a `PermissionError` in
  `apply_production_qa_state` to accept `HUMAN_REVIEW` and nothing else
  as the new status, and only `PASS`/`REVISION_REQUIRED` as storable
  verdicts. Never touches `Human review state`.
- `qa_writer.py` — renders `templates/PRODUCTION_QA.md`, checks grouped
  by area (`Content, Voice, Assets, Timeline, Captions, Thumbnail,
  Output`).
- `pipeline.py` (`run_production_qa(root, apply=False)`, wrapped in
  try/except returning `SYSTEM_ERROR` rather than crashing the caller) —
  gates on `Production status` in `{METADATA, HUMAN_REVIEW}`, then three
  hard **`BLOCKED`** staleness gates evaluated before any check runs
  (current script hash vs. `PRODUCTION.md`'s stored one; voice record's
  stored script hash vs. current; each scene's asset content hash vs.
  current, reusing `agents/assets/src/hashing.compute_asset_content_hash`
  directly) — staleness is never a soft check, since a QA pass evaluated
  against outdated inputs can't be trusted at all, the same reasoning
  `agents/assembler/`'s, `agents/captions/`'s, and `agents/thumbnail/`'s
  own preconditions already use. Then a required-artifact-existence gate
  (voice/timeline/captions/thumbnail all present or `BLOCKED`). Then all
  seven `check_*` functions run and aggregate into `PASS` (zero failed
  checks) or `REVISION_REQUIRED` (one or more failed).
- **Known limitation, found and documented rather than routed around**:
  `RETRIEVED`-strategy assets can never fully pass this phase, since
  `agents/assets/`'s `LocalTestAssetRetrievalProvider` always returns
  `RETRIEVAL_NOT_IMPLEMENTED` — a `RETRIEVED` asset's `Generation/
  retrieval status` can only legitimately be `NOT_STARTED` this phase, so
  any production containing an all-`FACT` scene (which defaults to
  `RETRIEVED`) correctly and honestly reports `REVISION_REQUIRED`, never
  a false `PASS`. See "Genuine finding" below.
- 25 tests (`agents/production_qa/tests/`) — pipeline tests covering
  tasks 32-43 (19 tests) and full-pipeline integration tests covering
  tasks 44-50 (6 tests) — all pass after the fixes below.

**Step 6 — Schema changes** (all additive; the Phase 7A golden fixture
remains valid as-is, since it never reaches these later production
stages):
1. `templates/PRODUCTION.md` — new `## Assembly / Output` section
   (`Timeline reference`/`Video output reference`/`Assembly status`),
   inserted between `Asset references (rollup)` and `Thumbnail`,
   initialized `NOT_STARTED` by `agents/producer/` the same way as every
   other rollup, populated by `agents/assembler/`.
2. `templates/TIMELINE.md` (new) — identity table (Timeline/Content/
   Production ID, Assembly content hash, Total duration), `## Scene
   timeline` table, `## Output` table (`Playable` — `YES`/`NO`/
   `UNVERIFIED`, documented as never `YES` unless independently confirmed
   by the renderer that produced it), `## Assembly status`.
3. `templates/CAPTIONS.md` (new) — identity table (incl. `Max characters
   per line`/`Max lines per caption`, both explicit, never hidden
   defaults), `## Scene captions` (per-scene `### Scene \`<id>\`` H3
   subsections each with their own caption table), `## Generation
   status`.
4. `templates/THUMBNAIL.md` (new) — identity table, `## Concept` table,
   `## Claim / theme relationship`, `## Authenticity considerations`,
   `## Generation strategy`, `## Thumbnail status`.
5. `templates/PRODUCTION_QA.md` (new) — identity table (incl. `Verdict`:
   `PASS`/`REVISION_REQUIRED`/`BLOCKED`/`SYSTEM_ERROR`), `## Checks`
   grouped by area, `## Reasons`, `## Notes`.

**Step 7 — Isolated test fixtures:** every new agent's tests build a
fresh, isolated, `status = APPROVED` content item in a
`tempfile.TemporaryDirectory()`, reusing every real upstream pipeline
(`agents/producer/`, `agents/voice/`, `agents/visual_planner/`,
`agents/assets/`, and each new agent's own predecessor) rather than
hand-rolling any production file. The real golden sample's
`CONTENT_ITEM.md status` remains untouched.

**Step 8 — Documentation:** `agents/assembler/CONTRACT.md`/`README.md`,
`agents/captions/CONTRACT.md`/`README.md`,
`agents/thumbnail/CONTRACT.md`/`README.md`,
`agents/production_qa/CONTRACT.md`/`README.md` (all new);
`agents/producer/CONTRACT.md`/`src/production_writer.py` (updated for the
new `Assembly / Output` rollup); `SYSTEM.md`, `README.md` (root),
`agents/README.md`, `STATE.md` (this file) — all updated.

## Errors and fixes (this phase)

1. **`check_assets` read the wrong table for asset strategy.** Initially
   read `Generated vs. retrieved` from the top identity table, but that
   field actually lives inside the asset's own `## Provenance` section.
   `strategy` was always empty, so no strategy-specific check ever ran —
   silently passing productions that should have failed. Found via manual
   CLI smoke-testing (a FACT-only fixture produced `PASS` instead of the
   expected `REVISION_REQUIRED`). Fixed by parsing the `## Provenance`
   section's own table; re-verified both the FACT-only fixture (now
   correctly `REVISION_REQUIRED`) and the all-hypothetical fixture (still
   `PASS`).
2. **Markdown table separator-row filter was broken** in `check_timeline`
   and `check_captions` — `line.strip().strip("|")` only strips leading/
   trailing pipes, not the internal ones in `"|---|---|---|"`. Fixed by
   `line.replace("|", "").strip()` then checking the remainder is all
   `"-"`.
3. **H3-within-H2 parsing gap** — `check_captions` looked up
   `sections.get(f"Scene \`{id}\`", "")` on `parsing.parse_sections`'s
   output, but that helper only splits on `## ` while
   `captions_writer.py` nests per-scene bodies as `### Scene \`...\``
   inside one `## Scene captions` H2 section. Fixed with a new
   `_split_h3_subsections` helper.
4. **Dead/unreachable code in `check_output`** — a leftover
   `if False else None` expression. Fixed by changing the function's
   signature to take `production_text` directly and properly parse the
   `Title / description` section.
5. **Staleness was initially a soft check, not a hard gate.** Re-reading
   the task's own test list (staleness tests expect `BLOCKED` only, no
   `REVISION_REQUIRED` alternative, unlike the present-but-incomplete
   tests which explicitly allow either) revealed this was architecturally
   wrong before any test even ran. Fixed by adding three explicit
   `BLOCKED` gates in `pipeline.py`, ahead of all seven checks.
6. **Test ordering bug in `agents/thumbnail/tests/`** — one test
   registered a new claim *after* the builder had already run Producer
   (which validates claim references at build time), reproducing the
   identical ordering bug from earlier phases. Fixed by moving claim
   registration into the builder's own `extra_claims` parameter.

Every other new module (Assembler's 21 tests, Captions' 17 tests) passed
on the first run.

## Validation performed

1. Combined suite — `python3 -m unittest discover -s agents -t . -p
   "test_*.py"` — **323/323 pass, 0 regressions** (247 pre-existing + 21
   Assembler + 17 Captions + 13 Thumbnail + 25 Production QA).
2. Every agent's own suite re-run individually and green: researcher 43,
   safety 27, originality 31, orchestrator 30, producer 20, voice 33,
   visual_planner 18, assets 45, assembler 21, captions 17, thumbnail 13,
   production_qa 25.
3. Golden-sample safety: `git status --short -- content/` empty after
   every test run; a dedicated `test_golden_sample_never_modified` in
   every new agent plus a full end-to-end
   `test_golden_sample_untouched_by_full_pipeline` in
   `agents/production_qa/tests/test_integration.py` running all seven
   new/reused `apply=True` agents against the real golden sample and
   confirming zero byte-level changes.
4. No publishing capability anywhere: AST-based scans (checking for
   `upload`/`publish`/`post_video`/`youtube`/`schedule_publish`
   identifiers) across every new agent's `src/`, individually and in one
   combined integration-level scan, plus a behavioral test confirming
   `Production status` never becomes anything beyond `HUMAN_REVIEW` after
   a full real pipeline run.
5. Manual CLI smoke test of the entire 8-agent pipeline (`producer` →
   `voice` → `visual_planner` → `assets` → `assembler` → `captions` →
   `thumbnail` → `production_qa`, each `--apply`) against a fresh
   isolated fixture: confirmed `Production status` reaches exactly
   `HUMAN_REVIEW` with `verdict: PASS`.
6. Dry-run/apply safety, immutable history (never overwrites an existing
   finished artifact — a changed upstream input blocks rather than
   silently regenerating), and hard-coded write whitelists verified in
   every new agent's own `test_mutation_boundaries.py`/equivalent.

## Genuine finding

Same as Phase 7C-2's finding (Voice must run before Visual Planner, not
after, for the pipeline to be reachable at all) — carried forward
unchanged since it still governs every new agent's precondition. New
finding this phase: **the `RETRIEVED` asset strategy can never legitimately
reach `PASS` in Production QA**, because no real asset-retrieval
integration exists anywhere in this codebase (`LocalTestAssetRetrievalProvider`
always returns `RETRIEVAL_NOT_IMPLEMENTED`, never `RETRIEVED`). This is
not a bug to route around — it's an honest, correct reflection of what's
actually built: a production is only genuinely ready for human review
this phase if every scene is hypothetical/generated/non-representational,
or `HUMAN_PROVIDED` with real stated provenance. Documented in
`agents/production_qa/CONTRACT.md` and `README.md`, and encoded
explicitly in `agents/production_qa/tests/builders.py`'s
`build_passing_item` (deliberately all-`ASSUMPTION`/`SPECULATION` claims,
never all-`FACT`).

## Known limitations

- No real video rendering — `agents/assembler/`'s only provider
  (`LocalTestVideoRenderer`) writes a placeholder manifest, never a
  playable video; no video-encoding tool is installed in this
  environment.
- No real thumbnail image generation — `agents/thumbnail/`'s only
  provider (`LocalTestThumbnailProvider`) produces a text specification,
  never a generated image.
- `RETRIEVED`-strategy assets can never fully pass Production QA this
  phase — see "Genuine finding" above; this is intentional and honest,
  not a shortcut.
- No versioned assembly/caption/thumbnail/QA supersession — one attempt
  (`-01`) per production this phase; a stale artifact is reported and
  left untouched, matching every prior phase's identical documented
  limitation for `producer/`/`voice/`/`assets/`.
- Production QA is structural only — no visual-quality, pronunciation,
  or historical-accuracy evaluation exists or is claimed.
- No full pipeline orchestration across all eight production agents yet
  (each is invoked individually via its own CLI) and no self-review/
  revision loop that automatically re-runs a stage after a
  `REVISION_REQUIRED` fix.
- `agents/visual_planner/`'s Phase 7B interim allowance (accepting
  `Production status = PRODUCTION_PLANNING`) remains unremoved, same
  documented limitation carried over from every prior phase.
- No actual publishing, YouTube integration, analytics, or learning
  system exists anywhere — `HUMAN_REVIEW` remains the highest state any
  agent may ever reach; `APPROVED` and `READY_TO_PUBLISH` remain
  exclusively human-set, per `CONSTITUTION.md` rule 2.

## Next task

**Phase 7E — Full Pipeline Orchestration + Self-Review Loop**: a thin
orchestrator that runs all eight production agents in sequence
(`producer → voice → visual_planner → assets → assembler → captions →
thumbnail → production_qa`), stopping at the first stage that blocks or
aborts, mirroring `agents/orchestrator/`'s existing pattern for the
content-review agents; plus a self-review loop that can re-run a single
stage after its `REVISION_REQUIRED` cause is fixed, without ever
re-running or overwriting a stage that already succeeded. Still no
YouTube publishing, no analytics, no learning systems — publishing
remains permanently human-gated per `CONSTITUTION.md` rule 2. Not started
yet.
