# Voice

Implements [`CONTRACT.md`](./CONTRACT.md) — **not implemented yet.** This
is a Phase 7 contract-only deliverable; there is no `src/` here.

## Responsibility

Converts a production's narration (from `scenes/scene-<n>.md`, verbatim
from `SCRIPT.md`) into voiceover audio, recorded as
`templates/VOICE.md`. Never alters narration meaning or inserts
unsupported claims. No specific TTS/voice provider is named anywhere in
this contract or `templates/VOICE.md` — deliberately, so a provider can
be chosen (or swapped) later without a schema change.

## Relationship to other agents

Runs after `agents/producer/` (which produces the scenes this agent reads
narration from) and before `agents/visual_planner/` in
`templates/PRODUCTION.md`'s `Production status` sequence
(`PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING → ...`).
