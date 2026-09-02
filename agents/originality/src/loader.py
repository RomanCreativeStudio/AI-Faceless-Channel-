"""Loads a content item's on-disk records for originality review, plus
(optionally auto-discovered) sibling channel content metadata and
supplied reference material. Reuses agents/researcher/src's generic
loading utilities rather than re-parsing the same templates a second way
— see README.md "Relationship to agents/researcher and agents/safety".
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing
from ...researcher.src.errors import NoLoadableContent, StructuralFailure
from ...researcher.src.loader import (
    load_claims,
    load_content_item,
    load_research,
    load_script,
)
from .models import ChannelItemSummary, OriginalityBundle


def _summarize_content_item(item_root: Path) -> ChannelItemSummary | None:
    content_item_path = item_root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        return None
    identity = parsing.parse_table(content_item_path.read_text(encoding="utf-8"))
    content_id = parsing.strip_single_backticks(identity.get("Content ID", ""))
    title = identity.get("Working title", "") or identity.get("Final title", "")
    premise = identity.get("Premise", "")

    hook = ""
    beat_count = 0
    script_path = item_root / "SCRIPT.md"
    if script_path.is_file():
        sections = parsing.parse_sections(script_path.read_text(encoding="utf-8"))
        hook = sections.get("Hook", "")
        beats = sections.get("Narrative beats", "")
        beat_count = sum(1 for ln in beats.splitlines() if ln.strip()[:2].rstrip(".").isdigit())

    return ChannelItemSummary(content_id=content_id, title=title, premise=premise, hook=hook, beat_count=beat_count)


def discover_channel_index(root: Path) -> list[ChannelItemSummary]:
    """Scan sibling content items under the same `content/` tree,
    excluding `root` itself. Never touches anything outside the repo's
    own `content/` directory, and never performs any network access.
    """
    root = root.resolve()
    content_dir = None
    for ancestor in [root, *root.parents]:
        if ancestor.name == "content":
            content_dir = ancestor
            break
    if content_dir is None:
        return []

    summaries: list[ChannelItemSummary] = []
    for content_item_path in content_dir.glob("*/*/CONTENT_ITEM.md"):
        item_root = content_item_path.parent
        if item_root.resolve() == root:
            continue
        summary = _summarize_content_item(item_root)
        if summary is not None:
            summaries.append(summary)
    return summaries


def load_reference_texts(reference_paths: list[Path] | None) -> dict:
    texts: dict = {}
    for path in reference_paths or []:
        path = Path(path)
        if path.is_file():
            texts[str(path)] = path.read_text(encoding="utf-8")
    return texts


def load_originality_bundle(
    root: Path,
    channel_index: list[ChannelItemSummary] | None = None,
    reference_paths: list[Path] | None = None,
) -> OriginalityBundle:
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        raise NoLoadableContent(f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    script_path = root / "SCRIPT.md"
    if not script_path.is_file():
        raise NoLoadableContent(f"no SCRIPT.md under {root} — nothing to originality-review yet")
    script_text = script_path.read_text(encoding="utf-8")
    script_table = parsing.parse_table(script_text)
    script_sections = parsing.parse_sections(script_text)

    claims = load_claims(root / "claims")
    research = load_research(root / "research")
    _, script_rows = load_script(script_path)
    script_claim_ids = [row.short_id for row in script_rows]

    for short_id in script_claim_ids:
        if short_id not in claims:
            raise StructuralFailure(
                f"SCRIPT.md cites claim {short_id!r} with no corresponding "
                f"claims/{short_id}.md file"
            )

    if channel_index is None:
        channel_index = discover_channel_index(root)

    return OriginalityBundle(
        content_item=content_item,
        script_text=script_text,
        script_table=script_table,
        script_sections=script_sections,
        claims=claims,
        research=research,
        script_claim_ids=script_claim_ids,
        channel_index=channel_index,
        reference_texts=load_reference_texts(reference_paths),
    )
