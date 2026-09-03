# Captions Template

One copy per captions attempt, store under
`content/<pillar>/<content-id>/captions/captions-<n>.md`. Produced by
`agents/captions/` from each scene's `Narration text` — deterministic
segmentation only, never a rewrite. See `agents/captions/CONTRACT.md` for
the exact segmentation rule and configurable defaults.

**Every caption's text is a verbatim substring of the source scene's
`Narration text`.** No paraphrasing, no grammar "fixes," no qualifier
("may", "could", "likely", "hypothetical", "we cannot know") ever
removed or softened — those qualifiers are part of this system's safety
architecture (`CONSTITUTION.md` rule 4).

| Field | Value |
|---|---|
| Captions ID | `<content-id>-captions-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Production ID | `<matches PRODUCTION.md>` |
| Captions content hash | `<sha256 of every scene's Narration text this is built from — see agents/captions/CONTRACT.md>` |
| Max characters per line | `<configured value>` |
| Max lines per caption | `<configured value>` |

## Scene captions

Repeated per scene:

### Scene `<scene-01>`

| Caption # | Start | End | Text |
|---|---|---|---|
| 1 | `0.0s` | `<Ns>` | `<verbatim chunk of the scene's Narration text>` |

## Generation status

`NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `REVISION_REQUIRED`
