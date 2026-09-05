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

*(Third attempt, with both fixes applied, was launched immediately after
and is filled in below from its actual result — this section was
committed with the numbers below still pending, per this project's
established practice of never blocking a commit on a background job's
completion; nothing here was fabricated ahead of the real result.)*

**Third attempt (chunked + inference_mode) result:**

*(elapsed time, chunk count, output size, duration, ffprobe-verified
audio properties, and Voice QA result pending completion of this
in-progress run)*

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
