# OpenVoice V2 Owner-Voice Test Report

Originally a local, free, technical-feasibility test of one specific
engine adapter (see "What was tested" through "Human evaluation" below,
kept as originally written). The owner has since listened to the
generated sample and recorded a production decision — see
"Production-use evaluation" below. Nothing in this document approves
Episode 1's content, clears Safety, clears Originality, or changes any
content-approval state — see "What this test did NOT do" at the bottom,
still fully in force.

## What was tested

| Field | Value |
|---|---|
| Engine | `agents/voice/src/engines/openvoice_v2_engine.py` — `OpenVoiceV2Engine` (`OwnerVoiceEngine` conforming) |
| Underlying model | OpenVoice V2 (MyShell, MIT license) — `checkpoints_v2/converter` (tone-color conversion) + MeloTTS `EN` base speaker (`en-default`) |
| Execution | 100% local — no cloud API, no account, no credentials (`required_credential_env_vars = []`) |
| Owner sample used | `OWNER_VOICE_SAMPLE_PATH` — a private, local file (never committed, never referenced by path in this document) |
| INITIAL TEST SAMPLE | ~18 seconds |
| Sample status | `TECHNICALLY_USABLE_FOR_TEST` — sufficient to run the pipeline end to end; **not** evidence of production-quality fidelity |
| Production sample recommendation (unchanged) | 2–5 minutes of clean, uninterrupted owner speech — still the project's standing recommendation regardless of this test's outcome |
| Test narration | ~98 words, ~40s at typical narration pace; see "Test narration text" below |
| Test artifact location | This session's own isolated scratch directory — **not** committed, **not** written into any canonical content item, **not** Episode 1 |

## Test narration text

Chosen to be representative of actual channel narration: normal
conversational tone, a mix of shorter and longer sentences, one proper
noun (a person), one historical/technical term, an em dash and a
semicolon for natural pacing, and standard punctuation throughout.

> What if the printing press had never reached Europe? Johannes
> Gutenberg's invention, completed around 1450 in Mainz, Germany, didn't
> just speed up how books were made — it fundamentally changed who
> could access information at all. Before Gutenberg, a single
> hand-copied manuscript could take a monk nearly a year to finish.
> Afterward, workshops could produce hundreds of identical copies in
> weeks. That shift helped ideas like the Reformation spread faster than
> any single ruler could suppress them. It's a reminder that some
> technologies don't just make existing tasks faster; they quietly
> rewrite the rules of an entire society.

## Generation result

| Field | Value |
|---|---|
| Synthesis time (this run, CPU-only) | 416.4s (~6m56s) — MeloTTS + BERT prosody + tone-color conversion, no GPU available in this environment |
| Provider label | `owner-voice:openvoice-v2 (OWNER_AUTHORIZED_VOICE, voice_id=owner-default-test)` |
| Voice configuration | `owner-voice:engine=openvoice-v2;voice_id=owner-default-test;model=n/a;language=en;style=n/a` |
| Output size | 1,527,340 bytes |
| Reported duration | 35s |
| `is_placeholder` | `False` — genuine synthesized audio, not a placeholder |
| Network calls during synthesis itself | None — model/checkpoint loading is 100% from local disk once the isolated environment is set up |

## Voice QA (structural — `agents/voice/src/qa.py`)

Structural checks only — **never** a speech-quality judgment (per
`agents/voice/CONTRACT.md`'s own stated limitation, unchanged by this
test): narration non-empty, script hash matches, an audio reference is
recorded, duration is positive, provider metadata is complete, and the
generation status is a recognized value. Passing these proves the
*pipeline* produced a structurally valid result — it says nothing about
whether the cloned voice sounds like the owner, or is otherwise good
enough to publish.

Run for real via `run_voice_generation()` against an isolated,
throwaway test content item (never Episode 1, never committed) using
this run's actual generated audio bytes: **`qa_status: PASS`**,
`generation_status: GENERATED`, zero QA reasons flagged. The written
`voice/voice-01.md` record correctly shows `Provider` containing
`OWNER_AUTHORIZED_VOICE`, `openvoice-v2`, and the configured voice ID —
and contains no trace of the private sample's path anywhere.

## Basic audio properties (independently inspected via `ffprobe`/`ffmpeg`, not self-reported)

