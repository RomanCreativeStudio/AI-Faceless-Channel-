# Owner Voice Reference — Active Configuration

**This file is committed and contains no private audio content** —
only stable, repo-relative pointers, checksums, and decision provenance.
The actual voice samples live under `owner_voice_samples/` (fully
gitignored — see `.gitignore`), never in Git, never uploaded anywhere.
This file exists so a future session/operator can determine, without
guessing, which reference is currently authorized for production and
why — per the owner's own explicit instruction to make this
"deterministic and auditable."

## Active production reference

```
ACTIVE_REFERENCE_ID   = D (30-second sample)
ACTIVE_REFERENCE_PATH = owner_voice_samples/production_reference.wav   (gitignored, local-only)
ENGINE                = openvoice-v2
TAU                   = 0.3   (OpenVoice's own shipped default — unchanged, not tuned)
DURATION              = 30.07s
SAMPLE_RATE           = 44,100 Hz
CHANNELS              = 1 (mono)
SHA-256                = 961d4cc31b3d60ee14d2791a3da0348e89d939bc8c46cc92347283d32b2a77b1
SELECTED_ON            = 2026-09-07
SELECTED_BY            = owner, via direct listening (agents/voice/OPENVOICE_V2_SIMILARITY_EXPERIMENT.md)
```

**To use this reference**, an operator sets, in the isolated OpenVoice
V2 environment (`agents/voice/src/engines/README.md`):

```bash
export OWNER_VOICE_SAMPLE_PATH=/absolute/path/to/AI-Faceless-Channel-/owner_voice_samples/production_reference.wav
```

The SHA-256 above lets anyone confirm, without opening or listening to
the file, that a given `owner_voice_samples/production_reference.wav`
on disk is genuinely the same file this decision was made about
(`sha256sum owner_voice_samples/production_reference.wav`).

## Decision record

From the owner's direct listening evaluation
(`agents/voice/OPENVOICE_V2_SIMILARITY_EXPERIMENT.md` Section 6):

- **D** (this reference, tau=0.3): "sounds like the owner and is
  noticeably more audible/clear." Selected as the production reference.
- **C** (baseline 18s sample, tau=0.4): "also represents the owner
  well, but is slightly quieter." **Not** selected — and per the
  owner's explicit instruction, `tau` is **not** being changed to 0.4
  on the strength of this observation: the controlled experiment
  (Section 5 of that report) did not establish an objective similarity
  improvement from `tau=0.4` over the shipped default, and repeated
  tau-tuning was explicitly declined unless a new controlled experiment
  is requested.
- **A/B** (baseline 18s sample, tau=0.3/0.2): superseded by D as the
  active reference; **not deleted** — see "Previous reference" below.

`tau` remains `0.3` in production — this is already what
`_openvoice_v2_chunk_worker.py` uses by omission (it never passed a
`tau` override), so **no code change was needed or made** to hold tau
at its current value.

## Previous reference (preserved, not deleted)

```
PREVIOUS_REFERENCE_ID   = baseline (18-second sample, used through the
                           original OpenVoice V2 activation and the
                           first full-episode narration/pipeline test)
PREVIOUS_REFERENCE_PATH = owner_voice_samples/baseline_18s_experimental.wav   (gitignored, local-only)
DURATION                = 17.60s
SAMPLE_RATE             = 44,100 Hz
CHANNELS                = 1 (mono)
SHA-256                  = 12dbc658555519f8f4dbcb1a8cdcd9d403f13ef082531913ee969d0aaf30aa61
STATUS                  = superseded, kept for reference/comparison only — do not use for new
                           production narration unless the owner explicitly reinstates it
```

## Auditability

- Neither file's content, nor any content derived from it (VAD
  segments, cached embeddings), has ever been committed — confirmed via
  `git status`/`git log` showing no changes under `owner_voice_samples/`
  (which is fully gitignored) and no `.pt`/`.pth` artifacts tracked.
- This manifest is the single source of truth for "which reference is
  active" — if `OWNER_VOICE_SAMPLE_PATH` is ever set to something other
  than `ACTIVE_REFERENCE_PATH` above without a corresponding update to
  this file, that is a deviation from the recorded decision and should
  be treated as such.
- Changing the active reference again requires the same process this
  one followed: a controlled comparison
  (`OPENVOICE_V2_SIMILARITY_EXPERIMENT.md`-style), the owner's own
  listening evaluation, and an update to this file — never an automated
  or inferred switch.
