"""Data model mirroring templates/CONTENT_ITEM.md, RESEARCH.md, CLAIM.md,
REVIEW.md. Field names/enums are taken verbatim from those templates —
this module does not invent new vocabulary, only represents it in Python.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Classification(str, Enum):
    FACT = "FACT"
    ASSUMPTION = "ASSUMPTION"
    INFERENCE = "INFERENCE"
    SPECULATION = "SPECULATION"


class FactCheckStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    DISPUTED = "DISPUTED"
    FALSE = "FALSE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NA = "N/A"


class SourceReliability(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"


class ReviewVerdict(str, Enum):
    PASS = "PASS"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    REJECT = "REJECT"


class EvidenceSupport(str, Enum):
    """Computed during FACT_CHECK evaluation; not a persisted CLAIM.md
    field — see agents/researcher/CONTRACT.md's Phase 5 implementation
    notes for why. Distinct from FactCheckStatus: this is "what the
    evidence shows," FactCheckStatus is "what that means for the claim."
    """

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # ASSUMPTION claims


@dataclass
class ResearchEntry:
    path: Path
    content_id: str
    source: str
    source_type: str
    source_url: str
    source_reliability: SourceReliability
    related_claims: list[str]  # short claim ids, e.g. "c10"
    conflicting_evidence: str
    raw_text: str = field(repr=False, default="")


@dataclass
class Claim:
    path: Path
    short_id: str  # filename stem, e.g. "c11" — canonical local key
    claim_id: str  # full id from the file, e.g. "wi-...-c11"
    content_id: str
    exact_claim: str
    supporting_sources: list[str]  # research file references, raw tokens
    derived_from: list[str]  # short claim ids
    evidence: str
    confidence_level: ConfidenceLevel
    classification: Classification
    contradictory_evidence: str
    fact_check_status: FactCheckStatus
    raw_text: str = field(repr=False, default="")


@dataclass
class ContentItem:
    path: Path
    content_id: str
    content_pillar: str
    status: str
    research_state: str
    fact_check_state: str
    raw_text: str = field(repr=False, default="")


@dataclass
class ScriptClaimRow:
    short_id: str
    classification: str
    fact_check_status: str
    beats: str


@dataclass
class ContentBundle:
    """Everything the agent loaded for one content item."""

    root: Path
    content_item: ContentItem
    research: dict[str, ResearchEntry]  # keyed by filename stem
    claims: dict[str, Claim]  # keyed by short_id
    script_text: str
    script_claim_rows: list[ScriptClaimRow]


@dataclass
class ReviewRecord:
    path: Path
    role: str
    attempt: int
    verdict: ReviewVerdict
    reviewed_content_hash: str
    raw_text: str = field(repr=False, default="")


@dataclass
class ClaimEvaluation:
    short_id: str
    classification: Classification
    evidence_support: EvidenceSupport
    fact_check_status: FactCheckStatus
    reason: str


@dataclass
class FactCheckResult:
    content_id: str
    verdict: ReviewVerdict
    reasons: list[str]
    required_changes: list[str]
    notes: list[str]
    claim_evaluations: list[ClaimEvaluation]
    escalate_to_human: bool
    content_hash: str
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    review_path: str = ""
