# Assembler

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7D MVP — `src/`/`tests/`
exist and are stdlib-only, matching the shape of the other agents in
this repo.

## Responsibility

```
Structured production records (scenes, voice, assets) → Timeline → Video artifact
```

Combines a production's scenes, voiceover track, and asset records into
a deterministic `templates/TIMELINE.md` schedule and a video artifact.
Never creates or modifies claims, `SCRIPT.md`, `CONTENT_ITEM.md` status,
reviewer states, asset provenance, or voice records.

## Actual video artifact status

**A real renderer now exists (Phase 8): `agents/assembler/src/real_provider.py`'s
`FFmpegVideoRenderer`.** `LocalTestVideoRenderer` remains the CLI's and
every test's default, unchanged — it still writes the deterministic,
permanently-labeled placeholder manifest (`output/video-01.manifest.txt`),
and `templates/TIMELINE.md`'s `Playable` field is `NO` for it, same as
before. `FFmpegVideoRenderer` is a second `VideoRenderer` implementation
(`provider.py`'s `render()` gained one additive parameter, `root: Path`,
for it to resolve scenes' narration/visual/caption references into real
files — the placeholder renderer ignores it). It:

1. Normalizes each scene's real visual asset into a silent video segment
   held for exactly that scene's `templates/TIMELINE.md` duration.
2. Concatenates every segment (stream-copy — safe because normalization
   already gave every segment identical codec parameters).
3. Muxes in the real narration audio and burns in captions built from
   `agents/captions/`'s own per-scene, scene-relative timings plus each
   scene's `start` offset (`captions_reader.py`) — never a
   `templates/CAPTIONS.md` schema change.

If narration is longer than the timeline's total duration, only the
**last** scene's held duration is extended to cover the difference
(documented, not silently absorbed) — every other scene's duration is
exactly what `templates/TIMELINE.md` records; `-shortest` then trims any
leftover silent video past the audio's own end. `Playable = YES` is only
ever returned once this renderer's own `ffprobe` call has independently
confirmed the output has both a video and an audio stream and a positive
duration.

**A real architectural friction, found and documented, not silently
worked around:** `agents/full_pipeline/`'s stage order runs `ASSEMBLER`
*before* `CAPTIONS` (and `agents/captions/`'s own preconditions require
`Production status == CAPTIONS`, which only `ASSEMBLER`'s own successful
completion sets — captions structurally cannot run first). So the first,
in-sequence assembler pass has no `captions/captions-01.md` to burn in
yet — `FFmpegVideoRenderer` handles this gracefully (silent captions, no
crash) rather than blocking the whole stage on a file that hasn't been
produced yet. A genuinely captioned cut currently requires a second,
explicit render pass after `agents/captions/` runs (not yet automated by
any agent — see STATE.md's Phase 8 "Known limitations"); reordering
`CAPTIONS` before `ASSEMBLER` would fix this properly but is a bigger
change than "swap in a real provider," so it's deliberately left as a
documented follow-up rather than done under this phase's own instruction
not to redesign the pipeline.

## How it works

- **Approval gate**: `CONTENT_ITEM.md status == APPROVED` (checked
  independently of `PRODUCTION.md`), `PRODUCTION.md Production status`
  in `{ASSEMBLY, CAPTIONS}` (the second is this agent's own successful
  terminal state, accepted so a re-run can reach the already-up-to-date/
  staleness check).
- **Consistency checks** before building anything: the current
  `SCRIPT.md` hash matches `PRODUCTION.md`'s stored one;
  `voice/voice-01.md`'s `Generation status` is `GENERATED` and its own
  stored `Script content hash` matches the current script (else the
  voice track is stale — blocked); every scene has a
  `assets/asset-<n>.md` whose `Scene/visual content hash` matches that
  scene's *current* content hash (reusing
  `agents/assets/src/hashing.py`'s `compute_asset_content_hash`
  directly) — a missing or stale asset blocks assembly rather than
  substituting an unrelated one; every scene's claim references resolve
  to a real `claims/*.md` file; scene `Order` values are exactly `1..N`
  with no gaps.
- **Timeline** (`templates/TIMELINE.md`): one row per scene, `Start`/
  `End` computed as a running sum of each scene's `Duration` — scenes
  never overlap by construction. `Total duration` is the sum of every
  scene's duration. An asset's `Historical authenticity classification`
  is never re-derived here — the timeline only *references* the asset
  record (`assets/asset-<n>.md`), so the classification `agents/assets/`
  already decided survives untouched into assembly.
- **Hash/staleness**: `Assembly content hash` = sha256 of the script
  hash, a hash of the voice record's own provider/config/audio
  reference, and every scene's asset content hash — see
  `agents/assembler/CONTRACT.md`'s "Hash / dependency model". A matching
  hash on re-run is a no-op; a mismatch is `STALE` (existing files
  untouched); a hash field present but blank is malformed and aborts
  safely.
- **Write boundary** (`mutate.py`): `timeline/timeline-<n>.md` and
  `output/video-<n>.manifest.txt` only (fresh files, never overwritten),
  plus `PRODUCTION.md`'s `Assembly / Output` section and (on success)
  `Production status`.
- **Dry-run / apply**: `run_video_assembly(root, apply=False)` (the
  default) computes and returns everything without touching disk;
  `apply=True` writes.

## Relationship to other agents

Reuses `agents/producer/src.hashing`, `agents/assets/src.hashing`, and
`agents/assets/src.scene_reader.load_scene_visual_records` directly —
generic scene-file reading and hashing, never another agent's domain
logic. Adds its own small reader (`scene_reader.py`) for the two fields
it additionally needs (`Duration`, `Transition`) that the reused reader
doesn't carry. Runs after `agents/assets/` (`Production status =
ASSEMBLY`) and hands off to `agents/captions/` (`Production status =
CAPTIONS`).

## Running it

```
python3 -m agents.assembler.src <content-item-dir> [--apply]
```

Prints a JSON result (`aborted`/`blocked`/`stale`/`already_up_to_date`/
`produced`, scene count, `assembly_content_hash`, `playable`). Without
`--apply`, nothing on disk changes.

```
python3 -m unittest discover -s agents/assembler/tests -t .
```

## Known limitations

- No real video rendering — see "Actual video artifact status" above.
- No versioned supersession — a stale assembly is reported and left
  untouched; regenerating is a human/operator decision this MVP
  surfaces, matching every other production agent's identical
  documented limitation.
- One timeline/output per production (`timeline-01`/`video-01` only).