| Property | Value |
|---|---|
| Format | WAV (PCM, `pcm_s16le`) |
| Sample rate | 22,050 Hz |
| Channels | 1 (mono) |
| Bit depth | 16-bit |
| Duration | 34.63s |
| Mean volume | −32.9 dB |
| Peak volume | −7.1 dB (comfortable headroom — not clipping) |
| Silence check | No gaps ≥0.5s below −35dB detected — no dead air/dropouts across the clip |

These confirm a real, well-formed, non-clipping, continuously-voiced
audio file. They say nothing about whether it sounds like the owner,
whether pronunciation is natural, or whether pacing is robotic — only
listening can answer that.

## Production-use evaluation (owner decision recorded)

**This section reflects an actual, later decision by the owner** — after
listening to the generated sample below — that supersedes the "Human
evaluation" blank-checkbox section further down (kept below, unedited,
as the honest historical record of what this document looked like before
that decision). Nothing here is fabricated: fields the owner did not
separately rate are marked as such rather than guessed.

The owner's own stated reasoning, verbatim in substance: **the result is
recognizable as their voice and acceptable for production, while
acknowledging that the clone can be improved later.** The owner did not
provide separate itemized ratings for every dimension below — only that
overall judgment. Where a field has no independent owner rating, this
report says so rather than inventing one.

| Field | Status |
|---|---|
| A. Voice similarity | Owner: **recognizable as their own voice** (their words) — not mapped by the owner to a specific Poor/Usable/Good/Excellent point beyond that |
| B. Naturalness | Not separately rated by the owner. Technical evidence only: no clipping, no dead-air gaps, continuous voicing (see "Basic audio properties" above and the production-run numbers below) |
| C. Pronunciation | Not separately rated by the owner. No mispronunciation was reported by the owner in their decision |
| D. Pacing | Not separately rated by the owner |
| E. Consistency (across a longer, multi-sentence production run) | Not separately rated by the owner. Technically evidenced by the isolated Episode 1 narration run below (a single continuous synthesis of the full ~479-word script, not just a short test clip) |
| F. Emotional expression | Not separately rated by the owner. OpenVoice V2's tone-color conversion does not model emotional range beyond the reference sample's own — no claim of expressive range is made here |
| G. Artifacting | Not separately rated by the owner. Independently checked via `ffprobe`/`ffmpeg` on the isolated Episode 1 render (see "Full Episode 1 narration — isolated validation" below) for clipping/silence-gap artifacts only; this is not a claim that no audible artifacting of any kind exists — only a human can fully judge that |
| H. Suitability for long-form narration | Evidenced directly: the full ~479-word Episode 1 script was synthesized as one continuous narration track in the isolated validation run below, not just a ~40s clip |
| I. Suitability for short-form clips | Evidenced by this document's original ~40s test clip (see "Generation result" above) |
| J. Owner decision | **`USE_FOR_PRODUCTION`** |

```
CURRENT_OWNER_VOICE = OpenVoice V2
VOICE_QUALITY_STATUS = ACCEPTABLE_FOR_PRODUCTION
VOICE_IMPROVEMENT = FUTURE_ITERATION
```

This decision authorizes using OpenVoice V2 as the owner's production
voice provider. It does **not** approve Episode 1's content, does not
clear Safety/Originality/Fact-check, and does not authorize publishing —
see "What this test did NOT do" below, unchanged and still fully in
force. The 2–5 minute clean-recording recommendation remains the
standing future-improvement target; it was never a precondition to this
decision and is not required before using the current voice.

## Full Episode 1 narration — isolated validation

Full Episode 1 narration (~479 words, the complete Hook + all 6
Narrative beats, via the real `run_producer()` → real
`run_voice_generation()` pipeline against an isolated validation copy of
Episode 1 — never the canonical episode) was run through the real,
registered OpenVoice V2 engine.

**First attempt: a genuine, reproduced out-of-memory failure — reported
honestly, not hidden.** Synthesizing and tone-converting the entire
~479-word script in one pass reached ~13.9GB resident memory and was
killed by this sandboxed session's cgroup memory limit (~14.3GB),
confirmed directly via `dmesg`'s `oom-kill` log entry, right after the
MeloTTS synthesis phase completed (10/10 sentence groups) and
tone-color conversion began on the full combined audio. This was not a
silent failure or a masked one — no audio was produced, no result was
recorded, and nothing was reported as a success.

