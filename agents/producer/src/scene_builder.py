"""Deterministic SCRIPT.md -> scene-draft decomposition: the Hook (if
present) becomes its own scene, then one scene per Narrative beat, in
order — no condensation, no paraphrasing, no invented content. See
agents/producer/CONTRACT.md's Forbidden actions ("scene narration must be
verbatim") and Purpose ("SCRIPT -> STRUCTURED SCENES, deterministic").

Reuses agents/researcher/src.parsing (generic table/section parsing) and
.errors (NoLoadableContent / StructuralFailure) rather than inventing new
failure vocabulary.
"""
from __future__ import annotations

import re

from ...researcher.src import parsing
from ...researcher.src.errors import NoLoadableContent, StructuralFailure
from ...researcher.src.models import Claim
from .duration import estimate_duration_seconds
from .models import SceneDraft

_BEAT_RE = re.compile(r"^\d+\.\s*(.*)$")
_CLAIMS_SUFFIX_RE = re.compile(r"—\s*claims:\s*(.+)\s*$")


def _extract_beats(narrative_beats_body: str) -> list[str]:
    """Join each numbered beat's (possibly line-wrapped) text into one
    string per beat, in order."""
    beats: list[str] = []
    current: list[str] = []
    for raw_line in narrative_beats_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _BEAT_RE.match(line)
        if m:
            if current:
                beats.append(" ".join(current))
            current = [m.group(1)]
        elif current:
            current.append(line)
    if current:
        beats.append(" ".join(current))
    return beats


def _clean_beat_text(text: str) -> str:
    """Strips only markdown bold syntax (formatting, not content) and
    collapses whitespace (a SCRIPT.md author may hard-wrap a long beat or
    Hook across multiple source lines for readability, per this repo's
    own established style) — the underlying words are left exactly as
    written in SCRIPT.md, never paraphrased. Whitespace collapsing is
    required, not cosmetic: an embedded newline persisted verbatim into a
    scene file's own `| Narration text | ... |` table cell corrupts that
    markdown table (a cell cannot span lines) — this is the same
    "formatting only, never content" transformation
    agents/voice/src/narration.py's own PROVIDER-READY NARRATION step
    already applies for the identical reason, one stage later.
    """
    cleaned = text.replace("**", "").strip(" —").strip()
    return _collapse_whitespace(cleaned)


def _collapse_whitespace(text: str) -> str:
    """Formatting only, never content — see _clean_beat_text's docstring
    for why this is required, not cosmetic."""
    return re.sub(r"\s+", " ", text).strip()


def _build_scene(
    order: int,
    content_id: str,
    script_reference: str,
    narration_text: str,
    claim_ids: list[str],
    claims: dict[str, Claim],
    words_per_minute: int,
) -> SceneDraft:
    duration = estimate_duration_seconds(narration_text, words_per_minute)
    classifications = sorted({claims[cid].classification.value for cid in claim_ids})
    return SceneDraft(
        scene_id=f"{content_id}-scene-{order:02d}",
        filename=f"scene-{order:02d}.md",
        order=order,
        duration_seconds=duration,
        script_reference=script_reference,
        narration_text=narration_text,
        claim_ids=claim_ids,
        classifications_present=classifications,
    )


def build_scenes(
    script_text: str,
    content_id: str,
    claims: dict[str, Claim],
    words_per_minute: int,
) -> list[SceneDraft]:
    """Raises NoLoadableContent if SCRIPT.md has no usable Narrative beats
    (malformed script -> fail safely, never produce zero/invented scenes).
    Raises StructuralFailure if a beat cites a claim ID with no
    corresponding claims/<id>.md file (never invents a fake claim).
    """
    sections = parsing.parse_sections(script_text)
    hook = sections.get("Hook", "").strip()
    narrative_body = sections.get("Narrative beats", "").strip()
    if not narrative_body:
        raise NoLoadableContent(
            "SCRIPT.md has no (or an empty) '## Narrative beats' section — "
            "nothing to decompose into scenes"
        )

    raw_beats = _extract_beats(narrative_body)
    if not raw_beats:
        raise NoLoadableContent(
            "SCRIPT.md's '## Narrative beats' section has no numbered beats "
            "(expected lines starting '1.', '2.', ...)"
        )

    scenes: list[SceneDraft] = []
    order = 1

    if hook and not hook.upper().startswith("N/A"):
        hook_text = _collapse_whitespace(parsing.strip_single_backticks(hook))
        scenes.append(
            _build_scene(order, content_id, "SCRIPT.md Hook", hook_text, [], claims, words_per_minute)
        )
        order += 1

    for beat_number, raw_beat in enumerate(raw_beats, start=1):
        m = _CLAIMS_SUFFIX_RE.search(raw_beat)
        if m:
            claim_ids = parsing.backtick_tokens(m.group(1))
            beat_text = _clean_beat_text(raw_beat[: m.start()])
        else:
            claim_ids = []
            beat_text = _clean_beat_text(raw_beat)

        for short_id in claim_ids:
            if short_id not in claims:
                raise StructuralFailure(
                    f"SCRIPT.md's Narrative beat {beat_number} cites claim "
                    f"{short_id!r} with no corresponding claims/{short_id}.md file"
                )

        scenes.append(
            _build_scene(
                order,
                content_id,
                f"SCRIPT.md Narrative beat {beat_number}",
                beat_text,
                claim_ids,
                claims,
                words_per_minute,
            )
        )
        order += 1

    return scenes
