"""Path/field-whitelisted writers for the Voice agent: only fresh
voice/voice-<n>.md + voice/voice-<n>.audio.txt files, and PRODUCTION.md's
Voiceover information section + Production status — no generic "write
anything" helper. See CONTRACT.md's Allowed actions.

`_replace_table_field`/`_replace_section_body` are duplicated small
helpers rather than imported cross-agent, mirroring
agents/safety/src/mutate.py's and agents/visual_planner/src/mutate.py's
own precedent for the same pattern — see those modules' docstrings for
why.
"""
from __future__ import annotations

import re
from pathlib import Path

_VOICE_FILENAME_RE = re.compile(r"^voice-\d+\.md$")
_AUDIO_FILENAME_RE = re.compile(r"^voice-\d+\.audio\.txt$")
# Phase 8: the additional, closed set of real-audio container extensions a
# real VoiceProvider may produce — still a hard whitelist, never "any
# extension", matching every other writer in this module exactly.
_AUDIO_BINARY_FILENAME_RE = re.compile(r"^voice-\d+\.wav$")


def write_voice_file(root: Path, filename: str, text: str) -> Path:
    if not _VOICE_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/voice may not write voice file {filename!r} — "
            "only voice-<n>.md is permitted"
        )
    voice_dir = root / "voice"
    voice_dir.mkdir(exist_ok=True)
    path = voice_dir / filename
    path.write_text(text, encoding="utf-8")
    return path


def write_audio_artifact(root: Path, filename: str, content: str) -> Path:
    if not _AUDIO_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/voice may not write audio artifact {filename!r} — "
            "only voice-<n>.audio.txt is permitted"
        )
    voice_dir = root / "voice"
    voice_dir.mkdir(exist_ok=True)
    path = voice_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def write_audio_artifact_binary(root: Path, filename: str, data: bytes) -> Path:
    """Phase 8: the one new write path for a real VoiceProvider's genuine
    binary audio — filename-whitelisted exactly like every other writer in
    this module, just a different, still-closed extension set.
    """
    if not _AUDIO_BINARY_FILENAME_RE.match(filename):
        raise PermissionError(
            f"agents/voice may not write binary audio artifact {filename!r} — "
            "only voice-<n>.wav is permitted"
        )
    voice_dir = root / "voice"
    voice_dir.mkdir(exist_ok=True)
    path = voice_dir / filename
    path.write_bytes(data)
    return path


def _replace_table_field(text: str, field_name: str, new_value: str) -> str:
    pattern = re.compile(
        r"^(\|\s*" + re.escape(field_name) + r"\s*\|\s*).*?(\s*\|\s*)$", re.MULTILINE
    )
    if not pattern.search(text):
        raise ValueError(f"field {field_name!r} not found as a table row")
    return pattern.sub(lambda m: f"{m.group(1)}{new_value}{m.group(2)}", text, count=1)


def _replace_section_body(text: str, heading: str, new_body: str) -> str:
    marker = f"## {heading}"
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"PRODUCTION.md has no '{marker}' section")
    body_start = idx + len(marker)
    rest = text[body_start:]
    next_heading_idx = rest.find("\n## ")
    body_end = body_start + (next_heading_idx if next_heading_idx != -1 else len(rest))
    return text[:body_start] + "\n\n" + new_body.strip() + "\n\n" + text[body_end:].lstrip("\n")


def apply_production_voiceover(
    text: str,
    voice_record_path: str,
    narration_source: str,
    generation_status: str,
    new_production_status: str | None,
) -> str:
    body = (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Voice record | `{voice_record_path}` |\n"
        f"| Narration source | {narration_source} |\n"
        f"| Generation status | `{generation_status}` |"
    )
    text = _replace_section_body(text, "Voiceover information", body)
    if new_production_status:
        text = _replace_table_field(text, "Production status", f"`{new_production_status}`")
    return text
