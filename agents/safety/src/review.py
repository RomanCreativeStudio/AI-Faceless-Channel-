"""Derives one SAFETY_REVIEW verdict from the twelve signal evaluations,
per CONTRACT.md's "Verdict derivation" list.
"""
from __future__ import annotations

from ...researcher.src.models import ReviewVerdict
from .models import REJECT_TIER_SIGNALS, RiskLevel, SignalEvaluation


def derive_verdict(
    evaluations: list[SignalEvaluation],
) -> tuple[ReviewVerdict, list[str], list[str], bool]:
    """Returns (verdict, reasons, required_changes, escalate_to_human)."""
    reasons: list[str] = []
    required_changes: list[str] = []
    escalate = False
    verdict = ReviewVerdict.PASS

    for e in evaluations:
        if e.risk_level is RiskLevel.HIGH_RISK:
            reasons.append(f"{e.signal.value}: HIGH_RISK — {e.reason}")
            if e.signal in REJECT_TIER_SIGNALS:
                verdict = ReviewVerdict.REJECT
                required_changes.append(
                    f"{e.signal.value}: this content cannot proceed as-is — remove/rework "
                    "the flagged material entirely"
                )
                escalate = True
            else:
                if verdict is not ReviewVerdict.REJECT:
                    verdict = ReviewVerdict.REVISION_REQUIRED
                required_changes.append(f"{e.signal.value}: revise to resolve — {e.reason}")
                escalate = True
        elif e.risk_level is RiskLevel.REVIEW_REQUIRED:
            reasons.append(f"{e.signal.value}: REVIEW_REQUIRED — {e.reason}")
            required_changes.append(
                f"{e.signal.value}: human judgment needed — this system cannot "
                "reliably resolve it"
            )
            escalate = True
            if verdict is ReviewVerdict.PASS:
                verdict = ReviewVerdict.REVISION_REQUIRED

    if verdict is ReviewVerdict.PASS:
        reasons.append(
            f"all {len(evaluations)} safety signals are LOW_RISK or NOT_APPLICABLE"
        )

    return verdict, reasons, required_changes, escalate
