"""Internal helper, invoked as a SEPARATE OS SUBPROCESS by
`OpenVoiceV2Engine.synthesize()` for each narration chunk — never
imported or invoked directly by `pipeline.py`, `owner_voice.py`,
`provider_selection.py`, or any other part of this codebase.

Why a subprocess: real, repeated testing against Episode 1's full
narration hit the same ~13.9GB memory ceiling and was OOM-killed on
THREE separate attempts (confirmed each time via `dmesg`'s `oom-kill`
log) — first with no chunking, then with chunking alone, then with
chunking plus `torch.inference_mode()`. Each fix let more chunks
complete before the same ceiling was hit, but never eliminated the
accumulation. That pattern (memory growing per call, regardless of
autograd state, and never released by explicit `del`/`gc.collect()`)
points to memory retained inside PyTorch's/MeloTTS's/OpenVoice's own
native/allocator internals across repeated in-process calls — not
something this adapter's code can reliably force free from within the
same process. Running each chunk as an independent OS process makes
this unconditional: whatever the exact cause, the OS reclaims 100% of a
process's memory the moment it exits, every time.

Receives only: a checkpoint directory, a device, MeloTTS language/
speaker identifiers, a path to a plain-text file holding one chunk's
narration text, and a path to an already-computed target speaker
embedding (`target_se`, saved by the parent process — never the raw
owner sample; this worker never touches the owner's sample path or
contents at all, only a derived embedding tensor). Writes one output
WAV file and exits. Never receives, logs, or could reveal the owner's
private sample path — only the parent process (`openvoice_v2_engine.py`)
ever touches that.
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Internal OpenVoice V2 single-chunk synthesis worker (see module docstring)"
    )
    parser.add_argument("--checkpoint-dir", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--melo-language", required=True)
    parser.add_argument("--speaker-key", required=True)
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--target-se-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args(argv)

    try:
        import torch
        from melo.api import TTS
        from openvoice.api import ToneColorConverter
    except ImportError as exc:
        print(f"ERROR: required package not importable: {exc}", file=sys.stderr)
        return 1

    with open(args.text_file, "r", encoding="utf-8") as fh:
        chunk_text = fh.read()
    if not chunk_text.strip():
        print("ERROR: empty chunk text file", file=sys.stderr)
        return 1

    converter = ToneColorConverter(f"{args.checkpoint_dir}/converter/config.json", device=args.device)
    converter.load_ckpt(f"{args.checkpoint_dir}/converter/checkpoint.pth")

    speaker_embedding_path = f"{args.checkpoint_dir}/base_speakers/ses/{args.speaker_key}.pth"
    source_se = torch.load(speaker_embedding_path, map_location=args.device)
    target_se = torch.load(args.target_se_path, map_location=args.device)

    model = TTS(language=args.melo_language, device=args.device)
    speaker_ids = model.hps.data.spk2id
    melo_speaker_key = next(
        (k for k in speaker_ids.keys() if k.lower().replace("_", "-") == args.speaker_key), None,
    )
    if melo_speaker_key is None:
        print(
            f"ERROR: MeloTTS has no speaker matching {args.speaker_key!r} for "
            f"language {args.melo_language!r}",
            file=sys.stderr,
        )
        return 1

    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        base_audio_path = os.path.join(tmp, "base.wav")
        with torch.inference_mode():
            model.tts_to_file(chunk_text, speaker_ids[melo_speaker_key], base_audio_path, speed=1.0)
            converter.convert(
                audio_src_path=base_audio_path,
                src_se=source_se,
                tgt_se=target_se,
                output_path=args.output_path,
                message="@MyShell",
            )

    if not os.path.isfile(args.output_path):
        print("ERROR: conversion reported success but produced no output file", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