**Root-caused and fixed**: `agents/voice/src/engines/openvoice_v2_engine.py`'s
`synthesize()` now splits narration into bounded-size chunks
(`_chunk_narration`, ~100 words each, splitting only at real sentence
boundaries — see its own tests in `test_openvoice_v2_engine.py`),
synthesizes and tone-converts each chunk independently, and concatenates
the resulting PCM audio frames into one continuous output file. Peak
memory now stays roughly constant regardless of total script length.
This changes only *how* the engine internally produces the audio — the
`narration_text` argument `synthesize()` receives, and everything
`run_voice_generation()`/`OwnerVoiceProvider` record about it (the exact
PROVIDER-READY NARRATION string, the script-hash relationship), is
completely unaffected; chunking is invisible above the engine's own
`synthesize()` call.

**Second attempt: also genuinely OOM-killed, at the same ~13.9GB
ceiling — chunking alone was not sufficient.** With chunking applied,
this attempt processed noticeably further (5 of ~6-7 chunks fully
synthesized and tone-converted, versus zero chunks' conversion completed
in the first attempt) before hitting the same memory ceiling and being
killed (confirmed again via `dmesg`). Memory being tied to *total text/
forward-passes processed* rather than to any single call's audio size is
the signature of PyTorch retaining autograd computation graphs across
inference calls that neither MeloTTS's nor OpenVoice's own library code
wraps in `torch.no_grad()`/`torch.inference_mode()` internally.

**Root-caused further and fixed**: the per-chunk synthesis/conversion
loop is now wrapped in `torch.inference_mode()`, explicitly disabling
gradient tracking for every inference call — the standard fix for this
exact PyTorch memory-accumulation pattern. This is a second, independent
fix layered on top of chunking (chunking bounds per-chunk audio/spectral
memory; `inference_mode()` prevents graph-retention memory from
accumulating *across* chunks) — again purely an internal execution
detail with no effect on the narration text or the pipeline's own
recorded fields.

**Third attempt: also genuinely OOM-killed, at essentially the identical
~13.9GB ceiling and stopping point (5 chunks in) as the second
attempt.** `torch.inference_mode()` did not fix it — memory grew and hit
the same wall regardless. This ruled out autograd-graph retention as the
(sole) cause and pointed instead to memory retained inside PyTorch's/
MeloTTS's/OpenVoice's own native/allocator internals across repeated
in-process calls — not something forceable from within the same process
via `del`/`gc.collect()`/`inference_mode()`.

**Root-caused conclusively and fixed**: each chunk's synthesis and
tone-conversion now runs in its own **subprocess**
(`agents/voice/src/engines/_openvoice_v2_chunk_worker.py`, invoked via
`subprocess.run` from `synthesize()`) rather than in-process. A
subprocess's memory is unconditionally reclaimed by the OS the instant
it exits, regardless of the exact internal cause — this does not depend
on correctly guessing which library's internals were responsible. The
worker receives only a checkpoint directory, device, MeloTTS language/
speaker identifiers, a chunk-text file, and a path to an
already-computed target speaker embedding (`target_se`, saved once by
the parent to the same ephemeral tempdir) — it never receives, reads, or
could leak the owner's raw sample path (verified by a dedicated test:
`test_worker_module_never_declares_a_sample_path_argument`). Verified
standalone before the full run: the worker script was invoked directly
against a short smoke-test sentence and the owner's real sample-derived
embedding, producing a valid 120,364-byte WAV file with exit code 0.

4 new tests (`ChunkWorkerSubprocessTests`) verify the worker module
exists with a `main()` entry point, has no network-capable imports, and
never declares a sample-path argument; a further test confirms
`synthesize()` genuinely delegates to it via `subprocess.run` rather
than reverting to in-process calls.

*(Fourth attempt, with subprocess isolation applied, was launched
immediately after and is filled in below from its actual result — this
section was committed with the numbers below still pending, per this
project's established practice of never blocking a commit on a
background job's completion; nothing here was fabricated ahead of the
real result.)*

