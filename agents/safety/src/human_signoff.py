"""Human Safety signoff: an explicit, auditable record of a human
owner's decision on a `SAFETY_REVIEW` human-escalation signal — never
inferred from editing a file, changing a status, rerunning a command, or
any other side effect. See `templates/HUMAN_SAFETY_SIGNOFF.md` for the
full schema and what this record does and does not do.

This module owns only the record itself (model, loader, writer) —
`agents/orchestrator/src/human_safety_continuation.py` owns deciding
what a signoff is allowed to unblock. Kept in `agents/safety/` because a
signoff is fundamentally about Safety's own escalation, mirroring how
`agents/researcher/src/revision.py` (a researcher concern) lives beside
`agents/researcher/src/loader.py` rather than in the orchestrator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from ...researcher.src import parsing

_SIGNOFF_FILENAME_RE = re.compile(r"^signoff-(?P<attempt>\d+)$")


class HumanSafetyDecision(str, Enum):
    CLEARED = "CLEARED"
    NOT_CLEARED = "NOT_CLEARED"


class MalformedSignoff(Exception):
    """A signoff-<n>.md file exists but is missing a required field or
    has an unrecognized value — never silently treated as CLEARED or
    skipped; the caller must fail closed."""


@dataclass
class HumanSafetySignoff:
    path: Path
    attempt: int
    content_id: str
    reviewer: str
    decision: HumanSafetyDecision
    decided_at: str
    reviewed_content_hash: str
    triggering_review_attempt: str
    signals_covered: list[str]
    historical_context_reviewed: bool
    review_scope: str
    notes: str
    raw_text: str


def load_human_safety_signoffs(signoffs_dir: Path) -> list[HumanSafetySignoff]:
    """All recorded signoffs for one content item, sorted by attempt
    ascending — same shape as agents/researcher/src/loader.load_reviews.
    Raises MalformedSignoff on a file that looks like a signoff but is
    missing/invalid a required field, rather than silently ignoring it:
    a broken signoff must never be mistaken for "no signoff yet" (which
    reads as WAITING_FOR_HUMAN_SAFETY_REVIEW) or silently skipped (which
    could let a wrong-numbered later file appear to be the latest).
    """
    signoffs: list[HumanSafetySignoff] = []
    if not signoffs_dir.is_dir():
        return signoffs
    for path in sorted(signoffs_dir.glob("signoff-*.md")):
        m = _SIGNOFF_FILENAME_RE.match(path.stem)
        if not m:
            continue
        text = path.read_text(encoding="utf-8")
        table = parsing.parse_table(text)
        sections = parsing.parse_sections(text)

        decision_raw = parsing.first_backtick_token(table.get("Decision", ""))
        try:
            decision = HumanSafetyDecision(decision_raw)
        except ValueError as exc:
            raise MalformedSignoff(
                f"{path}: Decision must be CLEARED or NOT_CLEARED, got {decision_raw!r}"
            ) from exc

        reviewed_hash = parsing.strip_single_backticks(table.get("Reviewed content hash", ""))
        if not reviewed_hash or reviewed_hash.upper() == "N/A":
            raise MalformedSignoff(f"{path}: Reviewed content hash is required and cannot be N/A")

        reviewer = parsing.strip_single_backticks(table.get("Reviewer", "")).strip()
        if not reviewer:
            raise MalformedSignoff(f"{path}: Reviewer is required")

        signals_raw = table.get("Signals covered", "")
        signals_covered = parsing.backtick_tokens(signals_raw) or [
            t.strip() for t in signals_raw.split(",") if t.strip()
        ]
        if not signals_covered:
            raise MalformedSignoff(f"{path}: Signals covered must name at least one signal")

        context_raw = parsing.first_backtick_token(
            table.get("Historical/sensitive context reviewed", "")
        )
        if context_raw not in ("YES", "NO"):
            raise MalformedSignoff(
                f"{path}: Historical/sensitive context reviewed must be YES or NO, got {context_raw!r}"
            )

        signoffs.append(
            HumanSafetySignoff(
                path=path,
                attempt=int(m.group("attempt")),
                content_id=parsing.strip_single_backticks(table.get("Content ID", "")),
                reviewer=reviewer,
                decision=decision,
                decided_at=parsing.strip_single_backticks(table.get("Decided at", "")),
                reviewed_content_hash=reviewed_hash,
                triggering_review_attempt=parsing.strip_single_backticks(
                    table.get("Triggering review attempt", "")
                ),
                signals_covered=signals_covered,
                historical_context_reviewed=(context_raw == "YES"),
                review_scope=sections.get("Review scope", "").strip(),
                notes=sections.get("Notes / reasoning (optional)", "").strip(),
                raw_text=text,
            )
        )
    signoffs.sort(key=lambda s: s.attempt)
    return signoffs


def next_signoff_attempt_number(signoffs: list[HumanSafetySignoff]) -> int:
    return (signoffs[-1].attempt + 1) if signoffs else 1


def render_signoff_markdown(
    *,
    content_id: str,
    attempt: int,
    reviewer: str,
    decision: HumanSafetyDecision,
    reviewed_content_hash: str,
    triggering_review_attempt: str,
    signals_covered: list[str],
    historical_context_reviewed: bool,
    review_scope: str,
    notes: str = "",
    decided_at: str | None = None,
) -> str:
    """Renders one signoff-<n>.md per templates/HUMAN_SAFETY_SIGNOFF.md.
    Pure formatting — never called automatically by any agent; only a
    human-invoked path (see record_human_safety_decision below) writes
    the result to disk, and only after the human has supplied every
    required field explicitly.
    """
    decided_at = decided_at or datetime.now(timezone.utc).isoformat()
    signals_str = ", ".join(f"`{s}`" for s in signals_covered)
    context_str = "YES" if historical_context_reviewed else "NO"
    notes_body = notes.strip() or "(none)"
    return f"""# Human Safety Signoff {attempt} — {content_id}

