"""Loads scenes/scene-<n>.md records into models.SceneRecord. Reuses
agents/researcher/src.parsing directly (each scene's per-section mini
tables are ordinary `| Field | Value |` tables, so the same generic
parse_table/parse_sections helpers work unmodified).
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing
from .models import SceneRecord


def _extract_claim_ids(claim_refs_body: str) -> list[str]:
    lines = [
        line for line in claim_refs_body.splitlines()
        if not line.strip().startswith("Classifications present")
    ]
    return parsing.backtick_tokens("\n".join(lines))


def load_scene(path: Path) -> SceneRecord:
    text = path.read_text(encoding="utf-8")
    identity = parsing.parse_table(text)
    sections = parsing.parse_sections(text)
    narration_table = parsing.parse_table(sections.get("Narration", ""))
    claim_refs_body = sections.get("Source / claim references", "")

    return SceneRecord(
        path=path,
        filename=path.name,
        scene_id=parsing.strip_single_backticks(identity.get("Scene ID", "")),
        content_id=parsing.strip_single_backticks(identity.get("Content ID", "")),
        order=int(identity.get("Order", "0") or 0),
        narration_text=narration_table.get("Narration text", ""),
        claim_ids=_extract_claim_ids(claim_refs_body),
        raw_text=text,
    )


def load_scenes(scenes_dir: Path) -> list[SceneRecord]:
    if not scenes_dir.is_dir():
        return []
    return [load_scene(p) for p in sorted(scenes_dir.glob("scene-*.md"))]
