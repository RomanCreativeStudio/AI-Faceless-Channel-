"""Path/field-whitelisted writers for the Captions agent: only
captions/captions-<n>.md, and PRODUCTION.md's Captions section +
Production status — no generic "write anything" helper.
"""
from __future__ import annotations

import re
from pathlib import Path

_CAPTIONS_FILENAME_RE = re.compile(r"^captions-\d+\.md$")


def write_captions_file(root: Path, filename: str, text: str) -> Path:
    if not _CAPTIONS_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/captions may not write captions file {filename!r} — "
            "only captions-<n>.md is permitted"
        )
    captions_dir = root / "captions"
    captions_dir.mkdir(exist_ok=True)
    path = captions_dir / filename
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


def apply_production_captions(
    text: str, captions_reference: str, status: str, new_production_status: str | None
) -> str:
    body = (
        "| Field | Value |\n"
        "|---|---|\n"
        "| Source | Derived from each scene's Narration text |\n"
        f"| Status | `{status}` |"
    )
    text = _replace_section_body(text, "Captions", body)
    if new_production_status:
        text = _replace_table_field(text, "Production status", f"`{new_production_status}`")
    return text
