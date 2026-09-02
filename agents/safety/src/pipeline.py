"""Top-level orchestration for the Safety Reviewer: run_safety_review()
is the one entry point. Same dry-run-by-default / apply-opt-in shape as
agents/researcher/src/pipeline.py, reusing the generic multi-pass gating
functions from there (see README.md "Relationship to agents/researcher").
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src.errors import NoLoadableContent, StructuralFailure
from ...researcher.src.loader import load_content_item, load_reviews
from ...researcher.src.models import ReviewVerdict
from ...researcher.src.multipass import can_run_new_attempt, next_attempt_number
from . import mutate
from .hashing import compute_reviewed_content_hash
from .loader import load_safety_bundle
from .models import SafetyReviewResult
from .review import derive_verdict
from .review_writer import render_review_markdown
from .signals import evaluate_all_signals

ROLE_LABEL = "SAFETY_REVIEWER"
ROLE_FILE_PREFIX = "safety_reviewer"


def run_safety_review(root: Path, apply: bool = False) -> SafetyReviewResult:
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return SafetyReviewResult(
            content_id="", verdict=ReviewVerdict.REJECT, signal_evaluations=[],
            reasons=[], required_changes=[], notes=[], escalate_to_human=False,
            content_hash="", aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}",
        )
    content_item = load_content_item(content_item_path)

    try:
        bundle = load_safety_bundle(root)
    except NoLoadableContent as exc:
        if apply:
            mutate.append_notes_log(
                content_item_path, f"[safety agent] safety review aborted: {exc}"
            )
        return SafetyReviewResult(
            content_id=content_item.content_id, verdict=ReviewVerdict.REJECT,
            signal_evaluations=[], reasons=[], required_changes=[], notes=[],
            escalate_to_human=False, content_hash="", aborted=True, abort_reason=str(exc),
        )
    except StructuralFailure as exc:
        return _write_structural_rejection(root, content_item, str(exc), apply)

    reviews = load_reviews(root / "reviews", ROLE_FILE_PREFIX)
    allowed, block_reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)

    evaluations = evaluate_all_signals(bundle)
    verdict, reasons, required_changes, escalate = derive_verdict(evaluations)
    content_hash = compute_reviewed_content_hash(bundle)

    result = SafetyReviewResult(
        content_id=content_item.content_id,
        verdict=verdict,
        signal_evaluations=evaluations,
        reasons=reasons,
        required_changes=required_changes,
        notes=[],
        escalate_to_human=escalate,
        content_hash=content_hash,
    )

    if not allowed:
        result.blocked = True
        result.blocked_reason = block_reason
        result.escalate_to_human = True
        return result

    if apply:
        _apply_result(root, content_item, reviews, result)

    return result


def _write_structural_rejection(root: Path, content_item, reason: str, apply: bool) -> SafetyReviewResult:
    reviews = load_reviews(root / "reviews", ROLE_FILE_PREFIX)
    allowed, block_reason = can_run_new_attempt(reviews, content_item, ROLE_LABEL)
    result = SafetyReviewResult(
        content_id=content_item.content_id,
        verdict=ReviewVerdict.REJECT,
        signal_evaluations=[],
        reasons=[f"structural failure: {reason}"],
        required_changes=[f"fix the data model: {reason}"],
        notes=[],
        escalate_to_human=True,
        content_hash="",
    )
    if not allowed:
        result.blocked = True
        result.blocked_reason = block_reason
        return result
    if apply:
        _apply_result(root, content_item, reviews, result)
    return result


def _apply_result(root: Path, content_item, reviews, result: SafetyReviewResult) -> None:
    attempt = next_attempt_number(reviews)
    review_text = render_review_markdown(result, attempt)
    reviews_dir = root / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    review_path = reviews_dir / f"{ROLE_FILE_PREFIX}-{attempt}.md"
    review_path.write_text(review_text, encoding="utf-8")
    result.review_path = str(review_path)

    mutate.update_content_item_field(content_item.path, "Safety state", f"`{result.verdict.value}`")
    mutate.append_notes_log(
        content_item.path,
        f"[safety agent] SAFETY_REVIEW attempt #{attempt} -> {result.verdict.value} "
        f"(see reviews/{ROLE_FILE_PREFIX}-{attempt}.md)",
    )
