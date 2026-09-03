"""CLI: python -m agents.voice.src <content-item-dir> [--apply]
    [--voice-configuration CFG] [--wpm N]

Prints a deterministic, machine-readable JSON voice-generation result.
Without --apply nothing on disk changes (dry run); with --apply it writes
voice/voice-01.md + voice/voice-01.audio.txt and updates only
PRODUCTION.md's Voiceover information section + (conditionally)
Production status, per CONTRACT.md. Uses the deterministic local test
provider only — see agents/voice/README.md's "Test provider."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_voice_generation
from .test_provider import DEFAULT_TEST_WORDS_PER_MINUTE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Voice MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    parser.add_argument("--voice-configuration", default="default-test-voice")
    parser.add_argument(
        "--wpm", type=int, default=DEFAULT_TEST_WORDS_PER_MINUTE,
        help=f"narration words per minute for the test provider's duration estimate (default {DEFAULT_TEST_WORDS_PER_MINUTE})",
    )
    args = parser.parse_args(argv)

    result = run_voice_generation(
        args.content_item_dir, apply=args.apply,
        voice_configuration=args.voice_configuration, words_per_minute=args.wpm,
    )

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "voice_id": result.voice_id,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "stale": result.stale,
        "stale_reason": result.stale_reason,
        "already_up_to_date": result.already_up_to_date,
        "provider_label": result.provider_label,
        "is_placeholder": result.is_placeholder,
        "script_content_hash": result.script_content_hash,
        "duration_seconds": result.duration_seconds,
        "generation_status": result.generation_status,
        "qa_status": result.qa_status,
        "qa_reasons": result.qa_reasons,
        "voice_path": result.voice_path,
        "audio_path": result.audio_path,
        "production_path": result.production_path,
        "reasons": result.reasons,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
