"""Stage adapters for the eight production agents. Each adapter wires an
existing agent's own real entry point directly — no reimplementation of
any agent's algorithm, hashing, or write path. See CONTRACT.md's "Stage
adapters".
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ...assembler.src.pipeline import run_video_assembly
from ...assets.src.pipeline import run_asset_generation
from ...captions.src.pipeline import run_caption_generation
from ...producer.src.pipeline import run_producer
from ...production_qa.src.pipeline import run_production_qa
from ...thumbnail.src.pipeline import run_thumbnail_generation
from ...visual_planner.src.pipeline import run_visual_planner
from ...voice.src.pipeline import run_voice_generation
from .models import (
    ASSEMBLER,
    ASSETS,
    CAPTIONS,
    PRODUCER,
    PRODUCTION_QA,
    THUMBNAIL,
    VISUAL_PLANNER,
    VOICE,
)


@dataclass
class ProductionStageAdapter:
    stage: str
    run: Callable[[Path, bool], Any]
    normalize: Callable[[Any, bool], tuple]  # (raw result, apply) -> (outcome, reasons, produced, stale)


def normalize_standard_result(result: Any, apply: bool) -> tuple[str, list[str], bool, bool]:
    """Reads the one shared result shape every production agent except
    agents/production_qa/ uses (aborted/blocked/stale/already_up_to_date/
    a produced-or-planned success property/reasons) — generic, reused for
    all seven of those agents rather than duplicated per agent.

    `apply` matters because every production agent's own `produced`/
    `planned` property is only ever True once `apply=True` actually wrote
    something (see e.g. agents/producer/src/models.py's `produced`
    property) — a dry run that would have succeeded still reports
    `produced=False` by design. Without knowing `apply`, a genuine dry-run
    PASS would be indistinguishable from "nothing happened" and get
    mislabeled SYSTEM_ERROR.
    """
    if getattr(result, "aborted", False):
        return "SYSTEM_ERROR", [getattr(result, "abort_reason", "aborted")], False, False
    if getattr(result, "blocked", False):
        return "BLOCKED", [getattr(result, "blocked_reason", "blocked")], False, False
    stale = bool(getattr(result, "stale", False))
    if stale:
        return "BLOCKED", [getattr(result, "stale_reason", "stale")], False, True
    if getattr(result, "already_up_to_date", False):
        return "PASS", list(getattr(result, "reasons", [])), False, False
    produced = bool(getattr(result, "produced", False) or getattr(result, "planned", False))
    if produced:
        return "PASS", list(getattr(result, "reasons", [])), True, False
    if not apply:
        # A dry run cleared every failure/staleness check above but never
        # writes, so `produced` is expected to be False — a genuine PASS.
        return "PASS", list(getattr(result, "reasons", [])), False, False
    return (
        "SYSTEM_ERROR",
        [f"{type(result).__name__} returned an unrecognized result shape (apply=True but nothing produced)"],
        False,
        False,
    )


def normalize_qa_result(result: Any, apply: bool) -> tuple[str, list[str], bool, bool]:
    """agents/production_qa/'s result is verdict-shaped
    (PASS/REVISION_REQUIRED/BLOCKED/SYSTEM_ERROR) rather than the shared
    aborted/blocked/stale shape — see agents/production_qa/src/models.py.
    """
    if getattr(result, "aborted", False):
        return "SYSTEM_ERROR", [getattr(result, "abort_reason", "aborted")], False, False
    verdict = getattr(result, "verdict", "SYSTEM_ERROR")
    produced = bool(getattr(result, "produced", False))
    if verdict == "SYSTEM_ERROR":
        return "SYSTEM_ERROR", list(getattr(result, "reasons", [])), produced, False
    if verdict == "BLOCKED":
        reason = getattr(result, "blocked_reason", "") or "; ".join(getattr(result, "reasons", []))
        stale = "stale" in reason.lower()
        return "BLOCKED", [reason], produced, stale
    if verdict == "REVISION_REQUIRED":
        return "REVISION_REQUIRED", list(getattr(result, "reasons", [])), produced, False
    return "PASS", list(getattr(result, "reasons", [])), produced, False


def build_production_adapters() -> list[ProductionStageAdapter]:
    """The eight production-stage adapters, in the real, verified
    precondition order (PRODUCER -> VOICE -> VISUAL_PLANNER -> ASSETS ->
    ASSEMBLER -> CAPTIONS -> THUMBNAIL -> PRODUCTION_QA) — see
    CONTRACT.md's "Stage ordering" for why this differs from a literal
    reading of the task brief.
    """
    return [
        ProductionStageAdapter(
            stage=PRODUCER,
            run=lambda root, apply: run_producer(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=VOICE,
            run=lambda root, apply: run_voice_generation(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=VISUAL_PLANNER,
            run=lambda root, apply: run_visual_planner(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=ASSETS,
            run=lambda root, apply: run_asset_generation(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=ASSEMBLER,
            run=lambda root, apply: run_video_assembly(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=CAPTIONS,
            run=lambda root, apply: run_caption_generation(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=THUMBNAIL,
            run=lambda root, apply: run_thumbnail_generation(root, apply=apply),
            normalize=normalize_standard_result,
        ),
        ProductionStageAdapter(
            stage=PRODUCTION_QA,
            run=lambda root, apply: run_production_qa(root, apply=apply),
            normalize=normalize_qa_result,
        ),
    ]
