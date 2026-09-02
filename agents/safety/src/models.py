"""Safety-specific data model. Reuses agents/researcher/src.models'
ReviewVerdict/ReviewRecord/ContentItem/Classification directly (see
README.md) rather than redefining them — those are already generic,
role-agnostic vocabulary from templates/REVIEW.md and
templates/CONTENT_ITEM.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    LOW_RISK = "LOW_RISK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_RISK = "HIGH_RISK"


class SafetySignal(str, Enum):
    DANGEROUS_INSTRUCTION = "DANGEROUS_INSTRUCTION"
    ILLEGAL_ACTIVITY = "ILLEGAL_ACTIVITY"
    DECEPTION = "DECEPTION"
    IMPERSONATION = "IMPERSONATION"
    SYNTHETIC_MEDIA = "SYNTHETIC_MEDIA"
    AI_DISCLOSURE = "AI_DISCLOSURE"
    MISINFORMATION_RISK = "MISINFORMATION_RISK"
    PRIVACY = "PRIVACY"
    DEFAMATION = "DEFAMATION"
    COPYRIGHT_RISK = "COPYRIGHT_RISK"
    SENSITIVE_CONTENT = "SENSITIVE_CONTENT"
    TITLE_THUMBNAIL_MISREPRESENTATION = "TITLE_THUMBNAIL_MISREPRESENTATION"


# Signals severe enough that HIGH_RISK maps to REJECT rather than
# REVISION_REQUIRED — see CONTRACT.md "Verdict derivation" rule 1.
REJECT_TIER_SIGNALS = frozenset({SafetySignal.DANGEROUS_INSTRUCTION, SafetySignal.ILLEGAL_ACTIVITY})


@dataclass
class SignalEvaluation:
    signal: SafetySignal
    risk_level: RiskLevel
    reason: str
    evidence: str = ""


@dataclass
class SafetyBundle:
    """Everything the Safety Reviewer loaded for one content item."""

    content_item: "object"  # agents.researcher.src.models.ContentItem
    script_text: str
    script_table: dict
    script_sections: dict
    claims: dict  # short_id -> agents.researcher.src.models.Claim
    script_claim_ids: list


@dataclass
class SafetyReviewResult:
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