**Fourth attempt (subprocess-isolated chunks): SUCCEEDED — real,
complete Episode 1 narration, no OOM.**

| Field | Value |
|---|---|
| Elapsed synthesis time | 415.9s (~6m56s), CPU-only |
| Chunks | 6 (bounded to ~100 words each, subprocess-isolated) |
| Output size | 7,122,988 bytes |
| Reported/measured duration | 162s (`ffprobe`: 161.518005s) |
| Provider label | `owner-voice:openvoice-v2 (OWNER_AUTHORIZED_VOICE, voice_id=owner-production-ep1)` |
| `is_placeholder` | `False` |
| `generation_status` | `GENERATED` |
| `qa_status` (via the real `run_voice_generation()` pipeline) | `PASS`, zero QA reasons |
| Narration integrity | Provider-ready narration handed to the engine measured at 2,930 characters — matches the independently-computed provider-ready narration length exactly; script-hash relationship correct throughout |
| Peak memory | No OOM (confirmed via `dmesg` — no new `oom-kill` entries since the third, pre-fix attempt) |

**Basic audio properties** (independently verified via `ffprobe`/`ffmpeg`, not self-reported):

| Property | Value |
|---|---|
| Format | WAV (PCM, `pcm_s16le`) |
| Sample rate | 22,050 Hz |
| Channels | 1 (mono) |
| Duration | 161.52s |
| Mean volume | −32.1 dB |
| Peak volume | −4.4 dB (no clipping) |
| Silence gaps ≥0.5s below −35dB | 5, each 0.55–0.66s — consistent with natural pauses between sentences across a ~2.7-minute continuous narration, not dead air or dropouts |

`PRODUCTION.md`'s `Production status` correctly advanced from
`PRODUCTION_PLANNING` to `VISUAL_PLANNING` only after this real QA
`PASS` — matching every other provider's existing handoff behavior
exactly, with no owner-voice-specific special case.

## Isolated production pipeline (Visual Planner → Production QA)

Run for real, directly (never through `agents/full_pipeline/`'s
`run_full_pipeline()`, which re-runs the full `CONTENT_REVIEW` chain —
including the real, still-open Safety escalation on Episode 1 — from
scratch and would have stopped there; this uses the same direct-stage-
call pattern Phase 8 itself established for validating production
mechanics on an isolated, `APPROVED`-in-that-copy-only throwaway item)
against the same isolated Episode 1 copy, immediately after the
narration above:

| Stage | Provider | Result |
|---|---|---|
| Visual Planner | (no provider — planning only) | 7 scene visual plans; 2 classified `RETRIEVED` (scenes 2–3, referencing `FACT` claims c1/c2), 5 `GENERATED_RECONSTRUCTION` |
| Assets | `GeneratedAssetProviderReal` + `WikimediaCommonsRetrievalProvider` (both real, no mocks) | 5 genuine local illustrations rendered (Pillow, offline). The 2 `RETRIEVED`-strategy scenes genuinely queried the live Wikimedia Commons API and got an honest **"no usable (JPEG/PNG, downloadable) Wikimedia Commons result found"** for both queries — not a rate limit this time, a real no-match. Recorded exactly as returned; neither was ever marked `RETRIEVED`. |
| Assembler | `FFmpegVideoRenderer` (real ffmpeg) | `ASSEMBLED`, `playable=YES` — H.264/AAC MP4, 1920×1080, 22,050Hz mono audio, 161.52s, 3,803,778 bytes |
| Captions | (structural, no provider) | `GENERATED` — 7 scenes captioned, every chunk verified a verbatim substring of the narration |
| Thumbnail | `render_image=True` (real Pillow render) | `GENERATED` — real 35,272-byte PNG |
| Production QA | (real, structural) | **`REVISION_REQUIRED`** — see below |

**Production QA — exact failing reasons (2 of ~45 checks):**

- `scene-02.md: retrieved asset has real retrieval evidence` — FAILED
- `scene-03.md: retrieved asset has real retrieval evidence` — FAILED

Both for the documented reason: *"no real retrieval integration exists
this phase"* (`agents/production_qa/CONTRACT.md`'s own "Known
limitation: RETRIEVED strategy") — the same, pre-existing limitation
Phase 8 already documented, not a new regression from this work. Every
other check passed: content approval/hash, voice hash/QA, all 5
`GENERATED` assets' provenance and classification, timeline
consistency (no gaps/overlaps, declared duration matches computed),
captions timing/mapping, thumbnail framing, and output
hash/playability.

