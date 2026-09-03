"""Visual-Planner-specific data model. Reuses
agents/researcher/src.models' Classification and
agents/producer/src.hashing directly rather than redefining them — see
README.md "Relationship to agents/producer".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class HistoricalAuthenticity(str, Enum):
    """Mirrors templates/ASSET.md's "Historical authenticity
    classification" vocabulary exactly — never invented here."""

    AUTHENTIC_HISTORICAL_MEDIA = "AUTHENTIC_HISTORICAL_MEDIA"
    GENERATED_RECONSTRUCTION = "GENERATED_RECONSTRUCTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class SceneRecord:
    path: Path
    filename: str  # "scene-<n>.md"
    scene_id: str
    content_id: str
    order: int
    narration_text: str
    claim_ids: list[str]
    raw_text: str = field(repr=False, default="")


@dataclass
class VisualPlan:
    scene: SceneRecord
    visual_type: str
    visual_description: str
    asset_type: str
    generated_or_retrieved: str  # "GENERATED" | "RETRIEVED" | "N/A"
    authenticity: HistoricalAuthenticity
    basis: str
    needs_asset: bool
    asset_filename: str = ""


@dataclass
class VisualPlanningResult:
    content_id: str
    production_id: str
    plans: list[VisualPlan]
    reasons: list[str]
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    production_path: str = ""
    scene_paths: list[str] = field(default_factory=list)
    asset_paths: list[str] = field(default_factory=list)

    @property
    def planned(self) -> bool:
        return bool(self.production_path)
