# Owner-voice engine adapters

Real `OwnerVoiceEngine` implementations live here — one file per engine,
each registered only when explicitly imported (see each module's own
docstring). Nothing in `agents/voice/src/__init__.py`, `pipeline.py`, or
`provider_selection.py` imports anything from this directory
automatically; the provider registry (`agents/voice/src/owner_voice.py`)
stays genuinely empty until an operator opts in.

## `openvoice_v2_engine.py` — OpenVoice V2 (local, free, MIT-licensed)

The first real engine implemented, per
`agents/voice/PROVIDER_EVALUATION.md` Section 3.5 — chosen specifically
because it is local (no cloud upload of the owner's sample), free, and
commercially licensed. This is a **local-only experiment to test
technical feasibility**, not a claim that OpenVoice V2's output is
production-quality — see `agents/voice/OPENVOICE_V2_TEST_REPORT.md` for
the actual, honest evaluation once a test has been run.

### Why an isolated environment

OpenVoice V2 needs `torch`, `torchaudio`, the `openvoice` package,
MeloTTS, and a ~530MB `unidic` dictionary — none of which belong in this
repository's own `requirements.txt` (which stays limited to what
`agents/assets/`/`agents/assembler/` actually need for real production:
Pillow, ffmpeg). Installing OpenVoice's stack keeps the rest of this
project's test suite (stdlib + Pillow only) fast, and never at risk of
a heavy ML dependency conflict. The exact commands below build a
throwaway virtualenv under `.voice-experiments/` (gitignored in full —
see `.gitignore`) that is never required for anything else in this
repository to work.

### Setup (reproduced from the actual working install)

```bash
cd /path/to/AI-Faceless-Channel-
mkdir -p .voice-experiments && cd .voice-experiments
python3 -m venv openvoice-env
source openvoice-env/bin/activate

# torch/torchaudio: install together, pinned, from the CPU-only index.
# A newer, unpinned "pip install torch" pulled a torchaudio that could
# not load its C extension in this environment (looked for a CUDA
# runtime library that a CPU-only machine will never have) — pinning
# both to a known-compatible pair, installed together so pip resolves
# ABI-matching wheels, avoided it.
pip install --force-reinstall "torch==2.3.1" "torchaudio==2.3.1" \
    --index-url https://download.pytorch.org/whl/cpu

git clone --depth 1 https://github.com/myshell-ai/OpenVoice.git openvoice-repo
cd openvoice-repo
pip install -e .

# OpenVoice's own requirements.txt pins faster-whisper==0.9.0, whose
# own pinned "av==10.*" dependency has no prebuilt wheel for Python
# 3.11 and fails to compile from source in this environment (missing
# libavformat/libavcodec *development* headers — the runtime .so files
# are present, but not the -dev/pkg-config files a from-source build
# needs). Installing an unpinned, current faster-whisper instead pulls
# in a newer "av" release that DOES ship a prebuilt wheel, with no
# compilation and no behavior difference relevant to this use case.
pip install "faster-whisper"
pip install librosa pydub wavmark eng_to_ipa inflect unidecode \
    whisper-timestamped pypinyin cn2an jieba langid soundfile

# MeloTTS (V2's base-speaker TTS engine).
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download   # ~530MB dictionary, one-time

# Checkpoints: the officially-documented S3 bucket
# (myshell-public-repo-host) returned NoSuchBucket — retired since the
# docs were written. Used the maintained Hugging Face mirror instead
# (same files, same license):
mkdir -p checkpoints_v2/converter checkpoints_v2/base_speakers/ses
BASE="https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main"
curl -sSL -o checkpoints_v2/converter/config.json "$BASE/converter/config.json"
curl -sSL -o checkpoints_v2/converter/checkpoint.pth "$BASE/converter/checkpoint.pth"
for spk in en-au en-br en-default en-india en-newest en-us es fr jp kr zh; do
  curl -sSL -o "checkpoints_v2/base_speakers/ses/${spk}.pth" "$BASE/base_speakers/ses/${spk}.pth"
done
```

Note: `gradio` (in OpenVoice's own `requirements.txt`) was deliberately
**not** installed — it is only needed for OpenVoice's own web demo app
(`openvoice_app.py`), which this integration never uses; `se_extractor`
and `ToneColorConverter`, the only two things this adapter imports, do
not require it.

### Using it

```bash
source .voice-experiments/openvoice-env/bin/activate
export OWNER_VOICE_ENGINE=openvoice-v2
export OWNER_VOICE_ID=<an identifier of your choosing>
export OWNER_VOICE_SAMPLE_PATH=/private/path/to/owner_sample.wav   # never inside this repo
export OPENVOICE_V2_CHECKPOINT_DIR=/path/to/.voice-experiments/openvoice-repo/checkpoints_v2
export PYTHONPATH=/path/to/AI-Faceless-Channel-/.voice-experiments/openvoice-repo:$PYTHONPATH

python3 -c "
from agents.voice.src.engines import openvoice_v2_engine  # registers the engine
from agents.voice.src.owner_voice import OwnerVoiceConfig, OwnerVoiceProvider

config = OwnerVoiceConfig.from_env()
provider = OwnerVoiceProvider(config)
audio = provider.generate('Some narration text.', config.voice_configuration_string())
"
```

Outside that environment (`OWNER_VOICE_ENGINE=openvoice-v2` set, but the
venv not active and this module never imported), `check_owner_voice_
availability()` reports `OWNER_VOICE_NOT_CONFIGURED` with the precise
missing piece — never a silent fallback to a different voice.
