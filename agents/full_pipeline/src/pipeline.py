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
from ...researcher.src.pipeline import run_fact_check
from ...researcher.src.revision import run_autonomous_revision
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


def _attempt_researcher_revision(
    root: Path, apply: bool, review_result, originality_channel_index=None,
    originality_reference_paths=None,
):
    """Invokes agents/researcher/'s Autonomous Revision Mode against the
    FACT_CHECKER attempt agents/orchestrator/ just produced (never
    re-running fact-check redundantly — reuses that exact attempt 1).
    Returns `None` if revision made no difference this call (dry run, no
    successors created, blocked, or aborted) — the caller then falls
    through to ordinary REVISION_REQUIRED handling. Otherwise returns
    `(new_review_result, new_review_outcome)` reflecting attempt 2 and,
    if that reached PASS, a full re-run of the content-review chain so
    SAFETY_REVIEW/ORIGINALITY_REVIEW get their turn — never continuing
    downstream with an unresolved factual issue (task section 10).
    """
    revision_result = run_autonomous_revision(root, apply=apply)
    if revision_result.aborted or revision_result.blocked or not revision_result.produced:
        return None
    if not apply:
        # A dry run diagnoses but writes no successor, so there is
        # nothing on disk yet for a real re-check — see
        # agents/researcher/README.md's "Known limitations".
        return None

    # Attempt 2, evaluating the successor in place of what it superseded.
    run_fact_check(root, apply=True, claim_substitutions=revision_result.claim_substitutions)

    # A full re-run of the content-review chain, whatever attempt 2's own
    # verdict was: if it reached PASS, agents/orchestrator/'s own
    # freshness check reuses it for free (see CONTRACT.md's "Hash and
    # supersession behavior") and SAFETY_REVIEW/ORIGINALITY_REVIEW get
    # their turn for the first time; if attempt 2 is still
    # REVISION_REQUIRED, the exact same two-consecutive-attempts gate
    # already reused here (can_run_new_attempt, inside
    # agents/orchestrator/'s own adapter) correctly refuses a third
    # attempt and reports the still-failing latest verdict — never a
    # separate, competing retry system.
    rerun = run_automated_review(
        root, apply=apply, originality_channel_index=originality_channel_index,
        originality_reference_paths=originality_reference_paths,
    )
    outcome = _REVIEW_OUTCOME_MAP.get(rerun.overall_result.value, "SYSTEM_ERROR")
    return rerun, outcome


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
        # The one autonomous-fix capability that exists this phase (Phase
        # 7F): agents/researcher/'s Autonomous Revision Mode, and only
        # when FACT_CHECK itself was the blocking stage — SAFETY_REVIEW/
        # ORIGINALITY_REVIEW still have no autonomous-fix authority. See
        # agents/researcher/CONTRACT.md's "Autonomous Revision Mode".
        if review_result.first_blocking_stage == "FACT_CHECK":
            revision_outcome = _attempt_researcher_revision(
                root, apply, review_result, originality_channel_index, originality_reference_paths,
            )
            if revision_outcome is not None:
                review_result, review_outcome = revision_outcome
                stage_results[CONTENT_REVIEW] = StageRunOutcome(
                    stage=CONTENT_REVIEW, executed=True, skipped=False, outcome=review_outcome,
                    reasons=[review_result.blocking_reason] if review_result.blocking_reason else [],
                    produced=apply and review_outcome == "PASS", attempt=2, raw_result=review_result,
                )
                if review_result.human_escalation:
                    escalated.append(CONTENT_REVIEW)

                if review_outcome == "PASS":
                    completed.append(CONTENT_REVIEW)
                    # fall through to CONTENT_APPROVAL_GATE below
                elif review_outcome in ("REJECT", "ESCALATED"):
                    skipped.extend(STAGE_ORDER[1:])
                    reason = (
                        f"CONTENT_REVIEW escalated at {review_result.first_blocking_stage} even "
                        f"after autonomous revision was attempted: {review_result.blocking_reason}"
                    )
                    return _finish(
                        pipeline_status=ESCALATE_TO_HUMAN, current_stage=CONTENT_REVIEW,
                        human_action_required=True, human_action_reason=reason, terminal_reason=reason,
                    )
                else:
                    failed.append(CONTENT_REVIEW)
                    revision_requests[CONTENT_REVIEW] = [review_result.blocking_reason]
                    skipped.extend(STAGE_ORDER[1:])
                    reason = (
                        f"CONTENT_REVIEW: autonomous revision was attempted but "
                        f"{review_result.first_blocking_stage} still requires revision — "
                        f"{review_result.blocking_reason}. Human action required."
                    )
                    return _finish(
                        pipeline_status=REVISION_REQUIRED, current_stage=CONTENT_REVIEW,
                        human_action_required=True, human_action_reason=reason, terminal_reason=reason,
                    )

        if CONTENT_REVIEW not in completed:
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

    # review_outcome == "PASS" (either on the first attempt, or after a
    # successful autonomous revision already appended it above).
    if CONTENT_REVIEW not in completed:
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
