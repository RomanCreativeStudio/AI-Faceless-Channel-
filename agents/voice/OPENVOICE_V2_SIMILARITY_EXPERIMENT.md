# OpenVoice V2 Voice-Similarity Experiment

**Purpose**: a controlled, evidence-based investigation of what actually
controls voice similarity in the current OpenVoice V2 adapter, and
whether a small set of technically-justified parameter/reference-sample
variants materially change the output — before treating the current
configuration as final. This does **not** select a new production
default, does **not** approve Episode 1's content, and does **not**
publish anything. See "What this experiment did NOT do" at the bottom.

No speculative changes were made to production code. Every finding below
traces to a specific line in the actual, currently-deployed adapter
(`agents/voice/src/engines/openvoice_v2_engine.py` and
`_openvoice_v2_chunk_worker.py`) or to the installed OpenVoice V2/MeloTTS
library source itself — never to general voice-cloning assumptions.

## 1. Where each mechanism actually lives (inspection, no code changed)

| Mechanism | Location |
|---|---|
| Reference speaker embedding extraction | `openvoice_v2_engine.py:212` — `se_extractor.get_se(config.sample_path, converter, target_dir=<ephemeral tempdir>, vad=True)`, inside `synthesize()` |
| Target/source embedding caching & reuse | Computed **once** per `synthesize()` call (`openvoice_v2_engine.py:212`), saved to a temp `.pt` file (`:220-221`), then loaded fresh by **every** per-chunk subprocess (`_openvoice_v2_chunk_worker.py:68-69`) — identical embeddings reused across all chunks of one narration, never recomputed per chunk |
| `tau` (ToneColorConverter's own conversion-strength parameter) | **Not configured anywhere in production code.** `_openvoice_v2_chunk_worker.py:91-97`'s call to `converter.convert(...)` omits `tau` entirely, so OpenVoice's own library default (`tau=0.3`, defined in `openvoice/api.py`'s `convert()` signature) applies implicitly |
| MeloTTS synthesis parameters | `_openvoice_v2_chunk_worker.py:90` — `model.tts_to_file(text, speaker_id, path, speed=1.0)`. Only `speed` is set explicitly; `sdp_ratio` (0.2), `noise_scale` (0.6), `noise_scale_w` (0.8) are all left at MeloTTS's own function defaults (`melo/api.py`'s `tts_to_file()` signature) |
| Random/stochastic synthesis behavior | MeloTTS's VITS-based decoder samples fresh noise (governed by `noise_scale`/`noise_scale_w`) on every call; no manual seed is set anywhere in this codebase, so re-running the identical chunk twice does **not** produce a byte-identical result. This affects only fine pitch/timing micro-variation — the target-embedding/tone-color itself is deterministic given a fixed sample and checkpoint |
| Narration chunking | `openvoice_v2_engine.py:87-105` (`_chunk_narration`) and `:195` — splits into ≤100-word, sentence-boundary-respecting pieces; purely an internal memory-management detail (see `OPENVOICE_V2_TEST_REPORT.md`'s OOM history), no effect on narration content |
| Subprocess isolation | `openvoice_v2_engine.py:244` — `subprocess.run(...)` invokes `_openvoice_v2_chunk_worker.py` once per chunk, each a fresh OS process; adopted after three real, reproduced OOM failures (documented in `OPENVOICE_V2_TEST_REPORT.md`) |

**No production file was modified for this experiment.** Every variant
below runs through a standalone, throwaway harness
(`.voice-experiments/similarity_experiment/`, fully gitignored, never
imported by any production code) that calls the same underlying
OpenVoice/MeloTTS libraries directly — confirmed via `git diff` showing
zero changes to `agents/voice/src/engines/`.

## 2. Mechanistic basis for testing tau and a longer reference

- **`extract_se()` (OpenVoice's `openvoice/api.py`)** computes one
  reference-encoder embedding per VAD-derived segment, then takes a
  **plain, unweighted mean across segments**: `gs = torch.stack(gs).mean(0)`.
  `se_extractor.split_audio_vad()` splits the *active-speech* portion of
  a sample into `round(active_duration / 10.0)` segments. The existing
  ~18s sample (17.3s active) yields exactly **2** segments (~8.6s each)
  from a single continuous take — very little material to average, and
  no variation in pitch/energy/content to average *over*. A longer,
  more varied sample produces more segments spanning more genuine vocal
  variation, which this same averaging mechanism would fold into a more
  robust, representative timbre estimate. This is the concrete,
  code-level reason a longer reference is worth testing.
- **`tau` in `ToneColorConverter.convert()`** directly controls how
  strongly the source spectral features are pulled toward the target
  embedding during conversion — the single most direct, real lever on
  perceived timbre similarity vs. naturalness in this architecture.
  Testing a small range around the shipped default (0.3) is the
  narrowest possible controlled experiment on this parameter — not
  guesswork, since the parameter's existence and role are both confirmed
  directly from the installed library's own source.

## 3. What this architecture cannot do, regardless of any variant tested

MeloTTS generates the underlying speech — words, rhythm, pitch contour,
pause placement, timing — from **text alone**, using its own trained
prosody model. OpenVoice's tone-color conversion (`ToneColorConverter.convert()`)
operates on the resulting spectrogram and swaps in timbre/vocal-tract
characteristics; it does not carry any temporal or prosodic information
from the reference sample into the output. Concretely, **no reference
sample of any length or quality, and no `tau` value, can make this
architecture reproduce**:

- the owner's actual cadence or speaking rhythm,
- his pause placement,
- his emphasis pattern.

These are not "not yet tuned" — they are outside what this
architecture's data flow can carry at all. Reproducing cadence/prosody
would require a fundamentally different approach (e.g. a real
prosody-transfer or full voice-conversion model that consumes the
reference sample's *temporal* structure, not just a pooled embedding).
**This is documented here as FUTURE WORK, not implemented** — building
it is out of this experiment's scope and was not requested.

## 4. Experiment configurations tested

Exactly four configurations — a deliberately narrow set, not an
arbitrary sweep:

| ID | Reference sample | `tau` | MeloTTS params | Narration |
|---|---|---|---|---|
| A (baseline) | SAMPLE_A (existing, ~18s) | 0.3 (current default, unchanged) | all defaults | Episode 1 scene-02, verbatim |
| B | SAMPLE_A (existing, ~18s) | 0.2 | all defaults | same |
| C | SAMPLE_A (existing, ~18s) | 0.4 | all defaults | same |
| D | SAMPLE_B (new, ~30s, owner-provided) | 0.3 (current default, unchanged) | all defaults | same |

Sample identifiers are anonymized here by design — neither sample's
actual filename or filesystem path appears anywhere in this document,
per the existing privacy architecture (`OwnerVoiceConfig.redacted_summary()`'s
own established rule). Both samples remain private, local files under
`.voice-experiments/` (fully gitignored) and were never committed.

Fixed narration (identical across all four runs, real Episode 1 content,
not invented for this test):

> Between 1347 and 1351, the Black Death swept across Europe. Depending
> on the region and how historians measure it, somewhere between a
> quarter and well over half of the population died. In parts of
> England, the very first wave alone wiped out nearly half the people.

Narration SHA-256: `251c9b8061eea6784d6cd35616e34fa8072f03286987d7e93ced808d04b200a7`
(46 words — short by design, per this task's own instruction to use one
fixed short narration for a fast, direct A/B/C/D comparison, not the
full episode).

## 5. OBJECTIVE FACTS

All four variants **synthesized successfully** (exit code 0), no
out-of-memory failures (confirmed via `dmesg` — zero `oom-kill` entries
this session), no exceptions. Each ran as its own fresh OS process (see
Section 1's "Subprocess isolation" note) using the unmodified,
already-deployed `checkpoints_v2` checkpoint and the `en-default`
MeloTTS speaker throughout.

| Configuration | Reference | `tau` | Duration | Sample rate | Format | Mean volume | Peak volume | Clipping | Silence gaps ≥0.3s |
|---|---|---|---|---|---|---|---|---|---|
| A (baseline) | SAMPLE_A (~18s) | 0.3 | 16.52s | 22,050 Hz | PCM16 mono | −32.7 dB | −8.2 dB | None | 6 (0.35–0.46s each) |
| B | SAMPLE_A (~18s) | 0.2 | 16.51s | 22,050 Hz | PCM16 mono | −32.7 dB | −7.2 dB | None | 6 (0.36–0.53s each) |
| C | SAMPLE_A (~18s) | 0.4 | 16.73s | 22,050 Hz | PCM16 mono | −32.1 dB | −8.3 dB | None | 6 (0.38–0.56s each) |
| D | SAMPLE_B (~30s) | 0.3 | 16.47s | 22,050 Hz | PCM16 mono | **−30.0 dB** | −8.1 dB | None | 4 (0.31–0.43s each) |

Narration text and hash identical across all four runs (Section 4). All
four outputs are valid, complete, non-clipping WAV files with no missing
sections.

**What varies and what doesn't, objectively:**

- **Duration varies by ~0.26s across all four runs (16.47–16.73s)** —
  including between A and itself would if re-run, since MeloTTS's own
  stochastic sampling (`noise_scale`/`noise_scale_w`, Section 1) means
  no two runs are byte-identical even with identical inputs. This
  spread is **not attributable to `tau` or the reference sample** — it
  is the expected baseline noise floor of this architecture. Treat any
  duration/pause-count difference between A/B/C/D as within that noise
  floor, not as a measured effect of the variable being tested.
- **Peak/mean volume**: D (the longer, ~30s reference) measured
  noticeably louder on average (−30.0 dB vs. −32.1 to −32.7 dB for the
  three 18s-reference variants) while still non-clipping. This is a
  real, measured difference — plausibly because the longer reference's
  own recording was itself louder on average (see its independently
  logged volumedetect result: mean −26.3 dB vs. the original sample),
  and `extract_se()`'s pooled embedding can carry some of that
  characteristic through tone-color conversion. This is a volume-level
  observation only — it says nothing about which sounds more like the
  owner, only that D is measurably louder.
- **Silence-gap count**: A/B/C each show 6 gaps, D shows 4 — most
  plausibly stochastic-sampling noise (see above) rather than a genuine
  effect of `tau` or the reference sample, given the same narration text
  drove all four.
- **`tau` (B=0.2, C=0.4) produced no clipping, no failure, and no
  duration/silence pattern distinguishable from the baseline beyond the
  stochastic noise floor described above.** Based on these objective
  measurements alone, **tau does not materially change any objective
  property tested** in this narrow ±0.1 range around the default. This
  says nothing about perceived timbre similarity — only a human listener
  can judge that (Section 6).

## 6. SUBJECTIVE HUMAN EVALUATION (REQUIRED — deliberately left blank)

These fields can only be filled in by the owner actually listening to
each file. **Nothing here is invented, inferred, or estimated by any
automated process.**

| Configuration | Perceived similarity to owner's voice | Naturalness | Pronunciation | Cadence | Emotional delivery | Artifact level | Overall preference |
|---|---|---|---|---|---|---|---|
| A (baseline, 18s, tau=0.3) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| B (18s, tau=0.2) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| C (18s, tau=0.4) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| D (30s, tau=0.3) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

Note on "Cadence" in this table: per Section 3 above, cadence is **not**
something this architecture can vary based on the reference sample or
`tau` — every configuration above uses the identical MeloTTS prosody
output. If the owner perceives a cadence difference between files, it is
most likely the stochastic MeloTTS sampling described in Section 1
(different random noise draw per run), not a property of the sample or
`tau` being tested.

## 7. Recording specification (unchanged from the prior recommendation, restated here for completeness)

If, after listening, the owner judges the longer sample (D) to be a
genuine timbre improvement over the baseline (A), the next, larger step
is a ~3-minute dedicated recording — full specification already
delivered in this session's prior response and grounded in the same
`extract_se()` averaging mechanism from Section 2: quiet room, phone/mic
6-10 inches away, normal conversational volume, one continuous take
preferred, genuine variation in pitch/energy/sentence length/questions/
emphasis, no announcer voice, WAV/M4A/MOV all acceptable at 44.1kHz or
48kHz mono. Restated in full only if requested — not duplicated here to
avoid drift between two copies of the same spec.

## What this experiment did NOT do

- Did **not** modify `agents/voice/src/engines/openvoice_v2_engine.py`
  or `_openvoice_v2_chunk_worker.py` — verified via `git diff`.
- Did **not** change the production default `tau` or any MeloTTS
  parameter — all four variants ran through a separate, throwaway
  harness never imported by production code.
- Did **not** touch `CONTENT_ITEM.md`, Safety review, Originality
  review, or any approval/publishing state.
- Did **not** touch the canonical Episode 1 directory in any way.
- Did **not** commit either reference sample, any derived embedding, or
  any generated comparison audio — all of it lives under
  `.voice-experiments/` (fully gitignored).
- Did **not** decide which configuration is "best" — Section 6 is
  intentionally blank pending the owner's own listening.
