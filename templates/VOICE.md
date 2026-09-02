# Voice Template

One copy per voiceover track (typically one per production, covering all
scenes' narration), store under
`content/<pillar>/<content-id>/voice/voice-<n>.md`. Referenced by
`templates/PRODUCTION.md`'s "Voiceover information" section.

**Provider-agnostic by design.** No specific TTS/voice provider is named
or assumed anywhere in this template — `Provider` and `Voice
configuration` are free-text fields precisely so a future implementation
can swap providers without changing this schema. Nothing here commits to
an API, a vendor, or a technical integration.

| Field | Value |
|---|---|
| Voice ID | `<content-id>-voice-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Provider | `<abstract label, e.g. "TBD" or a provider name once chosen — this field alone must never be assumed elsewhere in the system>` |
| Voice configuration | `<voice/style parameters as the provider defines them — opaque to everything outside this record>` |

## Narration source

`<the full narration text this track covers, or a pointer to SCRIPT.md's sections/beats in order — must match scene-level "Narration text" fields exactly, never paraphrase>`

## Generated audio

| Field | Value |
|---|---|
| Reference | `<file path once generated — "not yet generated" until then>` |
| Duration | `<actual rendered duration once generated — "N/A" until then>` |

## Generation status

`NOT_STARTED` \| `IN_PROGRESS` \| `GENERATED` \| `REVISION_REQUIRED`

## QA status

`NOT_STARTED` \| `IN_PROGRESS` \| `PASS` \| `REVISION_REQUIRED`

`<notes — e.g. mispronunciation, pacing, audio artifacts>`
