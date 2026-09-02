# Production Golden Fixture — Audit (Phase 7)

Validates `templates/PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md`
against the existing Black Death What If? golden sample, before any
production agent (`agents/producer/`, `agents/voice/`,
`agents/visual-planner/`) is implemented. Mirrors the role
`content/.../AUDIT.md` played for the content-item schema in Phase 3 —
kept as a separate file so that file (part of the existing golden sample)
stays untouched by this phase, per the task's explicit requirement.

## Honesty check: this content item has not actually reached APPROVED

`CONTENT_ITEM.md`'s `status` here is `SCRIPT`, unchanged by this fixture.
Per `agents/orchestrator/`'s own Phase 6 run against this exact content
item, `FACT_CHECK` returns `REVISION_REQUIRED` (`c1` `DISPUTED`, `c11`
`UNRESOLVED`) — this item is **not** approved, and `agents/producer/
CONTRACT.md`'s Preconditions require `status = APPROVED` before a real
Producer may create a `PRODUCTION.md` at all. This fixture exists purely
to validate the schema against realistic content, exactly as the
original golden sample did for `templates/CLAIM.md` etc. in Phase 3 —
it is not a claim that this item is production-ready, and
`PRODUCTION.md`'s own "Separation from content lifecycle" section and
Notes/history log say so explicitly.

## Checklist results (per Phase 7 Step 9)

**1. Every production field has a clear purpose.**
Walked every field in `PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md`
against this real script while building the fixture; none were left
unused or redundant. The one field that came closest to unclear in
practice — `PRODUCTION.md`'s per-section rollups (Visual requirements,
Music/audio, Transitions, Asset references) — earned its place: without
them, reconstructing "what does this whole production need" would require
opening every scene file individually.

**2. Scene records can represent a complete video.**
Four scenes (`scenes/scene-01.md`–`scene-04.md`), 46s total, condensed
from `SCRIPT.md`'s six narrative beats — ordered, timed, with narration,
visual, caption, music, and transition fields for each. A renderer with
real narration/assets could assemble these into an actual sequence
without further authorial input.

**3. Scene records can reference claims.**
Every scene's "Source / claim references" field cites real claim IDs
(`c1`, `c2`, `c4`/`c12`/`c3`/`c10`/`c11`/`c6`, `c7`/`c8`/`c9`) — all
twelve of the content item's claims are covered across the four scenes.

**4. Assets have provenance.**
All three `assets/asset-<n>.md` files have `Generated vs. retrieved`,
`Source`, and `Licensing/provenance status` fields populated honestly —
`UNVERIFIED`/`not yet sourced`/`not yet produced` throughout, since no
real generation or retrieval has happened. None defaults to a
reassuring-sounding value it hasn't earned.

**5. Generated historical imagery cannot be confused with authentic
media.**
Demonstrated directly: `asset-01` (infographic map) and `asset-03`
(hypothetical scenario illustration) are both `GENERATED_RECONSTRUCTION`,
each with an explicit "why" — a modern infographic isn't a period
artifact, and a "what if" scenario has no possible authentic source at
all. `asset-02` (period plague artwork) is the one case aiming for
`AUTHENTIC_HISTORICAL_MEDIA`, and its own `Basis for classification`
field explicitly flags that this is *intent*, not a verified claim yet —
if no genuinely authentic item can be sourced, the classification itself
must change, not the honesty of the field. This proves the schema
supports the distinction the task requires, not just states it.

**6. Voice provider is abstracted.**
`voice/voice-01.md`'s `Provider` and `Voice configuration` are both
`TBD` — deliberately, not a placeholder oversight. Nothing in this
fixture, `templates/VOICE.md`, or `agents/voice/CONTRACT.md` names or
assumes a specific vendor.

**7. Production is separate from content status.**
`PRODUCTION.md`'s own "Separation from content lifecycle" section states
this explicitly, and in practice: `CONTENT_ITEM.md` was not touched by
building this fixture (confirmed by `git status` — see `STATE.md`) and
its `status` remains `SCRIPT` throughout.

**8. Human approval remains mandatory.**
`PRODUCTION.md`'s "Human review state" is `NOT_STARTED` with an explicit
note that `READY_TO_PUBLISH` requires a human `APPROVED` there, mirroring
`templates/VIDEO_QA.md`'s existing final-approval gate. No field in this
fixture or any new template asserts approval that hasn't happened.

**9. No publishing capability exists.**
Nothing in `templates/PRODUCTION.md`/`SCENE.md`/`ASSET.md`/`VOICE.md` or
any of the three new agent contracts mentions publishing except to
explicitly forbid it (see each `CONTRACT.md`'s "Forbidden actions").

## Genuine finding: `SCRIPT.md` doesn't yet contain verbatim spoken narration

`SCRIPT.md` states up front it is "a representative structure... not a
polished 10–15 minute script." Its "Narrative beats" are *descriptions*
of beats ("what actually happened: 1347–1351, spread across Europe,
mortality estimates from ~25% to 60%+...") rather than word-for-word
spoken lines — only the Hook is actual quoted spoken text. Building this
fixture surfaced that `templates/SCENE.md`'s "Narration text" field
("the exact text to be spoken, verbatim — never paraphrased from the
script by the renderer") has an implicit precondition:
**`SCRIPT.md` must contain real spoken-form narration for every beat
before a Producer can populate scenes with anything better than a
beat-description placeholder.** This fixture's `scenes/*.md` files quote
`SCRIPT.md`'s beat descriptions verbatim (so nothing is invented) but
flag in each file's Narration section that this is not yet final
narration. This is not a template defect — `templates/SCENE.md` is
correct to require verbatim text — it's a real gap between this
particular script's current level of polish and what production actually
needs, worth knowing before `agents/producer/` is implemented: a real
Producer run will need either a fuller `SCRIPT.md` or its own explicit
"draft narration, not final" state, which the current schema already
supports (`Generation/retrieval status: NOT_STARTED` /
`REVISION_REQUIRED`) without needing a new field.

## Conclusion

The production schema holds up against a realistic (if intentionally
unapproved) script: every field earned its place, the fact/hypothesis
and authentic/generated distinctions both survive contact with real
content, and production stayed fully decoupled from content status and
from publishing. One genuine gap was found (script narration polish, not
a schema defect) and documented rather than silently worked around.
