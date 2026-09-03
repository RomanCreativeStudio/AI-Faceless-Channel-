"""Deterministic scene-duration estimator: word count / configured
words-per-minute. `words_per_minute` is always an explicit parameter
(agents/producer/src/pipeline.py's run_producer takes it as a keyword
argument) — never a hidden, hardcoded assumption. DEFAULT_WORDS_PER_MINUTE
is only the fallback used when a caller doesn't override it.
"""
from __future__ import annotations

DEFAULT_WORDS_PER_MINUTE = 150


def estimate_duration_seconds(text: str, words_per_minute: int) -> int:
    if words_per_minute <= 0:
        raise ValueError("words_per_minute must be positive")
    word_count = len(text.split())
    if word_count == 0:
        return 0
    seconds = (word_count / words_per_minute) * 60
    return max(1, round(seconds))
