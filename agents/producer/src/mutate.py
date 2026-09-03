"""Path-whitelisted file creation for the Producer: PRODUCTION.md (root)
and scenes/scene-<n>.md only — no generic "write anything" helper. Both
functions only ever create a *fresh* file; agents/producer/src/pipeline.py
never calls these once a PRODUCTION.md already exists for a content item
(see its staleness handling / CONTRACT.md's "Re-running" section) so
existing production history is never overwritten by this module.
"""
from __future__ import annotations

import re
from pathlib import Path

_SCENE_FILENAME_RE = re.compile(r"^scene-\d+\.md$")


def write_production_file(root: Path, text: str) -> Path:
    path = root / "PRODUCTION.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_scene_file(root: Path, filename: str, text: str) -> Path:
    if not _SCENE_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/producer may not write scenes file {filename!r} — "
            "only scene-<n>.md is permitted"
        )
    scenes_dir = root / "scenes"
    scenes_dir.mkdir(exist_ok=True)
    path = scenes_dir / filename
    path.write_text(text, encoding="utf-8")
    return path
