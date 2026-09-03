"""Top-level orchestration for the Full Pipeline: run_full_pipeline() is
the one entry point. Sequences CONTENT_REVIEW (delegated entirely to
agents/orchestrator/) -> CONTENT_APPROVAL_GATE (read-only) -> the eight
production agents, stopping at the first stage that doesn't cleanly
succeed. See CONTRACT.md's "Stage ordering", "Self-review behavior", and
"Terminal states" for the full reasoning behind every decision here.
"""
from __future__ import annotations

from pathlib import Path

from ...orchestrator.src.pipeline import run_automated_review
from ...researcher.src import parsing
from ...researcher.src.loader import load_content_item
from .status_sequence import stage_already_completed_by_a_later_stage
from .models import (
    BLOCKED,
    COMPLETE,
    CONTENT_APPROVAL_GATE,
    CONTENT_REVIEW,
    ESCALATE_TO_HUMAN,
    MAX_STAGE_ATTEMPTS,
    PASS,
    PRODUCTION_QA,
    PRODUCTION_STAGE_ORDER,
    REVISION_REQUIRED,
    STAGE_ORDER,
    SYSTEM_ERROR,
    PipelineResult,
    StageRunOutcome,
)
from .stages import build_production_adapters

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"

# Maps agents/orchestrator/'s OrchestratorResult.overall_result values to
# this orchestrator's own StageRunOutcome.outcome vocabulary for the
# CONTENT_REVIEW super-stage. Not a new interpretation of what any
# reviewer's verdict means (CONTRACT.md's "Important distinction") — just
# a label translation for one already-computed field.
_REVIEW_OUTCOME_MAP = {
    "PASS": "PASS",
    "REVISION_REQUIRED": "REVISION_REQUIRED",
    "REJECT": "REJECT",
    "HUMAN_ESCALATION": "ESCALATED",
    "SYSTEM_ERROR": "SYSTEM_ERROR",
}


