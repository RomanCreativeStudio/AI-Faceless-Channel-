# Captions

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7D MVP — `src/`/
`tests/` exist and are stdlib-only.

## Responsibility

```
Narration sentence → caption chunks → timestamps
```

Derives on-screen captions from each scene's already-approved
`Narration text`. Never introduces a new fact, changes a claim, changes
uncertainty, or alters What If? framing — see "Caption integrity" below.

## Segmentation (deterministic, documented defaults)

1. Split narration into sentences on `.`/`!`/`?` followed by whitespace
   — purely punctuation-based, no semantic detection.
2. Pack each sentence into caption chunks word-by-word (never splitting a
   word) up to `max_characters_per_line × max_lines_per_caption`
   characters — **defaults 40 × 2 = 80**, both explicit parameters to
   `run_caption_generation(...)`, never hidden.
3. Time each chunk proportionally to its character length within the
   scene's own `Duration` (from `templates/SCENE.md`) — never an
   independent re-estimate, so caption timing stays consistent with
   `templates/TIMELINE.md`.

## Caption integrity

Every caption's `Text` is a verbatim substring of its source scene's
`Narration text` — no paraphrasing, no grammar "fixes," and every hedge
("may", "could", "likely", "hypothetical", "we cannot know") survives
unaltered, since segmentation only ever inserts whitespace/line breaks
between existing words, never changes them.

## Hash / staleness

`Captions content hash` = sha256 of every scene's `Narration text`, in
scene order. A matching hash on re-run is a no-op; a mismatch (a scene's
narration changed) is `STALE` — existing captions untouched. A hash
field present but blank is malformed and aborts safely. No versioned
supersession this MVP (same documented limitation as every other
production agent).

## Write boundary

`mutate.py`'s whitelist: `captions/captions-<n>.md` only (fresh file,
never overwritten), plus `PRODUCTION.md`'s `Captions` section and (on
success) `Production status`.

## Relationship to other agents

Reuses `agents/producer/src.hashing`, `agents/assets/src.scene_reader`,
and `agents/assembler/src.scene_reader.load_scene_timing` directly —
generic scene-file reading, never another agent's domain logic. Runs
after `agents/assembler/` (`Production status = CAPTIONS`) and hands off
to `agents/thumbnail/` (`Production status = THUMBNAIL`).

## Running it

```
python3 -m agents.captions.src <content-item-dir> [--apply]
```

```
python3 -m unittest discover -s agents/captions/tests -t .
```

## Known limitations

- No versioned supersession — see "Hash / staleness" above.
- One captions record per production (`captions-01` only).
- Segmentation is punctuation/character-count based only — no
  linguistic/readability optimization.
