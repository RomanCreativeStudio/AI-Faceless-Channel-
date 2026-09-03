"""Builds isolated, asset-collection-ready fixtures for Asset agent tests
by reusing agents/producer's and agents/visual_planner's own
tests/builders.py plus the real run_producer()/run_visual_planner() —
never hand-rolling PRODUCTION.md/scene/asset skeleton files, so these
tests exercise the actual Producer -> Visual Planner -> Assets handoff.
Never touches the real golden sample or any committed fixture.
"""
from __future__ import annotations

from pathlib import Path

from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item as build_producer_item
from ...producer.tests.builders import write_claim  # re-exported for test convenience
from ...visual_planner.src.pipeline import run_visual_planner
from ...voice.src.pipeline import run_voice_generation


def _build_common(root: Path, content_id: str, extra_claims, **kwargs):
    build_producer_item(root, content_id=content_id, **kwargs)
    for short_id, classification in extra_claims or []:
        write_claim(root, short_id, content_id=content_id, classification=classification)
    producer_result = run_producer(root, apply=True)
    if not producer_result.produced:
        raise AssertionError(f"fixture setup failed to produce a plan: {producer_result}")


def build_visual_planned_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Builds an APPROVED content item, runs the real Producer, then the
    real Visual Planner (both apply=True), leaving PRODUCTION.md (status
    ASSET_COLLECTION) + scenes/ + any Visual-Planner-created
    assets/asset-<n>.md skeletons ready for agents/assets/ to consume.
    """
    _build_common(root, content_id, extra_claims, **kwargs)
    planner_result = run_visual_planner(root, apply=True)
    if not planner_result.planned:
        raise AssertionError(f"fixture setup failed to plan visuals: {planner_result}")


def build_full_pipeline_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Same as build_visual_planned_item, but also runs the real Voice
    agent first, in the canonical production-lifecycle order
    (PRODUCTION_PLANNING -> VOICE -> VISUAL_PLANNING -> ASSET_COLLECTION —
    see templates/PRODUCTION.md), so Voice's and the Asset agent's
    outputs can be checked for independence against a fixture where both
    have actually run.
    """
    _build_common(root, content_id, extra_claims, **kwargs)
    voice_result = run_voice_generation(root, apply=True)
    if not voice_result.produced:
        raise AssertionError(f"fixture setup failed to generate voice: {voice_result}")
    planner_result = run_visual_planner(root, apply=True)
    if not planner_result.planned:
        raise AssertionError(f"fixture setup failed to plan visuals: {planner_result}")
