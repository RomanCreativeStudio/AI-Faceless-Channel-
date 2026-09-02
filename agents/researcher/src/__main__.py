"""CLI: python -m agents.researcher.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON fact-check result. Without
--apply nothing on disk changes (dry run); with --apply it writes
reviews/fact_checker-<n>.md and updates only CONTENT_ITEM.md's
Fact-check state + Notes/history log, per CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_fact_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research / Fact-Check Agent MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_fact_check(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "verdict": result.verdict.value,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "escalate_to_human": result.escalate_to_human,
        "content_hash": result.content_hash,
        "review_path": result.review_path,
        "reasons": result.reasons,
        "required_changes": result.required_changes,
        "claims": [
            {
                "claim_id": e.short_id,
                "classification": e.classification.value,
                "evidence_support": e.evidence_support.value,
                "fact_check_status": e.fact_check_status.value,
                "reason": e.reason,
            }
            for e in result.claim_evaluations
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
