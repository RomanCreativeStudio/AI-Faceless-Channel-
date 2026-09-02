"""Top-level orchestration: run_fact_check() is the one function a caller
needs. It glues together loader -> evidence -> factcheck -> multipass ->
review_writer -> mutate, enforcing everything agents/researcher/CONTRACT.md
says this agent may and may not do.

`apply=False` (default) is a dry run: nothing on disk changes, the caller
gets back the FactCheckResult to inspect. `apply=True` writes the
reviews/fact_checker-<n>.md file and updates only CONTENT_ITEM.md's
Fact-check state field plus its Notes/history log — exactly the "Allowed
actions" CONTRACT.md permits, nothing else.
"""
from __future__ import annotations

from pathlib import Path

from . import factcheck, mutate
from .errors import NoLoadableContent, StructuralFailure
from .hashing import compute_reviewed_content_hash
from .loader import load_bundle, load_content_item, load_reviews
from .models import FactCheckResult, ReviewVerdict
from .multipass import can_run_new_attempt, next_attempt_number
from .review_writer import render_review_markdown

ROLE = "fact_checker"


def run_fact_check(root: Path, apply: bool = False) -> FactCheckResult:
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return FactCheckResult(
            content_id="",
            verdict=ReviewVerdict.REJECT,
            reasons=[],
            required_changes=[],
            notes=[],
            claim_evaluations=[],
            escalate_to_human=False,
            content_hash="",
            aborted=True,
            abort_reason=f"no CONTENT_ITEM.md under {root}",
        )
    content_item = load_content_item(content_item_path)

    try:
        bundle = load_bundle(root)
    except NoLoadableContent as exc:
        if apply:
            mutate.append_notes_log(
                content_item_path, f"[researcher agent] fact-check aborted: {exc}"
            )
        return FactCheckResult(
            content_id=content_item.content_id,
            verdict=ReviewVerdict.REJECT,
            reasons=[],
            required_changes=[],
            notes=[],
            claim_evaluations=[],
            escalate_to_human=False,
            content_hash="",
            aborted=True,
            abort_reason=str(exc),
        )
    except StructuralFailure as exc:
        return _write_structural_rejection(root, content_item, str(exc), apply)

    reviews = load_reviews(root / "reviews", ROLE)
    allowed, block_reason = can_run_new_attempt(reviews, content_item, "FACT_CHECKER")

    evaluations, atomicity_violations = factcheck.evaluate_all(bundle)
    verdict, reasons, required_changes, escalate = factcheck.derive_verdict(
        evaluations, atomicity_violations
    )
    content_hash = compute_reviewed_content_hash(
        bundle, [e.short_id for e in evaluations]
    )
    notes = [f"{e.short_id}: {e.classification.value}/{e.evidence_support.value} -> {e.fact_check_status.value} ({e.reason})" for e in evaluations]

    result = FactCheckResult(
        content_id=content_item.content_id,
        verdict=verdict,
        reasons=reasons,
        required_changes=required_changes,
        notes=notes,
        claim_evaluations=evaluations,
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


def _write_structural_rejection(
    root: Path, content_item, reason: str, apply: bool
) -> FactCheckResult:
    reviews = load_reviews(root / "reviews", ROLE)
    allowed, block_reason = can_run_new_attempt(reviews, content_item, "FACT_CHECKER")
    result = FactCheckResult(
        content_id=content_item.content_id,
        verdict=ReviewVerdict.REJECT,
        reasons=[f"structural failure: {reason}"],
        required_changes=[f"fix the data model: {reason}"],
        notes=[],
        claim_evaluations=[],
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


def _apply_result(root: Path, content_item, reviews, result: FactCheckResult) -> None:
    attempt = next_attempt_number(reviews)
    review_text = render_review_markdown(result, attempt)
    reviews_dir = root / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    review_path = reviews_dir / f"{ROLE}-{attempt}.md"
    review_path.write_text(review_text, encoding="utf-8")
    result.review_path = str(review_path)

    mutate.update_content_item_field(
        content_item.path, "Fact-check state", f"`{result.verdict.value}`"
    )
    mutate.append_notes_log(
        content_item.path,
        f"[researcher agent] FACT_CHECK attempt #{attempt} -> {result.verdict.value} "
        f"(see reviews/{ROLE}-{attempt}.md)",
    )
