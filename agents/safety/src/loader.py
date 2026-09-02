"""Loads a content item's on-disk records for safety review. Reuses
agents/researcher/src's generic loading utilities (content item, claims,
script) rather than re-parsing the same templates a second way — see
README.md "Relationship to agents/researcher".
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing
from ...researcher.src.errors import NoLoadableContent, StructuralFailure
from ...researcher.src.loader import load_claims, load_content_item, load_script
from .models import SafetyBundle


def load_safety_bundle(root: Path) -> SafetyBundle:
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        raise NoLoadableContent(f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    script_path = root / "SCRIPT.md"
    if not script_path.is_file():
        raise NoLoadableContent(f"no SCRIPT.md under {root} — nothing to safety-review yet")
    script_text = script_path.read_text(encoding="utf-8")
    script_table = parsing.parse_table(script_text)
    script_sections = parsing.parse_sections(script_text)

    claims = load_claims(root / "claims")
    _, script_rows = load_script(script_path)
    script_claim_ids = [row.short_id for row in script_rows]

    for short_id in script_claim_ids:
        if short_id not in claims:
            raise StructuralFailure(
                f"SCRIPT.md cites claim {short_id!r} with no corresponding "
                f"claims/{short_id}.md file"
            )

    return SafetyBundle(
        content_item=content_item,
        script_text=script_text,
        script_table=script_table,
        script_sections=script_sections,
        claims=claims,
        script_claim_ids=script_claim_ids,
    )
