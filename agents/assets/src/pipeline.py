"""Top-level orchestration for the Asset agent: run_asset_generation() is
the one entry point. Same dry-run-by-default / apply-opt-in shape as
agents/producer/src/pipeline.py, agents/voice/src/pipeline.py, and
agents/visual_planner/src/pipeline.py.

See CONTRACT.md's Preconditions, "Relationship to agents/visual_planner/"
(how an existing Visual-Planner-created assets/asset-<n>.md skeleton is
completed rather than conflicted with), and "Re-running / staleness".
"""
from __future__ import annotations

from pathlib import Path

from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_claims, load_content_item
from . import mutate
from .asset_writer import render_asset_markdown
from .classification import classify_authenticity, default_strategy_for
from .hashing import compute_asset_content_hash
from .models import (
    AssetGenerationResult,
    AssetPlan,
    AssetStrategy,
    HistoricalAuthenticity,
    SceneVisualRecord,
)
from .provider import AssetRetrievalProvider, GeneratedAssetProvider
from .qa import evaluate_asset_qa
from .scene_reader import load_scene_visual_records
from .test_providers import LocalTestAssetRetrievalProvider, LocalTestGeneratedAssetProvider

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"
NEXT_PRODUCTION_STATUS = "ASSEMBLY"
ALLOWED_PRODUCTION_STATUSES = {"ASSET_COLLECTION", NEXT_PRODUCTION_STATUS}


