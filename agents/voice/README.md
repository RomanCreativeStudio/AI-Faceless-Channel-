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

## Owner voice (Phase 8 follow-up)

**Goal:** `Owner records/teaches voice → voice system generates
narration in the owner's voice → AI handles repetitive narration
production → human reviews final audio.` This is a third
`VoiceProvider` implementation (`agents/voice/src/owner_voice.py`'s
`OwnerVoiceProvider`) — nothing in `pipeline.py`, `mutate.py`, or
`templates/VOICE.md` changed for it to exist.

**Authorization.** This provider exists only for the channel's human
owner's own voice. Every `GeneratedAudio` it returns carries an explicit
`OWNER_AUTHORIZED_VOICE` marker in its provider label (recorded into
`voice/voice-<n>.md`'s `Provider` field automatically, via the existing
schema — no template change needed). It is not, and must never become, a
generic arbitrary-person voice-cloning system.

**No vendor is selected or hard-coded.** Real synthesis is delegated to
a small `OwnerVoiceEngine` protocol, looked up by name
(`OWNER_VOICE_ENGINE`) in a registry that starts **empty**. This
environment was checked directly (no TTS/voice-cloning package
installed, no relevant API key or credential env var present, no
`piper`/`espeak`/`festival` binary on `PATH`) — nothing was assumed.
Until a specific engine is chosen and its adapter registered (a
separate, later piece of work, per this task's own "Provider selection"
priorities: owner-authorized cloning first, then quality, privacy,
predictable cost, accessibility, and cross-episode consistency),
`OwnerVoiceProvider` can never report itself available.

**Configuration** — environment variables, all optional except where a
real engine requires them:

| Variable | Meaning |
|---|---|
| `OWNER_VOICE_ID` | The owner-authorized voice identifier (required) |
| `OWNER_VOICE_SAMPLE_PATH` | Path to the owner's private voice sample — **never committed** (required) |
| `OWNER_VOICE_ENGINE` | Which registered `OwnerVoiceEngine` to use — no default (required) |
| `OWNER_VOICE_MODEL` | Model identifier, if the engine has one (optional) |
| `OWNER_VOICE_LANGUAGE` | Defaults to `en` |
| `OWNER_VOICE_STYLE` | Speaking style, as the engine defines it (optional) |
| `OWNER_VOICE_STABILITY` / `OWNER_VOICE_CONSISTENCY` | 0–1 controls, only if the engine supports them (optional) |
| `OWNER_VOICE_PRONUNCIATION` | `word=phonetic;word2=phonetic2` overrides (optional) |

All of this is read once into an `OwnerVoiceConfig` (`from_env()`).
Nothing vendor-specific appears in `pipeline.py`, `templates/VOICE.md`,
or anywhere outside `agents/voice/src/owner_voice.py`.

**Privacy.** `OWNER_VOICE_SAMPLE_PATH` points at a private, local file —
this repository never reads its contents into any committed artifact,
never persists it, and never echoes the path itself back in any log,
error, or `voice/voice-<n>.md` record (`OwnerVoiceConfig.redacted_summary()`
and `voice_configuration_string()` both omit it by construction — see
their docstrings). `.gitignore` protects `/owner_voice_samples/`,
`/.private/`, and `*.owner-voice-sample.*` in case a sample is ever
placed inside this repository's working tree; nothing in this codebase
creates a fake sample or a placeholder pretending to be the owner's
voice.

**Failure behavior.** `check_owner_voice_availability(config)` reports
`OWNER_VOICE_AVAILABLE` or `OWNER_VOICE_NOT_CONFIGURED` with a specific,
non-secret reason (missing voice ID, missing/nonexistent/empty sample,
no engine configured, an unregistered engine name, missing credential
*environment variable names* — never values, or the engine's own
"not available" reason). `OwnerVoiceProvider.generate()` raises
`OwnerVoiceNotConfiguredError` whenever that check fails — it never
falls back to `LocalFallbackVoiceProvider` or `LocalTestVoiceProvider`
and never returns placeholder/generic audio under the owner-voice label.
Check current status any time, without generating anything:

```
python3 -m agents.voice.src.owner_voice_cli
```

**Fallback behavior.** `LocalFallbackVoiceProvider` (Phase 8's
`FliteVoiceProvider`, now exported under this second, role-accurate
name too — never deleted, never rewritten) remains available for tests,
development, and any run that *explicitly* selects it via
`agents/voice/src/provider_selection.py`'s `resolve_voice_provider(...)`.
It never activates automatically in place of a failed owner-voice
request.

**Provenance.** Reuses `templates/VOICE.md`'s existing fields — no
schema change. `Provider` carries the engine name, `OWNER_AUTHORIZED_VOICE`,
and the voice ID; `Voice configuration` (`OwnerVoiceConfig.voice_configuration_string()`)
carries engine/voice/model/language/style/stability/consistency as
identifiers only; `Script content hash`, `Generated audio` (reference +
duration), `Generation status`, and the generation timestamp are exactly
the same fields every other provider populates. The raw sample is never
stored in any of them — only identifiers.

**Narration integrity.** `OwnerVoiceProvider` receives exactly the same
PROVIDER-READY NARRATION every other provider does
(`narration.py` — quote/whitespace normalization only) and cannot
rewrite, summarize, or otherwise alter it; `agents/voice/src/qa.py`'s
existing structural checks (narration non-empty, script hash matches,
audio reference/duration recorded, provider metadata complete) apply
unchanged.

**Human approval boundary.** Voice generation — by any provider,
including this one — never touches `CONTENT_ITEM.md`, never sets
`status`, never advances Safety/Originality/approval state, and never
publishes anything. Generating audio in the owner's voice is not itself
an approval of anything; a human still reviews the final audio (and the
full content-review chain still applies) before any of that happens.

**Current status in this environment: not configured, by design.** No
engine is registered, so `OWNER_VOICE_AVAILABLE` cannot be true here yet.
Once a real engine is chosen and its adapter added (registered via
`register_owner_voice_engine`), and the owner's actual sample/config is
supplied via the environment, real generation becomes a separate,
explicit validation step — never assumed or fabricated ahead of that.

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
- **`OwnerVoiceProvider` has no engine registered yet** — the adapter
  boundary, configuration, capability detection, and tests all exist
  (see "Owner voice" above), but no specific voice-cloning vendor/local
  model has been selected or configured in this environment. Real
  owner-voice narration is a separate, later validation step once one
  is.