Generated by a human owner via `agents/safety/src/human_signoff.py`'s
`record_human_safety_decision()`. See `templates/HUMAN_SAFETY_SIGNOFF.md`
for what this record does and does not do — it never overrides an
automated `HIGH_RISK`/`REJECT`-tier Safety finding and never sets
`CONTENT_ITEM.md`'s `status` to `APPROVED`.

| Field | Value |
|---|---|
| Signoff ID | `{content_id}-human-safety-signoff-{attempt}` |
| Content ID | `{content_id}` |
| Reviewer | {reviewer} |
| Decision | `{decision.value}` |
| Decided at | {decided_at} |
| Reviewed content hash | `{reviewed_content_hash}` |
| Triggering review attempt | `{triggering_review_attempt}` |
| Signals covered | {signals_str} |
| Historical/sensitive context reviewed | `{context_str}` |

## Review scope

{review_scope.strip()}

## Notes / reasoning (optional)

{notes_body}

## What this record does NOT do

A `CLEARED` decision here resolves only the signal(s) named above, only
for the exact content hash above. A `NOT_CLEARED` decision leaves the
content item blocked (`EDITORIAL_REVISION_REQUIRED`) — nothing may retry
automatically or proceed to `ORIGINALITY_REVIEW`.
"""


def record_human_safety_decision(
    root: Path,
    *,
    reviewer: str,
    decision: HumanSafetyDecision,
    reviewed_content_hash: str,
    triggering_review_attempt: str,
    signals_covered: list[str],
    historical_context_reviewed: bool,
    review_scope: str,
    notes: str = "",
) -> Path:
    """The one function that writes a new human_safety_signoffs/signoff-<n>.md.

    Every argument is required and explicit — there is no default
    Decision, no inference from CONTENT_ITEM.md's current state, and no
    way to call this without the caller (a human, or a thin CLI wrapper
    acting only on a human-supplied --decision flag) having actually
    typed `CLEARED` or `NOT_CLEARED`. Never invoked by any review/
    revision/orchestrator agent automatically.
    """
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    if not signals_covered:
        raise ValueError("signals_covered must name at least one SafetySignal")
    if not review_scope.strip():
        raise ValueError("review_scope is required — state what was actually reviewed")
    if decision is HumanSafetyDecision.NOT_CLEARED and not notes.strip():
        raise ValueError("notes are required when recording NOT_CLEARED — state what needs revision")

    root.mkdir(parents=True, exist_ok=True)
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        raise FileNotFoundError(f"no CONTENT_ITEM.md under {root}")
    content_id = parsing.strip_single_backticks(
        parsing.parse_table(content_item_path.read_text(encoding="utf-8")).get("Content ID", "")
    )

    signoffs_dir = root / "human_safety_signoffs"
    signoffs_dir.mkdir(exist_ok=True)
    existing = load_human_safety_signoffs(signoffs_dir)
    attempt = next_signoff_attempt_number(existing)

    text = render_signoff_markdown(
        content_id=content_id,
        attempt=attempt,
        reviewer=reviewer,
        decision=decision,
        reviewed_content_hash=reviewed_content_hash,
        triggering_review_attempt=triggering_review_attempt,
        signals_covered=signals_covered,
        historical_context_reviewed=historical_context_reviewed,
        review_scope=review_scope,
        notes=notes,
    )
    path = signoffs_dir / f"signoff-{attempt}.md"
    path.write_text(text, encoding="utf-8")
    return path
