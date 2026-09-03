"""CLI: python -m agents.captions.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON captions result. Without
--apply nothing on disk changes; with --apply it writes
captions/captions-01.md and updates only PRODUCTION.md's Captions
section + Production status, per CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_caption_generation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captions MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_caption_generation(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "captions_id": result.captions_id,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "stale": result.stale,
        "stale_reason": result.stale_reason,
        "already_up_to_date": result.already_up_to_date,
        "captions_content_hash": result.captions_content_hash,
        "generation_status": result.generation_status,
        "captions_path": result.captions_path,
        "production_path": result.production_path,
        "reasons": result.reasons,
        "scene_count": len(result.scenes),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
