"""The canonical `Production status` sequence, exactly as
templates/PRODUCTION.md documents it — read-only knowledge, reused here
solely to decide whether a stage's job has already been completed by a
*later* stage on a repeat call, never to duplicate any agent's own
precondition logic or to write anything.

Why this exists: each production agent's own CONTRACT.md accepts only a
narrow re-entry window (its own precondition state, plus the state it
itself sets on success — e.g. agents/voice/'s ALLOWED_PRODUCTION_STATUSES
= {PRODUCTION_PLANNING, VISUAL_PLANNING}). That's correct and sufficient
for each agent standalone. But this orchestrator calls *every* stage on
every invocation (see CONTRACT.md's "Self-review behavior" — there is no
per-stage skip based on prior orchestrator state, since none is kept).
Once a later stage has genuinely advanced Production status past an
earlier stage's own accepted window, re-invoking that earlier stage would
hit its precondition gate and report a false BLOCKED — not because
anything is wrong, but only because this orchestrator asked a question
that agent was never designed to answer twice removed. Comparing the
*current* status against the canonical sequence, read once per stage from
the one Production status field every agent already reads, tells this
orchestrator "a later stage already finished this one's job" without
importing or duplicating any single agent's own precondition set.
"""
from __future__ import annotations

from .models import ASSEMBLER, ASSETS, CAPTIONS, PRODUCTION_QA, THUMBNAIL, VISUAL_PLANNER, VOICE

# Verbatim from templates/PRODUCTION.md's "Production status" section.
PRODUCTION_STATUS_SEQUENCE = [
    "PRODUCTION_PLANNING",
    "VOICE",
    "VISUAL_PLANNING",
    "ASSET_COLLECTION",
    "ASSEMBLY",
    "CAPTIONS",
    "THUMBNAIL",
    "METADATA",
    "PRODUCTION_QA",
    "HUMAN_REVIEW",
    "APPROVED",
    "READY_TO_PUBLISH",
]

# The Production status value each stage's own successful completion
# sets (its documented NEXT_PRODUCTION_STATUS, or the literal value its
# _apply_result hard-codes) — read from each agent's own src/pipeline.py,
# never guessed. PRODUCER has no entry: it doesn't gate on Production
# status at all (only on CONTENT_ITEM.md status + its own script-hash
# check), so it is always safe to re-invoke regardless of how far
# production has progressed — confirmed empirically, not assumed.
STAGE_COMPLETION_STATUS = {
    VOICE: "VISUAL_PLANNING",
    VISUAL_PLANNER: "ASSET_COLLECTION",
    ASSETS: "ASSEMBLY",
    ASSEMBLER: "CAPTIONS",
    CAPTIONS: "THUMBNAIL",
    THUMBNAIL: "METADATA",
    PRODUCTION_QA: "HUMAN_REVIEW",
}


def _status_index(status: str) -> int:
    try:
        return PRODUCTION_STATUS_SEQUENCE.index(status)
    except ValueError:
        return -1  # an unrecognized status is never treated as "ahead" of anything


def stage_already_completed_by_a_later_stage(current_status: str, stage: str) -> bool:
    """True only when Production status has moved *strictly past* the
    status this stage's own success would set — i.e. some later stage
    already did this one's job on an earlier call. Equal to the stage's
    own completion status is still within that agent's own accepted
    re-entry window (its own idempotent already-up-to-date check applies
    normally) and is deliberately NOT treated as "already done" here.
    """
    completion_status = STAGE_COMPLETION_STATUS.get(stage)
    if completion_status is None:
        return False
    return _status_index(current_status) > _status_index(completion_status)
