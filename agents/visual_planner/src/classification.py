"""The Visual Safety Rule, implemented deterministically from claim
Classification values only — no NLP, no creativity. See
agents/visual_planner/CONTRACT.md's Purpose/Forbidden actions and
templates/ASSET.md's Historical authenticity classification section.

Rule (as given in the Phase 7B task description):
- No claim references at all -> ON_SCREEN_TEXT_GRAPHIC / NOT_APPLICABLE
  (e.g. a modern infographic — not a representational depiction).
- Every referenced claim is FACT -> ARCHIVAL_IMAGE /
  AUTHENTIC_HISTORICAL_MEDIA, but only as a *sourcing intent* — the
  asset's Verification status stays NOT_STARTED until a specific,
  provenanced item is actually confirmed (mirrors the Phase 7A golden
  fixture's assets/asset-02.md pattern).
- Any referenced claim is ASSUMPTION/INFERENCE/SPECULATION (a "what if"
  or otherwise non-established depiction) -> GENERATED_RECONSTRUCTION,
  unconditionally. Generated content must never be classified
  AUTHENTIC_HISTORICAL_MEDIA under any circumstance.
"""
from __future__ import annotations

from ...researcher.src.models import Claim, Classification
from .models import HistoricalAuthenticity, SceneRecord, VisualPlan

NON_FACT_CLASSIFICATIONS = frozenset(
    {Classification.ASSUMPTION, Classification.INFERENCE, Classification.SPECULATION}
)


def classify_scene(scene: SceneRecord, claims: dict[str, Claim]) -> VisualPlan:
    if not scene.claim_ids:
        return VisualPlan(
            scene=scene,
            visual_type="ON_SCREEN_TEXT_GRAPHIC",
            visual_description=(
                "On-screen text/graphic framing — no claim references, so no "
                "historical depiction is required for this scene."
            ),
            asset_type="NOT_APPLICABLE",
            generated_or_retrieved="N/A",
            authenticity=HistoricalAuthenticity.NOT_APPLICABLE,
            basis="No claim references — not a representational depiction (Visual Safety Rule).",
            needs_asset=False,
        )

    referenced_classifications = {claims[cid].classification for cid in scene.claim_ids}

    if referenced_classifications & NON_FACT_CLASSIFICATIONS:
        return VisualPlan(
            scene=scene,
            visual_type="GENERATED_RECONSTRUCTION",
            visual_description=(
                "A generated illustration/reconstruction depicting this scene's "
                "hypothetical or inferred content — never to be presented as "
                "authentic historical media."
            ),
            asset_type="IMAGE",
            generated_or_retrieved="GENERATED",
            authenticity=HistoricalAuthenticity.GENERATED_RECONSTRUCTION,
            basis=(
                "At least one referenced claim is ASSUMPTION/INFERENCE/SPECULATION "
                "— this scene depicts something that did not (or may not have) "
                "actually happened as stated, so it must never be classified "
                "AUTHENTIC_HISTORICAL_MEDIA (Visual Safety Rule)."
            ),
            needs_asset=True,
        )

    return VisualPlan(
        scene=scene,
        visual_type="ARCHIVAL_IMAGE",
        visual_description=(
            "A genuine period/archival image or document related to this scene's "
            "factual content — a sourcing target, not yet a verified asset."
        ),
        asset_type="IMAGE",
        generated_or_retrieved="RETRIEVED",
        authenticity=HistoricalAuthenticity.AUTHENTIC_HISTORICAL_MEDIA,
        basis=(
            "All referenced claims are FACT. This classification states sourcing "
            "intent only — Verification status stays NOT_STARTED until a specific, "
            "provenanced item is actually confirmed; if no genuinely authentic item "
            "can be sourced, this classification must be revisited, never left as an "
            "unverified claim (mirrors the Phase 7A golden fixture's asset-02.md)."
        ),
        needs_asset=True,
    )
