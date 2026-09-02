"""The three stage adapters. Each wires together an existing agent's own
loader/hashing/run functions — the orchestrator never reimplements what a
bundle is, how it's hashed, or what a PASS means. Nothing here duplicates
evidence/signal evaluation; every `run` callable IS the agent's own
`run_fact_check`/`run_safety_review`/`run_originality_review`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ...researcher.src import factcheck as researcher_factcheck
from ...researcher.src.hashing import compute_reviewed_content_hash as researcher_hash
from ...researcher.src.loader import load_bundle as researcher_load_bundle
from ...researcher.src.pipeline import ROLE as FACT_CHECK_ROLE_PREFIX
from ...researcher.src.pipeline import run_fact_check
from ...safety.src.hashing import compute_reviewed_content_hash as safety_hash
from ...safety.src.loader import load_safety_bundle
from ...safety.src.pipeline import ROLE_FILE_PREFIX as SAFETY_ROLE_PREFIX
from ...safety.src.pipeline import run_safety_review
from ...originality.src.hashing import compute_reviewed_content_hash as originality_hash
from ...originality.src.loader import load_originality_bundle
from ...originality.src.pipeline import ROLE_FILE_PREFIX as ORIGINALITY_ROLE_PREFIX
from ...originality.src.pipeline import run_originality_review
from .models import FACT_CHECK, ORIGINALITY_REVIEW, SAFETY_REVIEW


@dataclass
class StageAdapter:
    stage: str
    review_role_prefix: str
    load_bundle: Callable[[Path], Any]  # may raise NoLoadableContent/StructuralFailure
    compute_hash: Callable[[Any], str]
    run: Callable[[Path, bool], Any]  # (root, apply) -> stage's own Result dataclass


def _researcher_hash(bundle) -> str:
    claim_ids = researcher_factcheck.claims_under_review(bundle)
    return researcher_hash(bundle, claim_ids)


def build_default_adapters(
    originality_channel_index=None,
    originality_reference_paths=None,
) -> list[StageAdapter]:
    """The three adapters in pipeline order. `originality_channel_index`/
    `originality_reference_paths` are threaded through to
    run_originality_review exactly as they are to a direct call — see
    agents/originality/CONTRACT.md's Inputs for what they mean.
    """
    return [
        StageAdapter(
            stage=FACT_CHECK,
            review_role_prefix=FACT_CHECK_ROLE_PREFIX,
            load_bundle=researcher_load_bundle,
            compute_hash=_researcher_hash,
            run=lambda root, apply: run_fact_check(root, apply=apply),
        ),
        StageAdapter(
            stage=SAFETY_REVIEW,
            review_role_prefix=SAFETY_ROLE_PREFIX,
            load_bundle=load_safety_bundle,
            compute_hash=safety_hash,
            run=lambda root, apply: run_safety_review(root, apply=apply),
        ),
        StageAdapter(
            stage=ORIGINALITY_REVIEW,
            review_role_prefix=ORIGINALITY_ROLE_PREFIX,
            load_bundle=lambda root: load_originality_bundle(
                root, channel_index=originality_channel_index, reference_paths=originality_reference_paths
            ),
            compute_hash=originality_hash,
            run=lambda root, apply: run_originality_review(
                root, apply=apply, channel_index=originality_channel_index,
                reference_paths=originality_reference_paths,
            ),
        ),
    ]
