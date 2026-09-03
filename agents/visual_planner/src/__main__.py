"""CLI: python -m agents.visual_planner.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON visual-planning result.
Without --apply nothing on disk changes (dry run); with --apply it
updates each scene's Visual type/description/Asset requirement, writes
assets/asset-<n>.md, and updates PRODUCTION.md's rollups + status, per
CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_visual_planner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visual Planner MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_visual_planner(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "planned": result.planned,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "production_path": result.production_path,
        "scene_paths": result.scene_paths,
        "asset_paths": result.asset_paths,
        "reasons": result.reasons,
        "plans": [
            {
                "scene_filename": p.scene.filename,
                "visual_type": p.visual_type,
                "authenticity": p.authenticity.value,
                "generated_or_retrieved": p.generated_or_retrieved,
                "needs_asset": p.needs_asset,
                "asset_filename": p.asset_filename,
            }
            for p in result.plans
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
