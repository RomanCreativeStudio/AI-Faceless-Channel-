"""The eight originality dimensions from CONTRACT.md. Deterministic,
lexical/structural only — no semantic embeddings, no NLP model. Word-set
overlap (Jaccard similarity) and curated stock-phrase lists are crude by
design: they catch some explicit, blatant cases and will miss subtler
ones. See README.md "Known limitations" — never treat a LOW_RISK/
NOT_APPLICABLE result here as confirmation of originality.
"""
from __future__ import annotations

import re

from ...researcher.src.models import Classification
from .models import OriginalityBundle, OriginalitySignal, RiskLevel, SignalEvaluation

_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "is",
    "are", "was", "were", "with", "this", "that", "how", "what", "why",
    "did", "does", "do", "it", "its", "as", "at", "by", "from", "be",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_STOCK_PHRASES = [
    "in this video, we will explore", "in this video we will explore",
    "have you ever wondered", "let's dive in", "let's take a look",
    "in conclusion", "without further ado", "buckle up", "stay tuned",
    "in today's video",
]

_ANALYTICAL_MARKERS = [
    "why", "how", "consequence", "impact", "lesson", "reveals", "changed",
    "meant", "what if", "trade-off", "tradeoff", "cost",
]


def _stock_phrase_hits(text: str) -> list[str]:
    lower = text.lower()
    return [p for p in _STOCK_PHRASES if p in lower]


def _title(bundle: OriginalityBundle) -> str:
    from ...researcher.src import parsing

    identity = parsing.parse_table(bundle.content_item.raw_text)
    return identity.get("Working title", "") or identity.get("Final title", "")


def _premise(bundle: OriginalityBundle) -> str:
    from ...researcher.src import parsing

    identity = parsing.parse_table(bundle.content_item.raw_text)
    return identity.get("Premise", "")


def _hook(bundle: OriginalityBundle) -> str:
    return bundle.script_sections.get("Hook", "")


def _body_text(bundle: OriginalityBundle) -> str:
    return "\n".join(v for k, v in bundle.script_sections.items())


DUPLICATION_HIGH_THRESHOLD = 0.6
DUPLICATION_REVIEW_THRESHOLD = 0.35


def check_internal_duplication(bundle: OriginalityBundle) -> SignalEvaluation:
    if not bundle.channel_index:
        return SignalEvaluation(
            OriginalitySignal.INTERNAL_DUPLICATION, RiskLevel.NOT_APPLICABLE,
            "no other channel content available to compare against",
        )

    my_topic_words = _words(_title(bundle)) | _words(_premise(bundle))
    my_hook_words = _words(_hook(bundle))

    best_topic = (0.0, "")
    best_hook = (0.0, "")
    for other in bundle.channel_index:
        topic_sim = _jaccard(my_topic_words, _words(other.title) | _words(other.premise))
        if topic_sim > best_topic[0]:
            best_topic = (topic_sim, other.content_id)
        hook_sim = _jaccard(my_hook_words, _words(other.hook))
        if hook_sim > best_hook[0]:
            best_hook = (hook_sim, other.content_id)

    worst_sim, worst_id, kind = max(
        (best_topic[0], best_topic[1], "topic/premise"),
        (best_hook[0], best_hook[1], "hook"),
    )
    if worst_sim >= DUPLICATION_HIGH_THRESHOLD:
        return SignalEvaluation(
            OriginalitySignal.INTERNAL_DUPLICATION, RiskLevel.HIGH_RISK,
            f"{kind} overlaps {worst_sim:.0%} (word-set Jaccard) with existing "
            f"content item {worst_id!r} — substantial repeat risk",
        )
    if worst_sim >= DUPLICATION_REVIEW_THRESHOLD:
        return SignalEvaluation(
            OriginalitySignal.INTERNAL_DUPLICATION, RiskLevel.REVIEW_REQUIRED,
            f"{kind} overlaps {worst_sim:.0%} with existing content item "
            f"{worst_id!r} — similar topic is not automatically copied "
            "content, a human should confirm the angle differs",
        )
    return SignalEvaluation(
        OriginalitySignal.INTERNAL_DUPLICATION, RiskLevel.LOW_RISK,
        f"highest overlap found was {worst_sim:.0%}, below the review threshold",
    )


