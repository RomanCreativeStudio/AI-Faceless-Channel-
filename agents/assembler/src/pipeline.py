"""Top-level orchestration for the Assembler: run_video_assembly() is the
one entry point. Same dry-run-by-default / apply-opt-in shape as every
other production agent. See CONTRACT.md's Preconditions, "Renderer
abstraction", "Timeline model", and "Hash / dependency model".
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ...assets.src.hashing import compute_asset_content_hash
from ...assets.src.scene_reader import load_scene_visual_records
from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_claims, load_content_item
from . import mutate
from .hashing import compute_assembly_content_hash, compute_voice_hash_component
from .models import AssemblyResult, SceneTimelineEntry
from .provider import VideoRenderer
from .scene_reader import load_scene_timing
from .test_provider import LocalTestVideoRenderer
from .timeline_writer import render_timeline_markdown

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"
NEXT_PRODUCTION_STATUS = "CAPTIONS"
ALLOWED_PRODUCTION_STATUSES = {"ASSEMBLY", NEXT_PRODUCTION_STATUS}


def run_video_assembly(
    root: Path, apply: bool = False, renderer: VideoRenderer | None = None
) -> AssemblyResult:
    def _empty(**overrides) -> AssemblyResult:
        base = dict(
            content_id="", production_id="", timeline_id="", filename="", scenes=[],
            total_duration=0, assembly_content_hash="", renderer_label="", output_reference="",
            output_format="", output_hash="", playable="UNVERIFIED", assembly_status="NOT_STARTED",
            reasons=[],
        )
        base.update(overrides)
        return AssemblyResult(**base)

    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
        return _empty(
            content_id=content_item.content_id, blocked=True,
            blocked_reason=(
                f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                f"{REQUIRED_CONTENT_ITEM_STATUS!r} — refusing to assemble"
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
                f"agents/assembler/CONTRACT.md's Preconditions require {sorted(ALLOWED_PRODUCTION_STATUSES)}"
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

    # --- Voice ---
    voice_path = root / "voice" / "voice-01.md"
    if not voice_path.is_file():
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason="no voice/voice-01.md — voice generation has not happened yet",
        )
    voice_text = voice_path.read_text(encoding="utf-8")
    voice_identity = parsing.parse_table(voice_text)
    voice_provider = parsing.strip_single_backticks(voice_identity.get("Provider", ""))
    voice_configuration = voice_identity.get("Voice configuration", "")
    voice_script_hash = parsing.strip_single_backticks(voice_identity.get("Script content hash", ""))
    voice_sections = parsing.parse_sections(voice_text)
    voice_generation_status = voice_sections.get("Generation status", "").strip().strip("`")
    audio_table = parsing.parse_table(voice_sections.get("Generated audio", ""))
    audio_reference = parsing.strip_single_backticks(audio_table.get("Reference", ""))

    if voice_generation_status != "GENERATED":
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=(
                f"voice/voice-01.md Generation status is {voice_generation_status!r}, not 'GENERATED'"
            ),
        )
    if voice_script_hash != current_script_hash:
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=(
                f"voice/voice-01.md's Script content hash {voice_script_hash!r} does not match "
                f"the current script hash {current_script_hash!r} — voice track is stale"
            ),
        )
    if not audio_reference or audio_reference.lower() == "not yet generated":
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason="voice/voice-01.md has no audio reference recorded",
        )

    voice_hash_component = compute_voice_hash_component(
        voice_provider, voice_configuration, voice_script_hash, audio_reference
    )

    # --- Scenes ---
    scene_visual_records = load_scene_visual_records(root / "scenes")
    if not scene_visual_records:
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            aborted=True, abort_reason=f"no scenes/scene-*.md under {root}",
        )

    orders = sorted(s.order for s in scene_visual_records)
    expected_orders = list(range(1, len(scene_visual_records) + 1))
    if orders != expected_orders:
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=f"scene Order values are not contiguous 1..N: found {orders}",
        )

    claims = load_claims(root / "claims")
    missing_claims = [
        (s.filename, cid) for s in scene_visual_records for cid in s.claim_ids if cid not in claims
    ]
    if missing_claims:
        detail = "; ".join(f"{fn} cites {cid!r}" for fn, cid in missing_claims)
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=f"missing claim provenance: {detail}",
        )

    # --- Assets, resolved and verified per scene, in order ---
    asset_hashes: list[str] = []
    scene_entries: list[SceneTimelineEntry] = []
    cumulative_start = 0
    for scene in scene_visual_records:
        asset_filename = f"asset-{scene.order:02d}.md"
        asset_path = root / "assets" / asset_filename
        if not asset_path.is_file():
            return _empty(
                content_id=content_item.content_id, production_id=production_id, blocked=True,
                blocked_reason=f"missing required asset: assets/{asset_filename} for {scene.filename}",
            )
        asset_text = asset_path.read_text(encoding="utf-8")
        asset_identity = parsing.parse_table(asset_text)
        stored_asset_hash = parsing.strip_single_backticks(
            asset_identity.get("Scene/visual content hash", "")
        )
        if not stored_asset_hash or stored_asset_hash == "N/A":
            return _empty(
                content_id=content_item.content_id, production_id=production_id, blocked=True,
                blocked_reason=(
                    f"assets/{asset_filename} has no Scene/visual content hash recorded — "
                    "asset generation incomplete"
                ),
            )
        current_asset_hash = compute_asset_content_hash(scene)
        if stored_asset_hash != current_asset_hash:
            return _empty(
                content_id=content_item.content_id, production_id=production_id, blocked=True,
                blocked_reason=(
                    f"assets/{asset_filename} is stale relative to {scene.filename} "
                    f"(stored hash {stored_asset_hash!r}, current {current_asset_hash!r})"
                ),
            )
        asset_hashes.append(stored_asset_hash)

        duration_seconds, transition_in, transition_out = load_scene_timing(scene.path)
        start = cumulative_start
        end = start + duration_seconds
        cumulative_start = end

        scene_entries.append(
            SceneTimelineEntry(
                scene_id=scene.scene_id, filename=scene.filename, order=scene.order,
                start=start, end=end, duration_seconds=duration_seconds,
                narration_reference="voice/voice-01.md", visual_reference=f"assets/{asset_filename}",
                captions_reference="captions/captions-01.md",
                transition_in=transition_in, transition_out=transition_out,
                claim_ids=scene.claim_ids,
            )
        )

    total_duration = cumulative_start
    assembly_content_hash = compute_assembly_content_hash(
        current_script_hash, voice_hash_component, asset_hashes
    )

    content_id = content_item.content_id
    timeline_id = f"{content_id}-timeline-01"
    filename = "timeline-01.md"
    timeline_path = root / "timeline" / filename

    if timeline_path.is_file():
        existing_text = timeline_path.read_text(encoding="utf-8")
        existing_identity = parsing.parse_table(existing_text)
        if "Assembly content hash" in existing_identity:
            existing_hash = parsing.strip_single_backticks(existing_identity["Assembly content hash"])
            if not existing_hash or existing_hash == "N/A":
                return _empty(
                    content_id=content_id, production_id=production_id, aborted=True,
                    abort_reason=(
                        f"existing {timeline_path} is malformed (Assembly content hash "
                        "field present but empty)"
                    ),
                )
            if existing_hash == assembly_content_hash:
                return _empty(
                    content_id=content_id, production_id=production_id, timeline_id=timeline_id,
                    filename=filename, assembly_content_hash=assembly_content_hash,
                    reasons=["timeline/timeline-01.md already up to date"], already_up_to_date=True,
                )
            return _empty(
                content_id=content_id, production_id=production_id, timeline_id=timeline_id,
                filename=filename, assembly_content_hash=assembly_content_hash, stale=True,
                stale_reason=(
                    f"timeline/timeline-01.md exists with Assembly content hash {existing_hash!r}, "
                    f"but current inputs hash to {assembly_content_hash!r} — some upstream artifact "
                    "changed since assembly. Refusing to silently regenerate."
                ),
            )

    active_renderer = renderer or LocalTestVideoRenderer()
    render_result = active_renderer.render(scene_entries, total_duration)
    output_filename = "video-01.manifest.txt"
    output_reference = f"output/{output_filename}"
    output_hash = hashlib.sha256(render_result.artifact_content.encode("utf-8")).hexdigest()

    result = AssemblyResult(
        content_id=content_id, production_id=production_id, timeline_id=timeline_id, filename=filename,
        scenes=scene_entries, total_duration=total_duration, assembly_content_hash=assembly_content_hash,
        renderer_label=render_result.provider_label, output_reference=output_reference,
        output_format=render_result.format, output_hash=output_hash, playable=render_result.playable,
        assembly_status="ASSEMBLED", reasons=[f"assembled {len(scene_entries)} scene(s)"],
    )

    if apply:
        _apply_result(root, content_id, result, render_result.artifact_content, production_text)

    return result


def _apply_result(root: Path, content_id: str, result: AssemblyResult, artifact_content: str, production_text: str) -> None:
    output_path = mutate.write_output_artifact(root, "video-01.manifest.txt", artifact_content)
    timeline_text = render_timeline_markdown(result, content_id)
    timeline_path = mutate.write_timeline_file(root, result.filename, timeline_text)

    updated_production = mutate.apply_production_assembly(
        production_text,
        timeline_reference=f"timeline/{result.filename}",
        video_reference=result.output_reference,
        assembly_status=result.assembly_status,
        new_production_status=NEXT_PRODUCTION_STATUS,
    )
    production_path = root / "PRODUCTION.md"
    production_path.write_text(updated_production, encoding="utf-8")

    result.timeline_path = str(timeline_path)
    result.output_path = str(output_path)
    result.production_path = str(production_path)
