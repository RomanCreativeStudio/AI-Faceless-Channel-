# Contract: Assembler

Governs turning a production's structured records (scenes, voice, assets)
into a deterministic timeline and a video artifact. Phase 7D MVP —
`src/`/`tests/` exist.

Subordinate to `CONSTITUTION.md` and to `templates/TIMELINE.md`/
`PRODUCTION.md` (the schemas it produces against).

## Purpose

```
Structured production records (scenes, voice, assets) → Timeline → Video artifact
```

Never creates or modifies claims, research, `SCRIPT.md`, `CONTENT_ITEM.md`
status, reviewer states, approval state, asset provenance, or voice
records — it only *reads* them to build a timeline and (attempt to)
render an output.

## Preconditions

- `CONTENT_ITEM.md status == APPROVED` (checked independently of
  `PRODUCTION.md`, the same defense-in-depth every production agent uses).
- `PRODUCTION.md Production status` in `{ASSET_COLLECTION's successor
  ASSEMBLY, CAPTIONS}` — i.e. `ASSEMBLY` (set by `agents/assets/` once
  every scene's asset is current — this agent's own literal stage name)
  or `CAPTIONS` (this agent's own successful terminal state, accepted so
  a re-run can reach the already-up-to-date/staleness check, same
  pattern every prior production agent uses).
- The current `SCRIPT.md` hash matches `PRODUCTION.md`'s stored one.
- `voice/voice-01.md` exists, its `Generation status` is `GENERATED`, and
  its own stored `Script content hash` matches the current script — a
  mismatch means the voice track is stale relative to the script;
  BLOCKED, never silently reused.
- Every scene has a corresponding `assets/asset-<n>.md` whose `Scene/
  visual content hash` matches that scene's current content hash (reusing
  `agents/assets/src/hashing.py`'s `compute_asset_content_hash` directly)
  — a missing or stale asset BLOCKs assembly for that scene rather than
  substituting an unrelated one.
- Every scene's claim references still resolve to a `claims/*.md` file.

## Renderer abstraction

```python
class VideoRenderer(Protocol):
    label: str
    def render(self, scenes: list[SceneTimelineEntry], total_duration: int) -> RenderResult: ...
```

`pipeline.py` depends only on this interface. This phase's only
implementation, `LocalTestVideoRenderer`, produces a deterministic,
permanently-labeled placeholder — see "Actual video artifact status".

## Actual video artifact status

**No real video is rendered this phase.** This environment has no
`ffmpeg` (or any video-encoding tool) installed, and every agent in this
repository is stdlib-only by established, repeated project convention
(`SYSTEM.md`'s "Out of scope" list, every prior phase) — installing a new
dependency to add real rendering would be a unilateral architecture
change, not a Phase 7D task. `LocalTestVideoRenderer` therefore writes a
deterministic **manifest** (`output/video-<n>.manifest.txt`) describing
the scene-by-scene sequence a real renderer would assemble — permanently
labeled `TEST / PLACEHOLDER VIDEO MANIFEST — not a real video file`, with
`templates/TIMELINE.md`'s `Playable` field always `NO`. This is the
"deterministic renderer abstraction, documented" option `agents/assembler/
CONTRACT.md`'s own task explicitly allows when real rendering "is not
safely available" — never claiming an artifact is playable without
independent verification. A future real renderer (ffmpeg-backed or
otherwise) is a second `VideoRenderer` implementation; nothing in
`pipeline.py` needs to change to add one.

## Timeline model

`templates/TIMELINE.md`'s `Scene timeline` table: one row per scene, in
`Order`, with `Start`/`End` computed as a running sum of each scene's
`Duration` (from `templates/SCENE.md`) — the first scene starts at `0s`,
each subsequent scene's `Start` equals the previous scene's `End`, so
scenes can never overlap by construction. `Total duration` is the sum of
every scene's duration; this agent verifies scene `Order` values are
exactly `1..N` with no gaps or duplicates (a corrupted/missing scene
would otherwise silently produce a wrong timeline) before computing
anything.

## Hash / dependency model

`Assembly content hash` = sha256 of: the current script hash, the current
voice record's own hash, and every scene's asset content hash (sorted by
scene order) — capturing every upstream input the timeline depends on.
If any upstream artifact changes (script → voice stale → assembly stale;
or an asset's underlying scene changes → that asset stale → assembly
stale), this hash changes and a re-run's mismatch is detected the same
way `agents/producer/`'s/`agents/voice/`'s/`agents/assets/`'s own hashes
work — reusing `agents/producer/src/hashing.py`'s `compute_script_content_hash`
and `agents/assets/src/hashing.py`'s `compute_asset_content_hash` directly,
never duplicating either.

## Re-running / staleness

A matching `Assembly content hash` on an existing `timeline/timeline-01.md`
is a no-op. A mismatch means some upstream input changed since assembly —
`STALE`, the existing timeline/output are left untouched (no
versioned supersession this MVP, matching every other production agent's
identical documented limitation). A hash field present but blank is
malformed and aborts safely.

## Allowed actions

- Read `CONTENT_ITEM.md`, `PRODUCTION.md`, `SCRIPT.md`, every scene,
  `voice/voice-01.md`, every `assets/asset-<n>.md`, and referenced claims
  (existence only)
- Create `timeline/timeline-<n>.md` and `output/video-<n>.manifest.txt`
  (never overwrites an existing, unstale one)
- Update `PRODUCTION.md`'s `Assembly / Output` section, and advance
  `Production status` from `ASSEMBLY` to `CAPTIONS` once assembled

## Forbidden actions

Never creates or modifies a claim, `research/*.md`, `SCRIPT.md`,
`CONTENT_ITEM.md` (status or any stage state), a `scenes/scene-<n>.md`
field, a `voice/voice-<n>.md` field, an `assets/asset-<n>.md` field
(including never stripping or overriding its `Historical authenticity
classification` — that classification is carried into the timeline's
claim-reference metadata unchanged, never re-derived), `reviews/*.md`, or
anything under `CONTENT_ITEM.md`'s approval state. Never publishes.

## Handoff

On completion, `timeline/timeline-<n>.md`'s `Assembly status` is
`ASSEMBLED` and `PRODUCTION.md`'s `Production status` advances to
`CAPTIONS`.
