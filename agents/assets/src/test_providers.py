"""Deterministic local/test providers — no external API, no network, no
real image/video/audio generation or retrieval. Exist to prove the
pipeline end-to-end; a real provider implements the same interfaces
(provider.py) and can be swapped in (agents/assets/src/pipeline.py's
`generated_provider=`/`retrieval_provider=` arguments) without changing
pipeline.py or mutate.py at all.

Output is explicitly, permanently labeled placeholder — never mistaken
for a real image/video/audio file or a completed retrieval (CONTRACT.md's
Forbidden actions).
"""
from __future__ import annotations

import hashlib

from .provider import GeneratedArtifact, RetrievalResult

GENERATED_PLACEHOLDER_LABEL = (
    "TEST / PLACEHOLDER GENERATED ASSET — this is NOT an actual image, "
    "video, or audio file"
)
RETRIEVAL_NOT_IMPLEMENTED = "RETRIEVAL_NOT_IMPLEMENTED"


class LocalTestGeneratedAssetProvider:
    """Deterministic stand-in GENERATED-strategy provider. Same visual
    description + asset type always produces the same artifact content —
    no randomness, no network calls, no real synthesis of any kind."""

    label = "local-test-generated-asset-provider"

    def generate(self, visual_description: str, asset_type: str) -> GeneratedArtifact:
        content_hash = hashlib.sha256(visual_description.encode("utf-8")).hexdigest()[:16]
        artifact_content = (
            f"{GENERATED_PLACEHOLDER_LABEL}\n"
            f"Provider: {self.label}\n"
            f"Asset type: {asset_type}\n"
            f"Visual description hash: {content_hash}\n"
            "---\n"
            f"{visual_description}\n"
        )
        return GeneratedArtifact(
            provider_label=self.label, artifact_content=artifact_content, is_placeholder=True
        )


class LocalTestAssetRetrievalProvider:
    """Deterministic stand-in RETRIEVED-strategy provider. Never contacts
    any external service and never fabricates a source, URL, or
    organization name — see CONTRACT.md's Forbidden actions."""

    label = "local-test-retrieval-provider"

    def retrieve(self, visual_description: str, asset_type: str) -> RetrievalResult:
        return RetrievalResult(
            provider_label=self.label,
            status=RETRIEVAL_NOT_IMPLEMENTED,
            requirement_note=(
                "No external retrieval provider is integrated yet. A human or a "
                f"future retrieval integration must source a real, provenanced "
                f"{asset_type} matching: {visual_description}"
            ),
            source_reference="not yet sourced",
        )
