"""CLI: python -m agents.full_pipeline.src <content-item-dir> [--apply]

Runs CONTENT_REVIEW -> CONTENT_APPROVAL_GATE -> PRODUCER -> VOICE ->
VISUAL_PLANNER -> ASSETS -> ASSEMBLER -> CAPTIONS -> THUMBNAIL ->
PRODUCTION_QA in order via the existing agents, stopping at the first
stage that doesn't cleanly succeed. Prints a deterministic,
machine-readable JSON result. Dry run by default; --apply lets each
invoked stage write through its own existing, whitelisted path (this
orchestrator itself writes nothing — see CONTRACT.md's "Protected
fields"). No --publish flag exists, and none will ever be added.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_full_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Full Pipeline Orchestrator (Phase 7E)")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="let invoked stages write to disk")
    args = parser.parse_args(argv)

    result = run_full_pipeline(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "pipeline_status": result.pipeline_status,
        "current_stage": result.current_stage,
        "completed_stages": result.completed_stages,
        "skipped_stages": result.skipped_stages,
        "blocked_stages": result.blocked_stages,
        "failed_stages": result.failed_stages,
        "escalated_stages": result.escalated_stages,
        "revision_requests": result.revision_requests,
        "attempt_counts": result.attempt_counts,
        "stale_artifacts": result.stale_artifacts,
        "human_action_required": result.human_action_required,
        "human_action_reason": result.human_action_reason,
        "terminal_reason": result.terminal_reason,
        "apply": result.apply,
        "timestamp": result.timestamp,
        "stages": {
            stage: {
                "executed": o.executed,
                "skipped": o.skipped,
                "outcome": o.outcome,
                "reasons": o.reasons,
                "produced": o.produced,
                "stale": o.stale,
                "attempt": o.attempt,
            }
            for stage, o in result.stage_results.items()
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
