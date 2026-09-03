# Producer

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7B MVP —
`src/`/`tests/` exist and are stdlib-only, matching the shape of
`agents/researcher/`, `agents/safety/`, and `agents/originality/`.

## Responsibility

Turns an `APPROVED` content item's `SCRIPT.md` into a structured
`PRODUCTION.md` + `scenes/scene-<n>.md` set (`templates/PRODUCTION.md`,
`templates/SCENE.md`) — narration decomposed into scenes with estimated
timing and carried-forward claim references. Generates no media itself.
Deliberately non-creative: SCRIPT → STRUCTURED SCENES only, no AI
generation, no paraphrasing, no invented content — see "Known
limitations" below and CONTRACT.md's Purpose.

## How it works

- **Approval gate** (`pipeline.py`): refuses to run at all unless
  `CONTENT_ITEM.md`'s `status` is exactly `APPROVED` — the strictest gate
  in the whole pipeline, per CONTRACT.md's Preconditions. Anything else
  returns a structured `blocked` result with no mutation.
- **Scene generation** (`scene_builder.py`): the Hook (if present) becomes
  scene 1; each `## Narrative beats` numbered item becomes its own scene,
  in order — no condensation, no paraphrasing. A beat's trailing
  `` — claims: `c1`, `c2` `` suffix is parsed for claim references, each
  cross-validated against `claims/*.md` (missing claim -> fails safely,
  never invents one).
- **Duration** (`duration.py`): `estimated_seconds = round(word_count /
  words_per_minute * 60)`. `words_per_minute` is always an explicit
  parameter (`run_producer(..., words_per_minute=...)`, `--wpm` on the
  CLI) — `DEFAULT_WORDS_PER_MINUTE = 150` is only the fallback, never a
  hidden assumption.
- **Hash/staleness** (`hashing.py` + `pipeline.py`): `Script content hash`
  is `sha256(SCRIPT.md)`. If `PRODUCTION.md` already exists, a matching
  hash means it's already up to date (no-op); a mismatched hash means the
  script changed since — the Producer refuses to regenerate and returns a
  structured `stale` result instead of silently overwriting. This MVP
  does **not** implement versioned supersession (`prod-01` → `prod-02`,
  mirroring `templates/CLAIM.md`'s pattern) — see "Known limitations."
- **Write boundary** (`mutate.py`): a hard-coded path whitelist —
  `PRODUCTION.md` (root) and `scenes/scene-<n>.md` only, and only ever as
  fresh files (never overwrites an existing one). No generic "write
  anything" helper.
- **Dry-run / apply**: `run_producer(root, apply=False)` (the default)
  computes and returns everything without touching disk; `apply=True`
  writes. Same shape as every other agent in this repo.

## Relationship to other agents

Reuses `agents/researcher/src`'s generic infrastructure (`parsing`,
`errors.NoLoadableContent`/`StructuralFailure`,
`loader.load_content_item`/`load_claims`) directly — never
`agents/researcher/`'s fact-check domain logic. Runs only after
`agents/orchestrator/`'s automated review layer and full human approval
(`CONTENT_ITEM.md` `status = APPROVED`) — see CONTRACT.md
"Preconditions". Hands off to `agents/voice/` (narration → audio, no MVP
yet — Phase 7C) and `agents/visual_planner/` (scenes → finalized visual
requirements, reuses this agent's `hashing.py` directly), which each own
later `templates/PRODUCTION.md` sections the Producer only initializes as
placeholders.

See `content/what-if/wi-20260902-black-death-modern-medicine/PRODUCTION.md`
for the Phase 7A golden fixture showing the target shape of this agent's
output (hand-built for schema validation, not agent-generated — the real
golden sample is intentionally never `APPROVED`, so a real Producer run
can never target it; see `agents/producer/tests/test_approval_gate.py`).

## Running it

```
python3 -m agents.producer.src <content-item-dir> [--apply] [--wpm 150]
```

Prints a JSON result (`aborted`/`blocked`/`stale`/`already_up_to_date`/
`produced`, scene summaries). Without `--apply`, nothing on disk changes.

```
python3 -m unittest discover -s agents/producer/tests -t .
```

## Known limitations

- **No versioned supersession.** A stale production plan is reported and
  left untouched, but the MVP does not automatically create a `prod-02`
  successor the way `templates/CLAIM.md` does for claims — that requires
  a human/operator to decide what to do about the changed script first,
  which is a reasonable place to stop for an MVP given "do not build
  unnecessary infrastructure" (Phase 7B task instructions).
- **Beat text, not always polished spoken narration.** Scene narration is
  copied verbatim from `SCRIPT.md`'s beats — but if a script's beats are
  descriptions rather than spoken-form lines (as `PRODUCTION_AUDIT.md`
  found for the golden sample), the Producer faithfully reproduces that,
  it doesn't fix it. A real production needs a fully spoken-form
  `SCRIPT.md` before Producer output is voice-ready.
- **Visual/music fields are placeholders only**, by design — see
  `agents/visual_planner/`.
