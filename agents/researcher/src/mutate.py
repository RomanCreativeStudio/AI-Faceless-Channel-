"""Narrow, whitelisted field-level writers — the only way this codebase
touches an existing CONTENT_ITEM.md or CLAIM.md file. Each function edits
exactly one table row and leaves every other byte untouched, and the
allowed field names are hard-whitelisted per
agents/researcher/CONTRACT.md's "Allowed actions" / "Outputs" sections so
writing an unlisted field is a programming error, not a runtime choice.

Claims are otherwise immutable (templates/CLAIM.md): there is no function
here to change `Classification` or `Exact claim` on an existing claim.
`supersede_claim` is the only way to "correct" a claim — it creates a new
file and appends a note to the old one; it never edits the old claim's
table.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

from .models import Claim, Classification

CONTENT_ITEM_WRITABLE_FIELDS = {"Research state", "Fact-check state"}
CLAIM_WRITABLE_FIELDS = {
    "Fact-check status",
    "Evidence",
    "Contradictory evidence",
    "Confidence level",
}

_REVISION_FILENAME_RE = re.compile(r"^revision-\d+\.md$")


def write_revision_file(root: Path, filename: str, text: str) -> Path:
    """Autonomous Revision Mode's one new write path (see
    agents/researcher/CONTRACT.md's "Autonomous Revision Mode" — "Revision
    authority"). Only `revisions/revision-<n>.md` is permitted — fails
    closed on anything else, matching every other whitelisted writer in
    this module and every sibling agent's own mutate.py.
    """
    if not _REVISION_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/researcher may not write revision file {filename!r} — "
            "only revision-<n>.md is permitted"
        )
    revisions_dir = root / "revisions"
    revisions_dir.mkdir(exist_ok=True)
    path = revisions_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


def _replace_table_field(text: str, field_name: str, new_value: str) -> str:
    pattern = re.compile(
        r"^(\|\s*" + re.escape(field_name) + r"\s*\|\s*).*?(\s*\|\s*)$", re.MULTILINE
    )
    if not pattern.search(text):
        raise ValueError(f"field {field_name!r} not found as a table row")
    return pattern.sub(lambda m: f"{m.group(1)}{new_value}{m.group(2)}", text, count=1)


def update_content_item_field(path: Path, field_name: str, new_value: str) -> None:
    if field_name not in CONTENT_ITEM_WRITABLE_FIELDS:
        raise PermissionError(
            f"agents/researcher may not write CONTENT_ITEM.md field {field_name!r} "
            f"— only {sorted(CONTENT_ITEM_WRITABLE_FIELDS)} are permitted"
        )
    text = path.read_text(encoding="utf-8")
    path.write_text(_replace_table_field(text, field_name, new_value), encoding="utf-8")


def update_claim_field(path: Path, field_name: str, new_value: str) -> None:
    if field_name not in CLAIM_WRITABLE_FIELDS:
        raise PermissionError(
            f"agents/researcher may not write CLAIM.md field {field_name!r} "
            f"— only {sorted(CLAIM_WRITABLE_FIELDS)} are permitted"
        )
    text = path.read_text(encoding="utf-8")
    path.write_text(_replace_table_field(text, field_name, new_value), encoding="utf-8")


def append_notes_log(path: Path, entry: str, today: date | None = None) -> None:
    """Append one line under CONTENT_ITEM.md's '## Notes / history log'
    heading. Never edits or removes any existing line — append-only."""
    today = today or datetime.now(timezone.utc).date()
    text = path.read_text(encoding="utf-8")
    heading = "## Notes / history log"
    idx = text.rfind(heading)
    if idx == -1:
        raise ValueError("CONTENT_ITEM.md has no '## Notes / history log' section")
    new_line = f"- {today.isoformat()} — {entry}\n"
    updated = text + ("" if text.endswith("\n") else "\n") + new_line
    path.write_text(updated, encoding="utf-8")


def supersede_claim(
    old_claim: Claim,
    new_short_id: str,
    new_exact_claim: str,
    new_classification: Classification,
    reason: str,
    template_render,
) -> str:
    """Create a new claim file superseding `old_claim`. The old claim's
    table is never touched — a trailing note pointing at the new claim ID
    is appended to its prose instead (mirrors the convention already used
    by claims/c3.md's "Revision note" in the golden sample).

    `template_render(new_short_id, new_exact_claim, new_classification,
    old_claim) -> str` builds the new file's full text — kept as a
    caller-supplied callback so this module doesn't need to know every
    field a new claim requires.
    """
    new_path = old_claim.path.parent / f"{new_short_id}.md"
    if new_path.exists():
        raise FileExistsError(f"{new_path} already exists")
    new_path.write_text(template_render(new_short_id, new_exact_claim, new_classification, old_claim), encoding="utf-8")

    old_text = old_claim.path.read_text(encoding="utf-8")
    note = (
        f"\n\n**Superseded ({datetime.now(timezone.utc).date().isoformat()}):** "
        f"replaced by `{new_short_id}` — {reason}. This claim's table is left "
        "unchanged; only this trailing note was appended (claims are immutable "
        "per templates/CLAIM.md's Atomicity rule).\n"
    )
    old_claim.path.write_text(old_text.rstrip("\n") + note, encoding="utf-8")
    return str(new_path)
