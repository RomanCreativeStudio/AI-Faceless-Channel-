"""Top-level orchestration for the Voice agent: run_voice_generation() is
the one entry point. Same dry-run-by-default / apply-opt-in shape as
agents/producer/src/pipeline.py and agents/visual_planner/src/pipeline.py.

Preconditions (CONTRACT.md): CONTENT_ITEM.md status == APPROVED (checked
independently, not just inferred from PRODUCTION.md existing);
PRODUCTION.md Production status == PRODUCTION_PLANNING; the current
SCRIPT.md's hash must match PRODUCTION.md's stored Script content hash.

Staleness handling mirrors agents/producer/src/pipeline.py's: if
voice/voice-01.md already exists, a matching Script content hash means
it's already up to date (no-op); a mismatched hash means SCRIPT.md
changed since generation, so the existing voice record is stale and is
never silently regenerated or overwritten.
"""
from __future__ import annotations

from pathlib import Path

from ...producer.src.hashing import compute_script_content_hash
from ...researcher.src import parsing
from ...researcher.src.loader import load_content_item
from . import mutate
from .models import VoiceResult
from .narration import build_provider_ready_narration, build_source_narration
from .provider import VoiceProvider
from .qa import evaluate_voice_qa
from .test_provider import DEFAULT_TEST_WORDS_PER_MINUTE, LocalTestVoiceProvider
from .voice_writer import render_voice_markdown

REQUIRED_CONTENT_ITEM_STATUS = "APPROVED"
NEXT_PRODUCTION_STATUS = "VISUAL_PLANNING"
# PRODUCTION_PLANNING is the state a fresh run starts from (what Producer
# leaves behind). VISUAL_PLANNING is also accepted: it's the state THIS
# agent itself leaves behind after a successful generation (see
# NEXT_PRODUCTION_STATUS below) — without it, re-running Voice after its
# own success would always hit this precondition and never reach the
# already-up-to-date/staleness check that re-running is actually for.
# Voice never regresses Production status backward; a stale re-run in
# either state just refuses and reports why.
ALLOWED_PRODUCTION_STATUSES = {"PRODUCTION_PLANNING", NEXT_PRODUCTION_STATUS}
DEFAULT_VOICE_CONFIGURATION = "default-test-voice"


