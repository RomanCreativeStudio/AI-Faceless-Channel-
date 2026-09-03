"""CLI: python -m agents.assembler.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON assembly result. Without
--apply nothing on disk changes (dry run); with --apply it writes
timeline/timeline-01.md + output/video-01.manifest.txt and updates only
PRODUCTION.md's Assembly / Output section + Production status, per
CONTRACT.md. Uses the deterministic local test renderer only — no real
video encoding exists this phase.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_video_assembly


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assembler MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_video_assembly(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "timeline_id": result.timeline_id,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "stale": result.stale,
        "stale_reason": result.stale_reason,
        "already_up_to_date": result.already_up_to_date,
        "total_duration": result.total_duration,
        "assembly_content_hash": result.assembly_content_hash,
        "renderer_label": result.renderer_label,
        "output_reference": result.output_reference,
        "playable": result.playable,
        "assembly_status": result.assembly_status,
        "timeline_path": result.timeline_path,
        "output_path": result.output_path,
        "production_path": result.production_path,
        "reasons": result.reasons,
        "scene_count": len(result.scenes),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
