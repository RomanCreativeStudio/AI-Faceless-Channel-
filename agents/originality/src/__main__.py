"""CLI: python -m agents.originality.src <content-item-dir> [--apply] [--reference FILE ...]

Prints a deterministic, machine-readable JSON originality-review result.
Without --apply nothing on disk changes (dry run); with --apply it writes
reviews/originality_reviewer-<n>.md and updates only CONTENT_ITEM.md's
Originality state + Notes/history log, per CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_originality_review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Originality Reviewer MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    parser.add_argument(
        "--reference", action="append", type=Path, default=None,
        help="path to supplied comparison/reference material (repeatable)",
    )
    args = parser.parse_args(argv)

    result = run_originality_review(args.content_item_dir, apply=args.apply, reference_paths=args.reference)

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
        "signals": [
            {
                "signal": e.signal.value,
                "risk_level": e.risk_level.value,
                "reason": e.reason,
                "evidence": e.evidence,
            }
            for e in result.signal_evaluations
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
