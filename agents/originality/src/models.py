"""Originality-specific data model. Defined independently rather than
imported from agents/safety (siblings, not dependents of each other) even
though the RiskLevel vocabulary is the same shape — see CONTRACT.md
"Relationship to agents/researcher and agents/safety". Reuses
agents/researcher/src.models' ReviewVerdict/ReviewRecord/ContentItem/
Classification directly (already generic, role-agnostic).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RiskLevel(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    LOW_RISK = "LOW_RISK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_RISK = "HIGH_RISK"


class OriginalitySignal(str, Enum):
    INTERNAL_DUPLICATION = "INTERNAL_DUPLICATION"
    CONCEPT_DISTINCTIVENESS = "CONCEPT_DISTINCTIVENESS"
    FRAMING_DISTINCTIVENESS = "FRAMING_DISTINCTIVENESS"
    SCRIPT_DISTINCTIVENESS = "SCRIPT_DISTINCTIVENESS"
    SOURCE_DEPENDENCE = "SOURCE_DEPENDENCE"
    TEMPLATE_REPETITION = "TEMPLATE_REPETITION"
    TITLE_HOOK_DISTINCTIVENESS = "TITLE_HOOK_DISTINCTIVENESS"
    EXTERNAL_SIMILARITY_RISK = "EXTERNAL_SIMILARITY_RISK"


# No originality signal ever escalates to REJECT — see CONTRACT.md "Core
# principle": a definitive duplication/plagiarism judgment is a human
# call, never this system's. Unlike Safety, this set is intentionally
# empty; kept as a named constant so verdict derivation reads the same
# shape as agents/safety/src/review.py rather than special-casing itself.
REJECT_TIER_SIGNALS: frozenset[OriginalitySignal] = frozenset()


@dataclass
class SignalEvaluation:
    signal: OriginalitySignal
    risk_level: RiskLevel
    reason: str
    evidence: str = ""


@dataclass
class ChannelItemSummary:
    """Lightweight metadata for one *other* content item, used for
    INTERNAL_DUPLICATION / TEMPLATE_REPETITION comparisons. Never the
    current item being reviewed."""

    content_id: str
    title: str
    premise: str
    hook: str
    beat_count: int = 0


@dataclass
class OriginalityBundle:
    content_item: "object"  # agents.researcher.src.models.ContentItem
    script_text: str
    script_table: dict
    script_sections: dict
    claims: dict  # short_id -> agents.researcher.src.models.Claim
    research: dict  # filename stem -> agents.researcher.src.models.ResearchEntry
    script_claim_ids: list
    channel_index: list  # list[ChannelItemSummary], excludes the current item
    reference_texts: dict  # {path_str: text} of supplied comparison material


@dataclass
class OriginalityReviewResult:
    content_id: str
    verdict: "object"  # agents.researcher.src.models.ReviewVerdict
    signal_evaluations: list[SignalEvaluation]
    reasons: list[str]
    required_changes: list[str]
    notes: list[str]
    escalate_to_human: bool
    content_hash: str
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    review_path: str = ""
