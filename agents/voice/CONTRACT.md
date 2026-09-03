# Contract: Voice

Governs converting approved narration into voiceover audio.
Provider-agnostic by design — see `templates/VOICE.md`. Phase 7C-1 MVP —
`src/`/`tests/` exist.

Subordinate to `CONSTITUTION.md` and to `templates/VOICE.md` (the schema
it produces against). Where anything below conflicts with that, it wins.

## Purpose

Convert a production's narration text (carried into `scenes/scene-<n>.md`
by `agents/producer/`, verbatim from `SCRIPT.md`) into a generated
voiceover audio track, recorded as `templates/VOICE.md`. Does not touch
narration wording, visuals, or assembly. This MVP's actual audio output
is a deterministic, clearly-labeled placeholder — see "Provider
abstraction" and `agents/voice/README.md`'s "Test provider."

## Preconditions

- `CONTENT_ITEM.md`'s `status` must be `APPROVED` — the same gate
  `agents/producer/CONTRACT.md` enforces, checked independently here
  rather than trusted transitively through `PRODUCTION.md` (defense in
  depth: a `PRODUCTION.md` file existing is not proof the content behind
  it was ever actually approved — see
  `agents/visual_planner/CONTRACT.md`'s own defense-in-depth note, found
  for the identical reason in Phase 7B).
- `PRODUCTION.md` must exist with `Production status` equal to either
  `PRODUCTION_PLANNING` (the state a fresh run starts from — what
  `agents/producer/` leaves behind) or `VISUAL_PLANNING` (the state this
  agent itself leaves behind after a successful generation — see
  "Handoff"). Both are accepted so that re-running this agent after its
  own prior success can still reach its own already-up-to-date/staleness
  check instead of always failing this precondition; this agent never
  moves `Production status` backward, and a stale re-run in either state
  still just refuses and reports why (see "Re-running / staleness").

  **Gap found and fixed before implementation:** this contract previously
  required `Production status = VOICE`, describing that state as "reached
  after `agents/producer/` completes `PRODUCTION_PLANNING`" — but
  `agents/producer/CONTRACT.md`'s own Handoff section is explicit that
  Producer's output state is `PRODUCTION_PLANNING` and it "does not
  advance further; `VOICE` is `agents/voice/`'s stage to start, not the
  Producer's to trigger." No agent ever sets `Production status` to
  `VOICE`, so requiring it literally would make this agent permanently
  unrunnable — the same class of gap Visual Planner's Preconditions hit
  in Phase 7B. Unlike that case, no interim allowance is needed: this
  agent *is* the one responsible for the `VOICE` stage, so it is the one
  that runs starting from `PRODUCTION_PLANNING` (the actual state
  Producer leaves) and — per "Handoff" below — is itself the one that
  advances `Production status` onward, once its own work is genuinely
  complete.
