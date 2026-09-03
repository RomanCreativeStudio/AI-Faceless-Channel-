"""Builds isolated, production-ready fixtures for Visual Planner tests by
reusing agents/producer's own tests/builders.py plus the real
run_producer() — never hand-rolling PRODUCTION.md/scene files, so these
tests exercise the actual Producer -> Visual Planner handoff rather than a
stand-in for it. Never touches the real golden sample or any committed
fixture.
"""
from __future__ import annotations

from pathlib import Path

from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item as build_producer_item
from ...producer.tests.builders import write_claim  # re-exported for test convenience


def build_produced_item(
    root: Path,
    content_id: str = "test-item",
    extra_claims: list[tuple[str, str]] | None = None,
    **kwargs,
) -> None:
    """Builds an APPROVED content item and runs the real Producer against
    it (apply=True), leaving PRODUCTION.md + scenes/ ready for
    agents/visual_planner/ to consume.

    `extra_claims` is a list of (short_id, classification) pairs written
    *before* the Producer runs — any claim ID a script beat cites must
    already exist on disk, since the Producer itself validates claim
    references and fails safely otherwise (agents/producer/CONTRACT.md).
    """
    build_producer_item(root, content_id=content_id, **kwargs)
    for short_id, classification in extra_claims or []:
        write_claim(root, short_id, content_id=content_id, classification=classification)
    result = run_producer(root, apply=True)
    if not result.produced:
        raise AssertionError(f"fixture setup failed to produce a plan: {result}")