def run_asset_generation(
    root: Path,
    apply: bool = False,
    generated_provider: GeneratedAssetProvider | None = None,
    retrieval_provider: AssetRetrievalProvider | None = None,
    human_provided: dict[str, dict] | None = None,
) -> AssetGenerationResult:
    """`human_provided` maps a scene's filename ("scene-02.md") to a dict
    optionally carrying a "source" key. A scene's presence as a key in
    this dict opts it into the HUMAN_PROVIDED strategy — never the
    deterministic default; see CONTRACT.md's "Asset strategies".
    """
    human_provided = human_provided or {}

    def _empty(**overrides) -> AssetGenerationResult:
        base = dict(content_id="", production_id="", plans=[], reasons=[])
        base.update(overrides)
        return AssetGenerationResult(**base)

    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
        return _empty(
            content_id=content_item.content_id,
            blocked=True,
            blocked_reason=(
                f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                f"{REQUIRED_CONTENT_ITEM_STATUS!r} — agents/assets/CONTRACT.md's "
                "Preconditions require full human approval before any asset may be "
                "created; refusing to generate"
            ),
        )

    production_path = root / "PRODUCTION.md"
    if not production_path.is_file():
        return _empty(
            content_id=content_item.content_id,
            aborted=True, abort_reason=f"no PRODUCTION.md under {root}",
        )
    production_text = production_path.read_text(encoding="utf-8")
    production_table = parsing.parse_table(production_text)
    production_id = parsing.strip_single_backticks(production_table.get("Production ID", ""))
    production_status = parsing.strip_single_backticks(production_table.get("Production status", ""))

    if production_status not in ALLOWED_PRODUCTION_STATUSES:
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            blocked=True,
            blocked_reason=(
                f"PRODUCTION.md Production status is {production_status!r} — "
                "agents/assets/CONTRACT.md's Preconditions require "
                f"{sorted(ALLOWED_PRODUCTION_STATUSES)}"
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
            content_id=content_item.content_id, production_id=production_id,
            blocked=True,
            blocked_reason=(
                f"SCRIPT.md has changed since PRODUCTION.md was created (stored hash "
                f"{stored_production_hash!r}, current hash {current_script_hash!r}) — "
                "the production plan is stale; refusing to build assets from outdated "
                "scenes. Re-run agents/producer/ (and agents/visual_planner/) first."
            ),
        )

    scenes = load_scene_visual_records(root / "scenes")
    if not scenes:
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
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
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            blocked=True,
            blocked_reason=(
                "missing claim provenance — cannot build an asset without a "
                f"claims/*.md file: {detail}. Refusing to invent a claim."
            ),
        )

    active_generated_provider = generated_provider or LocalTestGeneratedAssetProvider()
    active_retrieval_provider = retrieval_provider or LocalTestAssetRetrievalProvider()
    known_claim_ids = set(claims.keys())

    plans: list[AssetPlan] = []
    stale_filenames: list[str] = []
    already_up_to_date_filenames: list[str] = []

    for scene in scenes:
        filename = f"asset-{scene.order:02d}.md"
        asset_path = root / "assets" / filename
        content_hash = compute_asset_content_hash(scene)

        authenticity_override: HistoricalAuthenticity | None = None

        if asset_path.is_file():
            existing_text = asset_path.read_text(encoding="utf-8")
            existing_identity = parsing.parse_table(existing_text)

            if "Scene/visual content hash" in existing_identity:
                existing_hash = parsing.strip_single_backticks(
                    existing_identity["Scene/visual content hash"]
                )
                if not existing_hash or existing_hash == "N/A":
                    return _empty(
                        content_id=content_item.content_id, production_id=production_id,
                        aborted=True,
                        abort_reason=(
                            f"existing {asset_path} is malformed (Scene/visual content "
                            "hash field present but empty) — cannot safely determine staleness"
                        ),
                    )
                if existing_hash == content_hash:
                    already_up_to_date_filenames.append(filename)
                    continue
                stale_filenames.append(filename)
                continue

            # A Visual-Planner-only skeleton (no Scene/visual content hash
            # recorded yet) — read forward its authenticity classification
            # only; see CONTRACT.md's "Relationship to agents/visual_planner/".
            existing_sections = parsing.parse_sections(existing_text)
            existing_auth_table = parsing.parse_table(
                existing_sections.get("Historical authenticity classification", "")
            )
            classification_raw = parsing.first_backtick_token(
                existing_auth_table.get("Classification", "")
            )
            try:
                authenticity_override = HistoricalAuthenticity(classification_raw)
            except ValueError:
                authenticity_override = None

        if authenticity_override is not None:
            authenticity = authenticity_override
            basis = (
                f"Historical authenticity classification preserved verbatim from "
                f"agents/visual_planner/'s existing assets/{filename} — see "
                "CONTRACT.md's 'Relationship to agents/visual_planner/'."
            )
        else:
            authenticity, basis = classify_authenticity(scene, claims)

        scene_human_provided = human_provided.get(scene.filename)
        strategy = (
            AssetStrategy.HUMAN_PROVIDED
            if scene_human_provided is not None
            else default_strategy_for(authenticity)
        )

        plans.append(
            _build_plan(
                scene, filename, content_hash, authenticity, basis, strategy,
                scene_human_provided, active_generated_provider, active_retrieval_provider,
            )
        )

    qa_reasons: dict[str, list[str]] = {}
    qa_passed_overall = True
    for plan in plans:
        passed, plan_reasons = evaluate_asset_qa(plan, known_claim_ids)
        if plan_reasons:
            qa_reasons[plan.filename] = plan_reasons
        if not passed:
            qa_passed_overall = False

    reasons: list[str] = []
    if plans:
        reasons.append(f"built {len(plans)} asset plan(s)")
    if already_up_to_date_filenames:
        reasons.append(f"already up to date: {already_up_to_date_filenames}")
    if stale_filenames:
        reasons.append(f"stale (scene changed since last generation): {stale_filenames}")

    result = AssetGenerationResult(
        content_id=content_item.content_id, production_id=production_id,
        plans=plans, reasons=reasons,
        stale_filenames=stale_filenames, already_up_to_date_filenames=already_up_to_date_filenames,
        qa_passed=qa_passed_overall, qa_reasons=qa_reasons,
    )

    if apply and plans:
        _apply_result(
            root, content_item.content_id, plans, production_text,
            len(scenes), stale_filenames, already_up_to_date_filenames, result,
        )

    return result