def check_concept_distinctiveness(bundle: OriginalityBundle) -> SignalEvaluation:
    premise = _premise(bundle).strip()
    if len(premise) < 40:
        return SignalEvaluation(
            OriginalitySignal.CONCEPT_DISTINCTIVENESS, RiskLevel.REVIEW_REQUIRED,
            f"premise is only {len(premise)} characters — too short for this "
            "MVP to identify a thesis; a human should confirm one exists",
        )
    return SignalEvaluation(
        OriginalitySignal.CONCEPT_DISTINCTIVENESS, RiskLevel.LOW_RISK,
        "premise has enough content for a thesis to plausibly be present "
        "(this MVP cannot judge whether it is a *good* one)",
    )


def check_framing_distinctiveness(bundle: OriginalityBundle) -> SignalEvaluation:
    text = _body_text(bundle).lower()
    if any(marker in text for marker in _ANALYTICAL_MARKERS):
        return SignalEvaluation(
            OriginalitySignal.FRAMING_DISTINCTIVENESS, RiskLevel.LOW_RISK,
            "analytical framing language found (why/how/impact/consequence-type wording)",
        )
    return SignalEvaluation(
        OriginalitySignal.FRAMING_DISTINCTIVENESS, RiskLevel.REVIEW_REQUIRED,
        "no analytical framing language found — script may be a plain "
        "chronological summary rather than an angled narrative; a human "
        "should confirm",
    )


def check_script_distinctiveness(bundle: OriginalityBundle) -> SignalEvaluation:
    hits = _stock_phrase_hits(_hook(bundle) + " " + bundle.script_sections.get("Conclusion", ""))
    if hits:
        return SignalEvaluation(
            OriginalitySignal.SCRIPT_DISTINCTIVENESS, RiskLevel.REVIEW_REQUIRED,
            f"generic stock phrase(s) found: {hits} — flagged for human "
            "judgment, not an automatic failure",
        )
    return SignalEvaluation(
        OriginalitySignal.SCRIPT_DISTINCTIVENESS, RiskLevel.LOW_RISK,
        "no stock/generic phrases from this MVP's curated list found",
    )


def _real_sources(tokens: list) -> set:
    return {t for t in tokens if t.strip().upper() not in ("", "N/A")}


def check_source_dependence(bundle: OriginalityBundle) -> SignalEvaluation:
    fact_claims = [c for c in bundle.claims.values() if c.classification is Classification.FACT]
    if len(fact_claims) < 2:
        return SignalEvaluation(
            OriginalitySignal.SOURCE_DEPENDENCE, RiskLevel.NOT_APPLICABLE,
            "fewer than two FACT claims — not enough to assess source spread",
        )
    distinct_sources = set()
    for c in fact_claims:
        distinct_sources.update(_real_sources(c.supporting_sources))
    if len(distinct_sources) <= 1:
        return SignalEvaluation(
            OriginalitySignal.SOURCE_DEPENDENCE, RiskLevel.HIGH_RISK,
            f"{len(fact_claims)} FACT claims cite only {len(distinct_sources)} "
            "distinct real source(s) (excluding N/A) — script may be overly "
            "dependent on one source, or lacks citations entirely",
        )
    return SignalEvaluation(
        OriginalitySignal.SOURCE_DEPENDENCE, RiskLevel.LOW_RISK,
        f"{len(fact_claims)} FACT claims draw on {len(distinct_sources)} distinct sources",
    )


