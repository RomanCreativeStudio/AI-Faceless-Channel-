# Thumbnail

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7D MVP — `src/`/
`tests/` exist and are stdlib-only.

## Responsibility

Produces a thumbnail **specification** (never a generated image) and
the production's basic `Title / description` metadata. Must never imply
something happened if the content is hypothetical — see "Fact / What
If? framing" below.

## Fact / What If? framing

`Title concept` is never synthesized prose — it's built only from
`CONTENT_ITEM.md`'s own already-approved `Working title`:

- Already hedged (contains `?`, or starts with "what if"/"could"/
  "might") → used verbatim.
- `what-if` pillar, not already hedged → wrapped in the one fixed
  template `"What if: {title}?"` — never rewording the title itself.
- Any other pillar → used verbatim, never artificially hedged.

`Authenticity considerations` is read (never recomputed) from each
scene's already-decided `assets/asset-<n>.md` classification — if any is
`GENERATED_RECONSTRUCTION`, the spec states plainly the thumbnail must
not present it as real. This doubles as the disclosure/uncertainty note.

## Provider abstraction

`ThumbnailProvider.generate_spec(title_source, visual_source,
hedge_required, authenticity_summary) -> ThumbnailSpec`. This phase's
only implementation, `LocalTestThumbnailProvider`, is deterministic and
produces a specification only — never a real generated image. A future
real image-generation integration is a second implementation; nothing in
`pipeline.py` needs to change to add one.

## Hash / staleness

`Thumbnail content hash` = sha256 of `Working title` + content pillar +
every referenced claim's `Classification`, in scene order. A matching
hash on re-run is a no-op; a mismatch (title/pillar/claim classification
changed) is `STALE` — existing spec untouched. A hash field present but
blank is malformed and aborts safely.

## Write boundary

`mutate.py`'s whitelist: `thumbnail/thumbnail-<n>.md` only (fresh file),
plus `PRODUCTION.md`'s `Thumbnail` and `Title / description` sections and
(on success) `Production status`.

## Relationship to other agents

Reuses `agents/producer/src.hashing` and
`agents/assets/src.scene_reader.load_scene_visual_records` directly.
Reads (never recomputes) each scene's `assets/asset-<n>.md` authenticity
classification — data already decided by `agents/assets/`, not
re-derived domain logic. Runs after `agents/captions/` (`Production
status = THUMBNAIL`) and hands off to `agents/production_qa/`
(`Production status = METADATA`).

## Running it

```
python3 -m agents.thumbnail.src <content-item-dir> [--apply]
```

```
python3 -m unittest discover -s agents/thumbnail/tests -t .
```

## Known limitations

- No real image generation — a specification only, always labeled as a
  placeholder.
- No versioned supersession.
- No SEO/marketing optimization — `Description` is a placeholder, never
  synthesized copy.
