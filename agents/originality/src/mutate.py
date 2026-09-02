"""Narrow, whitelisted field-level writer for CONTENT_ITEM.md's
`Originality state` field only — the sole field this contract permits.
Reuses agents/researcher/src/mutate.py's `append_notes_log` directly
(already generic). Same shape as agents/safety/src/mutate.py, defined
independently per-agent so each whitelist is its own hard-coded constant.

This agent has no claim-writing or research-writing function at all —
CONTRACT.md's Forbidden actions list claims/research as fully protected.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...researcher.src.mutate import append_notes_log  # re-exported, generic

CONTENT_ITEM_WRITABLE_FIELDS = {"Originality state"}

__all__ = ["append_notes_log", "update_content_item_field", "CONTENT_ITEM_WRITABLE_FIELDS"]


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
            f"agents/originality may not write CONTENT_ITEM.md field {field_name!r} "
            f"— only {sorted(CONTENT_ITEM_WRITABLE_FIELDS)} is permitted"
        )
    text = path.read_text(encoding="utf-8")
    path.write_text(_replace_table_field(text, field_name, new_value), encoding="utf-8")
