"""CLI: python -m agents.orchestrator.src <content-item-dir> [--apply]

Runs FACT_CHECK -> SAFETY_REVIEW -> ORIGINALITY_REVIEW in order via the
existing agents, stopping at the first stage that doesn't PASS. Prints a
deterministic, machine-readable JSON result. Dry run by default;
--apply lets each invoked stage write through its own existing,
whitelisted path (the orchestrator itself writes nothing).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_automated_review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified Automated Review Orchestrator")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="let invoked stages write to disk")
    args = parser.parse_args(argv)

    result = run_automated_review(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "overall_result": result.overall_result.value,
        "pipeline_status": result.pipeline_status,
        "stages_executed": result.stages_executed,
        "stages_skipped": result.stages_skipped,
        "first_blocking_stage": result.first_blocking_stage,
        "blocking_reason": result.blocking_reason,
        "human_escalation": result.human_escalation,
        "apply": result.apply,
        "timestamp": result.timestamp,
        "stages": {
            stage: {
                "executed": o.executed,
                "reused_existing_pass": o.reused_existing_pass,
                "system_error": o.system_error,
                "system_error_message": o.system_error_message,
                "verdict": o.verdict.value if o.verdict is not None else None,
                "escalate_to_human": o.escalate_to_human,
                "blocked": o.blocked,
                "blocked_reason": o.blocked_reason,
                "review_path": o.review_path,
                "reasons": o.reasons,
                "required_changes": o.required_changes,
            }
            for stage, o in result.stage_results.items()
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