- The current `SCRIPT.md` must exist and its content hash
  (`agents/producer/src/hashing.py`'s `compute_script_content_hash`,
  reused directly) must match `PRODUCTION.md`'s stored `Script content
  hash` — otherwise the production plan itself is stale relative to the
  script, and generating voice from it would build on outdated scenes.

## Schema change (documented per the Phase 7C-1 task's requirement)

`templates/VOICE.md` gained one new field: `Script content hash` in the
identity table, mirroring the identical, already-established pattern in
`templates/PRODUCTION.md`/`REVIEW.md`. Reason: requirement 4 of this
phase's task ("VOICE.md must record: script hash... If SCRIPT.md
changes... the existing voice result becomes STALE") cannot be met
without persisting the hash the voice track was generated against. No
other template was touched, and no other field was added — "Provider-ready
narration" is *not* a persisted field; see `templates/VOICE.md`'s
"Narration source" section and "Narration integrity" below for why a
single documented sentence was sufficient instead of growing the schema.

## Provider abstraction

`agents/voice/src/provider.py` defines a `VoiceProvider` interface
(`generate(narration_text, voice_configuration) -> GeneratedAudio`) that
every provider — test or real — implements. `agents/voice/src/pipeline.py`
depends only on that interface, never on a specific provider's internals.
This MVP's only implementation is `agents/voice/src/test_provider.py`'s
`LocalTestVoiceProvider` — deterministic, no network calls, no external
API, output permanently labeled `TEST / PLACEHOLDER AUDIO`. A future real
TTS provider is a second `VoiceProvider` implementation; nothing in
`pipeline.py`, `mutate.py`, or `templates/VOICE.md` needs to change to
add one. No specific commercial provider is named anywhere in this
contract, `templates/VOICE.md`, or any code this phase.

## Inputs

- `CONTENT_ITEM.md` (`status` — read-only)
- `PRODUCTION.md` (`Production status`, `Script content hash` — read-only
  except as listed below)
- `SCRIPT.md` (for its current content hash only — read-only)
- `scenes/scene-<n>.md` (`Narration text` fields, in order — read-only)

## Outputs

- `voice/voice-<n>.md`
- `voice/voice-<n>.audio.txt` — the placeholder/real audio artifact
  reference this MVP actually persists (see `agents/voice/README.md`
  "Artifact handling")

## Allowed actions

- Read `CONTENT_ITEM.md`, `PRODUCTION.md`, `SCRIPT.md`, and every scene's
  `Narration text`
- Create `voice/voice-<n>.md` (never overwrite an existing one — see
  "Re-running") with its own fields: `Provider`, `Voice configuration`,
  `Script content hash`, `Narration source`, `Generated audio`
  reference/duration, `Generation status`, `QA status`
- Create the corresponding `voice/voice-<n>.audio.txt` artifact file
- Update `PRODUCTION.md`'s `Voiceover information` section to point at
  the voice record it created, and advance `Production status` from
  `PRODUCTION_PLANNING` to `VISUAL_PLANNING` — but only once this agent's
  own `QA status` is genuinely `PASS`, never alongside generation
  unconditionally

## Forbidden actions

The Voice agent must **never**:

- Alter narration meaning. `Narration source` in `voice/voice-<n>.md`
  must match scene-level `Narration text` exactly — no summarizing,
  softening, or embellishing what the script says. The only
  transformation permitted anywhere in this pipeline, SOURCE NARRATION →
  PROVIDER-READY NARRATION (the text actually handed to a provider), is a
  deterministic normalization of curly quotes/apostrophes to straight
  ASCII ones and collapsing repeated whitespace — nothing else. It must
  never change a word, a number, a hedge phrase ("it's hard to say"), or
  a What If? fact/hypothesis distinction, and it is never itself
  persisted as a separate `templates/VOICE.md` field (see "Schema
  change" above).
- Insert unsupported claims. If a provider's text-normalization step
  would add or change factual content (numbers, names, dates) to make
  narration flow better, that output is rejected, not accepted — flag it
  for a human/Producer fix instead of "fixing" it silently.
- Publish anything, anywhere, under any condition.
- Modify `SCRIPT.md`, any `claims/*.md` file, or any `scenes/scene-<n>.md`
  field.
- Modify `CONTENT_ITEM.md` at all — not `status`, not `Owner approval
  state`, not any stage state.
- Commit the rest of the system to a specific TTS/voice provider. Every
  field this agent writes stays within `templates/VOICE.md`'s
  provider-agnostic shape — nothing downstream may assume a particular
  vendor's API, voice ID format, or configuration schema.
- Mark placeholder output as production-ready. `Generation status =
  GENERATED` means the (test or real) provider produced *something* that
  passed this agent's own structural QA checks — it is never itself a
  claim of production-quality speech; the test provider's output is
  always labeled `TEST / PLACEHOLDER AUDIO` in both the artifact file and
  `voice/voice-<n>.md`.

## Re-running / staleness

If `voice/voice-<n>.md` already exists for a content item: a matching
`Script content hash` means it's already up to date (no-op, nothing
rewritten); a mismatched hash means `SCRIPT.md` changed since generation
— the existing voice result is `STALE`. This agent refuses to silently
reuse or regenerate it, returning a structured `stale` result and leaving
the existing `voice/voice-<n>.md`/`voice-<n>.audio.txt` untouched, the
same conservative pattern `agents/producer/CONTRACT.md`'s "Re-running"
section uses. **Known limitation, documented rather than worked around:**
this MVP does not implement versioned supersession (`voice-01` →
`voice-02`) the way `templates/CLAIM.md` does for claims — regenerating
after a script change is a decision this MVP surfaces, not automates.

## Handoff

On completion, `voice/voice-<n>.md`'s `Generation status` is `GENERATED`
(or `REVISION_REQUIRED` if a QA check failed) and `PRODUCTION.md`'s
`Production status` advances to `VISUAL_PLANNING` only once voice `QA
status` is `PASS` — never automatically alongside generation. If QA does
not pass, `Production status` stays `PRODUCTION_PLANNING` so a corrected
re-run remains possible.
