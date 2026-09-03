"""Top-level orchestration for the Production QA agent:
run_production_qa() is the one entry point. Same dry-run-by-default /
apply-opt-in shape as every other production agent. See CONTRACT.md's
Preconditions, "Checks (per area)", and "Verdict states".
"""
from __future__ import annotations

from pathlib import Path

from ...assets.src.hashing import compute_asset_content_hash
from ...assets.src.scene_reader import load_scene_visual_records
from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_claims, load_content_item
from . import checks as check_fns
from . import mutate
from .models import ProductionQAResult
from .qa_writer import render_production_qa_markdown

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"
NEXT_PRODUCTION_STATUS = "HUMAN_REVIEW"
ALLOWED_PRODUCTION_STATUSES = {"METADATA", NEXT_PRODUCTION_STATUS}


def run_production_qa(root: Path, apply: bool = False) -> ProductionQAResult:
    def _empty(**overrides) -> ProductionQAResult:
        base = dict(
            content_id="", production_id="", qa_id="", filename="", verdict="BLOCKED",
            checks=[], reasons=[],
        )
        base.update(overrides)
        return ProductionQAResult(**base)

    try:
        content_item_path = root / "CONTENT_ITEM.md"
        if not content_item_path.is_file():
            return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")
        content_item = load_content_item(content_item_path)

        if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
            return _empty(
                content_id=content_item.content_id, blocked=True,
                blocked_reason=(
                    f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                    f"{REQUIRED_CONTENT_ITEM_STATUS!r} — refusing to run production QA"
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
                    f"agents/production_qa/CONTRACT.md's Preconditions require {sorted(ALLOWED_PRODUCTION_STATUSES)}"
                ),
            )

        script_path = root / "SCRIPT.md"
        if not script_path.is_file():
            return _empty(
                content_id=content_item.content_id, production_id=production_id, aborted=True,
                abort_reason=f"no valid current SCRIPT.md under {root}",
            )
        current_script_hash = compute_script_content_hash(script_path.read_text(encoding="utf-8"))

        # Staleness is a hard BLOCKED gate, not a soft check: a production
        # QA pass evaluated against outdated inputs can't be trusted at
        # all, the same reasoning agents/assembler/'s, agents/captions/'s,
        # and agents/thumbnail/'s own precondition gates already use.
        stored_production_hash = parsing.strip_single_backticks(
            production_table.get("Script content hash", "")
        )
        if stored_production_hash != current_script_hash:
            return _empty(
                content_id=content_item.content_id, production_id=production_id, blocked=True,
                blocked_reason=(
                    f"SCRIPT.md changed since PRODUCTION.md was created (stored "
                    f"{stored_production_hash!r}, current {current_script_hash!r}) — production "
                    "plan is stale; refusing to run QA against outdated inputs"
                ),
            )

        scenes = load_scene_visual_records(root / "scenes")
        if not scenes:
            return _empty(
                content_id=content_item.content_id, production_id=production_id, aborted=True,
                abort_reason=f"no scenes/scene-*.md under {root}",
            )

        claims = load_claims(root / "claims")

        required_files = {
            "voice/voice-01.md": root / "voice" / "voice-01.md",
            "timeline/timeline-01.md": root / "timeline" / "timeline-01.md",
            "captions/captions-01.md": root / "captions" / "captions-01.md",
            "thumbnail/thumbnail-01.md": root / "thumbnail" / "thumbnail-01.md",
        }
        missing_artifacts = [name for name, path in required_files.items() if not path.is_file()]
        if missing_artifacts:
            return _empty(
                content_id=content_item.content_id, production_id=production_id, blocked=True,
                blocked_reason=f"required artifacts missing, nothing to check: {missing_artifacts}",
            )

        voice_identity = parsing.parse_table(
            (root / "voice" / "voice-01.md").read_text(encoding="utf-8")
        )
        voice_script_hash = parsing.strip_single_backticks(
            voice_identity.get("Script content hash", "")
        )
        if voice_script_hash != current_script_hash:
            return _empty(
                content_id=content_item.content_id, production_id=production_id, blocked=True,
                blocked_reason=(
                    f"voice/voice-01.md's Script content hash {voice_script_hash!r} does not "
                    f"match the current script hash {current_script_hash!r} — voice track is "
                    "stale; refusing to run QA against an outdated voice record"
                ),
            )

        for scene in scenes:
            asset_path = root / "assets" / f"asset-{scene.order:02d}.md"
            if not asset_path.is_file():
                continue  # a missing asset is a REVISION_REQUIRED-level check failure, not BLOCKED
            asset_identity = parsing.parse_table(asset_path.read_text(encoding="utf-8"))
            if "Scene/visual content hash" not in asset_identity:
                continue  # likewise handled as a check failure
            stored_asset_hash = parsing.strip_single_backticks(
                asset_identity["Scene/visual content hash"]
            )
            current_asset_hash = compute_asset_content_hash(scene)
            if stored_asset_hash != current_asset_hash:
                return _empty(
                    content_id=content_item.content_id, production_id=production_id, blocked=True,
                    blocked_reason=(
                        f"assets/asset-{scene.order:02d}.md is stale relative to {scene.filename} "
                        f"(stored hash {stored_asset_hash!r}, current {current_asset_hash!r}) — "
                        "refusing to run QA against an outdated asset"
                    ),
                )

        content_pillar = content_item.content_pillar
        identity = parsing.parse_table(content_item.raw_text)
        working_title = (
            parsing.strip_single_backticks(identity.get("Working title", ""))
            or identity.get("Working title", "")
        )

        authenticity_found: set[str] = set()
        for scene in scenes:
            asset_path = root / "assets" / f"asset-{scene.order:02d}.md"
            if asset_path.is_file():
                asset_sections = parsing.parse_sections(asset_path.read_text(encoding="utf-8"))
                auth_table = parsing.parse_table(
                    asset_sections.get("Historical authenticity classification", "")
                )
                classification = parsing.first_backtick_token(auth_table.get("Classification", ""))
                if classification:
                    authenticity_found.add(classification)

        all_checks = []
        all_checks += check_fns.check_content(content_item, production_table, current_script_hash, scenes, claims)
        all_checks += check_fns.check_voice(root, current_script_hash)
        all_checks += check_fns.check_assets(root, scenes)
        all_checks += check_fns.check_timeline(root)
        all_checks += check_fns.check_captions(root, scenes)
        all_checks += check_fns.check_thumbnail(root, content_pillar, working_title, authenticity_found)
        all_checks += check_fns.check_output(root, production_text)

        failed = [c for c in all_checks if not c.passed]
        verdict = "PASS" if not failed else "REVISION_REQUIRED"
        reasons = [f"{c.area}: {c.check} — {c.note}" for c in failed]

        content_id = content_item.content_id
        qa_id = f"{content_id}-production-qa-01"
        filename = "production-qa-01.md"

        result = ProductionQAResult(
            content_id=content_id, production_id=production_id, qa_id=qa_id, filename=filename,
            verdict=verdict, checks=all_checks, reasons=reasons,
        )

        if apply:
            _apply_result(root, content_id, result, production_text)

        return result
    except Exception as exc:  # noqa: BLE001 — SYSTEM_ERROR must never crash the caller
        return _empty(verdict="SYSTEM_ERROR", reasons=[f"unexpected error during QA evaluation: {exc!r}"])


def _apply_result(root: Path, content_id: str, result: ProductionQAResult, production_text: str) -> None:
    qa_text = render_production_qa_markdown(result, content_id)
    qa_path = mutate.write_qa_file(root, result.filename, qa_text)

    notes = (
        "All checks passed."
        if result.verdict == "PASS"
        else f"{len(result.failed_checks)} check(s) failed — see Reasons."
    )
    new_status = NEXT_PRODUCTION_STATUS if result.verdict == "PASS" else None
    updated_production = mutate.apply_production_qa_state(production_text, result.verdict, notes, new_status)
    production_path = root / "PRODUCTION.md"
    production_path.write_text(updated_production, encoding="utf-8")

    result.qa_path = str(qa_path)
    result.production_path = str(production_path)
