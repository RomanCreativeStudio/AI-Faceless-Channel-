"""Top-level orchestration for the Thumbnail agent: run_thumbnail_generation()
is the one entry point. Same dry-run-by-default / apply-opt-in shape as
every other production agent. See CONTRACT.md's Preconditions and
"Fact / What If? framing".
"""
from __future__ import annotations

from pathlib import Path

from ...assets.src.scene_reader import load_scene_visual_records
from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_claims, load_content_item
from . import mutate
from .hashing import compute_thumbnail_content_hash
from .models import ThumbnailResult
from .provider import ThumbnailProvider
from .test_provider import PLACEHOLDER_NOTE, LocalTestThumbnailProvider
from .thumbnail_writer import render_thumbnail_markdown

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"
NEXT_PRODUCTION_STATUS = "METADATA"
ALLOWED_PRODUCTION_STATUSES = {"THUMBNAIL", NEXT_PRODUCTION_STATUS}


def run_thumbnail_generation(
    root: Path, apply: bool = False, provider: ThumbnailProvider | None = None
) -> ThumbnailResult:
    def _empty(**overrides) -> ThumbnailResult:
        base = dict(
            content_id="", production_id="", thumbnail_id="", filename="", spec=None,
            claim_theme_relationship="", authenticity_considerations="", generation_strategy="",
            thumbnail_content_hash="", thumbnail_status="NOT_STARTED", reasons=[],
        )
        base.update(overrides)
        return ThumbnailResult(**base)

    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
        return _empty(
            content_id=content_item.content_id, blocked=True,
            blocked_reason=(
                f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                f"{REQUIRED_CONTENT_ITEM_STATUS!r} — refusing to generate a thumbnail"
            ),
        )

    identity = parsing.parse_table(content_item.raw_text)
    working_title = parsing.strip_single_backticks(identity.get("Working title", "")) or identity.get("Working title", "")
    premise = identity.get("Premise", "")

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
                f"agents/thumbnail/CONTRACT.md's Preconditions require {sorted(ALLOWED_PRODUCTION_STATUSES)}"
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

    claims = load_claims(root / "claims")
    missing_claims = [
        (s.filename, cid) for s in scene_records for cid in s.claim_ids if cid not in claims
    ]
    if missing_claims:
        detail = "; ".join(f"{fn} cites {cid!r}" for fn, cid in missing_claims)
        return _empty(
            content_id=content_item.content_id, production_id=production_id, blocked=True,
            blocked_reason=f"missing claim provenance: {detail}",
        )

    classifications_in_order: list[str] = []
    claim_theme_parts: list[str] = []
    authenticity_found: set[str] = set()
    for scene in scene_records:
        for claim_id in scene.claim_ids:
            classification = claims[claim_id].classification.value
            classifications_in_order.append(classification)
            claim_theme_parts.append(f"`{claim_id}` ({classification})")

        asset_path = root / "assets" / f"asset-{scene.order:02d}.md"
        if asset_path.is_file():
            asset_sections = parsing.parse_sections(asset_path.read_text(encoding="utf-8"))
            auth_table = parsing.parse_table(
                asset_sections.get("Historical authenticity classification", "")
            )
            classification = parsing.first_backtick_token(auth_table.get("Classification", ""))
            if classification:
                authenticity_found.add(classification)

    content_pillar = content_item.content_pillar
    hedge_required = content_pillar == "what-if"

    if "GENERATED_RECONSTRUCTION" in authenticity_found:
        authenticity_considerations = (
            "This production includes hypothetical/generated content "
            "(GENERATED_RECONSTRUCTION) in at least one scene's asset — the thumbnail "
            "must not present it as authentic historical media. See assets/asset-<n>.md "
            "for the exact classification per scene."
        )
    elif "AUTHENTIC_HISTORICAL_MEDIA" in authenticity_found:
        authenticity_considerations = (
            "This production's visual sourcing intent is AUTHENTIC_HISTORICAL_MEDIA "
            "(not yet independently verified) — thumbnail imagery should reflect a "
            "real historical subject, not a generated one."
        )
    else:
        authenticity_considerations = (
            "No representational (AUTHENTIC_HISTORICAL_MEDIA/GENERATED_RECONSTRUCTION) "
            "asset exists for this production — thumbnail is text/graphic only."
        )

    claim_theme_relationship = (
        f"Represents claims: {', '.join(claim_theme_parts)}."
        if claim_theme_parts
        else "No claims referenced by any scene — framing/text-only thumbnail."
    )

    content_id = content_item.content_id
    thumbnail_id = f"{content_id}-thumbnail-01"
    filename = "thumbnail-01.md"
    thumbnail_path = root / "thumbnail" / filename

    thumbnail_content_hash = compute_thumbnail_content_hash(
        working_title, content_pillar, classifications_in_order
    )

    if thumbnail_path.is_file():
        existing_text = thumbnail_path.read_text(encoding="utf-8")
        existing_identity = parsing.parse_table(existing_text)
        if "Thumbnail content hash" in existing_identity:
            existing_hash = parsing.strip_single_backticks(existing_identity["Thumbnail content hash"])
            if not existing_hash or existing_hash == "N/A":
                return _empty(
                    content_id=content_id, production_id=production_id, aborted=True,
                    abort_reason=(
                        f"existing {thumbnail_path} is malformed (Thumbnail content hash "
                        "field present but empty)"
                    ),
                )
            if existing_hash == thumbnail_content_hash:
                return _empty(
                    content_id=content_id, production_id=production_id, thumbnail_id=thumbnail_id,
                    filename=filename, thumbnail_content_hash=thumbnail_content_hash,
                    reasons=["thumbnail/thumbnail-01.md already up to date"], already_up_to_date=True,
                )
            return _empty(
                content_id=content_id, production_id=production_id, thumbnail_id=thumbnail_id,
                filename=filename, thumbnail_content_hash=thumbnail_content_hash, stale=True,
                stale_reason=(
                    f"thumbnail/thumbnail-01.md exists with Thumbnail content hash "
                    f"{existing_hash!r}, but current inputs hash to "
                    f"{thumbnail_content_hash!r} — the title, pillar, or a claim classification "
                    "changed since. Refusing to silently regenerate."
                ),
            )

    active_provider = provider or LocalTestThumbnailProvider()
    authenticity_summary = ", ".join(sorted(authenticity_found)) or "NOT_APPLICABLE"
    spec = active_provider.generate_spec(working_title, premise, hedge_required, authenticity_summary)
    generation_strategy = f"{active_provider.label} — {PLACEHOLDER_NOTE}"

    result = ThumbnailResult(
        content_id=content_id, production_id=production_id, thumbnail_id=thumbnail_id,
        filename=filename, spec=spec, claim_theme_relationship=claim_theme_relationship,
        authenticity_considerations=authenticity_considerations, generation_strategy=generation_strategy,
        thumbnail_content_hash=thumbnail_content_hash, thumbnail_status="GENERATED",
        reasons=["generated thumbnail spec"],
    )

    if apply:
        _apply_result(root, content_id, result, working_title, production_text)

    return result


def _apply_result(
    root: Path, content_id: str, result: ThumbnailResult, working_title: str, production_text: str
) -> None:
    thumbnail_text = render_thumbnail_markdown(result, content_id)
    thumbnail_path = mutate.write_thumbnail_file(root, result.filename, thumbnail_text)

    updated_production = mutate.apply_production_thumbnail(
        production_text, thumbnail_reference=f"thumbnail/{result.filename}",
        status="GENERATED", working_title=working_title, new_production_status=NEXT_PRODUCTION_STATUS,
    )
    production_path = root / "PRODUCTION.md"
    production_path.write_text(updated_production, encoding="utf-8")

    result.thumbnail_path = str(thumbnail_path)
    result.production_path = str(production_path)
