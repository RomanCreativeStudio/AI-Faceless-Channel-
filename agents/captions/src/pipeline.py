"""Top-level orchestration for the Captions agent: run_caption_generation()
is the one entry point. Same dry-run-by-default / apply-opt-in shape as
every other production agent. See CONTRACT.md's Preconditions,
"Segmentation rule", and "Caption integrity".
"""
from __future__ import annotations

from pathlib import Path

from ...assembler.src.scene_reader import load_scene_timing
from ...assets.src.scene_reader import load_scene_visual_records
from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_content_item
from . import mutate
from .captions_writer import render_captions_markdown
from .hashing import compute_captions_content_hash
from .models import CaptionsResult, SceneCaptions
from .segmentation import (
    DEFAULT_MAX_CHARACTERS_PER_LINE,
    DEFAULT_MAX_LINES_PER_CAPTION,
    build_caption_chunks,
    build_caption_timestamps,
)

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"
NEXT_PRODUCTION_STATUS = "THUMBNAIL"
ALLOWED_PRODUCTION_STATUSES = {"CAPTIONS", NEXT_PRODUCTION_STATUS}


def run_caption_generation(
    root: Path,
    apply: bool = False,
    max_characters_per_line: int = DEFAULT_MAX_CHARACTERS_PER_LINE,
    max_lines_per_caption: int = DEFAULT_MAX_LINES_PER_CAPTION,
) -> CaptionsResult:
    def _empty(**overrides) -> CaptionsResult:
        base = dict(
            content_id="", production_id="", captions_id="", filename="", scenes=[],
            captions_content_hash="", max_characters_per_line=max_characters_per_line,
            max_lines_per_caption=max_lines_per_caption, generation_status="NOT_STARTED",
            reasons=[],
        )
        base.update(overrides)
        return CaptionsResult(**base)

    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
        return _empty(
            content_id=content_item.content_id, blocked=True,
            blocked_reason=(
                f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                f"{REQUIRED_CONTENT_ITEM_STATUS!r} — refusing to generate captions"
            ),
        )

    production_path = root / "PRODUCTION.md"
    if not production_path.is_file():
        return _empty(
            content_id=content_item.content_id, aborted=True,
            abort_reason=f"no PRODUCTION.md under {root}",
        )
    production_text = production_path.read_text(encoding="utf-8")
    production_table = parsing.parse_table(production_text)
    production_id = parsing.strip_single_backticks(production_table.get("Production ID", ""))
    production_status = parsing.strip_single_backticks(production_table.get("Production status", ""))

    if production_status not in ALLOWED_PRODUCTION_STATUSES:
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=(
                f"PRODUCTION.md Production status is {production_status!r} — "
                f"agents/captions/CONTRACT.md's Preconditions require {sorted(ALLOWED_PRODUCTION_STATUSES)}"
            ),
        )

    script_path = root / "SCRIPT.md"
    if not script_path.is_file():
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            aborted=True, abort_reason=f"no valid current SCRIPT.md under {root}",
        )
    current_script_hash = compute_script_content_hash(script_path.read_text(encoding="utf-8"))
    stored_production_hash = parsing.strip_single_backticks(
        production_table.get("Script content hash", "")
    )
    if stored_production_hash != current_script_hash:
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=(
                f"SCRIPT.md changed since PRODUCTION.md was created (stored "
                f"{stored_production_hash!r}, current {current_script_hash!r}) — production plan is stale"
            ),
        )

    scene_records = load_scene_visual_records(root / "scenes")
    if not scene_records:
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            aborted=True, abort_reason=f"no scenes/scene-*.md under {root}",
        )

    empty_narration = [s.filename for s in scene_records if not s.narration_text.strip()]
    if empty_narration:
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=f"scenes with empty narration: {empty_narration}",
        )

    content_id = content_item.content_id
    captions_id = f"{content_id}-captions-01"
    filename = "captions-01.md"
    captions_path = root / "captions" / filename

    narration_texts = [s.narration_text for s in scene_records]
    captions_content_hash = compute_captions_content_hash(narration_texts)

    if captions_path.is_file():
        existing_text = captions_path.read_text(encoding="utf-8")
        existing_identity = parsing.parse_table(existing_text)
        if "Captions content hash" in existing_identity:
            existing_hash = parsing.strip_single_backticks(existing_identity["Captions content hash"])
            if not existing_hash or existing_hash == "N/A":
                return _empty(
                    content_id=content_id, production_id=production_id, aborted=True,
                    abort_reason=(
                        f"existing {captions_path} is malformed (Captions content hash "
                        "field present but empty)"
                    ),
                )
            if existing_hash == captions_content_hash:
                return _empty(
                    content_id=content_id, production_id=production_id, captions_id=captions_id,
                    filename=filename, captions_content_hash=captions_content_hash,
                    reasons=["captions/captions-01.md already up to date"], already_up_to_date=True,
                )
            return _empty(
                content_id=content_id, production_id=production_id, captions_id=captions_id,
                filename=filename, captions_content_hash=captions_content_hash, stale=True,
                stale_reason=(
                    f"captions/captions-01.md exists with Captions content hash {existing_hash!r}, "
                    f"but current narration hashes to {captions_content_hash!r} — a scene's "
                    "narration changed since. Refusing to silently regenerate."
                ),
            )

    scenes: list[SceneCaptions] = []
    for scene in scene_records:
        duration_seconds, _, _ = load_scene_timing(scene.path)
        chunks_text = build_caption_chunks(
            scene.narration_text, max_characters_per_line, max_lines_per_caption
        )
        timed_chunks = build_caption_timestamps(chunks_text, scene.narration_text, duration_seconds)
        scenes.append(SceneCaptions(scene_filename=scene.filename, scene_id=scene.scene_id, chunks=timed_chunks))

    result = CaptionsResult(
        content_id=content_id, production_id=production_id, captions_id=captions_id, filename=filename,
        scenes=scenes, captions_content_hash=captions_content_hash,
        max_characters_per_line=max_characters_per_line, max_lines_per_caption=max_lines_per_caption,
        generation_status="GENERATED", reasons=[f"generated captions for {len(scenes)} scene(s)"],
    )

    if apply:
        _apply_result(root, content_id, result, production_text)

    return result


def _apply_result(root: Path, content_id: str, result: CaptionsResult, production_text: str) -> None:
    captions_text = render_captions_markdown(result, content_id)
    captions_path = mutate.write_captions_file(root, result.filename, captions_text)

    updated_production = mutate.apply_production_captions(
        production_text, captions_reference=f"captions/{result.filename}",
        status="GENERATED", new_production_status=NEXT_PRODUCTION_STATUS,
    )
    production_path = root / "PRODUCTION.md"
    production_path.write_text(updated_production, encoding="utf-8")

    result.captions_path = str(captions_path)
    result.production_path = str(production_path)
