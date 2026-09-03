"""Deterministic Asset QA checks — structural only, never a
visual-quality judgment. This agent cannot and does not claim to
determine whether an image "looks historically accurate" — that is a
future, unbuilt visual QA layer. See CONTRACT.md's "Asset QA".
"""
from __future__ import annotations

from .models import AssetPlan, AssetStrategy, HistoricalAuthenticity

VALID_VERIFICATION_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "VERIFIED", "DISPUTED", "REVIEW_REQUIRED"}
VALID_GENERATION_STATUSES = {
    "NOT_STARTED", "IN_PROGRESS", "GENERATED", "RETRIEVED", "HUMAN_PROVIDED", "REVISION_REQUIRED",
}


def evaluate_asset_qa(plan: AssetPlan, known_claim_ids: set[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not plan.asset_id.strip():
        reasons.append("asset ID is missing")
    if not plan.scene.scene_id.strip():
        reasons.append("scene ID is missing")

    if not isinstance(plan.strategy, AssetStrategy):
        reasons.append(f"strategy {plan.strategy!r} is not a recognized value")
    if not isinstance(plan.authenticity, HistoricalAuthenticity):
        reasons.append(f"authenticity classification {plan.authenticity!r} is not a recognized value")
    if plan.verification_status not in VALID_VERIFICATION_STATUSES:
        reasons.append(f"verification status {plan.verification_status!r} is not a recognized value")
    if plan.generation_status not in VALID_GENERATION_STATUSES:
        reasons.append(f"generation status {plan.generation_status!r} is not a recognized value")

    unresolved_claims = [c for c in plan.scene.claim_ids if c not in known_claim_ids]
    if unresolved_claims:
        reasons.append(f"claim references do not resolve: {unresolved_claims}")

    if plan.strategy is AssetStrategy.RETRIEVED:
        if plan.source and plan.source.startswith(("http://", "https://")):
            reasons.append("RETRIEVED asset has a source URL despite no real retrieval integration existing")
        if plan.generation_status == "RETRIEVED":
            reasons.append("RETRIEVED strategy must not claim generation status RETRIEVED without a real retrieval")

    if plan.strategy is AssetStrategy.GENERATED:
        if not plan.artifact_filename:
            reasons.append("GENERATED asset has no artifact reference")
        if plan.generation_status not in ("GENERATED", "NOT_STARTED"):
            reasons.append(f"GENERATED asset has an unexpected generation status {plan.generation_status!r}")

    if plan.strategy is AssetStrategy.HUMAN_PROVIDED:
        has_source = bool(plan.source) and plan.source.strip().lower() not in ("", "unknown")
        if not has_source and plan.verification_status != "REVIEW_REQUIRED":
            reasons.append("HUMAN_PROVIDED asset with no stated source must be REVIEW_REQUIRED")

    return (len(reasons) == 0, reasons)
