"""Loads scenes/scene-<n>.md records into models.SceneVisualRecord — the
Producer/Visual Planner-written fields this agent needs (order, claim
references, narration, and the Visual type/description Visual Planner
wrote). Reuses agents/researcher/src.parsing directly (generic table/
section parsing); does not reuse agents/visual_planner/src.loader's
SceneRecord because that model doesn't carry the Visual type/description
fields this agent needs — a second, small, self-contained reader here
mirrors agents/visual_planner/src/loader.py's own precedent of each
production agent owning its own scene-field reader rather than importing
another agent's domain model.
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing
from .models import SceneVisualRecord


def _extract_claim_ids(claim_refs_body: str) -> list[str]:
    lines = [
        line for line in claim_refs_body.splitlines()
        if not line.strip().startswith("Classifications present")
    ]
    return parsing.backtick_tokens("\n".join(lines))


def load_scene_visual_record(path: Path) -> SceneVisualRecord:
    text = path.read_text(encoding="utf-8")
    identity = parsing.parse_table(text)
    sections = parsing.parse_sections(text)
    narration_table = parsing.parse_table(sections.get("Narration", ""))
    visual_table = parsing.parse_table(sections.get("Visual", ""))
    claim_refs_body = sections.get("Source / claim references", "")

    return SceneVisualRecord(
        path=path,
        filename=path.name,
        scene_id=parsing.strip_single_backticks(identity.get("Scene ID", "")),
        content_id=parsing.strip_single_backticks(identity.get("Content ID", "")),
        order=int(identity.get("Order", "0") or 0),
        narration_text=narration_table.get("Narration text", ""),
        visual_type=parsing.strip_single_backticks(visual_table.get("Visual type", "")),
        visual_description=visual_table.get("Visual description", ""),
        claim_ids=_extract_claim_ids(claim_refs_body),
        raw_text=text,
    )


def load_scene_visual_records(scenes_dir: Path) -> list[SceneVisualRecord]:
    if not scenes_dir.is_dir():
        return []
    records = [load_scene_visual_record(p) for p in sorted(scenes_dir.glob("scene-*.md"))]
    records.sort(key=lambda s: s.order)
    return records
