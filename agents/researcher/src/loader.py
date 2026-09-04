"""Loads a content item's on-disk records (CONTENT_ITEM.md, research/,
claims/, SCRIPT.md) into the models in models.py.

This is the "structured input" seam CONTRACT.md and the Phase 5 task
description ask for: today it reads local files written by a human or a
prior agent pass. A future live-retrieval source for RESEARCH mode would
implement the same read-only contract this module exposes (return
ResearchEntry objects) without changing anything downstream — see
README.md "Swapping in live retrieval."
"""
from __future__ import annotations

import re
from pathlib import Path

from . import parsing
from .errors import NoLoadableContent, StructuralFailure
from .models import (
    Claim,
    ClaimSupportRelationship,
    Classification,
    ConfidenceLevel,
    ContentBundle,
    ContentItem,
    DiscoveryStatus,
    FactCheckStatus,
    ResearchEntry,
    RetrievalVerified,
    ReviewRecord,
    ReviewVerdict,
    ScriptClaimRow,
    SourceReliability,
)

_REVIEW_FILENAME_RE = re.compile(r"^(?P<role>[a-z_]+)-(?P<attempt>\d+)$")


def normalize_claim_ref(token: str) -> str:
    """"claims/c10.md" / "c10.md" / "c10" -> "c10"."""
    token = token.strip()
    base = token.rsplit("/", 1)[-1]
    if base.endswith(".md"):
        base = base[: -len(".md")]
    return base


def normalize_research_ref(token: str) -> str:
    """"research/01-who-plague-fact-sheet.md" -> "01-who-plague-fact-sheet"."""
    token = token.strip()
    base = token.rsplit("/", 1)[-1]
    if base.endswith(".md"):
        base = base[: -len(".md")]
    return base


def _split_refs(raw: str) -> list[str]:
    tokens = parsing.backtick_tokens(raw)
    if tokens:
        return tokens
    raw = raw.strip()
    if not raw or raw.upper().startswith("N/A"):
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def load_content_item(path: Path) -> ContentItem:
    text = path.read_text(encoding="utf-8")
    identity = parsing.parse_table(text)
    # Stage states live in a second table in the same file; parse_table
    # only returns the first table, so parse the states table separately
    # by scanning from the "## Stage states" section onward.
    sections_text = text.split("## Stage states", 1)
    states = parsing.parse_table(sections_text[1]) if len(sections_text) > 1 else {}

    return ContentItem(
        path=path,
        content_id=parsing.strip_single_backticks(identity.get("Content ID", "")),
        content_pillar=parsing.strip_single_backticks(identity.get("Content pillar", "")),
        status=_extract_current_status(text),
        research_state=parsing.strip_single_backticks(states.get("Research state", "")),
        fact_check_state=parsing.strip_single_backticks(states.get("Fact-check state", "")),
        raw_text=text,
    )


