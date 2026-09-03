"""Path/field-whitelisted writers for the Production QA agent: only
qa/production-qa-<n>.md, and PRODUCTION.md's Production QA state section
+ (only on PASS) Production status — no generic "write anything" helper.
Never touches PRODUCTION.md's Human review state (human-only, per that
section's own text — "never an agent") and never sets Production status
to APPROVED or READY_TO_PUBLISH.
"""
from __future__ import annotations

import re
from pathlib import Path

_QA_FILENAME_RE = re.compile(r"^production-qa-\d+\.md$")


def write_qa_file(root: Path, filename: str, text: str) -> Path:
    if not _QA_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/production_qa may not write qa file {filename!r} — "
            "only production-qa-<n>.md is permitted"
        )
    qa_dir = root / "qa"
    qa_dir.mkdir(exist_ok=True)
    path = qa_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


def _replace_table_field(text: str, field_name: str, new_value: str) -> str:
    pattern = re.compile(
        r"^(\|\s*" + re.escape(field_name) + r"\s*\|\s*).*?(\s*\|\s*)$", re.MULTILINE
    )
    if not pattern.search(text):
        raise ValueError(f"field {field_name!r} not found as a table row")
    return pattern.sub(lambda m: f"{m.group(1)}{new_value}{m.group(2)}", text, count=1)


def _replace_section_body(text: str, heading: str, new_body: str) -> str:
    marker = f"## {heading}"
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"PRODUCTION.md has no '{marker}' section")
    body_start = idx + len(marker)
    rest = text[body_start:]
    next_heading_idx = rest.find("\n## ")
    body_end = body_start + (next_heading_idx if next_heading_idx != -1 else len(rest))
    return text[:body_start] + "\n\n" + new_body.strip() + "\n\n" + text[body_end:].lstrip("\n")


_PRODUCTION_QA_ALLOWED_STATES = {"PASS", "REVISION_REQUIRED"}


def apply_production_qa_state(
    text: str, verdict: str, notes: str, new_production_status: str | None
) -> str:
    if verdict not in _PRODUCTION_QA_ALLOWED_STATES:
        raise PermissionError(
            f"agents/production_qa may not write Production QA state {verdict!r} — "
            f"only {sorted(_PRODUCTION_QA_ALLOWED_STATES)} are permitted (BLOCKED/SYSTEM_ERROR "
            "results are never written to PRODUCTION.md, nothing was actually checked)"
        )
    if new_production_status is not None and new_production_status not in ("HUMAN_REVIEW",):
        raise PermissionError(
            f"agents/production_qa may not set Production status to {new_production_status!r} — "
            "HUMAN_REVIEW is the only status this agent may ever set"
        )
    body = (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| State | `{verdict}` |\n"
        f"| Notes | {notes} |"
    )
    text = _replace_section_body(text, "Production QA state", body)
    if new_production_status:
        text = _replace_table_field(text, "Production status", f"`{new_production_status}`")
    return text
