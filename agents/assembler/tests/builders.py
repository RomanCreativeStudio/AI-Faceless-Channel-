"""Builds isolated, assembly-ready fixtures for Assembler tests by
reusing agents/producer's, agents/voice's, agents/visual_planner's, and
agents/assets's own real pipelines — never hand-rolling PRODUCTION.md/
scene/voice/asset files. Never touches the real golden sample or any
committed fixture.
"""
from __future__ import annotations

from pathlib import Path

from ...assets.src.pipeline import run_asset_generation
from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item as build_producer_item
from ...producer.tests.builders import write_claim  # re-exported for test convenience
from ...visual_planner.src.pipeline import run_visual_planner
from ...voice.src.pipeline import run_voice_generation


def build_assembly_ready_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Producer -> Voice -> Visual Planner -> Assets, all apply=True, in
    the canonical production-lifecycle order — leaving PRODUCTION.md
    (status ASSEMBLY) ready for agents/assembler/ to consume.
    """
    build_producer_item(root, content_id=content_id, **kwargs)
    for short_id, classification in extra_claims or []:
        write_claim(root, short_id, content_id=content_id, classification=classification)

    producer_result = run_producer(root, apply=True)
    if not producer_result.produced:
        raise AssertionError(f"fixture setup failed to produce a plan: {producer_result}")

    voice_result = run_voice_generation(root, apply=True)
    if not voice_result.produced:
        raise AssertionError(f"fixture setup failed to generate voice: {voice_result}")

    planner_result = run_visual_planner(root, apply=True)
    if not planner_result.planned:
        raise AssertionError(f"fixture setup failed to plan visuals: {planner_result}")

    asset_result = run_asset_generation(root, apply=True)
    if not asset_result.produced:
        raise AssertionError(f"fixture setup failed to generate assets: {asset_result}")
