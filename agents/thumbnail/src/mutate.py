"""Path/field-whitelisted writers for the Thumbnail agent: only
thumbnail/thumbnail-<n>.md, and PRODUCTION.md's Thumbnail + Title/
description sections + Production status — no generic "write anything"
helper.
"""
from __future__ import annotations

import re
from pathlib import Path

_THUMBNAIL_FILENAME_RE = re.compile(r"^thumbnail-\d+\.md$")


def write_thumbnail_file(root: Path, filename: str, text: str) -> Path:
    if not _THUMBNAIL_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/thumbnail may not write thumbnail file {filename!r} — "
            "only thumbnail-<n>.md is permitted"
        )
    thumbnail_dir = root / "thumbnail"
    thumbnail_dir.mkdir(exist_ok=True)
    path = thumbnail_dir / filename
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


def apply_production_thumbnail(
    text: str, thumbnail_reference: str, status: str, working_title: str,
    new_production_status: str | None,
) -> str:
    thumbnail_body = (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Asset reference | `{thumbnail_reference}` |\n"
        f"| Status | `{status}` |"
    )
    text = _replace_section_body(text, "Thumbnail", thumbnail_body)

    title_body = (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Working title | {working_title} |\n"
        "| Description | Not yet drafted — see `thumbnail/`, `SCRIPT.md`'s Premise/Conclusion. |"
    )
    text = _replace_section_body(text, "Title / description", title_body)

    if new_production_status:
        text = _replace_table_field(text, "Production status", f"`{new_production_status}`")
    return text
