"""Orchestrator-level result model. Reuses agents/researcher/src.models'
ReviewVerdict directly for per-stage verdicts (already generic). Defines
its own OverallResult — a strict superset used only to add SYSTEM_ERROR
(an infrastructure failure, never a reviewer verdict — see CONTRACT.md
"Error handling") alongside the four review-outcome categories the task
requires; nothing here re-derives what PASS/REVISION_REQUIRED/REJECT
mean for a single stage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OverallResult(str, Enum):
    PASS = "PASS"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    REJECT = "REJECT"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    SYSTEM_ERROR = "SYSTEM_ERROR"  # infrastructure failure, never a reviewer verdict


# Stage name constants — also used as dict keys in OrchestratorResult.stage_results.
FACT_CHECK = "FACT_CHECK"
SAFETY_REVIEW = "SAFETY_REVIEW"
ORIGINALITY_REVIEW = "ORIGINALITY_REVIEW"
STAGE_ORDER = [FACT_CHECK, SAFETY_REVIEW, ORIGINALITY_REVIEW]


@dataclass
class StageOutcome:
    """One stage's outcome as the orchestrator sees it — either the
    stage's own freshly-computed result, or a reused prior PASS."""

    stage: str
    executed: bool  # True if the stage's run_*() was actually invoked this call
    reused_existing_pass: bool  # True if a fresh prior PASS was reused instead
    system_error: bool
    system_error_message: str
    verdict: "object | None"  # agents.researcher.src.models.ReviewVerdict, or None on system_error
    escalate_to_human: bool
    blocked: bool
    blocked_reason: str
    review_path: str
    reasons: list[str] = field(default_factory=list)
    required_changes: list[str] = field(default_factory=list)
    raw_result: "object | None" = None  # the underlying FactCheckResult/SafetyReviewResult/OriginalityReviewResult


@dataclass
class OrchestratorResult:
    content_id: str
    overall_result: OverallResult
    pipeline_status: str
    stages_executed: list[str]
    stages_skipped: list[str]
    stage_results: dict  # stage name -> StageOutcome
    first_blocking_stage: str | None
    blocking_reason: str
    human_escalation: bool
    apply: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
