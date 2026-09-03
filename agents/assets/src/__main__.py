"""CLI: python -m agents.assets.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON asset-generation result.
Without --apply nothing on disk changes (dry run); with --apply it
writes assets/asset-<n>.md (+ assets/asset-<n>.generated.txt for
GENERATED-strategy assets) and updates only PRODUCTION.md's Asset
references (rollup) section + (conditionally) Production status, per
CONTRACT.md. Uses the deterministic local test providers only — no
real image/video generation or retrieval integration exists this phase.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_asset_generation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assets MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_asset_generation(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "stale_filenames": result.stale_filenames,
        "already_up_to_date_filenames": result.already_up_to_date_filenames,
        "qa_passed": result.qa_passed,
        "qa_reasons": result.qa_reasons,
        "production_path": result.production_path,
        "asset_paths": result.asset_paths,
        "artifact_paths": result.artifact_paths,
        "reasons": result.reasons,
        "plans": [
            {
                "filename": p.filename,
                "scene_filename": p.scene.filename,
                "strategy": p.strategy.value,
                "authenticity": p.authenticity.value,
                "verification_status": p.verification_status,
                "generation_status": p.generation_status,
                "artifact_filename": p.artifact_filename,
            }
            for p in result.plans
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
