"""Asset-specific data model. Reuses agents/producer/src.hashing and
agents/researcher/src.loader.load_claims directly rather than redefining
them — see README.md "Relationship to other agents".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AssetStrategy(str, Enum):
    GENERATED = "GENERATED"
    RETRIEVED = "RETRIEVED"
    HUMAN_PROVIDED = "HUMAN_PROVIDED"


class HistoricalAuthenticity(str, Enum):
    """Mirrors templates/ASSET.md's "Historical authenticity
    classification" vocabulary exactly — never invented here."""

    AUTHENTIC_HISTORICAL_MEDIA = "AUTHENTIC_HISTORICAL_MEDIA"
    GENERATED_RECONSTRUCTION = "GENERATED_RECONSTRUCTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class SceneVisualRecord:
    path: Path
    filename: str  # "scene-<n>.md"
    scene_id: str
    content_id: str
    order: int
    narration_text: str
    visual_type: str
    visual_description: str
    claim_ids: list[str]
    raw_text: str = field(repr=False, default="")


@dataclass
class AssetPlan:
    scene: SceneVisualRecord
    asset_id: str
    filename: str  # "asset-<n>.md"
    asset_type: str  # IMAGE | VIDEO_CLIP | AUDIO | MUSIC | GRAPHIC
    strategy: AssetStrategy
    authenticity: HistoricalAuthenticity
    basis: str
    source: str
    source_url: str
    generation_prompt: str
    generation_status: str  # NOT_STARTED | GENERATED | HUMAN_PROVIDED (never RETRIEVED this phase)
    verification_status: str  # NOT_STARTED | REVIEW_REQUIRED
    verification_notes: str
    content_hash: str
    artifact_filename: str = ""  # only for GENERATED strategy
    artifact_content: str = ""  # only for GENERATED strategy (text/placeholder), written at apply time
    # Phase 8 additions — all optional/defaulted so every pre-Phase-8 code
    # path (placeholder providers, HUMAN_PROVIDED) is unaffected.
    artifact_bytes: bytes | None = None  # GENERATED strategy, real binary image, written at apply time
    licensing_status: str = "UNVERIFIED"  # templates/ASSET.md's Licensing/provenance status vocabulary
    license_notes: str = "not yet checked — see Verification status below"
    retrieved_artifact_filename: str = ""  # only for RETRIEVED strategy, a real successful retrieval
    retrieved_artifact_bytes: bytes | None = None


@dataclass
class AssetGenerationResult:
    content_id: str
    production_id: str
    plans: list[AssetPlan]
    reasons: list[str]
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    stale_filenames: list[str] = field(default_factory=list)
    already_up_to_date_filenames: list[str] = field(default_factory=list)
    production_path: str = ""
    asset_paths: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    qa_passed: bool = True
    qa_reasons: dict = field(default_factory=dict)  # filename -> [reasons]

    @property
    def produced(self) -> bool:
        return bool(self.asset_paths)
