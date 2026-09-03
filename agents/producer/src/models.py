"""Producer-specific data model. Reuses
agents/researcher/src.errors.{NoLoadableContent,StructuralFailure} and
.loader/.models (ContentItem, Claim, Classification) directly rather than
redefining them — see README.md "Relationship to agents/researcher".
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SceneDraft:
    scene_id: str  # "<content-id>-scene-<n>"
    filename: str  # "scene-<n>.md"
    order: int
    duration_seconds: int
    script_reference: str
    narration_text: str  # verbatim from SCRIPT.md, never paraphrased
    claim_ids: list[str]  # short claim ids referenced by this scene's beat
    classifications_present: list[str]  # read-only rollup, from claims/*.md


@dataclass
class ProductionResult:
    content_id: str
    scenes: list[SceneDraft]
    production_id: str
    script_content_hash: str
    reasons: list[str]
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    stale: bool = False
    stale_reason: str = ""
    already_up_to_date: bool = False
    production_path: str = ""
    scene_paths: list[str] = field(default_factory=list)

    @property
    def produced(self) -> bool:
        """True only when this run actually wrote a new production plan."""
        return bool(self.production_path)
