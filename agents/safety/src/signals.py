"""The twelve safety signals from CONTRACT.md. Deterministic,
pattern/structural only — no NLP, no semantic understanding. Keyword
lists are small and curated; a miss is expected and documented (see
README.md "Known limitations"), never presented as a safety guarantee.
"""
from __future__ import annotations

import re

from ...researcher.src import parsing
from ...researcher.src.models import Classification
from .models import RiskLevel, SafetyBundle, SafetySignal, SignalEvaluation

_CERTAINTY_WORDS = re.compile(
    r"\b(definitely|certainly|undoubtedly|without question|guaranteed|proven that|100% (?:certain|sure))\b",
    re.IGNORECASE,
)

_DANGEROUS_PATTERNS = [
    re.compile(r"\bstep[- ]by[- ]step\b.{0,60}\b(bomb|explosive|weapon|poison|nerve agent)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bhow to (make|build|synthesize|create)\b.{0,40}\b(bomb|explosive|poison|nerve agent|bioweapon)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\binstructions? (for|to) (making|building|synthesizing)\b.{0,40}\b(bomb|explosive|weapon|poison)\b", re.IGNORECASE | re.DOTALL),
]

_ILLEGAL_PATTERNS = [
    re.compile(r"\bhow to (evade|avoid) (taxes|police|law enforcement)\b", re.IGNORECASE),
    re.compile(r"\bhow to (launder money|hack into|break into)\b", re.IGNORECASE),
    re.compile(r"\bstep[- ]by[- ]step\b.{0,60}\b(steal|rob|counterfeit)\b", re.IGNORECASE | re.DOTALL),
]

_DECEPTION_PATTERNS = [
    re.compile(r"\bpresent (this|it) as (real|genuine|authentic)\b", re.IGNORECASE),
    re.compile(r"\btell (viewers|the audience) (this|it) (actually happened|is real)\b.{0,30}(when|even though) it (isn'?t|is not)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bclaim (this|it) is real footage\b", re.IGNORECASE),
]

_IMPERSONATION_PATTERNS = [
    re.compile(r"\bpretend(?:s|ing)? to be [A-Z][a-z]+ [A-Z][a-z]+\b"),
    re.compile(r"\bin the voice of [A-Z][a-z]+ [A-Z][a-z]+\b"),
    re.compile(r"\bas if [A-Z][a-z]+ [A-Z][a-z]+ (?:said|were saying)\b"),
]

_SYNTHETIC_MEDIA_KEYWORDS = [
    "deepfake", "synthetic voice", "ai-generated face", "ai recreation",
    "digitally recreated likeness", "ai-generated likeness",
]

