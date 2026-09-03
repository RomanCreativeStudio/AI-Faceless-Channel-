"""Deterministic narration -> caption-chunk segmentation and timing. See
CONTRACT.md's "Segmentation rule". No semantic sentence detection, no
paraphrasing — purely punctuation- and character-count-based, so the
same input always segments the same way.
"""
from __future__ import annotations

import re

from .models import CaptionChunk

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

DEFAULT_MAX_CHARACTERS_PER_LINE = 40
DEFAULT_MAX_LINES_PER_CAPTION = 2


def split_into_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def chunk_sentence(sentence: str, max_chars: int) -> list[str]:
    """Packs words into chunks of at most max_chars, never splitting a
    word. A single word longer than max_chars is its own chunk (never
    truncated — truncation would alter the text)."""
    words = sentence.split()
    if not words:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        added_len = len(word) + (1 if current else 0)
        if current and current_len + added_len > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += added_len
    if current:
        chunks.append(" ".join(current))
    return chunks


def build_caption_chunks(
    narration_text: str,
    max_characters_per_line: int = DEFAULT_MAX_CHARACTERS_PER_LINE,
    max_lines_per_caption: int = DEFAULT_MAX_LINES_PER_CAPTION,
) -> list[str]:
    max_chars = max_characters_per_line * max_lines_per_caption
    chunks: list[str] = []
    for sentence in split_into_sentences(narration_text):
        chunks.extend(chunk_sentence(sentence, max_chars))
    return chunks


def build_caption_timestamps(
    chunks: list[str], narration_text: str, scene_duration_seconds: int
) -> list[CaptionChunk]:
    """Each chunk's duration is proportional to its character length
    within the scene's total narration length, cumulative from 0s."""
    total_chars = sum(len(c) for c in chunks)
    if total_chars == 0 or scene_duration_seconds <= 0:
        return [
            CaptionChunk(index=i + 1, start=0.0, end=0.0, text=c)
            for i, c in enumerate(chunks)
        ]

    entries: list[CaptionChunk] = []
    cumulative = 0.0
    for i, chunk in enumerate(chunks, start=1):
        share = len(chunk) / total_chars
        duration = scene_duration_seconds * share
        start = cumulative
        end = start + duration
        entries.append(CaptionChunk(index=i, start=round(start, 1), end=round(end, 1), text=chunk))
        cumulative = end
    return entries