def check_template_repetition(bundle: OriginalityBundle) -> SignalEvaluation:
    if not bundle.channel_index:
        return SignalEvaluation(
            OriginalitySignal.TEMPLATE_REPETITION, RiskLevel.NOT_APPLICABLE,
            "no other channel content available to compare structure against",
        )
    my_hits = set(_stock_phrase_hits(_body_text(bundle)))
    if not my_hits:
        return SignalEvaluation(
            OriginalitySignal.TEMPLATE_REPETITION, RiskLevel.LOW_RISK,
            "no stock phrasing in this item to compare for channel-wide repetition",
        )
    repeated_in = [o.content_id for o in bundle.channel_index if my_hits & set(_stock_phrase_hits(o.hook))]
    if len(repeated_in) >= 2:
        return SignalEvaluation(
            OriginalitySignal.TEMPLATE_REPETITION, RiskLevel.REVIEW_REQUIRED,
            f"stock phrasing {sorted(my_hits)} also appears in {len(repeated_in)} "
            f"other channel items ({repeated_in}) — may indicate a formulaic "
            "channel-wide template rather than a one-off",
        )
    return SignalEvaluation(
        OriginalitySignal.TEMPLATE_REPETITION, RiskLevel.LOW_RISK,
        "stock phrasing found but not repeated across other channel content",
    )


def check_title_hook_distinctiveness(bundle: OriginalityBundle) -> SignalEvaluation:
    title_words = _words(_title(bundle))
    hook_words = _words(_hook(bundle))
    if not hook_words:
        return SignalEvaluation(
            OriginalitySignal.TITLE_HOOK_DISTINCTIVENESS, RiskLevel.REVIEW_REQUIRED,
            "no hook text found",
        )
    overlap = _jaccard(title_words, hook_words)
    if overlap >= 0.8:
        return SignalEvaluation(
            OriginalitySignal.TITLE_HOOK_DISTINCTIVENESS, RiskLevel.REVIEW_REQUIRED,
            f"hook overlaps {overlap:.0%} with the title — may just restate it "
            "without adding a distinct angle",
        )
    return SignalEvaluation(
        OriginalitySignal.TITLE_HOOK_DISTINCTIVENESS, RiskLevel.LOW_RISK,
        f"hook overlaps only {overlap:.0%} with the title — adds distinct wording",
    )


EXTERNAL_HIGH_THRESHOLD = 0.5
EXTERNAL_REVIEW_THRESHOLD = 0.25


def check_external_similarity_risk(bundle: OriginalityBundle) -> SignalEvaluation:
    if not bundle.reference_texts:
        return SignalEvaluation(
            OriginalitySignal.EXTERNAL_SIMILARITY_RISK, RiskLevel.NOT_APPLICABLE,
            "no comparison/reference material was supplied for this review — "
            "this system does NOT perform internet-wide similarity search; "
            "this result says nothing about material it was never shown",
        )
    script_words = _words(_body_text(bundle))
    worst = (0.0, "")
    for path, text in bundle.reference_texts.items():
        sim = _jaccard(script_words, _words(text))
        if sim > worst[0]:
            worst = (sim, path)
    if worst[0] >= EXTERNAL_HIGH_THRESHOLD:
        return SignalEvaluation(
            OriginalitySignal.EXTERNAL_SIMILARITY_RISK, RiskLevel.HIGH_RISK,
            f"script overlaps {worst[0]:.0%} (word-set Jaccard) with supplied "
            f"reference material {worst[1]!r}",
        )
    if worst[0] >= EXTERNAL_REVIEW_THRESHOLD:
        return SignalEvaluation(
            OriginalitySignal.EXTERNAL_SIMILARITY_RISK, RiskLevel.REVIEW_REQUIRED,
            f"script overlaps {worst[0]:.0%} with supplied reference material "
            f"{worst[1]!r} — a human should judge whether this is shared "
            "common-knowledge/facts or derivative structure",
        )
    return SignalEvaluation(
        OriginalitySignal.EXTERNAL_SIMILARITY_RISK, RiskLevel.LOW_RISK,
        f"highest overlap against {len(bundle.reference_texts)} supplied "
        f"reference file(s) was {worst[0]:.0%}, below the review threshold",
    )


ALL_CHECKS = [
    check_internal_duplication,
    check_concept_distinctiveness,
    check_framing_distinctiveness,
    check_script_distinctiveness,
    check_source_dependence,
    check_template_repetition,
    check_title_hook_distinctiveness,
    check_external_similarity_risk,
]


def evaluate_all_signals(bundle: OriginalityBundle) -> list[SignalEvaluation]:
    return [check(bundle) for check in ALL_CHECKS]
