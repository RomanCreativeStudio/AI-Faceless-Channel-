# Project State

Last updated: 2026-09-03

## Phase

**Phase 6 — COMPLETE** (unchanged this phase).
**Phase 7A — Production Stack Foundation — COMPLETE** (unchanged).
**Phase 7B — Producer + Visual Planner MVP — COMPLETE** (unchanged).
**Phase 7C-1 — Voice Generation MVP — COMPLETE.**

## Completed (Phase 7C-1)

**Step 1 — Inspection:** re-read `CONSTITUTION.md`, `SYSTEM.md`,
`STATE.md`, `templates/VOICE.md`/`PRODUCTION.md`/`SCRIPT.md`,
`agents/voice/CONTRACT.md`, `agents/producer/`, `agents/orchestrator/`,
and the existing test infrastructure before writing any code. Found and
fixed one genuine gap before implementation started, documented in place:
`agents/voice/CONTRACT.md`'s Preconditions required `Production status =
VOICE`, a value no agent ever sets — `agents/producer/CONTRACT.md`'s own
Handoff section is explicit that Producer's output state is
`PRODUCTION_PLANNING` and it "does not advance further." Unlike the
analogous Visual Planner gap found in Phase 7B, no interim allowance to
another unbuilt agent was needed: Voice *is* the agent responsible for
the `VOICE` stage, so it runs starting from `PRODUCTION_PLANNING` (what
Producer actually leaves) and is itself the one that advances status
onward, once its own work is genuinely complete.

**Step 2 — Voice MVP** (`agents/voice/src/`):
- `provider.py` / `test_provider.py` — the provider abstraction:
  `VoiceProvider` protocol (`generate(narration_text,
  voice_configuration) -> GeneratedAudio`); `pipeline.py` depends only on
  this interface. `LocalTestVoiceProvider` is the only implementation
  this phase — deterministic (same input always produces the same
  duration and artifact content), no network calls, output permanently
  labeled `TEST / PLACEHOLDER AUDIO — not real speech, not
  production-quality`.
- `narration.py` — builds SOURCE NARRATION (verbatim, scene-order
  narration text, reusing `agents/visual_planner/src.loader.load_scenes`
  directly rather than re-parsing scene files a third time) and
  PROVIDER-READY NARRATION (the *only* transformation permitted anywhere
  in this pipeline: curly quotes/apostrophes → straight ASCII, repeated
  whitespace collapsed — nothing else; never changes a word, a number, a
  hedge phrase, or a What If? distinction).
- `qa.py` — deterministic, structural QA only (narration non-empty,
  script hash matches, audio reference recorded, duration positive,
  provider metadata complete, generation status valid) — explicitly
  **not** a speech-quality judgment; no pronunciation/emotion detection
  exists or is claimed.
- `mutate.py` — hard-coded whitelist: `voice/voice-<n>.md` +
  `voice/voice-<n>.audio.txt` (fresh files only, never overwritten), and
  `PRODUCTION.md`'s `Voiceover information` section + (only once QA
  passes) `Production status`.
- `pipeline.py` (`run_voice_generation(root, apply=False, provider=None,
  voice_configuration=..., words_per_minute=150)`) — gates on
  `CONTENT_ITEM.md status == APPROVED` (checked independently of
  `PRODUCTION.md`, defense-in-depth mirroring Visual Planner's own
  Phase 7B fix) and `PRODUCTION.md Production status` in
  `{PRODUCTION_PLANNING, VISUAL_PLANNING}` — the second accepted because
  it's Voice's own successful terminal state, so a re-run can still reach
  its own already-up-to-date/staleness check rather than always blocking
  on the precondition (found while writing the re-run tests — see "Genuine
  finding" below). Re-verifies `SCRIPT.md`'s hash against `PRODUCTION.md`'s
  stored one (reusing `agents/producer/src.hashing` directly) before
  generating. A matching existing `voice/voice-01.md` hash is a no-op; a
  mismatched one is a structured `stale` result, existing files
  untouched; a malformed existing record (blank/missing hash) aborts
  safely rather than guessing.
- 33 tests (`agents/voice/tests/`), all isolated fixtures, real golden
  sample confirmed untouched.

**Step 3 — Schema change** (`templates/VOICE.md`): added exactly one new
field, `Script content hash`, to the identity table — the same
already-established pattern in `templates/PRODUCTION.md`/`REVIEW.md`.
Reason documented in `agents/voice/CONTRACT.md`'s "Schema change"
section: required by this phase's task ("VOICE.md must record: script
hash... a script change makes the result STALE"), and nothing else could
satisfy it without persisting the hash. No other field or template was
touched; PROVIDER-READY NARRATION was deliberately *not* made a
persisted field (a documented sentence in `templates/VOICE.md`'s
"Narration source" section was enough).

**Step 4 — Isolated test fixtures:** every test builds its own fresh,
isolated, `status = APPROVED` content item in a
`tempfile.TemporaryDirectory()` (`agents/voice/tests/builders.py`, reusing
`agents/producer/tests/builders.py` and the real `run_producer()` call —
never hand-rolled `PRODUCTION.md`/scene files). The real golden sample's
`status` remains `SCRIPT`, untouched.

**Step 5 — Documentation:** `agents/voice/README.md` (rewritten from
Phase 7A's "not implemented yet" stub to describe the real MVP
architecture, provider abstraction, CLI usage, and known limitations),
`agents/voice/CONTRACT.md` (Preconditions fix, schema-change note,
provider-abstraction section), `SYSTEM.md`, `README.md` (root),
`agents/README.md`, `STATE.md` (this file).

## Validation performed

1. `agents/voice/tests/` — 33/33 pass: approved→plan, unapproved→blocked
   (no mutation), golden sample never modified, script hash recorded,
   script change→stale (existing files untouched), unchanged-script
   re-run is a no-op, narration preserved verbatim, What If? hedged
   language never altered or removed, provider-ready transform only
   normalizes quotes/whitespace, a custom provider is used instead of a
   hardcoded one, the built-in test provider is deterministic, placeholder
   output is always labeled and never marked production-ready, missing
   narration/SCRIPT.md/provider-configuration all fail safely, malformed
   existing VOICE.md fails safely, dry-run makes zero mutation, apply
   writes only voice-owned files/fields, `mutate.py` rejects
   non-whitelisted filenames, `CONTENT_ITEM.md` status/approval untouched,
   QA unit tests catch a missing audio reference / script-hash mismatch /
   empty narration / non-positive duration / incomplete provider metadata
   / invalid generation status, claims and reviewer/review-history state
   are never touched, no publishing-like identifier appears anywhere in
   `agents/voice/src/` (AST-checked), and a full Producer→Voice
   integration test (approved fixture with a Hook + 3 beats incl. an
   ASSUMPTION and a SPECULATION claim → 4 scenes → voice record: script
   hash consistent, narration verbatim, provider adapter works,
   deterministic test audio exists, production stays separate from
   content status, no protected field changes).
2. Producer (20), Visual Planner (18), Researcher (43), Safety (27),
   Originality (31), Orchestrator (30) — all still pass individually,
   re-run this phase.
3. Combined suite — `python3 -m unittest discover -s agents -t . -p
   "test_*.py"` — **202/202 pass, 0 regressions** (169 pre-existing + 33
   Voice).
4. Manual CLI smoke test (`python -m agents.producer.src` then
   `python -m agents.voice.src`, isolated scratch fixture, deleted after):
   confirmed the full apply pipeline end-to-end — `voice/voice-01.md`,
   `voice/voice-01.audio.txt`, and `PRODUCTION.md`'s updated `Voiceover
   information`/`Production status` inspected by hand against
   `templates/VOICE.md` and `agents/voice/CONTRACT.md`.
5. `git status --short` confirms zero modified files under
   `content/what-if/wi-20260902-black-death-modern-medicine/` — only new
   `agents/voice/` files, `templates/VOICE.md`, and
   `agents/voice/CONTRACT.md` changed outside documentation.
6. No existing agent implementation touched this phase — Producer's and
   Visual Planner's `src/`/`tests/` are untouched; only their
   already-established, reused modules (`hashing.py`, `loader.py`) were
   imported, never modified.

## Genuine finding

Writing `agents/voice/tests/test_hashing_staleness.py`'s re-run tests
surfaced that a literal `Production status == PRODUCTION_PLANNING`
precondition would make every re-run of Voice — even a harmless
already-up-to-date check — hit the precondition block instead of the
staleness logic it was meant to test, because a *successful* prior Voice
run already advances status to `VISUAL_PLANNING`. Not a defect in the
staleness design itself, just an incomplete precondition; fixed by
accepting `VISUAL_PLANNING` as a second valid entry state (Voice's own
terminal state), documented in both `pipeline.py` and
`agents/voice/CONTRACT.md`.

## Known limitations

- No versioned voice supersession (`voice-01`→`voice-02`) — a stale
  result is reported and left untouched, but regenerating after a script
  change is a human/operator decision this MVP surfaces rather than
  automates, matching Producer's identical documented limitation.
- Placeholder audio only — `voice/voice-<n>.audio.txt` is plain text
  describing what would be spoken, never a real audio container. No real
  TTS integration exists; adding one is a second `VoiceProvider`
  implementation, not built this phase.
- One voice track per production (`voice-01` only) — matches
  `templates/VOICE.md`'s "typically one per production" design.
- QA is structural only — no pronunciation/emotion/audio-artifact
  detection exists or is claimed.
- `agents/visual_planner/`'s Phase 7B interim allowance (accepting
  `Production status = PRODUCTION_PLANNING`, not just `VISUAL_PLANNING`)
  is now unnecessary on the real path, since `agents/voice/` genuinely
  sets `VISUAL_PLANNING` on success — but per this task's explicit scope
  ("update only" a specific file list, not including
  `agents/visual_planner/`), it was left untouched rather than removed.
  A candidate cleanup for a future phase, not a correctness problem now
  (the allowance is a superset, so nothing that used to work stops
  working).
- No actual media generation or retrieval exists anywhere —
  `ASSET_COLLECTION` and every stage after it in
  `templates/PRODUCTION.md`'s `Production status` sequence remain
  unbuilt, and Voice's own audio is a placeholder, not real speech.
- No publishing capability exists anywhere in this phase or any prior
  one — `READY_TO_PUBLISH` remains the ceiling, per `CONSTITUTION.md`
  rule 2.

## Next task

**Phase 7C-2 — Asset Generation / Retrieval MVP**: Scene → asset
strategy → generated/retrieved/human-provided asset → provenance →
authenticity classification → asset QA, building on
`agents/visual_planner/`'s existing visual requirements. Still no video
assembly, no FFmpeg, no captions rendering, no thumbnails, no YouTube
publishing, no analytics, no learning systems. Only after both Voice and
Asset systems work should the project move toward **Phase 7D — Video
Assembly + Captions + Thumbnail + Production QA**. Not started yet.
