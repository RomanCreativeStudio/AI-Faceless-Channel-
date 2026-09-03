"""Builds isolated, full-pipeline-ready fixtures by reusing existing test
infrastructure from agents/orchestrator/tests/ and agents/safety/tests/ —
never touches the real golden sample or any committed fixture; every
caller passes a fresh tempfile directory (see test files' setUp).
"""
from __future__ import annotations

from pathlib import Path

from ...orchestrator.tests.builders import (
    write_claim,
    write_content_item,
    write_research,
    write_script,
)

APPROVED_MARKER = "Current status: `SCRIPT`"
APPROVED_REPLACEMENT = "Current status: `APPROVED`"


def simulate_human_approval(root: Path) -> None:
    """Flips CONTENT_ITEM.md's status from SCRIPT to APPROVED — the one
    action no agent in this system, including this orchestrator, may ever
    perform (CONSTITUTION.md rule 1). This helper exists only so tests
    can exercise the production side of the pipeline; it is never called
    by any agent's own code.
    """
    path = root / "CONTENT_ITEM.md"
    text = path.read_text(encoding="utf-8")
    if APPROVED_MARKER not in text:
        raise AssertionError(f"expected {APPROVED_MARKER!r} in {path} before simulating approval")
    path.write_text(text.replace(APPROVED_MARKER, APPROVED_REPLACEMENT), encoding="utf-8")


def build_content_review_ready_item(
    root: Path,
    content_id: str = "test-item",
    claim_classification: str = "ASSUMPTION",
    beat: str = "1. A speculative beat about rerouting. — claims: `c1`",
) -> None:
    """A content item shaped so FACT_CHECK, SAFETY_REVIEW, and
    ORIGINALITY_REVIEW all independently PASS (mirrors
    agents/orchestrator/tests/builders.build_all_pass_item exactly).
    `claim_classification` defaults to ASSUMPTION (not FACT) so that, once
    approved, every scene's default asset strategy is GENERATED rather
    than RETRIEVED — the only way Production QA can genuinely reach PASS
    this phase (see agents/production_qa/CONTRACT.md's "Known limitation:
    RETRIEVED strategy").
    """
    root.mkdir(parents=True, exist_ok=True)
    write_content_item(root, content_id=content_id)
    write_research(root, content_id=content_id)
    write_claim(root, "c1", content_id=content_id, classification=claim_classification)
    write_script(
        root, content_id=content_id, beats=[beat],
        verified_claims_rows=[f"| `c1` | `{claim_classification}` | `UNVERIFIED` | 1 |"],
    )


def build_production_ready_item(
    root: Path,
    content_id: str = "test-item",
    claim_classification: str = "ASSUMPTION",
) -> None:
    """A content item that will cleanly reach CONTENT_REVIEW = PASS and
    is then flipped to APPROVED (simulating a human's action) — ready for
    a full production run. Callers still need to invoke
    run_full_pipeline() once to actually generate the review attempts
    before simulate_human_approval would be meaningful in a realistic
    sequence, but flipping status early is harmless for tests that only
    care about the production side.
    """
    build_content_review_ready_item(root, content_id=content_id, claim_classification=claim_classification)
    simulate_human_approval(root)


def build_fact_only_production_ready_item(root: Path, content_id: str = "test-item") -> None:
    """Same as build_production_ready_item, but with a FACT-classified
    claim — the default asset strategy becomes RETRIEVED, which can never
    pass Production QA this phase (no real retrieval integration exists).
    Used to exercise the documented "Production QA failure" scenario
    without fabricating a QA bug — it's a genuine, honest limitation.
    """
    build_production_ready_item(root, content_id=content_id, claim_classification="FACT")
