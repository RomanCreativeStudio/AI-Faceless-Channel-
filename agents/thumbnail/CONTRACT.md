# Contract: Thumbnail

Governs producing a thumbnail **specification** (never a generated image
— no external image-generation integration exists this phase) and the
production's basic title/description metadata. Phase 7D MVP —
`src/`/`tests/` exist.

Subordinate to `CONSTITUTION.md` and to `templates/THUMBNAIL.md`.

## Purpose

A structured thumbnail spec — title concept, visual concept, text
overlay, focal subject, composition, claim/theme relationship,
authenticity considerations, generation strategy, status — plus
`PRODUCTION.md`'s basic `Title / description` metadata. **Must never
imply something happened if the content is hypothetical** — see "Fact /
What If? framing" below. This is not a sophisticated SEO/marketing agent;
no clickbait, no invented facts, no certainty where the script has none.

## Preconditions

- `CONTENT_ITEM.md status == APPROVED` (checked independently).
- `PRODUCTION.md Production status` in `{THUMBNAIL, METADATA}` —
  `THUMBNAIL` is set by `agents/captions/`; `METADATA` is this agent's
  own successful terminal state, accepted for the standard re-run reason.
- The current `SCRIPT.md` hash matches `PRODUCTION.md`'s stored one.
- Every scene's claim references resolve to a `claims/*.md` file.

## Fact / What If? framing (the deterministic rule)

`Title concept` is **never synthesized prose** — it is built only from
`CONTENT_ITEM.md`'s own already-approved `Working title`:

- If `Working title` already reads as hedged (contains `?`, or starts
  with `what if`/`could`/`might`, case-insensitive) → used **verbatim**,
  unchanged.
- Else, if the content pillar is `what-if` → wrapped in a single fixed,
  non-content-altering template: `"What if: {Working title}?"` — the
  only transformation this agent ever applies, and it never touches the
  words of the title itself, only wraps them.
- Else (non-`what-if` pillars, already-established fact) → used verbatim,
  no wrapping.

This guarantees a hypothetical premise's thumbnail concept is always
hedged and a factual pillar's is never artificially hedged — matching
this phase's own example: `"THE BLACK DEATH WAS STOPPED!"` is never
produced from a `what-if` `Working title`; `"COULD MODERN MEDICINE HAVE
STOPPED IT?"` (or the title's own pre-existing hedge) is.

`Authenticity considerations` is derived by reading (never recomputing)
each scene's `assets/asset-<n>.md`'s already-decided `Historical
authenticity classification` — if any is `GENERATED_RECONSTRUCTION`, the
field states explicitly that the production includes hypothetical/
generated content the thumbnail must not present as real; this doubles
as the disclosure/uncertainty note task item 12 asks for, rather than a
separate invented field.

## Provider abstraction

```python
class ThumbnailProvider(Protocol):
    label: str
    def generate_spec(self, title_source: str, visual_source: str, hedge_required: bool, authenticity_summary: str) -> ThumbnailSpec: ...
```

This phase's only implementation, `LocalTestThumbnailProvider`, is
deterministic and produces a **specification**, explicitly labeled as a
placeholder, never a real generated image. A future real image-generation
integration is a second `ThumbnailProvider` implementation; nothing in
`pipeline.py` needs to change to add one.

## Hash / staleness

`Thumbnail content hash` = sha256 of `CONTENT_ITEM.md`'s `Working title`
+ content pillar + every referenced claim's `Classification`, in scene
order. A matching hash on re-run is a no-op; a mismatch is `STALE` —
existing spec untouched. A hash field present but blank is malformed and
aborts safely. No versioned supersession this MVP.

## Allowed actions

- Read `CONTENT_ITEM.md` (`Working title`, `Content pillar`),
  `PRODUCTION.md`, `SCRIPT.md`, every scene's claim references, every
  `assets/asset-<n>.md`'s `Historical authenticity classification`
- Create `thumbnail/thumbnail-<n>.md` (never overwrites an existing,
  unstale one)
- Update `PRODUCTION.md`'s `Thumbnail` section and `Title / description`
  section (mirroring `CONTENT_ITEM.md`'s `Working title` verbatim, and a
  placeholder `Description` — never synthesized marketing copy), and
  advance `Production status` from `THUMBNAIL` to `METADATA` once
  generated

## Forbidden actions

Never modifies `CONTENT_ITEM.md`, `SCRIPT.md`, any claim, any
`scenes/scene-<n>.md`/`voice/voice-<n>.md`/`assets/asset-<n>.md` field,
`timeline/timeline-<n>.md`, or `captions/captions-<n>.md`. Never invents
a fact or a claim, never implies a hypothetical premise happened, never
publishes.

## Handoff

On completion, `thumbnail/thumbnail-<n>.md`'s `Thumbnail status` is
`GENERATED` and `PRODUCTION.md`'s `Production status` advances to
`METADATA`.
