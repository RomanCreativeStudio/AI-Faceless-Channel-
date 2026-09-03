"""Top-level orchestration for the Visual Planner: run_visual_planner() is
the one entry point. Same dry-run-by-default / apply-opt-in shape as
agents/producer/src/pipeline.py.

Preconditions (CONTRACT.md): `Production status` must be
`VISUAL_PLANNING` or, as an explicitly-labeled Phase 7B interim allowance
(no `agents/voice/` implementation exists yet), `PRODUCTION_PLANNING`.

Defense-in-depth beyond CONTRACT.md's literal text: that interim
allowance means `Production status` alone can't tell a real, approved
production apart from a hand-built schema-validation fixture whose
`PRODUCTION.md` happens to carry a matching status/hash (exactly the
situation of the Phase 7A golden `PRODUCTION.md` fixture, whose
`CONTENT_ITEM.md` status is `SCRIPT`, never `APPROVED`). So this also
checks `CONTENT_ITEM.md`'s own `status` when the file is present,
mirroring agents/producer/CONTRACT.md's own gate, rather than relying on
the interim allowance alone to keep `--apply` from ever mutating
non-approved (including golden-sample) content.

Reuses agents/producer/src.hashing.compute_script_content_hash directly to
re-verify SCRIPT.md hasn't changed since the Producer ran — never
duplicates that hashing logic.
"""
from __future__ import annotations

from pathlib import Path

from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_claims, load_content_item
from . import mutate
from .asset_writer import render_asset_markdown
from .classification import classify_scene
from .loader import load_scenes
from .models import VisualPlanningResult

ALLOWED_STATUSES = {"VISUAL_PLANNING", "PRODUCTION_PLANNING"}
REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"


def run_visual_planner(root: Path, apply: bool = False) -> VisualPlanningResult:
    production_path = root / "PRODUCTION.md"
    if not production_path.is_file():
        return VisualPlanningResult(
            content_id="", production_id="", plans=[], reasons=[],
            aborted=True, abort_reason=f"no PRODUCTION.md under {root}",
        )

    production_text = production_path.read_text(encoding="utf-8")
    production_table = parsing.parse_table(production_text)
    content_id = parsing.strip_single_backticks(production_table.get("Content ID", ""))
    production_id = parsing.strip_single_backticks(production_table.get("Production ID", ""))
    status = parsing.strip_single_backticks(production_table.get("Production status", ""))

    content_item_path = root / "CONTENT_ITEM.md"
    if content_item_path.is_file():
        content_item_status = load_content_item(content_item_path).status
        if content_item_status != REQUIRED_CONTENT_ITEM_STATUS:
            return VisualPlanningResult(
                content_id=content_id, production_id=production_id, plans=[], reasons=[],
                blocked=True,
                blocked_reason=(
                    f"CONTENT_ITEM.md status is {content_item_status!r}, not "
                    f"{REQUIRED_CONTENT_ITEM_STATUS!r} — a PRODUCTION.md's own status "
                    "can't substitute for content approval (defense-in-depth beyond "
                    "CONTRACT.md's literal Preconditions, closing the gap the Phase 7B "
                    "interim allowance would otherwise leave open)"
                ),
            )

    if status not in ALLOWED_STATUSES:
        return VisualPlanningResult(
            content_id=content_id, production_id=production_id, plans=[], reasons=[],
            blocked=True,
            blocked_reason=(
                f"PRODUCTION.md Production status is {status!r} — "
                "agents/visual_planner/CONTRACT.md's Preconditions require "
                f"{sorted(ALLOWED_STATUSES)} (VISUAL_PLANNING, or the Phase 7B "
                "interim allowance PRODUCTION_PLANNING)"
            ),
        )

    script_path = root / "SCRIPT.md"
    if script_path.is_file():
        current_hash = compute_script_content_hash(script_path.read_text(encoding="utf-8"))
        stored_hash = parsing.strip_single_backticks(production_table.get("Script content hash", ""))
        if stored_hash and current_hash != stored_hash:
            return VisualPlanningResult(
                content_id=content_id, production_id=production_id, plans=[], reasons=[],
                blocked=True,
                blocked_reason=(
                    f"SCRIPT.md has changed since PRODUCTION.md was created (stored hash "
                    f"{stored_hash!r}, current hash {current_hash!r}) — the production plan "
                    "is stale; refusing to plan visuals from outdated scenes. Re-run "
                    "agents/producer/ first."
                ),
            )

    scenes = load_scenes(root / "scenes")
    if not scenes:
        return VisualPlanningResult(
            content_id=content_id, production_id=production_id, plans=[], reasons=[],
            aborted=True, abort_reason=f"no scenes/scene-*.md under {root}",
        )

    claims = load_claims(root / "claims")
    missing = [
        (scene.filename, cid)
        for scene in scenes
        for cid in scene.claim_ids
        if cid not in claims
    ]
    if missing:
        detail = "; ".join(f"{fn} cites {cid!r}" for fn, cid in missing)
        return VisualPlanningResult(
            content_id=content_id, production_id=production_id, plans=[], reasons=[],
            blocked=True,
            blocked_reason=(
                "missing claim provenance — cannot classify a scene's visual "
                f"authenticity without a claims/*.md file: {detail}. Revision required "
                "before visual planning can proceed."
            ),
        )

    plans = [classify_scene(scene, claims) for scene in scenes]
    for plan in plans:
        if plan.needs_asset:
            plan.asset_filename = f"asset-{plan.scene.order:02d}.md"

    result = VisualPlanningResult(
        content_id=content_id, production_id=production_id, plans=plans,
        reasons=[f"planned visuals for {len(plans)} scene(s)"],
    )

    if apply:
        _apply_result(root, content_id, plans, production_text)
        result.production_path = str(production_path)
        result.scene_paths = [str(p.scene.path) for p in plans]
        result.asset_paths = [
            str(root / "assets" / p.asset_filename) for p in plans if p.needs_asset
        ]

    return result


def _apply_result(root: Path, content_id: str, plans, production_text: str) -> None:
    for plan in plans:
        updated_scene_text = mutate.apply_scene_visual_fields(plan)
        mutate.write_scene_file(plan.scene.path, updated_scene_text)
        if plan.needs_asset:
            asset_text = render_asset_markdown(plan, content_id)
            mutate.write_asset_file(root, plan.asset_filename, asset_text)

    visual_rollup = "\n".join(
        f"- `{p.scene.filename}`: `{p.visual_type}` — {p.visual_description}" for p in plans
    )
    asset_rollup = (
        ", ".join(f"`assets/{p.asset_filename}`" for p in plans if p.needs_asset)
        or "none — no scene in this production needs a discrete asset record"
    )
    updated_production = mutate.apply_production_rollups(
        production_text, visual_rollup, asset_rollup, new_status="ASSET_COLLECTION"
    )
    (root / "PRODUCTION.md").write_text(updated_production, encoding="utf-8")
