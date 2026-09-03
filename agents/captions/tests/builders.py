"""Builds isolated, captions-ready fixtures for Captions tests by reusing
agents/producer's, agents/voice's, agents/visual_planner's, and
agents/assets's real pipelines plus the real agents/assembler — never
hand-rolling PRODUCTION.md/scene files. Never touches the real golden
sample or any committed fixture.
"""
from __future__ import annotations

from pathlib import Path

from ...assembler.src.pipeline import run_video_assembly
from ...assembler.tests.builders import build_assembly_ready_item
from ...producer.tests.builders import write_claim  # re-exported for test convenience


def build_captions_ready_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Producer -> Voice -> Visual Planner -> Assets -> Assembler, all
    apply=True — leaving PRODUCTION.md (status CAPTIONS) ready for
    agents/captions/ to consume.
    """
    build_assembly_ready_item(root, content_id=content_id, extra_claims=extra_claims, **kwargs)
    assembly_result = run_video_assembly(root, apply=True)
    if not assembly_result.produced:
        raise AssertionError(f"fixture setup failed to assemble: {assembly_result}")
