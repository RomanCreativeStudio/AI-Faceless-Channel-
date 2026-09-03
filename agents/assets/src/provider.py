"""Provider abstraction for asset acquisition. No specific image/video
generation vendor or stock-media/retrieval API is named or assumed
anywhere in this module — see agents/assets/CONTRACT.md's "Asset
strategies". A real provider is a future implementation of one of these
two interfaces; nothing in agents/assets/src/pipeline.py needs to change
to swap one in.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class GeneratedArtifact:
    provider_label: str
    artifact_content: str  # text content to persist as the placeholder artifact
    is_placeholder: bool


@dataclass
class RetrievalResult:
    provider_label: str
    status: str  # "RETRIEVAL_NOT_IMPLEMENTED" for this MVP's only provider
    requirement_note: str  # what a human/future integration would need to source
    source_reference: str  # never a fabricated URL/organization — "not yet sourced"


class GeneratedAssetProvider(Protocol):
    """Adapter interface every GENERATED-strategy provider (test or real)
    implements."""

    label: str

    def generate(self, visual_description: str, asset_type: str) -> GeneratedArtifact:
        ...


class AssetRetrievalProvider(Protocol):
    """Adapter interface every RETRIEVED-strategy provider (test or real)
    implements."""

    label: str

    def retrieve(self, visual_description: str, asset_type: str) -> RetrievalResult:
        ...
