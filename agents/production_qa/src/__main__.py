"""CLI: python -m agents.production_qa.src <content-item-dir> [--apply]

Prints a deterministic, machine-readable JSON production-QA result.
Without --apply nothing on disk changes; with --apply it writes
qa/production-qa-01.md and, only on PASS, advances PRODUCTION.md's
Production status to HUMAN_REVIEW, per CONTRACT.md. Never publishes,
never grants final approval.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import run_production_qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production QA MVP")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="write results to disk")
    args = parser.parse_args(argv)

    result = run_production_qa(args.content_item_dir, apply=args.apply)

    payload = {
        "content_id": result.content_id,
        "production_id": result.production_id,
        "qa_id": result.qa_id,
        "verdict": result.verdict,
        "produced": result.produced,
        "aborted": result.aborted,
        "abort_reason": result.abort_reason,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "qa_path": result.qa_path,
        "production_path": result.production_path,
        "reasons": result.reasons,
        "checks": [
            {"area": c.area, "check": c.check, "passed": c.passed, "note": c.note}
            for c in result.checks
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