def _truncate_prompt(text: str, max_chars: int = 220) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated


def _build_plan(
    scene: SceneVisualRecord,
    filename: str,
    content_hash: str,
    authenticity: HistoricalAuthenticity,
    basis: str,
    strategy: AssetStrategy,
    human_provided_info: dict | None,
    generated_provider: GeneratedAssetProvider,
    retrieval_provider: AssetRetrievalProvider,
) -> AssetPlan:
    asset_id = f"{scene.content_id}-{filename[:-3]}"
    asset_type = "GRAPHIC" if authenticity is HistoricalAuthenticity.NOT_APPLICABLE else "IMAGE"
    # Phase 8: agents/visual_planner/'s own visual_description is a fixed
    # boilerplate string per authenticity bucket (never scene-specific —
    # see its classification.py), which only mattered when GENERATED
    # meant "write a labeled placeholder" and RETRIEVED meant
    # "RETRIEVAL_NOT_IMPLEMENTED" regardless of the prompt. Now that a
    # real provider can act on this prompt, the scene's own narration
    # (always scene-specific, and the only text this codebase already
    # treats as this scene's real content — see templates/SCENE.md) is
    # unconditionally the better source; never cross-imports
    # visual_planner's own module or its exact boilerplate strings, so
    # this keeps working even if that module's wording changes.
    visual_prompt = (
        _truncate_prompt(scene.narration_text) or scene.visual_description
        or scene.visual_type or "N/A"
    )

    if strategy is AssetStrategy.GENERATED:
        generated = generated_provider.generate(visual_prompt, asset_type)
        verification_notes = (
            "Not yet verified — a placeholder generated asset, not real media."
            if generated.artifact_bytes is None
            else (
                "Not yet verified — a real, deterministically-rendered illustration "
                "(never photorealistic, always labeled GENERATED_RECONSTRUCTION both "
                "in this record and burned into the image itself); a human must still "
                "confirm it's appropriate for this scene before use."
            )
        )
        return AssetPlan(
            scene=scene, asset_id=asset_id, filename=filename, asset_type=asset_type,
            strategy=strategy, authenticity=authenticity, basis=basis,
            source=f"generated by {generated.provider_label}",
            source_url="N/A",
            generation_prompt=visual_prompt,
            generation_status="GENERATED",
            verification_status="NOT_STARTED",
            verification_notes=verification_notes,
            content_hash=content_hash,
            artifact_filename=f"{filename[:-3]}.{generated.artifact_extension}",
            artifact_content=generated.artifact_content,
            artifact_bytes=generated.artifact_bytes,
        )

    if strategy is AssetStrategy.RETRIEVED:
        retrieval = retrieval_provider.retrieve(visual_prompt, asset_type)
        if retrieval.status == "RETRIEVED" and retrieval.artifact_bytes is not None:
            retrieved_filename = f"{filename[:-3]}.retrieved.{retrieval.artifact_extension}"
            return AssetPlan(
                scene=scene, asset_id=asset_id, filename=filename, asset_type=asset_type,
                strategy=strategy, authenticity=authenticity, basis=basis,
                source=retrieval.source_reference, source_url=retrieval.source_url,
                generation_prompt="N/A",
                generation_status="RETRIEVED",
                verification_status="NOT_STARTED",
                verification_notes=(
                    f"Retrieved from {retrieval.provider_label}; license as reported by the "
                    f"source: {retrieval.license_text!r}. Not yet human-verified — a real "
                    "retrieval having succeeded is never itself a claim of editorial "
                    "appropriateness or license correctness."
                ),
                content_hash=content_hash,
                licensing_status=retrieval.licensing_status,
                license_notes=f"As reported by {retrieval.provider_label}: {retrieval.license_text}",
                retrieved_artifact_filename=retrieved_filename,
                retrieved_artifact_bytes=retrieval.artifact_bytes,
            )
        # RETRIEVAL_NOT_IMPLEMENTED (no real provider configured) or
        # RETRIEVAL_FAILED (a real provider tried and found nothing
        # usable) — either way, never fabricate a source or pretend a
        # retrieval happened.
        return AssetPlan(
            scene=scene, asset_id=asset_id, filename=filename, asset_type=asset_type,
            strategy=strategy, authenticity=authenticity, basis=basis,
            source=retrieval.source_reference,
            source_url=retrieval.source_url,
            generation_prompt="N/A",
            generation_status="NOT_STARTED",
            verification_status="NOT_STARTED",
            verification_notes=retrieval.requirement_note,
            content_hash=content_hash,
        )

    # HUMAN_PROVIDED
    source = (human_provided_info or {}).get("source", "")
    has_source = bool(source) and source.strip().lower() not in ("", "unknown")
    verification_status = "NOT_STARTED" if has_source else "REVIEW_REQUIRED"
    verification_notes = (
        f"Human-provided source stated: {source}. Not independently verified."
        if has_source
        else (
            "Human-provided asset with no stated source — flagged for required "
            "human review before use; authenticity is never assumed from strategy "
            "or filename alone (see CONTRACT.md)."
        )
    )
    return AssetPlan(
        scene=scene, asset_id=asset_id, filename=filename, asset_type=asset_type,
        strategy=strategy, authenticity=authenticity, basis=basis,
        source=source or "unknown",
        source_url="N/A",
        generation_prompt="N/A",
        generation_status="HUMAN_PROVIDED",
        verification_status=verification_status,
        verification_notes=verification_notes,
        content_hash=content_hash,
    )