_PRIVACY_PATTERNS = [
    re.compile(r"\b(home address|phone number|social security number|medical records? of)\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]

_DEFAMATION_PHRASES = [
    "committed fraud", "is a criminal", "is guilty of", "stole from",
    "is a liar", "engaged in fraud", "is corrupt",
]

_COPYRIGHT_NO_LICENSE = ["without a license", "no license", "unlicensed"]
_COPYRIGHT_REFERENCE_PATTERNS = [
    re.compile(r"\buse (the song|a clip from|footage from)\b", re.IGNORECASE),
    re.compile(r"\bclip from the (movie|film|show)\b", re.IGNORECASE),
    re.compile(r"\bcopyrighted (footage|music|clip|image)\b", re.IGNORECASE),
]
_COPYRIGHT_CLEARED_WORDS = ["licensed", "license obtained", "royalty-free", "public domain", "royalty free"]

_SENSITIVE_KEYWORDS = [
    "genocide", "mass casualty", "massacre", "concentration camp",
    "ethnic cleansing", "plague", "pandemic", "war crime",
]

_HYPOTHETICAL_MARKERS = ["what if", "could", "might", "hypothetical", "imagine"]
_ABSOLUTE_CERTAINTY_KEYWORDS = ["proven", "confirmed", "100%", "guaranteed", "definitely", "fact:"]


def _body_text(bundle: SafetyBundle) -> str:
    """SCRIPT.md content minus its header table — the narrative prose."""
    return "\n".join(v for k, v in bundle.script_sections.items())


def _low(signal: SafetySignal, reason: str) -> SignalEvaluation:
    return SignalEvaluation(signal, RiskLevel.LOW_RISK, reason)


def _na(signal: SafetySignal, reason: str) -> SignalEvaluation:
    return SignalEvaluation(signal, RiskLevel.NOT_APPLICABLE, reason)


def check_dangerous_instruction(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle)
    for pattern in _DANGEROUS_PATTERNS:
        m = pattern.search(text)
        if m:
            return SignalEvaluation(
                SafetySignal.DANGEROUS_INSTRUCTION, RiskLevel.HIGH_RISK,
                "actionable harmful-instruction pattern matched", evidence=m.group(0),
            )
    return _low(SafetySignal.DANGEROUS_INSTRUCTION, "no dangerous-instruction pattern matched")


def check_illegal_activity(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle)
    for pattern in _ILLEGAL_PATTERNS:
        m = pattern.search(text)
        if m:
            return SignalEvaluation(
                SafetySignal.ILLEGAL_ACTIVITY, RiskLevel.HIGH_RISK,
                "illegal-activity facilitation pattern matched", evidence=m.group(0),
            )
    return _low(SafetySignal.ILLEGAL_ACTIVITY, "no illegal-activity pattern matched")


def check_deception(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle)
    for pattern in _DECEPTION_PATTERNS:
        m = pattern.search(text)
        if m:
            return SignalEvaluation(
                SafetySignal.DECEPTION, RiskLevel.HIGH_RISK,
                "instructs presenting fabricated content as genuine", evidence=m.group(0),
            )
    return _low(SafetySignal.DECEPTION, "no deception pattern matched")


def _ai_disclosure_value(bundle: SafetyBundle) -> str:
    return parsing.first_backtick_token(bundle.script_table.get("AI disclosure required", ""))


def check_impersonation(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle)
    for pattern in _IMPERSONATION_PATTERNS:
        m = pattern.search(text)
        if m:
            disclosure = _ai_disclosure_value(bundle)
            if disclosure == "YES":
                return SignalEvaluation(
                    SafetySignal.IMPERSONATION, RiskLevel.REVIEW_REQUIRED,
                    "real-person impersonation pattern matched with AI disclosure "
                    "marked YES — a human must judge whether disclosure is adequate",
                    evidence=m.group(0),
                )
            return SignalEvaluation(
                SafetySignal.IMPERSONATION, RiskLevel.HIGH_RISK,
                "real-person impersonation pattern matched without AI disclosure",
                evidence=m.group(0),
            )
    return _low(SafetySignal.IMPERSONATION, "no impersonation pattern matched")


def check_synthetic_media(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle).lower()
    hit = next((kw for kw in _SYNTHETIC_MEDIA_KEYWORDS if kw in text), None)
    if hit is None:
        return _na(SafetySignal.SYNTHETIC_MEDIA, "no synthetic-media keyword found")
    disclosure = _ai_disclosure_value(bundle)
    if disclosure == "YES":
        return SignalEvaluation(
            SafetySignal.SYNTHETIC_MEDIA, RiskLevel.REVIEW_REQUIRED,
            f"synthetic-media keyword {hit!r} found with AI disclosure marked YES — "
            "a human must judge whether the disclosure is adequate for this use",
        )
    return SignalEvaluation(
        SafetySignal.SYNTHETIC_MEDIA, RiskLevel.HIGH_RISK,
        f"synthetic-media keyword {hit!r} found without AI disclosure",
    )


def check_ai_disclosure(bundle: SafetyBundle) -> SignalEvaluation:
    raw = bundle.script_table.get("AI disclosure required", "")
    value = parsing.first_backtick_token(raw)
    if value not in ("YES", "NO"):
        return SignalEvaluation(
            SafetySignal.AI_DISCLOSURE, RiskLevel.HIGH_RISK,
            f"AI disclosure requirement not decided (got {value!r})",
        )
    if value == "NO":
        justification = raw.split("`NO`", 1)[-1].strip(" -—")
        if not justification:
            return SignalEvaluation(
                SafetySignal.AI_DISCLOSURE, RiskLevel.REVIEW_REQUIRED,
                "AI disclosure marked NO with no stated justification",
            )
        return _low(SafetySignal.AI_DISCLOSURE, "AI disclosure marked NO with justification")
    # YES: a disclosure plan should appear somewhere in the body.
    if "disclos" in _body_text(bundle).lower():
        return _low(SafetySignal.AI_DISCLOSURE, "AI disclosure marked YES with a stated plan")
    return SignalEvaluation(
        SafetySignal.AI_DISCLOSURE, RiskLevel.REVIEW_REQUIRED,
        "AI disclosure marked YES but no disclosure plan found in the script body",
    )


_BULLET_RE = re.compile(r"^-\s+\*\*([A-Z ]+)\*\*", re.MULTILINE)


def _parse_fact_hypothesis_bullets(section_text: str) -> dict[str, list[str]]:
    """{'KNOWN FACT': ['c1', 'c2', ...], 'ASSUMPTION': [...], ...}."""
    bullets: dict[str, list[str]] = {}
    matches = list(_BULLET_RE.finditer(section_text))
    for i, m in enumerate(matches):
        label = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        chunk = section_text[start:end]
        bullets[label] = parsing.backtick_tokens(chunk)
    return bullets


_BEAT_CLAIMS_RE = re.compile(r"claims?:\s*(.+)$", re.IGNORECASE)


def check_misinformation_risk(bundle: SafetyBundle) -> SignalEvaluation:
    section = bundle.script_sections.get("What If? fact/hypothesis separation", "")
    pillar = bundle.content_item.content_pillar

    if not section:
        if pillar == "what-if":
            return SignalEvaluation(
                SafetySignal.MISINFORMATION_RISK, RiskLevel.HIGH_RISK,
                "what-if content item has no 'What If? fact/hypothesis separation' "
                "section in SCRIPT.md (required by CONSTITUTION.md rule 4)",
            )
        # fall through to the unsupported-certainty check below even
        # without the section, since that applies to any pillar.
        bullets: dict[str, list[str]] = {}
    else:
        bullets = _parse_fact_hypothesis_bullets(section)
        known_fact_ids = bullets.get("KNOWN FACT", [])
        mislabeled = []
        for short_id in known_fact_ids:
            claim = bundle.claims.get(short_id)
            if claim is not None and claim.classification is not Classification.FACT:
                mislabeled.append((short_id, claim.classification.value))
        if mislabeled:
            return SignalEvaluation(
                SafetySignal.MISINFORMATION_RISK, RiskLevel.HIGH_RISK,
                "claim(s) listed under KNOWN FACT are not classified FACT: "
                + ", ".join(f"{cid} is {cls}" for cid, cls in mislabeled),
            )

    # Unsupported certainty: a narrative beat citing a non-FACT claim
    # while using absolute-certainty language.
    beats_section = bundle.script_sections.get("Narrative beats", "")
    offenders = []
    for line in beats_section.splitlines():
        m = _BEAT_CLAIMS_RE.search(line)
        if not m:
            continue
        cited = parsing.backtick_tokens(m.group(1))
        non_fact_cited = [
            cid for cid in cited
            if bundle.claims.get(cid) is not None
            and bundle.claims[cid].classification is not Classification.FACT
        ]
        if non_fact_cited and _CERTAINTY_WORDS.search(line):
            offenders.append((line.strip(), non_fact_cited))
    if offenders:
        return SignalEvaluation(
            SafetySignal.MISINFORMATION_RISK, RiskLevel.HIGH_RISK,
            "absolute-certainty language used in a beat citing non-FACT claim(s): "
            + "; ".join(f"{cids} in {ln!r}" for ln, cids in offenders),
        )

    if not section and pillar != "what-if":
        return _na(
            SafetySignal.MISINFORMATION_RISK,
            "no fact/hypothesis section (not required for this pillar) and no "
            "unsupported-certainty language found",
        )
    return _low(SafetySignal.MISINFORMATION_RISK, "fact/hypothesis labeling consistent, no unsupported certainty found")


def check_privacy(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle)
    for pattern in _PRIVACY_PATTERNS:
        m = pattern.search(text)
        if m:
            return SignalEvaluation(
                SafetySignal.PRIVACY, RiskLevel.HIGH_RISK,
                "private personal data pattern matched", evidence=m.group(0),
            )
    return _low(SafetySignal.PRIVACY, "no privacy pattern matched")


def check_defamation(bundle: SafetyBundle) -> SignalEvaluation:
    text = _body_text(bundle).lower()
    hit = next((p for p in _DEFAMATION_PHRASES if p in text), None)
    if hit is None:
        return _low(SafetySignal.DEFAMATION, "no accusatory-phrase pattern matched")
    return SignalEvaluation(
        SafetySignal.DEFAMATION, RiskLevel.REVIEW_REQUIRED,
        f"accusatory phrase {hit!r} found about a named subject — whether it is "
        "adequately sourced needs human judgment, this MVP cannot reliably tell",
    )


def check_copyright_risk(bundle: SafetyBundle) -> SignalEvaluation:
    text = bundle.script_sections.get("Music / SFX requirements", "") + "\n" + bundle.script_sections.get("Visual requirements", "")
    lower = text.lower()
    if any(p in lower for p in _COPYRIGHT_NO_LICENSE):
        return SignalEvaluation(
            SafetySignal.COPYRIGHT_RISK, RiskLevel.HIGH_RISK,
            "explicit lack-of-license language found",
        )
    for pattern in _COPYRIGHT_REFERENCE_PATTERNS:
        m = pattern.search(text)
        if m:
            if any(w in lower for w in _COPYRIGHT_CLEARED_WORDS):
                return _low(SafetySignal.COPYRIGHT_RISK, "named third-party media referenced, but licensing/clearance noted")
            return SignalEvaluation(
                SafetySignal.COPYRIGHT_RISK, RiskLevel.REVIEW_REQUIRED,
                "named third-party copyrighted/trademarked material referenced "
                "without a licensing note", evidence=m.group(0),
            )
    return _na(SafetySignal.COPYRIGHT_RISK, "no third-party media referenced")


def check_sensitive_content(bundle: SafetyBundle) -> SignalEvaluation:
    text = (bundle.script_text + " " + bundle.content_item.raw_text).lower()
    hit = next((kw for kw in _SENSITIVE_KEYWORDS if kw in text), None)
    if hit is None:
        return _low(SafetySignal.SENSITIVE_CONTENT, "no sensitive-subject keyword found")
    return SignalEvaluation(
        SafetySignal.SENSITIVE_CONTENT, RiskLevel.REVIEW_REQUIRED,
        f"sensitive-subject keyword {hit!r} found — real tragedy/mass-casualty "
        "content warrants careful human review of tone and framing, not an "
        "automatic pass or fail",
    )


def check_title_thumbnail(bundle: SafetyBundle) -> SignalEvaluation:
    identity_table = parsing.parse_table(bundle.content_item.raw_text)
    title = identity_table.get("Working title", "") or identity_table.get("Final title", "")
    title_lower = title.lower()
    pillar = bundle.content_item.content_pillar

    if pillar == "what-if":
        if not any(marker in title_lower for marker in _HYPOTHETICAL_MARKERS):
            return SignalEvaluation(
                SafetySignal.TITLE_THUMBNAIL_MISREPRESENTATION, RiskLevel.HIGH_RISK,
                f"what-if content's title {title!r} has no hypothetical framing marker",
            )
        if any(kw in title_lower for kw in _ABSOLUTE_CERTAINTY_KEYWORDS):
            return SignalEvaluation(
                SafetySignal.TITLE_THUMBNAIL_MISREPRESENTATION, RiskLevel.HIGH_RISK,
                f"what-if title {title!r} mixes hypothetical framing with absolute-certainty language",
            )
        return _low(SafetySignal.TITLE_THUMBNAIL_MISREPRESENTATION, "what-if title correctly framed as hypothetical")

    has_absolute = any(kw in title_lower for kw in _ABSOLUTE_CERTAINTY_KEYWORDS)
    if not has_absolute:
        return _low(SafetySignal.TITLE_THUMBNAIL_MISREPRESENTATION, "no absolute-certainty language in title")
    has_non_fact_cited = any(
        c.classification is not Classification.FACT for c in bundle.claims.values()
    )
    if has_non_fact_cited:
        return SignalEvaluation(
            SafetySignal.TITLE_THUMBNAIL_MISREPRESENTATION, RiskLevel.HIGH_RISK,
            f"title {title!r} uses absolute-certainty language but the item includes "
            "non-FACT (inferred/speculative) claims",
        )
    return SignalEvaluation(
        SafetySignal.TITLE_THUMBNAIL_MISREPRESENTATION, RiskLevel.REVIEW_REQUIRED,
        f"title {title!r} uses absolute-certainty language — cannot confirm this is "
        "warranted without a completed fact-check",
    )


ALL_CHECKS = [
    check_dangerous_instruction,
    check_illegal_activity,
    check_deception,
    check_impersonation,
    check_synthetic_media,
    check_ai_disclosure,
    check_misinformation_risk,
    check_privacy,
    check_defamation,
    check_copyright_risk,
    check_sensitive_content,
    check_title_thumbnail,
]


def evaluate_all_signals(bundle: SafetyBundle) -> list[SignalEvaluation]:
    return [check(bundle) for check in ALL_CHECKS]
