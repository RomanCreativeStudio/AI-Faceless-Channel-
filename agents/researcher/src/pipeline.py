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


def run_fact_check(
    root: Path, apply: bool = False, claim_substitutions: dict[str, str] | None = None,
) -> FactCheckResult:
    """`claim_substitutions` (old short_id -> new short_id) is Autonomous
    Revision Mode's one extension point — see
    agents/researcher/src/revision.py and factcheck.claims_under_review's
    own docstring. `None` (the default, and every call site before Phase
    7F) reproduces the exact prior behavior unchanged. Every substitution
    used is disclosed at the top of the resulting REVIEW.md's Notes —
    never silent.
    """
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

    evaluations, atomicity_violations = factcheck.evaluate_all(bundle, claim_substitutions)
    verdict, reasons, required_changes, escalate = factcheck.derive_verdict(
        evaluations, atomicity_violations
    )
    # Reviewed content hash is always computed from the *original*,
    # unsubstituted claim ids SCRIPT.md actually cites — never the
    # substituted successor ids — so that agents/orchestrator/'s own
    # freshness re-check (which always recomputes plainly, with no
    # knowledge of any substitution) still recognizes this PASS as fresh
    # afterward. This is safe and stable: an original claim, once
    # superseded, is immutable forever, so its hash contribution never
    # changes again either. See agents/researcher/CONTRACT.md's
    # "Autonomous Revision Mode" -> "Hash and supersession behavior".
    content_hash = compute_reviewed_content_hash(
        bundle, factcheck.claims_under_review(bundle)
    )
    notes = [f"{e.short_id}: {e.classification.value}/{e.evidence_support.value} -> {e.fact_check_status.value} ({e.reason})" for e in evaluations]
    if claim_substitutions:
        notes = [
            f"AUTONOMOUS REVISION: evaluated successor claim {new!r} in place of superseded "
            f"claim {old!r} — see revisions/ for the full record."
            for old, new in sorted(claim_substitutions.items())
        ] + notes

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
        _apply_result(root, content_item, reviews, result, bundle, claim_substitutions)

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


def _apply_result(
    root: Path, content_item, reviews, result: FactCheckResult,
    bundle=None, claim_substitutions: dict[str, str] | None = None,
) -> None:
    attempt = next_attempt_number(reviews)
    review_text = render_review_markdown(result, attempt)
    reviews_dir = root / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    review_path = reviews_dir / f"{ROLE}-{attempt}.md"
    review_path.write_text(review_text, encoding="utf-8")

    if claim_substitutions and bundle is not None:
        # A substituted successor claim's own Fact-check status is
        # updated in place — the exact same whitelisted field every
        # ordinary claim already permits (mutate.CLAIM_WRITABLE_FIELDS);
        # never Exact claim/Classification. This is the one place a
        # re-fact-check pass writes back onto a claim file, and only for
        # claims Autonomous Revision Mode itself created this cycle.
        evaluated_by_short_id = {e.short_id: e for e in result.claim_evaluations}
        for new_short_id in claim_substitutions.values():
            evaluation = evaluated_by_short_id.get(new_short_id)
            claim = bundle.claims.get(new_short_id)
            if evaluation is None or claim is None:
                continue
            mutate.update_claim_field(
                claim.path, "Fact-check status", f"`{evaluation.fact_check_status.value}`"
            )
    result.review_path = str(review_path)

    mutate.update_content_item_field(
        content_item.path, "Fact-check state", f"`{result.verdict.value}`"
    )
    mutate.append_notes_log(
        content_item.path,
        f"[researcher agent] FACT_CHECK attempt #{attempt} -> {result.verdict.value} "
        f"(see reviews/{ROLE}-{attempt}.md)",
    )
