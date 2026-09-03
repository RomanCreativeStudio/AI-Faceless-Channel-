"""Path/field-whitelisted writers for the Assembler: only fresh
timeline/timeline-<n>.md + output/video-<n>.manifest.txt files, and
PRODUCTION.md's Assembly / Output section + Production status — no
generic "write anything" helper. See CONTRACT.md's Allowed actions.
"""
from __future__ import annotations

import re
from pathlib import Path

_TIMELINE_FILENAME_RE = re.compile(r"^timeline-\d+\.md$")
_OUTPUT_FILENAME_RE = re.compile(r"^video-\d+\.manifest\.txt$")


def write_timeline_file(root: Path, filename: str, text: str) -> Path:
    if not _TIMELINE_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/assembler may not write timeline file {filename!r} — "
            "only timeline-<n>.md is permitted"
        )
    timeline_dir = root / "timeline"
    timeline_dir.mkdir(exist_ok=True)
    path = timeline_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


def write_output_artifact(root: Path, filename: str, content: str) -> Path:
    if not _OUTPUT_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/assembler may not write output file {filename!r} — "
            "only video-<n>.manifest.txt is permitted"
        )
    output_dir = root / "output"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / filename
    path.write_text(content, encoding="utf-8")
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


def apply_production_assembly(
    text: str, timeline_reference: str, video_reference: str, assembly_status: str,
    new_production_status: str | None,
) -> str:
    body = (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Timeline reference | `{timeline_reference}` |\n"
        f"| Video output reference | `{video_reference}` |\n"
        f"| Assembly status | `{assembly_status}` |"
    )
    text = _replace_section_body(text, "Assembly / Output", body)
    if new_production_status:
        text = _replace_table_field(text, "Production status", f"`{new_production_status}`")
    return text
