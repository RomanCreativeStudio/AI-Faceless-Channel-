"""Field/path-whitelisted writers for the Visual Planner: only a scene's
Visual type/Visual description/Asset requirement fields, new
assets/asset-<n>.md files, and PRODUCTION.md's Visual requirements
(rollup)/Asset references (rollup)/Production status — no generic "write
anything" helper. See CONTRACT.md's Allowed actions.

The `_replace_table_field` regex is duplicated from
agents/researcher/src/mutate.py rather than imported, mirroring
agents/safety/src/mutate.py's own precedent for the same small helper —
see that module's docstring for why.
"""
from __future__ import annotations

import re
from pathlib import Path

from .models import VisualPlan

SCENE_WRITABLE_FIELDS = {"Visual type", "Visual description", "Asset requirement"}
PRODUCTION_WRITABLE_FIELDS = {"Production status"}
_ASSET_FILENAME_RE = re.compile(r"^asset-\d+\.md$")


def _replace_table_field(text: str, field_name: str, new_value: str) -> str:
    pattern = re.compile(
        r"^(\|\s*" + re.escape(field_name) + r"\s*\|\s*).*?(\s*\|\s*)$", re.MULTILINE
    )
    if not pattern.search(text):
        raise ValueError(f"field {field_name!r} not found as a table row")
    return pattern.sub(lambda m: f"{m.group(1)}{new_value}{m.group(2)}", text, count=1)


def apply_scene_visual_fields(plan: VisualPlan) -> str:
    text = plan.scene.raw_text
    text = _replace_table_field(text, "Visual type", f"`{plan.visual_type}`")
    description = plan.visual_description.replace("|", "/")
    text = _replace_table_field(text, "Visual description", description)
    asset_requirement = (
        f"`assets/{plan.asset_filename}`"
        if plan.needs_asset
        else "N/A — produced directly at assembly, no discrete asset record"
    )
    text = _replace_table_field(text, "Asset requirement", asset_requirement)
    return text


def write_scene_file(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_asset_file(root: Path, filename: str, text: str) -> Path:
    if not _ASSET_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/visual_planner may not write assets file {filename!r} — "
            "only asset-<n>.md is permitted"
        )
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    path = assets_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


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


def apply_production_rollups(text: str, visual_rollup: str, asset_rollup: str, new_status: str) -> str:
    text = _replace_section_body(text, "Visual requirements (rollup)", visual_rollup)
    text = _replace_section_body(text, "Asset references (rollup)", asset_rollup)
    text = _replace_table_field(text, "Production status", f"`{new_status}`")
    return text
