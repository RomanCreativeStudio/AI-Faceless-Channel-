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

**No real video is produced this phase.** This environment has no
`ffmpeg` (or any video-encoding tool) installed, and every agent in this
repo is stdlib-only by established convention — adding a dependency to
render real video would be a unilateral architecture change, not this
phase's task. `LocalTestVideoRenderer` (the only `VideoRenderer`
implementation this phase) writes a deterministic, permanently-labeled
placeholder manifest (`output/video-01.manifest.txt`) describing the
scene-by-scene sequence a real renderer would assemble.
`templates/TIMELINE.md`'s `Playable` field is always `NO` — this agent
never claims an artifact is playable without independent verification.
A future real renderer is a second `VideoRenderer` implementation;
nothing in `pipeline.py` needs to change to add one.

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
