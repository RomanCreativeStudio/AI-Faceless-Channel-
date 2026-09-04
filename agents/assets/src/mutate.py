"""Path/field-whitelisted writers for the Asset agent: only
assets/asset-<n>.md + assets/asset-<n>.generated.txt files, and
PRODUCTION.md's Asset references (rollup) section + Production status —
no generic "write anything" helper. See CONTRACT.md's Allowed actions.

`_replace_table_field`/`_replace_section_body` are duplicated small
helpers rather than imported cross-agent, mirroring
agents/visual_planner/src/mutate.py's and agents/voice/src/mutate.py's
own precedent for the same pattern.
"""
from __future__ import annotations

import re
from pathlib import Path

_ASSET_FILENAME_RE = re.compile(r"^asset-\d+\.md$")
_ARTIFACT_FILENAME_RE = re.compile(r"^asset-\d+\.generated\.txt$")
# Phase 8: real binary artifacts — a still-closed extension whitelist, not
# "any file". GENERATED real images are always PNG (illustration.py's own
# output format); RETRIEVED real images may be JPEG or PNG, whatever the
# source actually serves.
_GENERATED_BINARY_FILENAME_RE = re.compile(r"^asset-\d+\.generated\.png$")
_RETRIEVED_BINARY_FILENAME_RE = re.compile(r"^asset-\d+\.retrieved\.(jpg|jpeg|png)$")


def write_asset_file(root: Path, filename: str, text: str) -> Path:
    if not _ASSET_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/assets may not write assets file {filename!r} — "
            "only asset-<n>.md is permitted"
        )
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    path = assets_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


def write_generated_artifact(root: Path, filename: str, content: str) -> Path:
    if not _ARTIFACT_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/assets may not write artifact file {filename!r} — "
            "only asset-<n>.generated.txt is permitted"
        )
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    path = assets_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def write_generated_artifact_binary(root: Path, filename: str, data: bytes) -> Path:
    """Phase 8: a real GeneratedAssetProvider's genuine binary image —
    filename-whitelisted exactly like every other writer here."""
    if not _GENERATED_BINARY_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/assets may not write binary generated artifact {filename!r} — "
            "only asset-<n>.generated.png is permitted"
        )
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    path = assets_dir / filename
    path.write_bytes(data)
    return path


def write_retrieved_artifact_binary(root: Path, filename: str, data: bytes) -> Path:
    """Phase 8: a real AssetRetrievalProvider's genuinely retrieved image
    bytes — filename-whitelisted, append-only-in-spirit (this agent never
    overwrites a retrieved artifact once staleness/hash logic in
    pipeline.py has already decided a fresh write is warranted)."""
    if not _RETRIEVED_BINARY_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/assets may not write retrieved artifact {filename!r} — "
            "only asset-<n>.retrieved.(jpg|jpeg|png) is permitted"
        )
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    path = assets_dir / filename
    path.write_bytes(data)
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


def apply_production_asset_rollup(text: str, asset_rollup: str, new_production_status: str | None) -> str:
    text = _replace_section_body(text, "Asset references (rollup)", asset_rollup)
    if new_production_status:
        text = _replace_table_field(text, "Production status", f"`{new_production_status}`")
    return text