def run_voice_generation(
    root: Path,
    apply: bool = False,
    provider: VoiceProvider | None = None,
    voice_configuration: str = DEFAULT_VOICE_CONFIGURATION,
    words_per_minute: int = DEFAULT_TEST_WORDS_PER_MINUTE,
) -> VoiceResult:
    def _empty(**overrides) -> VoiceResult:
        base = dict(
            content_id="", production_id="", voice_id="", filename="",
            provider_label="", voice_configuration="", source_narration="",
            provider_ready_narration="", script_content_hash="", audio_reference="",
            duration_seconds=0, generation_status="NOT_STARTED", qa_status="NOT_STARTED",
            qa_reasons=[], reasons=[],
        )
        base.update(overrides)
        return VoiceResult(**base)

    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return _empty(aborted=True, abort_reason=f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    if content_item.status != REQUIRED_CONTENT_ITEM_STATUS:
        return _empty(
            content_id=content_item.content_id,
            blocked=True,
            blocked_reason=(
                f"CONTENT_ITEM.md status is {content_item.status!r}, not "
                f"{REQUIRED_CONTENT_ITEM_STATUS!r} — agents/voice/CONTRACT.md's "
                "Preconditions require full human approval before any voice "
                "generation may happen; refusing to generate"
            ),
        )

    production_path = root / "PRODUCTION.md"
    if not production_path.is_file():
        return _empty(
            content_id=content_item.content_id,
            aborted=True, abort_reason=f"no PRODUCTION.md under {root}",
        )
    production_text = production_path.read_text(encoding="utf-8")
    production_table = parsing.parse_table(production_text)
    production_id = parsing.strip_single_backticks(production_table.get("Production ID", ""))
    production_status = parsing.strip_single_backticks(production_table.get("Production status", ""))

    if production_status not in ALLOWED_PRODUCTION_STATUSES:
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            blocked=True,
            blocked_reason=(
                f"PRODUCTION.md Production status is {production_status!r} — "
                "agents/voice/CONTRACT.md's Preconditions require "
                f"{sorted(ALLOWED_PRODUCTION_STATUSES)}"
            ),
        )

    script_path = root / "SCRIPT.md"
    if not script_path.is_file():
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            aborted=True, abort_reason=f"no valid current SCRIPT.md under {root}",
        )
    script_text = script_path.read_text(encoding="utf-8")
    current_script_hash = compute_script_content_hash(script_text)

    stored_production_hash = parsing.strip_single_backticks(
        production_table.get("Script content hash", "")
    )
    if stored_production_hash != current_script_hash:
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            blocked=True,
            blocked_reason=(
                f"SCRIPT.md has changed since PRODUCTION.md was created (stored hash "
                f"{stored_production_hash!r}, current hash {current_script_hash!r}) — "
                "the production plan is stale; refusing to generate voice from "
                "outdated scenes. Re-run agents/producer/ first."
            ),
        )

    source_narration = build_source_narration(root / "scenes")
    if not source_narration.strip():
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            script_content_hash=current_script_hash,
            aborted=True,
            abort_reason=f"no narration text found in scenes/scene-*.md under {root}",
        )
    provider_ready_narration = build_provider_ready_narration(source_narration)

    voice_id = f"{content_item.content_id}-voice-01"
    filename = "voice-01.md"
    voice_path = root / "voice" / filename

    if voice_path.is_file():
        existing_table = parsing.parse_table(voice_path.read_text(encoding="utf-8"))
        existing_hash_raw = existing_table.get("Script content hash", None)
        if existing_hash_raw is None or not existing_hash_raw.strip():
            return _empty(
                content_id=content_item.content_id, production_id=production_id,
                script_content_hash=current_script_hash,
                aborted=True,
                abort_reason=(
                    f"existing {voice_path} is malformed (no Script content hash "
                    "recorded) — cannot safely determine staleness"
                ),
            )
        existing_hash = parsing.strip_single_backticks(existing_hash_raw)
        if existing_hash == current_script_hash:
            return _empty(
                content_id=content_item.content_id, production_id=production_id,
                voice_id=voice_id, filename=filename, script_content_hash=current_script_hash,
                reasons=["voice/voice-01.md already up to date with the current SCRIPT.md"],
                already_up_to_date=True,
            )
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            voice_id=voice_id, filename=filename, script_content_hash=current_script_hash,
            stale=True,
            stale_reason=(
                f"voice/voice-01.md exists with Script content hash {existing_hash!r}, "
                f"but the current SCRIPT.md hashes to {current_script_hash!r} — the "
                "script changed since this voice track was generated. Refusing to "
                "silently reuse or regenerate; the existing voice/voice-01.md and its "
                "audio artifact are left untouched per agents/voice/CONTRACT.md's "
                "Re-running section."
            ),
        )

    if not voice_configuration or not voice_configuration.strip():
        return _empty(
            content_id=content_item.content_id, production_id=production_id,
            script_content_hash=current_script_hash,
            aborted=True, abort_reason="no voice configuration provided",
        )

    active_provider = provider or LocalTestVoiceProvider(words_per_minute=words_per_minute)
    generated = active_provider.generate(provider_ready_narration, voice_configuration)

    prospective_audio_reference = f"voice/{filename[:-3]}.audio.txt"
    qa_passed, qa_reasons = evaluate_voice_qa(
        narration_text=source_narration,
        recorded_script_hash=current_script_hash,
        current_script_hash=current_script_hash,
        audio_reference=prospective_audio_reference,
        duration_seconds=generated.duration_seconds,
        provider_label=generated.provider_label,
        voice_configuration=generated.voice_configuration,
        generation_status="GENERATED",
    )

    result = VoiceResult(
        content_id=content_item.content_id,
        production_id=production_id,
        voice_id=voice_id,
        filename=filename,
        provider_label=generated.provider_label,
        voice_configuration=generated.voice_configuration,
        source_narration=source_narration,
        provider_ready_narration=provider_ready_narration,
        script_content_hash=current_script_hash,
        audio_reference=prospective_audio_reference,
        duration_seconds=generated.duration_seconds,
        generation_status="GENERATED",
        qa_status="PASS" if qa_passed else "REVISION_REQUIRED",
        qa_reasons=qa_reasons,
        reasons=[f"generated voice track via provider {generated.provider_label!r}"],
        is_placeholder=generated.is_placeholder,
    )

    if apply:
        _apply_result(root, result, generated.artifact_content, production_text)

    return result


def _apply_result(root: Path, result: VoiceResult, artifact_content: str, production_text: str) -> None:
    audio_filename = f"{result.filename[:-3]}.audio.txt"
    audio_path = mutate.write_audio_artifact(root, audio_filename, artifact_content)

    voice_text = render_voice_markdown(result)
    voice_path = mutate.write_voice_file(root, result.filename, voice_text)

    new_status = NEXT_PRODUCTION_STATUS if result.qa_status == "PASS" else None
    updated_production = mutate.apply_production_voiceover(
        production_text,
        voice_record_path=f"voice/{result.filename}",
        narration_source="SCRIPT.md Hook + Narrative beats (via scenes/scene-<n>.md)",
        generation_status=result.generation_status,
        new_production_status=new_status,
    )
    (root / "PRODUCTION.md").write_text(updated_production, encoding="utf-8")

    result.voice_path = str(voice_path)
    result.audio_path = str(audio_path)
    result.production_path = str(root / "PRODUCTION.md")
