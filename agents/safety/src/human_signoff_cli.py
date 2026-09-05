"""CLI: python -m agents.safety.src.human_signoff_cli <content-item-dir> \
    --reviewer "<name>" --decision CLEARED|NOT_CLEARED \
    --signals SENSITIVE_CONTENT [--signals OTHER_SIGNAL ...] \
    --scope "<what was actually reviewed>" \
    --historical-context-reviewed \
    [--notes "<reasoning>"]

The only intended way to record a human Safety decision. `--decision` is
a required, explicit flag — there is no default, and running this
command with no `--decision` fails argument parsing rather than assuming
anything. `--reviewed-content-hash` / `--triggering-review-attempt` are
computed automatically from the content item's current on-disk state
(the human is reviewing what's on disk right now, so hashing anything
else would misrepresent what was actually reviewed) — see
CONTRACT-equivalent notes in human_signoff.py.

Never invoked by any agent automatically. A human owner (or someone
acting on their explicit, one-time instruction) runs this by hand.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...researcher.src.loader import load_reviews
from .hashing import compute_reviewed_content_hash
from .human_signoff import HumanSafetyDecision, record_human_safety_decision
from .loader import load_safety_bundle
from .pipeline import ROLE_FILE_PREFIX


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a human Safety signoff decision")
    parser.add_argument("content_item_dir", type=Path)
    parser.add_argument("--reviewer", required=True, help="name/handle of the human owner deciding")
    parser.add_argument(
        "--decision", required=True, choices=[d.value for d in HumanSafetyDecision],
        help="explicit decision — no default",
    )
    parser.add_argument(
        "--signals", action="append", required=True, dest="signals",
        help="a SafetySignal name this decision addresses (repeatable)",
    )
    parser.add_argument("--scope", required=True, help="what was actually reviewed to reach this decision")
    parser.add_argument(
        "--historical-context-reviewed", action="store_true",
        help="confirms the flagged subject matter was read in context, not just the keyword",
    )
    parser.add_argument("--notes", default="", help="reasoning; required for NOT_CLEARED")
    args = parser.parse_args(argv)

    root = args.content_item_dir
    bundle = load_safety_bundle(root)
    reviewed_content_hash = compute_reviewed_content_hash(bundle)

    reviews = load_reviews(root / "reviews", ROLE_FILE_PREFIX)
    if not reviews:
        print(
            "error: no reviews/safety_reviewer-<n>.md found — run Safety before "
            "recording a human signoff",
            file=sys.stderr,
        )
        return 1
    triggering_review_attempt = str(reviews[-1].path)

    try:
        path = record_human_safety_decision(
            root,
            reviewer=args.reviewer,
            decision=HumanSafetyDecision(args.decision),
            reviewed_content_hash=reviewed_content_hash,
            triggering_review_attempt=triggering_review_attempt,
            signals_covered=args.signals,
            historical_context_reviewed=args.historical_context_reviewed,
            review_scope=args.scope,
            notes=args.notes,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"recorded: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
