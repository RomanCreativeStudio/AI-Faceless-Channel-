# Contract: Voice

Specification only — **not implemented this phase.** Governs converting
approved narration into voiceover audio. Provider-agnostic by design —
see `templates/VOICE.md`.

Subordinate to `CONSTITUTION.md` and to `templates/VOICE.md` (the schema
it produces against). Where anything below conflicts with that, it wins.

## Purpose

Convert a production's narration text (carried into `scenes/scene-<n>.md`
by `agents/producer/`, verbatim from `SCRIPT.md`) into a generated
voiceover audio track, recorded as `templates/VOICE.md`. Does not touch
narration wording, visuals, or assembly.

## Preconditions

Only runs against a `PRODUCTION.md` whose `Production status` is `VOICE`
(reached after `agents/producer/` completes `PRODUCTION_PLANNING`).

## Inputs

- `PRODUCTION.md` (status — read-only)
- `scenes/scene-<n>.md` (`Narration text` fields, in order — read-only)

## Outputs

- `voice/voice-<n>.md`

## Allowed actions

- Read `PRODUCTION.md` and every scene's `Narration text`
- Create/update `voice/voice-<n>.md`'s own fields: `Provider`, `Voice
  configuration`, `Narration source`, `Generated audio` reference/
  duration, `Generation status`, `QA status`
- Update `PRODUCTION.md`'s `Voiceover information` section to point at
  the voice record it created, and (once genuinely complete) advance
  `Production status` from `VOICE` to `VISUAL_PLANNING`

## Forbidden actions

The Voice agent must **never**:

- Alter narration meaning. `Narration source` in `voice/voice-<n>.md`
  must match scene-level `Narration text` exactly — no summarizing,
  softening, or embellishing what the script says.
- Insert unsupported claims. If a provider's text-normalization step
  would add or change factual content (numbers, names, dates) to make
  narration flow better, that output is rejected, not accepted — flag it
  for a human/Producer fix instead of "fixing" it silently.
- Publish anything, anywhere, under any condition.
- Modify `SCRIPT.md`, any `claims/*.md` file, or any `scenes/scene-<n>.md`
  field other than reading `Narration text`.
- Commit the rest of the system to a specific TTS/voice provider. Every
  field this agent writes stays within `templates/VOICE.md`'s
  provider-agnostic shape — nothing downstream may assume a particular
  vendor's API, voice ID format, or configuration schema.

## Handoff

On completion, `voice/voice-<n>.md`'s `Generation status` is `GENERATED`
(or `REVISION_REQUIRED` if something failed QA) and `PRODUCTION.md`'s
`Production status` advances to `VISUAL_PLANNING` only once voice `QA
status` is `PASS` — never automatically alongside generation.
