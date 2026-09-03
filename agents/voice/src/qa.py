"""Deterministic Voice QA checks — structural only, never a speech-quality
judgment. This agent cannot and does not claim to detect pronunciation,
emotion, or audio-artifact problems — see CONTRACT.md's Forbidden actions
and the Phase 7C-1 task's QA requirement ("do not claim the system can
detect pronunciation/emotion problems unless that capability actually
exists").
"""
from __future__ import annotations

VALID_GENERATION_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "GENERATED", "REVISION_REQUIRED"}


def evaluate_voice_qa(
    narration_text: str,
    recorded_script_hash: str,
    current_script_hash: str,
    audio_reference: str,
    duration_seconds: int,
    provider_label: str,
    voice_configuration: str,
    generation_status: str,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not narration_text.strip():
        reasons.append("narration text is empty")
    if recorded_script_hash != current_script_hash:
        reasons.append(
            f"script hash mismatch: recorded {recorded_script_hash!r}, "
            f"current {current_script_hash!r}"
        )
    if not audio_reference.strip():
        reasons.append("no audio reference recorded")
    if duration_seconds <= 0:
        reasons.append("duration is not a positive number")
    if not provider_label.strip() or not voice_configuration.strip():
        reasons.append("provider metadata is incomplete")
    if generation_status not in VALID_GENERATION_STATUSES:
        reasons.append(f"generation status {generation_status!r} is not a recognized value")
    return (len(reasons) == 0, reasons)
