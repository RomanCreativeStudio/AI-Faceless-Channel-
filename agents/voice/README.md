# Voice

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7C-1 MVP —
`src/`/`tests/` exist and are stdlib-only, matching the shape of the
other agents in this repo.

## Responsibility

Converts a production's narration (from `scenes/scene-<n>.md`, verbatim
from `SCRIPT.md`) into a voiceover audio track, recorded as
`templates/VOICE.md`. Never alters narration meaning or inserts
unsupported claims. This MVP's actual output is a deterministic,
clearly-labeled placeholder artifact — see "Test provider" below — not
real speech.

## Provider abstraction

```
VoiceProvider (protocol, provider.py)
        ↓
LocalTestVoiceProvider (test_provider.py) — the only implementation this phase
        ↓
GeneratedAudio (provider_label, voice_configuration, artifact_content,
                 duration_seconds, is_placeholder)
```

`agents/voice/src/pipeline.py` depends only on the `VoiceProvider`
interface (`generate(narration_text, voice_configuration) ->
GeneratedAudio`) — never on a specific provider's internals. No specific
TTS/voice vendor is named anywhere in this contract, `templates/VOICE.md`,
or any code this phase — deliberately, so a real provider can be added as
a second `VoiceProvider` implementation later without changing
`pipeline.py`, `mutate.py`, or the schema. `run_voice_generation(...,
provider=...)` accepts any object implementing the interface — see
`agents/voice/tests/test_provider_abstraction.py` for a fake provider
proving the pipeline never hardcodes the test provider's internals.

## Test provider

`LocalTestVoiceProvider` (`test_provider.py`) is deterministic: the same
narration text and `words_per_minute` always produce the same duration
and the same placeholder artifact content — no randomness, no network
calls, no real audio synthesis of any kind. Its output is permanently
labeled `TEST / PLACEHOLDER AUDIO — not real speech, not
production-quality` in both `voice/voice-<n>.md` and the persisted
artifact file (`voice/voice-<n>.audio.txt`, plain text — not a real audio
container). `Generation status = GENERATED` and `QA status = PASS` mean
this agent's own structural checks passed (see "QA" below); neither is
ever a claim of production-quality speech.

## Real provider (Phase 8)

`agents/voice/src/real_provider.py`'s `FliteVoiceProvider` is the first
production-capable `VoiceProvider` — a second implementation of
`provider.py`'s existing interface; nothing in `pipeline.py`/`mutate.py`
needed to change beyond two additive `GeneratedAudio` fields
(`artifact_bytes`, `artifact_extension`) that let a real provider persist
genuine binary audio (`voice/voice-<n>.wav`) alongside the original
text-artifact path (`voice/voice-<n>.audio.txt`), which the test provider
still uses unchanged.

It synthesizes real, intelligible (if robotic-sounding) speech via
**ffmpeg's own built-in `flite` filter** — fully offline, no network call,
no API key, deterministic. This was a deliberate choice, not a default:
this environment has no configured TTS API credentials of any kind
(checked, never assumed), and `CONTRACT.md`'s Forbidden actions already
rule out committing this codebase to a specific paid/keyed vendor. flite
ships inside ffmpeg's own build (`--enable-libflite`) — the same ffmpeg
dependency `agents/assembler/`'s real renderer already requires — so no
additional system dependency is introduced. Fails closed with
`VoiceProviderConfigurationError` if ffmpeg isn't installed, or
`VoiceProviderFailure` if synthesis produces no usable audio — never
silently substitutes a placeholder.

A real cloud/paid TTS vendor remains a distinct, deliberate future
`VoiceProvider` implementation — swapping one in requires no change to
`pipeline.py`, `mutate.py`, or the schema, by design.

## How it works

