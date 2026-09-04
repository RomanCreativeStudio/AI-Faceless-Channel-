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
    # Phase 8 additions — optional/defaulted so the existing placeholder
    # provider keeps working unchanged. A real provider sets
    # artifact_bytes to genuine binary image data and artifact_extension
    # to its real format ("png", ...); see mutate.write_generated_artifact/
    # write_generated_artifact_binary.
    artifact_bytes: bytes | None = None
    artifact_extension: str = "generated.txt"


@dataclass
class RetrievalResult:
    provider_label: str
    status: str  # "RETRIEVED" | "RETRIEVAL_FAILED" | "RETRIEVAL_NOT_IMPLEMENTED"
    requirement_note: str  # what a human/future integration would need to source, or why retrieval failed
    source_reference: str  # never a fabricated URL/organization — "not yet sourced"
    # Phase 8 additions — all optional/defaulted so the existing
    # not-implemented test provider keeps working unchanged. Populated
    # only on a genuine successful retrieval.
    source_url: str = "N/A"
    license_text: str = "N/A"  # the provider's own reported license/terms, verbatim, never invented
    licensing_status: str = "UNVERIFIED"  # one of templates/ASSET.md's Licensing/provenance status values
    artifact_bytes: bytes | None = None
    artifact_extension: str = ""  # "jpg" | "png", set only when artifact_bytes is set


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
