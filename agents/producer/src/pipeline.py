"""Top-level orchestration for the Producer: run_producer() is the one
entry point. Same dry-run-by-default / apply-opt-in shape as
agents/researcher/src/pipeline.py, reusing its generic loader/errors
rather than duplicating them (see README.md "Relationship to
agents/researcher").

Staleness handling (CONTRACT.md "Re-running"): if a PRODUCTION.md already
exists for this content item, the Producer never overwrites it — a
matching `Script content hash` means it's already up to date (no-op); a
mismatched hash means SCRIPT.md changed since, so the plan is stale and
the Producer refuses to touch the existing PRODUCTION.md/scenes/ at all,
returning a structured `stale` result instead of silently regenerating.
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing
from ...researcher.src.errors import NoLoadableContent, StructuralFailure
from ...researcher.src.loader import load_claims, load_content_item
from . import mutate
from .duration import DEFAULT_WORDS_PER_MINUTE
from .hashing import compute_script_content_hash
from .models import ProductionResult
from .production_writer import render_production_markdown
from .scene_builder import build_scenes
from .scene_writer import render_scene_markdown

APPROVED_STATUS = "APPROVED"


def run_producer(
    root: Path, apply: bool = False, words_per_minute: int = DEFAULT_WORDS_PER_MINUTE
) -> ProductionResult:
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return ProductionResult(
            content_id="", scenes=[], production_id="", script_content_hash="",
            reasons=[], aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}",
        )
    content_item = load_content_item(content_item_path)

    if content_item.status != APPROVED_STATUS:
        return ProductionResult(
            content_id=content_item.content_id, scenes=[], production_id="",
            script_content_hash="", reasons=[], blocked=True,
            blocked_reason=(
                f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                f"{APPROVED_STATUS!r} — agents/producer/CONTRACT.md's Preconditions "
                "require full human approval before any production plan may be "
                "created; refusing to produce"
            ),
        )

    script_path = root / "SCRIPT.md"
    if not script_path.is_file():
        return ProductionResult(
            content_id=content_item.content_id, scenes=[], production_id="",
            script_content_hash="", reasons=[], aborted=True,
            abort_reason=f"no SCRIPT.md under {root}",
        )
    script_text = script_path.read_text(encoding="utf-8")

    try:
        claims = load_claims(root / "claims")
        scenes = build_scenes(script_text, content_item.content_id, claims, words_per_minute)
    except (NoLoadableContent, StructuralFailure) as exc:
        return ProductionResult(
            content_id=content_item.content_id, scenes=[], production_id="",
            script_content_hash="", reasons=[], aborted=True, abort_reason=str(exc),
        )

    script_hash = compute_script_content_hash(script_text)
    production_id = f"{content_item.content_id}-prod-01"
    production_path = root / "PRODUCTION.md"

    if production_path.is_file():
        existing_table = parsing.parse_table(production_path.read_text(encoding="utf-8"))
        existing_hash = parsing.strip_single_backticks(existing_table.get("Script content hash", ""))
        if existing_hash == script_hash:
            return ProductionResult(
                content_id=content_item.content_id, scenes=scenes, production_id=production_id,
                script_content_hash=script_hash,
                reasons=["PRODUCTION.md already up to date with the current SCRIPT.md"],
                already_up_to_date=True,
            )
        return ProductionResult(
            content_id=content_item.content_id, scenes=scenes, production_id=production_id,
            script_content_hash=script_hash, reasons=[], stale=True,
            stale_reason=(
                f"PRODUCTION.md exists with Script content hash {existing_hash!r}, but "
                f"the current SCRIPT.md hashes to {script_hash!r} — the script changed "
                "since this production plan was created. Refusing to silently "
                "regenerate; the existing PRODUCTION.md/scenes/ are left untouched per "
                "agents/producer/CONTRACT.md's Re-running section."
            ),
        )

    result = ProductionResult(
        content_id=content_item.content_id, scenes=scenes, production_id=production_id,
        script_content_hash=script_hash, reasons=[f"produced {len(scenes)} scene(s)"],
    )

    if apply:
        _apply_result(root, content_item.content_id, production_id, script_hash, scenes)
        result.production_path = str(production_path)
        result.scene_paths = [str(root / "scenes" / s.filename) for s in scenes]

    return result


def _apply_result(
    root: Path, content_id: str, production_id: str, script_hash: str, scenes
) -> None:
    total_scenes = len(scenes)
    for scene in scenes:
        scene_text = render_scene_markdown(scene, content_id, total_scenes)
        mutate.write_scene_file(root, scene.filename, scene_text)

    production_text = render_production_markdown(content_id, production_id, script_hash, scenes)
    mutate.write_production_file(root, production_text)
