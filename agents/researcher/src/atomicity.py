"""Implements templates/CLAIM.md's Atomicity rule, checks 1 and 2 (the
two the template itself calls "mechanically-checkable, no NLP required").
Check 3 ("one classification fits without qualification") is a judgment
call the template acknowledges isn't mechanical — it's left to human/
research-time review, not enforced here.
"""
from __future__ import annotations

import re

_ABBREVIATIONS = ["e.g.", "i.e.", "etc.", "vs.", "approx.", "Dr.", "Mr.", "Mrs.", "St."]
_CONNECTOR_RE = re.compile(
    r"\bbecause\b|\btherefore\b|\bwhich means\b|\bso that\b", re.IGNORECASE
)
_PLACEHOLDER = "␟"  # a character that will never appear in claim text


def _mask_non_terminal_periods(text: str) -> str:
    masked = text
    for abbr in _ABBREVIATIONS:
        masked = masked.replace(abbr, abbr.replace(".", _PLACEHOLDER))
    masked = re.sub(r"(?<=\d)\.(?=\d)", _PLACEHOLDER, masked)  # decimals
    return masked


def check_atomicity(exact_claim: str) -> list[str]:
    """Return a list of Atomicity-rule violation messages; empty = atomic."""
    violations: list[str] = []
    text = exact_claim.strip()

    masked = _mask_non_terminal_periods(text)
    terminal_periods = masked.count(".")
    if terminal_periods > 1:
        violations.append(
            "more than one sentence (Atomicity rule 1): found "
            f"{terminal_periods} sentence-ending periods"
        )

    if ";" in text:
        violations.append(
            "semicolon joins two independently-checkable assertions (Atomicity rule 2)"
        )

    connector = _CONNECTOR_RE.search(text)
    if connector:
        violations.append(
            f"causal/inferential connector {connector.group(0)!r} fuses a fact to a "
            "conclusion drawn from it (Atomicity rule 2)"
        )

    return violations


def is_atomic(exact_claim: str) -> bool:
    return not check_atomicity(exact_claim)
