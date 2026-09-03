"""Computes templates/ASSET.md's `Scene/visual content hash` field: sha256
of the scene's narration text, visual type/description, and (sorted, for
order-independence) claim references. This is what makes per-asset
staleness detection (CONTRACT.md's "Re-running / staleness") mechanically
checkable, mirroring agents/producer/src/hashing.py's role for
PRODUCTION.md and agents/voice/src's reuse of it for VOICE.md.
"""
from __future__ import annotations

import hashlib

from .models import SceneVisualRecord


def compute_asset_content_hash(scene: SceneVisualRecord) -> str:
    hasher = hashlib.sha256()
    hasher.update(scene.narration_text.encode("utf-8"))
    hasher.update(scene.visual_type.encode("utf-8"))
    hasher.update(scene.visual_description.encode("utf-8"))
    for claim_id in sorted(scene.claim_ids):
        hasher.update(claim_id.encode("utf-8"))
    return hasher.hexdigest()
