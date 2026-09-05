# OpenVoice V2 Owner-Voice Test Report

**TEST ONLY — OPENVOICE V2 OWNER VOICE.** This is a local, free,
technical feasibility test of one specific engine adapter, not an
approved production asset, not a claim of production-quality speech,
and not a decision about which real voice-cloning provider (if any) the
channel will use. Nothing in this document approves Episode 1, clears
Safety, clears Originality, or changes any content-approval state — see
"What this test did NOT do" at the bottom.

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

## Human evaluation (REQUIRED — not fabricated here)

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
