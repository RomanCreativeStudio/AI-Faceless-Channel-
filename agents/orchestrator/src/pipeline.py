"""run_automated_review() — the orchestrator's single entry point.

Executes FACT_CHECK -> SAFETY_REVIEW -> ORIGINALITY_REVIEW in that exact
order, stopping at the first stage that doesn't cleanly PASS. It never
evaluates a claim, a safety signal, or an originality signal itself —
every `StageAdapter.run` call IS the real agent's own
`run_fact_check`/`run_safety_review`/`run_originality_review`. See
CONTRACT.md "Important distinction."
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src.loader import load_reviews
from ...researcher.src.models import ReviewVerdict
from .freshness import find_fresh_pass
from .models import OrchestratorResult, OverallResult, StageOutcome
from .stages import StageAdapter, build_default_adapters


def run_automated_review(
    root: Path,
    apply: bool = False,
    originality_channel_index=None,
    originality_reference_paths=None,
    stage_overrides: dict | None = None,
) -> OrchestratorResult:
    """`stage_overrides` (optional): {stage_name: run_callable(root, apply)}
    to substitute a stage's `run` function — used by tests to simulate a
    reviewer crash or a synthetic verdict without touching any agent's
    real code. Never set in normal use.
    """
    adapters = build_default_adapters(originality_channel_index, originality_reference_paths)
    if stage_overrides:
        for adapter in adapters:
            if adapter.stage in stage_overrides:
                adapter.run = stage_overrides[adapter.stage]

    content_id = ""
    stage_results: dict[str, StageOutcome] = {}
    executed: list[str] = []
    skipped: list[str] = []
    stopped = False
    first_blocking_stage: str | None = None
    blocking_reason = ""
    human_escalation = False
    system_error_occurred = False

    for adapter in adapters:
        if stopped:
            skipped.append(adapter.stage)
            continue

        outcome = _run_one_stage(root, adapter, apply)
        executed.append(adapter.stage)
        stage_results[adapter.stage] = outcome

        if not content_id and outcome.raw_result is not None:
            content_id = getattr(outcome.raw_result, "content_id", "") or content_id

        if outcome.system_error:
            system_error_occurred = True
            stopped = True
            first_blocking_stage = adapter.stage
            blocking_reason = outcome.system_error_message
            continue

        if outcome.verdict is not ReviewVerdict.PASS or outcome.blocked or outcome.escalate_to_human:
            stopped = True
            first_blocking_stage = adapter.stage
            blocking_reason = (
                "; ".join(outcome.reasons) or outcome.blocked_reason or "stage did not PASS"
            )
            human_escalation = outcome.escalate_to_human

    if system_error_occurred:
        overall = OverallResult.SYSTEM_ERROR
        pipeline_status = "SYSTEM_ERROR"
    elif first_blocking_stage is None:
        overall = OverallResult.PASS
        pipeline_status = "AUTOMATED_REVIEW_COMPLETE"
    else:
        blocking_outcome = stage_results[first_blocking_stage]
        if blocking_outcome.verdict is ReviewVerdict.REJECT:
            overall = OverallResult.REJECT
        elif blocking_outcome.escalate_to_human:
            overall = OverallResult.HUMAN_ESCALATION
        else:
            overall = OverallResult.REVISION_REQUIRED
        pipeline_status = f"BLOCKED_AT_{first_blocking_stage}"

    return OrchestratorResult(
        content_id=content_id,
        overall_result=overall,
        pipeline_status=pipeline_status,
        stages_executed=executed,
        stages_skipped=skipped,
        stage_results=stage_results,
        first_blocking_stage=first_blocking_stage,
        blocking_reason=blocking_reason,
        human_escalation=human_escalation,
        apply=apply,
    )


def _run_one_stage(root: Path, adapter: StageAdapter, apply: bool) -> StageOutcome:
    try:
        fresh = find_fresh_pass(root, adapter)
    except Exception:
        fresh = None  # freshness-check failure never blocks a real run

    if fresh is not None:
        return StageOutcome(
            stage=adapter.stage, executed=False, reused_existing_pass=True,
            system_error=False, system_error_message="",
            verdict=ReviewVerdict.PASS, escalate_to_human=False, blocked=False, blocked_reason="",
            review_path=str(fresh.path),
            reasons=[f"reusing existing PASS attempt #{fresh.attempt} (content hash unchanged)"],
            required_changes=[], raw_result=None,
        )

    try:
        result = adapter.run(root, apply)
    except Exception as exc:  # the reviewer itself crashed — never treat as PASS
        return StageOutcome(
            stage=adapter.stage, executed=True, reused_existing_pass=False,
            system_error=True, system_error_message=f"{adapter.stage} raised {type(exc).__name__}: {exc}",
            verdict=None, escalate_to_human=False, blocked=False, blocked_reason="",
            review_path="", reasons=[], required_changes=[], raw_result=None,
        )

    if getattr(result, "aborted", False):
        # Missing/unloadable content for this stage — a validation/system
        # failure, never a review verdict (CONTRACT.md "Error handling").
        return StageOutcome(
            stage=adapter.stage, executed=True, reused_existing_pass=False,
            system_error=True, system_error_message=result.abort_reason,
            verdict=None, escalate_to_human=False, blocked=False, blocked_reason="",
            review_path="", reasons=[], required_changes=[], raw_result=result,
        )

    verdict = result.verdict
    if getattr(result, "blocked", False):
        # Multi-pass gating refused a new attempt — the true current
        # state is the *last recorded* verdict, not whatever this
        # (unwritten) re-evaluation happened to compute.
        try:
            prior = load_reviews(root / "reviews", adapter.review_role_prefix)
            if prior:
                verdict = prior[-1].verdict
        except Exception:
            pass

    return StageOutcome(
        stage=adapter.stage, executed=True, reused_existing_pass=False,
        system_error=False, system_error_message="",
        verdict=verdict, escalate_to_human=result.escalate_to_human,
        blocked=result.blocked, blocked_reason=result.blocked_reason,
        review_path=result.review_path, reasons=list(result.reasons),
        required_changes=list(result.required_changes), raw_result=result,
    )
