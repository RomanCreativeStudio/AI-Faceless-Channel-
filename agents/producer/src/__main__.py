"""CLI: python -m agents.producer.src <content-item-dir> [--apply] [--wpm N]

Prints a deterministic, machine-readable JSON production result. Without
--apply nothing on disk changes (dry run); with --apply it writes
PRODUCTION.md + scenes/scene-<n>.md, per CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .duration import DEFAULT_WORDS_PER_MINUTE
from .pipeline import run_producer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Producer MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    parser.add_argument(
        "--wpm", type=int, default=DEFAULT_WORDS_PER_MINUTE,
        help=f"narration words per minute for duration estimates (default {DEFAULT_WORDS_PER_MINUTE})",
    )
    args = parser.parse_args(argv)

    result = run_producer(args.content_item_dir, apply=args.apply, words_per_minute=args.wpm)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "stale": result.stale,
        "stale_reason": result.stale_reason,
        "already_up_to_date": result.already_up_to_date,
        "script_content_hash": result.script_content_hash,
        "production_path": result.production_path,
        "scene_paths": result.scene_paths,
        "reasons": result.reasons,
        "scenes": [
            {
                "scene_id": s.scene_id,
                "order": s.order,
                "duration_seconds": s.duration_seconds,
                "claim_ids": s.claim_ids,
                "classifications_present": s.classifications_present,
            }
            for s in result.scenes
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
