# Contract: Captions

Governs deriving on-screen captions from a production's already-approved
narration. Phase 7D MVP — `src/`/`tests/` exist.

Subordinate to `CONSTITUTION.md` and to `templates/CAPTIONS.md` (the
schema it produces against).

## Purpose

```
Narration sentence → caption chunks → timestamps
```

Captions must be derived from approved narration and must **never**
introduce new facts, change a claim, change uncertainty, or alter What
If? framing. This agent does not touch narration wording — only how it's
chunked and timed for display.

## Preconditions

- `CONTENT_ITEM.md status == APPROVED` (checked independently).
- `PRODUCTION.md Production status` in `{CAPTIONS, THUMBNAIL}` — `CAPTIONS`
  is the state `agents/assembler/` sets once assembled (this agent's own
  literal stage name); `THUMBNAIL` is this agent's own successful
  terminal state, accepted for the standard re-run reason.
- The current `SCRIPT.md` hash matches `PRODUCTION.md`'s stored one.
- Every scene's `Narration text` is non-empty.

## Segmentation rule (deterministic, documented defaults)

1. Split each scene's `Narration text` into sentences on `.`/`!`/`?`
   followed by whitespace (`re.split(r"(?<=[.!?])\s+", text)`) — no
   semantic sentence detection, purely punctuation-based, so the same
   input always segments the same way.
2. Each sentence becomes one or more caption chunks, packed
   word-by-word (never splitting a word) up to `max_characters_per_line
   × max_lines_per_caption` characters — **defaults: 40 characters per
   line, 2 lines per caption (80 characters per caption)**, both
   explicit, configurable parameters to `run_caption_generation(...,
   max_characters_per_line=40, max_lines_per_caption=2)`, never a hidden
   assumption.
3. Each chunk's on-screen duration is proportional to its character
   length within the scene's total `Duration` (from `templates/SCENE.md`)
   — `chunk_seconds = scene_duration × len(chunk) / len(scene_narration)`,
   cumulative from `0s`. Captions are timed against the scene's own
   established duration (never independently re-estimated), so caption
   timing stays consistent with `templates/TIMELINE.md`.

## Caption integrity

**Every caption's `Text` is a verbatim substring of its source scene's
`Narration text`.** This agent never paraphrases, never "fixes" grammar,
and never removes a qualifier ("may", "could", "likely", "hypothetical",
"we cannot know", or any other hedge) — those qualifiers are part of
this system's safety architecture (`CONSTITUTION.md` rule 4,
`templates/SCRIPT.md`'s What If? fact/hypothesis separation). Verified
mechanically: every generated caption's `Text`, with chunk-boundary
whitespace stripped, must appear as a contiguous substring of the source
scene's `Narration text`.

## Hash / staleness

`Captions content hash` = sha256 of every scene's `Narration text`,
concatenated in scene order (reusing the same content this agent reads,
no separate computation elsewhere). A matching hash on re-run is a
no-op; a mismatch means a scene's narration changed since — `STALE`,
existing captions untouched. A hash field present but blank is malformed
and aborts safely. No versioned supersession this MVP — same documented
limitation as every other production agent.

## Allowed actions

- Read `CONTENT_ITEM.md`, `PRODUCTION.md`, `SCRIPT.md`, every scene's
  `Narration text`/`Duration`
- Create `captions/captions-<n>.md` (never overwrites an existing,
  unstale one)
- Update `PRODUCTION.md`'s `Captions` section, and advance `Production
  status` from `CAPTIONS` to `THUMBNAIL` once generated

## Forbidden actions

Never modifies `SCRIPT.md`, any `scenes/scene-<n>.md` field, any claim,
`CONTENT_ITEM.md` (status or any stage state), `voice/voice-<n>.md`,
`assets/asset-<n>.md`, or `timeline/timeline-<n>.md`. Never publishes.

## Handoff

On completion, `captions/captions-<n>.md`'s `Generation status` is
`GENERATED` and `PRODUCTION.md`'s `Production status` advances to
`THUMBNAIL`.