- **Approval gate** (`pipeline.py`): requires `CONTENT_ITEM.md status ==
  APPROVED` (checked independently, not merely inferred from
  `PRODUCTION.md` existing — see CONTRACT.md's Preconditions), and
  `PRODUCTION.md Production status` in `{PRODUCTION_PLANNING,
  VISUAL_PLANNING}` (the second is this agent's own successful terminal
  state, accepted so a re-run can still reach the already-up-to-date/
  staleness check — see CONTRACT.md). Anything else is a structured
  `blocked` result with no mutation.
- **Script/production consistency**: the current `SCRIPT.md`'s hash
  (reusing `agents/producer/src/hashing.py` directly) must match
  `PRODUCTION.md`'s stored `Script content hash`, or the run blocks —
  never generates voice from a production plan that's already stale
  relative to the script.
- **Narration** (`narration.py`): SOURCE NARRATION is every scene's
  `Narration text`, in order, concatenated verbatim (reuses
  `agents/visual_planner/src/loader.load_scenes` directly — generic
  scene-file reading, not visual-planning domain logic). PROVIDER-READY
  NARRATION applies exactly one deterministic transformation: curly
  quotes/apostrophes → straight ASCII, repeated whitespace collapsed.
  Nothing else — no word, number, hedge phrase, or What If? distinction
  is ever changed.
- **Hash/staleness** (`agents/producer/src/hashing.py`, reused): if
  `voice/voice-01.md` already exists, a matching `Script content hash`
  means it's already up to date (no-op); a mismatched hash means the
  script changed since generation — the existing voice result is `STALE`
  and is never silently reused or regenerated. A voice record whose
  `Script content hash` field is missing/blank is treated as malformed
  and fails safely rather than guessing.
- **QA** (`qa.py`): deterministic, structural checks only — narration is
  non-empty, the script hash matches, an audio reference is recorded, the
  duration is positive, provider metadata is complete, and the generation
  status is one of `templates/VOICE.md`'s recognized values. **This is
  not speech-quality evaluation** — no pronunciation, emotion, or
  audio-artifact detection exists or is claimed.
- **Write boundary** (`mutate.py`): a hard-coded path/field whitelist —
  `voice/voice-<n>.md` and `voice/voice-<n>.audio.txt` (only ever as
  fresh files, never overwritten), plus `PRODUCTION.md`'s `Voiceover
  information` section and (only once `QA status == PASS`) `Production
  status`. No generic "write anything" helper.
- **Dry-run / apply**: `run_voice_generation(root, apply=False)` (the
  default) computes and returns everything without touching disk;
  `apply=True` writes. Same shape as every other agent in this repo.

## Relationship to other agents

Reuses `agents/researcher/src`'s generic infrastructure (`parsing`,
`loader.load_content_item`), `agents/producer/src.hashing`, and
`agents/visual_planner/src.loader.load_scenes` directly — never
duplicates any of them, and never imports another agent's domain logic
(scene-splitting, visual classification). Runs after `agents/producer/`
(which produces the scenes this agent reads narration from) and before
`agents/visual_planner/` in `templates/PRODUCTION.md`'s `Production
status` sequence (`PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING → ...`)
— in practice this agent runs directly against `PRODUCTION_PLANNING` and
is itself the one that advances status to `VISUAL_PLANNING` once its own
`QA status` is `PASS`; see CONTRACT.md's Preconditions for why.

## Running it

```
python3 -m agents.voice.src <content-item-dir> [--apply] \
    [--voice-configuration CFG] [--wpm 150]
```

Prints a JSON result (`aborted`/`blocked`/`stale`/`already_up_to_date`/
`produced`, provider/QA/duration summary). Without `--apply`, nothing on
disk changes.

```
python3 -m unittest discover -s agents/voice/tests -t .
```

## Known limitations

- **No versioned supersession** — a stale voice result is reported and
  left untouched, but the MVP does not automatically create a `voice-02`
  successor; regenerating after a script change is a decision this MVP
  surfaces, not automates (same documented limitation as
  `agents/producer/`).
- **Placeholder audio remains the CLI's default and every test's
  default** — `LocalTestVoiceProvider` is what `python -m agents.voice.src`
  and the whole test suite still use unless a real provider is passed
  explicitly. Phase 8 added a real provider (`FliteVoiceProvider`, see
  above); it produces genuine, if robotic-sounding, offline speech —
  never a cloud-quality voice, and no cloud/paid TTS vendor is
  integrated.
- **No speech-quality QA.** `qa.py`'s checks are structural only (see
  "QA" above) — this is unchanged by having a real provider now: a human
  must still actually listen to the audio before it's production-ready.
- **One voice track per production** (`voice-01` only) — matches
  `templates/VOICE.md`'s "typically one per production" design; a
  multi-track production isn't modeled yet.
- **QA is structural only** — see "QA" above.