def _extract_current_status(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Current status:"):
            return parsing.strip_single_backticks(line[len("Current status:") :].strip())
    return ""


def load_research(research_dir: Path) -> dict[str, ResearchEntry]:
    entries: dict[str, ResearchEntry] = {}
    if not research_dir.is_dir():
        return entries
    for path in sorted(research_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        table = parsing.parse_table(text)
        sections = parsing.parse_sections(text)
        related_raw = sections.get("Related claims", "")
        related = [normalize_claim_ref(t) for t in _split_refs(related_raw)]
        reliability_raw = parsing.first_backtick_token(table.get("Source reliability", ""))
        try:
            reliability = SourceReliability(reliability_raw)
        except ValueError:
            reliability = SourceReliability.UNVERIFIED

        # Phase 7G additions — defaulted for entries that predate them
        # (templates/RESEARCH.md); never raise on an older, valid entry.
        discovery_raw = parsing.first_backtick_token(table.get("Discovery status", ""))
        try:
            discovery_status = DiscoveryStatus(discovery_raw) if discovery_raw else DiscoveryStatus.ACCEPTED
        except ValueError:
            discovery_status = DiscoveryStatus.ACCEPTED
        provider_result_id = parsing.strip_single_backticks(table.get("Provider result ID", "")) or "N/A"
        retrieval_raw = parsing.first_backtick_token(table.get("Retrieval verified", ""))
        try:
            retrieval_verified = (
                RetrievalVerified(retrieval_raw) if retrieval_raw else RetrievalVerified.UNVERIFIED
            )
        except ValueError:
            retrieval_verified = RetrievalVerified.UNVERIFIED
        support_raw = parsing.first_backtick_token(
            sections.get("Claim support relationship", ""), "N/A"
        )
        try:
            claim_support = ClaimSupportRelationship(support_raw)
        except ValueError:
            claim_support = ClaimSupportRelationship.NOT_APPLICABLE
        rejection_reason = sections.get("Rejection reason", "").strip() or "N/A"

        entries[path.stem] = ResearchEntry(
            path=path,
            content_id=parsing.strip_single_backticks(table.get("Content ID", "")),
            source=table.get("Source", ""),
            source_type=parsing.strip_single_backticks(table.get("Source type", "")),
            source_url=table.get("Source URL / reference", ""),
            source_reliability=reliability,
            related_claims=related,
            conflicting_evidence=sections.get("Conflicting evidence", ""),
            raw_text=text,
            discovery_status=discovery_status,
            provider_result_id=provider_result_id,
            retrieval_verified=retrieval_verified,
            claim_support_relationship=claim_support,
            rejection_reason=rejection_reason,
        )
    return entries


def load_claims(claims_dir: Path) -> dict[str, Claim]:
    claims: dict[str, Claim] = {}
    if not claims_dir.is_dir():
        return claims
    for path in sorted(claims_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        table = parsing.parse_table(text)

        classification_raw = parsing.first_backtick_token(table.get("Classification", ""))
        try:
            classification = Classification(classification_raw)
        except ValueError as exc:
            raise StructuralFailure(
                f"{path}: invalid or missing Classification {classification_raw!r}"
            ) from exc

        confidence_raw = parsing.first_backtick_token(table.get("Confidence level", ""), "N/A")
        try:
            confidence = ConfidenceLevel(confidence_raw)
        except ValueError:
            confidence = ConfidenceLevel.NA

        fact_check_raw = parsing.first_backtick_token(table.get("Fact-check status", ""))
        try:
            fact_check_status = FactCheckStatus(fact_check_raw)
        except ValueError as exc:
            raise StructuralFailure(
                f"{path}: invalid or missing Fact-check status {fact_check_raw!r}"
            ) from exc

        supporting_sources = _split_refs(table.get("Supporting sources", ""))
        derived_from = [
            normalize_claim_ref(t) for t in _split_refs(table.get("Derived from", ""))
        ]

        claims[path.stem] = Claim(
            path=path,
            short_id=path.stem,
            claim_id=parsing.strip_single_backticks(table.get("Claim ID", "")),
            content_id=parsing.strip_single_backticks(table.get("Content ID", "")),
            exact_claim=table.get("Exact claim", ""),
            supporting_sources=supporting_sources,
            derived_from=derived_from,
            evidence=table.get("Evidence", ""),
            confidence_level=confidence,
            classification=classification,
            contradictory_evidence=table.get("Contradictory evidence", ""),
            fact_check_status=fact_check_status,
            raw_text=text,
        )
    return claims


def load_script(script_path: Path) -> tuple[str, list[ScriptClaimRow]]:
    if not script_path.is_file():
        return "", []
    text = script_path.read_text(encoding="utf-8")
    rows: list[ScriptClaimRow] = []
    sections = parsing.parse_sections(text)
    body = sections.get("Verified claims", "")
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if cells[0].lower() == "claim id":
            continue
        if set(cells[0]) <= {"-"}:
            continue
        rows.append(
            ScriptClaimRow(
                short_id=normalize_claim_ref(parsing.strip_single_backticks(cells[0])),
                classification=parsing.strip_single_backticks(cells[1]),
                fact_check_status=parsing.strip_single_backticks(cells[2]),
                beats=cells[3],
            )
        )
    return text, rows


def load_reviews(reviews_dir: Path, role: str) -> list[ReviewRecord]:
    """Load all review attempts for `role`, sorted by attempt number
    ascending (templates/REVIEW.md numbering: reviews/<role>-<n>.md).
    """
    records: list[ReviewRecord] = []
    if not reviews_dir.is_dir():
        return records
    for path in sorted(reviews_dir.glob(f"{role}-*.md")):
        m = _REVIEW_FILENAME_RE.match(path.stem)
        if not m or m.group("role") != role:
            continue
        text = path.read_text(encoding="utf-8")
        table = parsing.parse_table(text)
        verdict_raw = parsing.first_backtick_token(table.get("Verdict", ""))
        try:
            verdict = ReviewVerdict(verdict_raw)
        except ValueError:
            continue  # not a well-formed review file; skip rather than crash
        content_hash = parsing.first_backtick_token(
            table.get("Reviewed content hash", ""), "N/A"
        )
        records.append(
            ReviewRecord(
                path=path,
                role=role,
                attempt=int(m.group("attempt")),
                verdict=verdict,
                reviewed_content_hash=content_hash,
                raw_text=text,
            )
        )
    records.sort(key=lambda r: r.attempt)
    return records


def load_bundle(root: Path) -> ContentBundle:
    """Load everything for one content item directory.

    Raises NoLoadableContent if there is nothing to fact-check at all, or
    StructuralFailure if the data itself is malformed (missing claim file
    a script cites, invalid classification) — both map to CONTRACT.md
    Failure conditions.
    """
    content_item_path = root / "CONTENT_ITEM.md"
    if not content_item_path.is_file():
        raise NoLoadableContent(f"no CONTENT_ITEM.md under {root}")
    content_item = load_content_item(content_item_path)

    research = load_research(root / "research")
    claims = load_claims(root / "claims")
    script_text, script_rows = load_script(root / "SCRIPT.md")

    if not research and not claims:
        raise NoLoadableContent(f"no research or claims found under {root}")

    for row in script_rows:
        if row.short_id not in claims:
            raise StructuralFailure(
                f"SCRIPT.md cites claim {row.short_id!r} with no corresponding "
                f"claims/{row.short_id}.md file"
            )

    return ContentBundle(
        root=root,
        content_item=content_item,
        research=research,
        claims=claims,
        script_text=script_text,
        script_claim_rows=script_rows,
    )
