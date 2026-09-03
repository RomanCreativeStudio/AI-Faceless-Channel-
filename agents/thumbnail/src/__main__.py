"""CLI: python -m agents.thumbnail.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON thumbnail result. Without
--apply nothing on disk changes; with --apply it writes
thumbnail/thumbnail-01.md and updates only PRODUCTION.md's Thumbnail +
Title/description sections + Production status, per CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_thumbnail_generation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thumbnail MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_thumbnail_generation(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "thumbnail_id": result.thumbnail_id,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "stale": result.stale,
        "stale_reason": result.stale_reason,
        "already_up_to_date": result.already_up_to_date,
        "thumbnail_content_hash": result.thumbnail_content_hash,
        "thumbnail_status": result.thumbnail_status,
        "title_concept": result.spec.title_concept if result.spec else "",
        "thumbnail_path": result.thumbnail_path,
        "production_path": result.production_path,
        "reasons": result.reasons,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
