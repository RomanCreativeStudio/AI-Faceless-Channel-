"""Builds isolated, QA-ready fixtures for Production QA tests by reusing
the real Producer -> Voice -> Visual Planner -> Assets -> Assembler ->
Captions -> Thumbnail pipeline. Never touches the real golden sample or
any committed fixture.

`build_passing_item` deliberately avoids any all-FACT scene — see
agents/production_qa/CONTRACT.md's "Known limitation: RETRIEVED
strategy": no real retrieval integration exists this phase, so a
RETRIEVED-strategy asset (the default for an all-FACT scene) can never
pass the "retrieved asset has real retrieval evidence" check. A
genuinely fully-valid ("PASS") fixture therefore uses only hypothetical/
no-claim scenes, which default to the GENERATED strategy instead.
"""
from __future__ import annotations

from pathlib import Path

from ...producer.tests.builders import write_claim  # re-exported for test convenience
from ...thumbnail.src.pipeline import run_thumbnail_generation
from ...thumbnail.tests.builders import build_thumbnail_ready_item


def build_qa_ready_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Producer -> Voice -> Visual Planner -> Assets -> Assembler ->
    Captions -> Thumbnail, all apply=True — leaving PRODUCTION.md (status
    METADATA) ready for agents/production_qa/ to consume.
    """
    build_thumbnail_ready_item(root, content_id=content_id, extra_claims=extra_claims, **kwargs)
    thumbnail_result = run_thumbnail_generation(root, apply=True)
    if not thumbnail_result.produced:
        raise AssertionError(f"fixture setup failed to generate thumbnail: {thumbnail_result}")


def build_passing_item(root: Path, content_id: str = "test-item") -> None:
    """A fixture whose every scene is hypothetical (never all-FACT), so
    it can legitimately reach Verdict = PASS this phase."""
    build_qa_ready_item(
        root,
        content_id=content_id,
        pillar="what-if",
        title="Could Modern Medicine Have Stopped It?",
        beats=["1. A hypothetical beat. — claims: `c4`"],
        extra_claims=[("c4", "ASSUMPTION")],
    )
