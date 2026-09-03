"""Reads the two scene-level fields Assembler needs that
agents/assets/src/scene_reader.py's SceneVisualRecord doesn't carry:
Duration and Transition In/Out. Reuses agents/assets/src/scene_reader.py's
load_scene_visual_records directly for everything else (narration, claim
references, order, visual fields) — generic scene-file reading, not
another agent's domain logic — rather than a third full duplicate reader.
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing


def load_scene_timing(path: Path) -> tuple[int, str, str]:
    text = path.read_text(encoding="utf-8")
    identity = parsing.parse_table(text)
    duration_raw = parsing.strip_single_backticks(identity.get("Duration", "0s"))
    try:
        duration_seconds = int(duration_raw.rstrip("s") or 0)
    except ValueError:
        duration_seconds = 0

    sections = parsing.parse_sections(text)
    transition_table = parsing.parse_table(sections.get("Transition", ""))
    transition_in = parsing.strip_single_backticks(transition_table.get("In", "N/A")) or "N/A"
    transition_out = parsing.strip_single_backticks(transition_table.get("Out", "N/A")) or "N/A"
    return duration_seconds, transition_in, transition_out