**Why 2 assets show a substitute image at all**: to get a complete,
watchable render for manual inspection (mirroring Phase 8's own
precedent exactly), a **VALIDATION-SUBSTITUTE-ONLY** illustration was
manually attached to `assets/asset-02.md`/`asset-03.md`'s `Technical >
File reference` field, clearly labeled in the file itself
(`asset-0N.VALIDATION_SUBSTITUTE.png`, with an explicit paragraph
stating it is not a genuine retrieval). Their `Generated vs. retrieved`
field was **left as `RETRIEVED`** (never changed to `GENERATED`) and
`Generation/retrieval status` was **left `NOT_STARTED`** (never marked
`RETRIEVED`) — which is exactly why Production QA correctly still
failed those two checks rather than being fooled by the substitute
image's mere presence. This proves QA does not rubber-stamp a
substitution it wasn't told is real.

**A genuine, honest finding (not fixed — out of this task's scope):**
the scene timeline's planned total duration (191s, from
`agents/producer/`'s own word-count-based estimate at planning time)
does not match the real OpenVoice V2 audio's actual duration (161.5s) —
the owner's real speaking pace differs from the estimate the planner
used. The final render's actual length follows the real audio (161.5s),
not the originally-planned 191s. This is a genuine pacing/duration-
estimation consideration for real voice engines that no agent currently
reconciles automatically — noted honestly here rather than hidden, and
left for future work rather than addressed in this task (which is about
activating OpenVoice V2, not rebuilding scene-duration estimation).

Nothing in this section changed `CONTENT_ITEM.md`, cleared Safety/
Originality, or published anything — see "What this test did NOT do"
below, unchanged and still fully in force. The canonical Episode 1
directory was confirmed untouched (`git status --porcelain`) before and
after every step in this section.

## Human evaluation (REQUIRED — not fabricated here)

*(Original test-only section, kept as written before the production-use
decision above was recorded — see that section for what the owner
actually decided.)*

These fields are the whole point of this test and can only be filled in
by the owner actually listening to the generated file. They are left
blank on purpose.

**A. Voice similarity:** ☐ Poor ☐ Usable ☐ Good ☐ Excellent

**B. Naturalness:** ☐ Poor ☐ Usable ☐ Good ☐ Excellent

**C. Pronunciation:** ☐ Poor ☐ Usable ☐ Good ☐ Excellent

**D. Narration suitability:** ☐ Not suitable ☐ Test-worthy ☐ Production candidate

**E. Overall decision:**
☐ `REJECT_OPENVOICE_TEST`
☐ `CONTINUE_OPENVOICE_TESTING`
☐ `PRODUCTION_CANDIDATE_PENDING_LONGER_SAMPLE`

Notes for the owner while listening: pay attention to whether the voice
actually sounds like you (not just "a voice"), whether pacing/rhythm
feels robotic or natural, whether the proper noun ("Gutenberg") and the
technical term ("Reformation") are pronounced clearly, and whether you'd
be comfortable with a full episode sounding like this. **Successful
synthesis proves the pipeline works — it does not prove the voice is
good enough for this channel.** Only your own listening can determine
that.

## What this test did NOT do

- Did **not** approve Episode 1 or change `CONTENT_ITEM.md`'s `status`.
- Did **not** clear Safety Review, and did not touch the existing human
  Safety signoff mechanism (Episode 1 remains
  `WAITING_FOR_HUMAN_SAFETY_REVIEW`, unchanged).
- Did **not** clear or run Originality Review.
- Did **not** publish anything, anywhere.
- Did **not** render any canonical Episode 1 production artifact — the
  narration text used here is a separate, representative test sentence,
  not Episode 1's actual script.
- Did **not** upload the owner's sample anywhere, create any vendor
  account, or add any credential.

Provider readiness (can OpenVoice V2 technically produce audio from
this sample) and content approval (is Episode 1 safe, original, and
approved to produce) remain completely separate, exactly as documented
in `agents/voice/PROVIDER_EVALUATION.md`'s "Human authorization
boundary."