def run_full_pipeline(
    root: Path,
    apply: bool = False,
    originality_channel_index=None,
    originality_reference_paths=None,
) -> PipelineResult:
    completed: list[str] = []
    skipped: list[str] = []
    blocked: list[str] = []
    failed: list[str] = []
    escalated: list[str] = []
    revision_requests: dict = {}
    attempt_counts: dict = {}
    stale_artifacts: list[str] = []
    stage_results: dict = {}
    content_id = ""

    def _finish(**overrides) -> PipelineResult:
        base = dict(
            content_id=content_id,
            pipeline_status=SYSTEM_ERROR,
            current_stage="",
            completed_stages=completed,
            skipped_stages=skipped,
            blocked_stages=blocked,
            failed_stages=failed,
            escalated_stages=escalated,
            revision_requests=revision_requests,
            attempt_counts=attempt_counts,
            stale_artifacts=stale_artifacts,
            human_action_required=False,
            human_action_reason="",
            terminal_reason="",
            stage_results=stage_results,
            apply=apply,
        )
        base.update(overrides)
        return PipelineResult(**base)

    # --- Stage: CONTENT_REVIEW — entirely delegated to agents/orchestrator/ ---
    try:
        review_result = run_automated_review(
            root, apply=apply,
            originality_channel_index=originality_channel_index,
            originality_reference_paths=originality_reference_paths,
        )
    except Exception as exc:  # noqa: BLE001 — a coordinated agent crashing is never a PASS
        stage_results[CONTENT_REVIEW] = StageRunOutcome(
            stage=CONTENT_REVIEW, executed=True, skipped=False, outcome=SYSTEM_ERROR,
            reasons=[f"{type(exc).__name__}: {exc}"], produced=False, attempt=1,
        )
        attempt_counts[CONTENT_REVIEW] = 1
        skipped.extend(STAGE_ORDER[1:])
        return _finish(
            pipeline_status=SYSTEM_ERROR, current_stage=CONTENT_REVIEW,
            terminal_reason=f"CONTENT_REVIEW raised an unexpected exception: {exc}",
        )

    content_id = review_result.content_id or content_id
    attempt_counts[CONTENT_REVIEW] = 1
    review_outcome = _REVIEW_OUTCOME_MAP.get(review_result.overall_result.value, "SYSTEM_ERROR")
    stage_results[CONTENT_REVIEW] = StageRunOutcome(
        stage=CONTENT_REVIEW, executed=bool(review_result.stages_executed), skipped=False,
        outcome=review_outcome, reasons=[review_result.blocking_reason] if review_result.blocking_reason else [],
        produced=apply and review_outcome == "PASS", attempt=1, raw_result=review_result,
    )
    if review_result.human_escalation:
        escalated.append(CONTENT_REVIEW)

    if review_outcome == "SYSTEM_ERROR":
        skipped.extend(STAGE_ORDER[1:])
        return _finish(
            pipeline_status=SYSTEM_ERROR, current_stage=CONTENT_REVIEW,
            terminal_reason=f"CONTENT_REVIEW: system error — {review_result.blocking_reason}",
        )

    if review_outcome in ("REJECT", "ESCALATED"):
        skipped.extend(STAGE_ORDER[1:])
        reason = (
            f"CONTENT_REVIEW escalated at {review_result.first_blocking_stage}: "
            f"{review_result.blocking_reason}"
        )
        return _finish(
            pipeline_status=ESCALATE_TO_HUMAN, current_stage=CONTENT_REVIEW,
            human_action_required=True, human_action_reason=reason, terminal_reason=reason,
        )

    if review_outcome == "REVISION_REQUIRED":
        failed.append(CONTENT_REVIEW)
        revision_requests[CONTENT_REVIEW] = [review_result.blocking_reason]
        skipped.extend(STAGE_ORDER[1:])
        reason = (
            f"CONTENT_REVIEW: {review_result.first_blocking_stage} requires revision — "
            f"{review_result.blocking_reason}. No agent in this phase has autonomous fix "
            "authority for this — see CONTRACT.md's Self-review behavior."
        )
        return _finish(
            pipeline_status=REVISION_REQUIRED, current_stage=CONTENT_REVIEW,
            human_action_required=True, human_action_reason=reason, terminal_reason=reason,
        )

    # review_outcome == "PASS"
    completed.append(CONTENT_REVIEW)

    # --- Stage: CONTENT_APPROVAL_GATE — read-only, no agent, no mutation ---
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        stage_results[CONTENT_APPROVAL_GATE] = StageRunOutcome(
            stage=CONTENT_APPROVAL_GATE, executed=True, skipped=False, outcome=SYSTEM_ERROR,
            reasons=[f"no CONTENT_ITEM.md under {root}"], attempt=1,
        )
        attempt_counts[CONTENT_APPROVAL_GATE] = 1
        skipped.extend(STAGE_ORDER[2:])
        return _finish(
            pipeline_status=SYSTEM_ERROR, current_stage=CONTENT_APPROVAL_GATE,
            terminal_reason=f"no CONTENT_ITEM.md under {root}",
        )

    content_item = load_content_item(content_item_path)
    content_id = content_item.content_id or content_id
    attempt_counts[CONTENT_APPROVAL_GATE] = 1

    if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
        reason = (
            f"CONTENT_ITEM.md status is {content_item.status!r}, not "
            f"{REQUIRED_CONTENT_ITEM_STATUS!r} — production cannot begin until a human sets "
            "status = APPROVED (CONSTITUTION.md rule 1). This is the expected human "
            "checkpoint, not a failure of the automated pipeline."
        )
        stage_results[CONTENT_APPROVAL_GATE] = StageRunOutcome(
            stage=CONTENT_APPROVAL_GATE, executed=True, skipped=False, outcome=BLOCKED,
            reasons=[reason], attempt=1,
        )
        blocked.append(CONTENT_APPROVAL_GATE)
        skipped.extend(STAGE_ORDER[2:])
        return _finish(
            pipeline_status=PASS, current_stage=CONTENT_APPROVAL_GATE,
            human_action_required=True, human_action_reason=reason, terminal_reason=reason,
        )

    stage_results[CONTENT_APPROVAL_GATE] = StageRunOutcome(
        stage=CONTENT_APPROVAL_GATE, executed=True, skipped=False, outcome=PASS,
        reasons=["CONTENT_ITEM.md status is APPROVED"], attempt=1,
    )
    completed.append(CONTENT_APPROVAL_GATE)

    # --- Production stages, in the real precondition order ---
    adapters = build_production_adapters()
    for index, adapter in enumerate(adapters):
        # Read-only: has a *later* stage already advanced Production
        # status past this one on a prior call? If so, this stage's own
        # narrow re-entry window (its own CONTRACT.md's Preconditions)
        # would report a false BLOCKED if invoked again — see
        # status_sequence.py's module docstring. Skip calling it; its job
        # is already done.
        production_path = root / "PRODUCTION.md"
        if production_path.is_file():
            current_status = parsing.strip_single_backticks(
                parsing.parse_table(production_path.read_text(encoding="utf-8")).get(
                    "Production status", ""
                )
            )
            if stage_already_completed_by_a_later_stage(current_status, adapter.stage):
                stage_results[adapter.stage] = StageRunOutcome(
                    stage=adapter.stage, executed=False, skipped=False, outcome="PASS",
                    reasons=[
                        f"Production status is already {current_status!r}, past this stage — "
                        "a later stage already completed this one's job on an earlier call"
                    ],
                    produced=False, attempt=0,
                )
                attempt_counts[adapter.stage] = 0
                completed.append(adapter.stage)
                continue

        raw = adapter.run(root, apply)
        content_id = getattr(raw, "content_id", "") or content_id
        attempt_counts[adapter.stage] = MAX_STAGE_ATTEMPTS
        outcome, reasons, produced, stale = adapter.normalize(raw, apply)
        stage_results[adapter.stage] = StageRunOutcome(
            stage=adapter.stage, executed=True, skipped=False, outcome=outcome,
            reasons=reasons, produced=produced, stale=stale, attempt=MAX_STAGE_ATTEMPTS,
            raw_result=raw,
        )
        if stale:
            stale_artifacts.append(adapter.stage)

        remaining = [a.stage for a in adapters[index + 1:]]

        if outcome == "SYSTEM_ERROR":
            skipped.extend(remaining)
            reason = f"{adapter.stage}: system error — {'; '.join(reasons)}"
            return _finish(
                pipeline_status=SYSTEM_ERROR, current_stage=adapter.stage, terminal_reason=reason,
            )

        if outcome == "BLOCKED":
            blocked.append(adapter.stage)
            skipped.extend(remaining)
            reason = f"{adapter.stage} blocked: {'; '.join(reasons)}"
            return _finish(
                pipeline_status=BLOCKED, current_stage=adapter.stage,
                human_action_required=True, human_action_reason=reason, terminal_reason=reason,
            )

        if outcome == "REVISION_REQUIRED":
            failed.append(adapter.stage)
            revision_requests[adapter.stage] = reasons
            skipped.extend(remaining)
            reason = (
                f"{adapter.stage} requires revision: {'; '.join(reasons)} — no agent in this "
                "phase has autonomous fix authority for this stage (see CONTRACT.md's "
                "Self-review behavior)."
            )
            return _finish(
                pipeline_status=REVISION_REQUIRED, current_stage=adapter.stage,
                human_action_required=True, human_action_reason=reason, terminal_reason=reason,
            )

        # PASS (fresh or already-up-to-date)
        completed.append(adapter.stage)

    # Every stage, including PRODUCTION_QA, passed.
    reason = (
        "PRODUCTION_QA passed — Production status is now HUMAN_REVIEW, the highest state any "
        "agent may ever reach (CONSTITUTION.md rule 2). Awaiting final human approval."
    )
    return _finish(
        pipeline_status=COMPLETE, current_stage=PRODUCTION_QA,
        human_action_required=True, human_action_reason=reason, terminal_reason=reason,
    )