def _apply_result(
    root: Path,
    content_id: str,
    plans: list[AssetPlan],
    production_text: str,
    total_scenes: int,
    stale_filenames: list[str],
    already_up_to_date_filenames: list[str],
    result: AssetGenerationResult,
) -> None:
    for plan in plans:
        if plan.strategy is AssetStrategy.GENERATED and plan.artifact_filename:
            if plan.artifact_bytes is not None:
                artifact_path = mutate.write_generated_artifact_binary(
                    root, plan.artifact_filename, plan.artifact_bytes
                )
            else:
                artifact_path = mutate.write_generated_artifact(
                    root, plan.artifact_filename, plan.artifact_content
                )
            result.artifact_paths.append(str(artifact_path))
        if plan.strategy is AssetStrategy.RETRIEVED and plan.retrieved_artifact_filename:
            artifact_path = mutate.write_retrieved_artifact_binary(
                root, plan.retrieved_artifact_filename, plan.retrieved_artifact_bytes
            )
            result.artifact_paths.append(str(artifact_path))
        asset_text = render_asset_markdown(plan, content_id)
        asset_path = mutate.write_asset_file(root, plan.filename, asset_text)
        result.asset_paths.append(str(asset_path))

    covered = len(plans) + len(already_up_to_date_filenames)
    new_status = (
        NEXT_PRODUCTION_STATUS if (not stale_filenames and covered >= total_scenes) else None
    )

    rollup_lines = [
        f"- `assets/{p.filename}`: `{p.strategy.value}` / `{p.authenticity.value}` "
        f"(scene `{p.scene.filename}`)"
        for p in plans
    ]
    rollup_lines += [f"- `assets/{fn}`: already up to date" for fn in already_up_to_date_filenames]
    rollup_lines += [f"- `assets/{fn}`: STALE — scene changed since generation" for fn in stale_filenames]
    rollup_text = "\n".join(rollup_lines) or "No assets recorded yet."

    updated_production = mutate.apply_production_asset_rollup(production_text, rollup_text, new_status)
    production_path = root / "PRODUCTION.md"
    production_path.write_text(updated_production, encoding="utf-8")
    result.production_path = str(production_path)
