"""Generic markdown parsing helpers for the `| Field | Value |` tables and
`## Heading` sections used by every template in templates/. Deliberately
simple: assumes cell values don't contain a literal "|" (true of every
file in this repo today) — see README.md "Known limitations."
"""
from __future__ import annotations

import re

_TABLE_ROW_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")


def parse_table(text: str) -> dict[str, str]:
    """Parse the first `| Field | Value |` table in `text` into a dict.

    Skips the header row and the `|---|---|` separator row.
    """
    rows: dict[str, str] = {}
    in_table = False
    for line in text.splitlines():
        m = _TABLE_ROW_RE.match(line.strip())
        if not m:
            if in_table:
                break  # table ended
            continue
        key, value = m.group(1), m.group(2)
        if key.lower() == "field" and value.lower() == "value":
            in_table = True
            continue
        if set(key) <= {"-"} and set(value) <= {"-"}:
            continue  # separator row
        if in_table:
            rows[key] = value
    return rows


def parse_sections(text: str) -> dict[str, str]:
    """Split `text` on `## Heading` lines; return {heading: body}."""
    sections: dict[str, str] = {}
    current_heading = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(buf).strip()
            current_heading = line[3:].strip()
            buf = []
        elif current_heading is not None:
            buf.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(buf).strip()
    return sections


def backtick_tokens(raw: str) -> list[str]:
    """Extract every `backtick-wrapped` token from a raw field value."""
    return _BACKTICK_RE.findall(raw)


def first_backtick_token(raw: str, default: str = "") -> str:
    """Return the first `backtick-wrapped` token in a field value that may
    carry trailing prose (e.g. "`HIGH` (UN public-health authority)").
    Falls back to `default` if there is no backtick-wrapped token at all.
    """
    tokens = _BACKTICK_RE.findall(raw)
    return tokens[0] if tokens else default


def strip_single_backticks(raw: str) -> str:
    """If `raw` is a single value wholly wrapped in one pair of
    backticks, return the inner text; otherwise return raw unchanged."""
    raw = raw.strip()
    if raw.startswith("`") and raw.endswith("`") and raw.count("`") == 2:
        return raw[1:-1]
    return raw
