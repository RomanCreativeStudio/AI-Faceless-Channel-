"""Computes templates/TIMELINE.md's `Assembly content hash` field: sha256
of the current script hash, the voice record's own contribution
(provider + configuration + script hash + audio reference), and every
scene's asset content hash (sorted by scene order) — capturing every
upstream input the timeline depends on. See CONTRACT.md's "Hash /
dependency model".
"""
from __future__ import annotations

import hashlib


def compute_voice_hash_component(
    provider: str, voice_configuration: str, voice_script_hash: str, audio_reference: str
) -> str:
    hasher = hashlib.sha256()
    for part in (provider, voice_configuration, voice_script_hash, audio_reference):
        hasher.update(part.encode("utf-8"))
    return hasher.hexdigest()


def compute_assembly_content_hash(
    script_hash: str, voice_hash_component: str, asset_hashes: list[str]
) -> str:
    hasher = hashlib.sha256()
    hasher.update(script_hash.encode("utf-8"))
    hasher.update(voice_hash_component.encode("utf-8"))
    for asset_hash in asset_hashes:
        hasher.update(asset_hash.encode("utf-8"))
    return hasher.hexdigest()
