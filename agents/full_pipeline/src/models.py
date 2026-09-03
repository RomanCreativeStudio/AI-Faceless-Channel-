"""Full-pipeline result model. Introduces no new hashing or staleness
algorithm — see CONTRACT.md "Freshness and invalidation". `PipelineResult`
is in-memory/CLI-output coordination metadata only, never persisted to
disk (this orchestrator has no mutate.py — see CONTRACT.md "Artifact
ownership").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Stage name constants, in the real, verified execution order — see
# CONTRACT.md's "Stage ordering" for why VOICE precedes VISUAL_PLANNER.
CONTENT_REVIEW = "CONTENT_REVIEW"
CONTENT_APPROVAL_GATE = "CONTENT_APPROVAL_GATE"
PRODUCER = "PRODUCER"
VOICE = "VOICE"
VISUAL_PLANNER = "VISUAL_PLANNER"
ASSETS = "ASSETS"
ASSEMBLER = "ASSEMBLER"
CAPTIONS = "CAPTIONS"
THUMBNAIL = "THUMBNAIL"
PRODUCTION_QA = "PRODUCTION_QA"

STAGE_ORDER = [
    CONTENT_REVIEW,
    CONTENT_APPROVAL_GATE,
    PRODUCER,
    VOICE,
    VISUAL_PLANNER,
    ASSETS,
    ASSEMBLER,
    CAPTIONS,
    THUMBNAIL,
    PRODUCTION_QA,
]

PRODUCTION_STAGE_ORDER = [
    PRODUCER, VOICE, VISUAL_PLANNER, ASSETS, ASSEMBLER, CAPTIONS, THUMBNAIL, PRODUCTION_QA,
]

# The six terminal pipeline_status values the task requires — see
# CONTRACT.md's "Terminal states" table for exactly what each means.
PASS = "PASS"
REVISION_REQUIRED = "REVISION_REQUIRED"
BLOCKED = "BLOCKED"
ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
SYSTEM_ERROR = "SYSTEM_ERROR"
COMPLETE = "COMPLETE"

VALID_PIPELINE_STATUSES = {PASS, REVISION_REQUIRED, BLOCKED, ESCALATE_TO_HUMAN, SYSTEM_ERROR, COMPLETE}

# Exactly one attempt per stage per call — see CONTRACT.md "Self-review
# behavior" for why this is a permanent architectural fact, not a
# placeholder for a future in-process retry loop.
MAX_STAGE_ATTEMPTS = 1


@dataclass
class StageRunOutcome:
    """One stage's outcome as this orchestrator sees it, normalized from
    that stage's own (heterogeneous) result shape by src/stages.py."""

    stage: str
    executed: bool
    skipped: bool
    outcome: str  # PASS | REVISION_REQUIRED | BLOCKED | REJECT | ESCALATED | SYSTEM_ERROR
    reasons: list[str] = field(default_factory=list)
    produced: bool = False  # True if this stage actually wrote something new this run
    stale: bool = False
    attempt: int = 0
    raw_result: "object | None" = None  # the real underlying agent Result dataclass


@dataclass
class PipelineResult:
    content_id: str
    pipeline_status: str
    current_stage: str
    completed_stages: list[str] = field(default_factory=list)
    skipped_stages: list[str] = field(default_factory=list)
    blocked_stages: list[str] = field(default_factory=list)
    failed_stages: list[str] = field(default_factory=list)  # REVISION_REQUIRED
    escalated_stages: list[str] = field(default_factory=list)
    revision_requests: dict = field(default_factory=dict)  # stage -> [reasons]
    attempt_counts: dict = field(default_factory=dict)  # stage -> int
    stale_artifacts: list[str] = field(default_factory=list)
    human_action_required: bool = False
    human_action_reason: str = ""
    terminal_reason: str = ""
    stage_results: dict = field(default_factory=dict)  # stage -> StageRunOutcome
    apply: bool = False
    aborted: bool = False
    abort_reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
