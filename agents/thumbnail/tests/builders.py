"""Builds isolated, thumbnail-ready fixtures for Thumbnail tests by
reusing the real Producer -> Voice -> Visual Planner -> Assets ->
Assembler -> Captions pipeline. Never touches the real golden sample or
any committed fixture.
"""
from __future__ import annotations

from pathlib import Path

from ...captions.src.pipeline import run_caption_generation
from ...captions.tests.builders import build_captions_ready_item
from ...producer.tests.builders import write_claim  # re-exported for test convenience


def build_thumbnail_ready_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Producer -> Voice -> Visual Planner -> Assets -> Assembler ->
    Captions, all apply=True — leaving PRODUCTION.md (status THUMBNAIL)
    ready for agents/thumbnail/ to consume.
    """
    build_captions_ready_item(root, content_id=content_id, extra_claims=extra_claims, **kwargs)
    captions_result = run_caption_generation(root, apply=True)
    if not captions_result.produced:
        raise AssertionError(f"fixture setup failed to generate captions: {captions_result}")
