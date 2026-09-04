"""Reads captions/captions-<n>.md's per-scene, scene-relative caption
chunks — generic file reading, not agents/captions/'s own domain logic
(segmentation itself stays exclusively in agents/captions/src/segmentation.py;
this module only parses the already-written record back out). Reused by
agents/assembler/src/real_provider.py to burn global-timeline-relative
subtitles into the rendered video — captions/'s own schema
(templates/CAPTIONS.md) is deliberately unchanged; global timing is
computed here by combining these scene-relative chunk times with the
timeline's own per-scene start offsets, never by changing what
agents/captions/ itself records.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...researcher.src import parsing


@dataclass
class CaptionChunkTiming:
    start: float  # scene-relative seconds
    end: float  # scene-relative seconds
    text: str


def _split_h3_subsections(body: str) -> dict[str, str]:
    """`## Scene captions`'s body holds one `### Scene ...` subsection per
    scene — parsing.parse_sections only splits on `## `, so H3s are split
    out here. Mirrors agents/production_qa/src/checks.py's own identical
    helper (duplicated, not imported — sibling-agent boundary, same
    established precedent as every mutate.py's small-helper duplication)."""
    subsections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("### "):
            if current is not None:
                subsections[current] = "\n".join(buf).strip()
            current = line[4:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        subsections[current] = "\n".join(buf).strip()
    return subsections


def load_scene_caption_chunks(captions_path: Path) -> dict[str, list[CaptionChunkTiming]]:
    """Returns {scene_id (backtick-quoted marker text, e.g. "`scene-01-id`"
    stripped to its raw form): [CaptionChunkTiming, ...]}, keyed by the
    exact scene_id string used in `### Scene \`<scene_id>\`` headings."""
    if not captions_path.is_file():
        return {}
    text = captions_path.read_text(encoding="utf-8")
    sections = parsing.parse_sections(text)
    scene_subsections = _split_h3_subsections(sections.get("Scene captions", ""))

    result: dict[str, list[CaptionChunkTiming]] = {}
    for heading, body in scene_subsections.items():
        # heading looks like "Scene `<scene_id>`"
        scene_id = heading.split("`")[1] if "`" in heading else heading.replace("Scene", "").strip()
        chunks: list[CaptionChunkTiming] = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or "Caption #" in line:
                continue
            content_only = line.replace("|", "").strip()
            if content_only and set(content_only) <= {"-"}:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4 or cells[0] == "—":
                continue
            try:
                start = float(parsing.strip_single_backticks(cells[1]).rstrip("s"))
                end = float(parsing.strip_single_backticks(cells[2]).rstrip("s"))
            except ValueError:
                continue
            chunks.append(CaptionChunkTiming(start=start, end=end, text=cells[3]))
        result[scene_id] = chunks
    return result
