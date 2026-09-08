"""Regression tests for two real bugs found in RETRIEVED-strategy search
construction, both confirmed by direct inspection and live (network)
testing against Wikimedia Commons during this investigation:

1. `_build_plan`'s RETRIEVED branch used to search using the scene's raw
   narration text truncated to a fixed 220-character window
   (`_truncate_prompt`). For Episode 1's beat 2 (absence of germ theory),
   the entity name "Pasteur" only appears in the narration's fourth
   sentence -- well past that cutoff -- even though a real, on-topic,
   public-domain Pasteur portrait genuinely exists and is findable on
   Wikimedia Commons by name (confirmed by prior manual investigation, see
   HUMAN_REVIEW.md's "Wikimedia asset status" section, and reconfirmed
   live this session).

2. Fixing (1) alone by joining *every* extracted entity into one query is
   not reliably better either: a live search for "Pasteur Lister Koch"
   (all three scientists named in that beat) returns mostly unrelated
   scanned documents and an unrelated same-surname photograph -- the
   combined query's relevance is diluted below what the single most
   distinctive entity, "Pasteur", achieves alone. `_build_retrieval_query_
   candidates` tries the joined query first, then each individual entity,
   in order, until one search succeeds.

Both fixes are deterministic, no-NLP, and never fabricate a term that
isn't literally present in the source narration -- they only re-select/
re-order substrings of it, and every candidate is a genuinely separate
real search. RETRIEVED-strategy query construction is the only thing
changed; GENERATED-strategy's illustration prompt (`visual_prompt`) is
untouched, verified explicitly below.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ..src.pipeline import (
    _build_retrieval_query_candidates,
    _extract_entity_phrases,
    _truncate_prompt,
    run_asset_generation,
)
from ..src.provider import GeneratedArtifact, RetrievalResult
from .builders import build_visual_planned_item

# Deliberately long lead-in so the entity name lands after the 220-char
# window a naive truncation would use -- mirrors the real Episode 1 beat.
LONG_LEADIN_NARRATION = (
    "Nobody living through it at the time understood in any way why the "
    "disease kept spreading through their communities and villages "
    "without any visible explanation at all, really, for a very long "
    "time indeed. That would only be established later, through the "
    "careful work of scientists like Pasteur."
)

# Mirrors the real Episode 1 beat 2 narration's shape: three entities
# joined by "and"/commas, in one late sentence.
THREE_SCIENTISTS_NARRATION = (
    "Nobody living through it understood why it was happening. The idea "
    "that specific microorganisms cause disease did not exist anywhere "
    "in the world yet. That would only be established later, through the "
    "work of scientists like Pasteur, Lister, and Koch."
)


class EntityPhraseExtractionTests(unittest.TestCase):
    def test_extracts_single_entity_past_the_truncation_window(self):
        self.assertGreater(LONG_LEADIN_NARRATION.index("Pasteur"), 220)
        self.assertNotIn("Pasteur", _truncate_prompt(LONG_LEADIN_NARRATION, 220))
        self.assertIn("Pasteur", _extract_entity_phrases(LONG_LEADIN_NARRATION))

    def test_multi_word_entity_joined_and_sentence_initial_word_skipped(self):
        text = (
            "Between 1347 and 1351, the Black Death swept across Europe. "
            "In parts of England, nearly half the people died."
        )
        entities = _extract_entity_phrases(text)
        self.assertEqual(entities, ["Black Death", "Europe", "England"])
        # "Between" and "In" are sentence-initial -- never candidates.
        self.assertNotIn("Between", entities)
        self.assertNotIn("In", entities)

    def test_three_entities_extracted_in_order(self):
        self.assertEqual(
            _extract_entity_phrases(THREE_SCIENTISTS_NARRATION),
            ["Pasteur", "Lister", "Koch"],
        )

    def test_duplicate_entity_mentioned_twice_appears_once(self):
        text = "Pasteur discovered this. Later, Pasteur was recognized for it."
        self.assertEqual(_extract_entity_phrases(text), ["Pasteur"])

    def test_no_entities_returns_empty_list(self):
        text = "there was widespread suffering and confusion during this period."
        self.assertEqual(_extract_entity_phrases(text), [])

    def test_never_fabricates_a_word_not_in_the_source_text(self):
        text = "Nobody understood why Pasteur mattered yet."
        for phrase in _extract_entity_phrases(text):
            self.assertIn(phrase, text)


class RetrievalQueryCandidateConstructionTests(unittest.TestCase):
    def test_single_entity_yields_one_candidate(self):
        candidates = _build_retrieval_query_candidates(LONG_LEADIN_NARRATION)
        self.assertEqual(candidates, ["Pasteur"])

    def test_multiple_entities_try_joined_query_first_then_each_alone(self):
        candidates = _build_retrieval_query_candidates(THREE_SCIENTISTS_NARRATION)
        self.assertEqual(candidates, ["Pasteur Lister Koch", "Pasteur", "Lister", "Koch"])

    def test_falls_back_to_truncated_narration_when_no_entities_found(self):
        text = "there was widespread suffering and confusion during this period of history."
        self.assertEqual(_build_retrieval_query_candidates(text), [_truncate_prompt(text)])

    def test_long_entity_list_still_respects_max_chars(self):
        text = " ".join(f"Entity{n} discovered thing {n}." for n in range(1, 60))
        candidates = _build_retrieval_query_candidates(text, max_chars=220)
        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertLessEqual(len(candidate), 220)

    def test_never_returns_duplicate_or_empty_candidates(self):
        candidates = _build_retrieval_query_candidates(THREE_SCIENTISTS_NARRATION)
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(c.strip() for c in candidates))


class _ScriptedRetrievalProvider:
    """Fake AssetRetrievalProvider that fails every query except one exact
    string (case-sensitive) -- lets a test prove pipeline.py genuinely
    tries multiple real candidate queries in order and stops at the first
    real success, mirroring the live-confirmed "joined query fails,
    individual entity succeeds" finding without a network call."""

    label = "scripted-test-retrieval-provider"

    def __init__(self, succeeds_for: str):
        self.succeeds_for = succeeds_for
        self.received_queries: list[str] = []

    def retrieve(self, visual_description: str, asset_type: str) -> RetrievalResult:
        self.received_queries.append(visual_description)
        if visual_description == self.succeeds_for:
            return RetrievalResult(
                provider_label=self.label,
                status="RETRIEVED",
                requirement_note="",
                source_reference=f"Test Commons file for {visual_description!r}",
                source_url="https://commons.wikimedia.org/wiki/File:Test.jpg",
                license_text="CC BY-SA 3.0",
                licensing_status="LICENSED",
                artifact_bytes=b"fake-jpeg-bytes",
                artifact_extension="jpg",
            )
        return RetrievalResult(
            provider_label=self.label,
            status="RETRIEVAL_FAILED",
            requirement_note=f"no usable result for {visual_description!r}",
            source_reference="not yet sourced",
        )


class _RecordingRetrievalProvider:
    """Fake AssetRetrievalProvider that records every query it receives
    and always fails closed -- for tests that only need to observe what
    query pipeline.py sends, not exercise a successful download."""

    label = "recording-test-retrieval-provider"

    def __init__(self):
        self.received_queries: list[str] = []

    def retrieve(self, visual_description: str, asset_type: str) -> RetrievalResult:
        self.received_queries.append(visual_description)
        return RetrievalResult(
            provider_label=self.label,
            status="RETRIEVAL_FAILED",
            requirement_note="test fixture always fails closed",
            source_reference="not yet sourced",
        )


class _RecordingGeneratedProvider:
    """Fake GeneratedAssetProvider recording every prompt it receives, to
    prove GENERATED's prompt construction is unaffected by this fix."""

    label = "recording-test-generated-provider"

    def __init__(self):
        self.received_prompts: list[str] = []

    def generate(self, visual_description: str, asset_type: str) -> GeneratedArtifact:
        self.received_prompts.append(visual_description)
        return GeneratedArtifact(
            provider_label=self.label,
            artifact_content="test placeholder",
            is_placeholder=True,
        )


class BuildPlanUsesEntityAwareQueryForRetrievedStrategyTests(unittest.TestCase):
    """End-to-end regression tests at the real run_asset_generation entry
    point -- prove the actual RETRIEVED code path (not just the helper
    functions in isolation) now tries entity-aware queries, in order,
    with real fallback behavior."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    def test_retrieved_strategy_first_query_contains_the_late_entity(self):
        # Default beat/claim (c1, FACT) -> RETRIEVED strategy.
        build_visual_planned_item(
            self.root,
            beats=[f"1. {LONG_LEADIN_NARRATION} — claims: `c1`"],
        )
        provider = _RecordingRetrievalProvider()
        run_asset_generation(self.root, apply=True, retrieval_provider=provider)
        self.assertEqual(len(provider.received_queries), 1)
        self.assertIn("Pasteur", provider.received_queries[0])

    def test_falls_back_from_joined_query_to_individual_entity_on_failure(self):
        # Reproduces the real, live-confirmed finding: the joined query
        # ("Pasteur Lister Koch") fails, but the single most distinctive
        # entity ("Pasteur") alone succeeds -- pipeline.py must actually
        # retry with the next candidate rather than giving up after one
        # failed attempt.
        build_visual_planned_item(
            self.root,
            beats=[f"1. {THREE_SCIENTISTS_NARRATION} — claims: `c1`"],
        )
        provider = _ScriptedRetrievalProvider(succeeds_for="Pasteur")
        result = run_asset_generation(self.root, apply=True, retrieval_provider=provider)

        self.assertEqual(
            provider.received_queries,
            ["Pasteur Lister Koch", "Pasteur"],
            "expected the joined query to be tried first and fail, then the "
            "single entity 'Pasteur' to be tried next and succeed",
        )
        matches = [p for p in result.plans if p.scene.claim_ids == ["c1"]]
        self.assertEqual(len(matches), 1)
        plan = matches[0]
        self.assertEqual(plan.generation_status, "RETRIEVED")
        self.assertIn("Pasteur", plan.verification_notes)

    def test_stops_at_first_successful_candidate_never_overwrites_it(self):
        build_visual_planned_item(
            self.root,
            beats=[f"1. {THREE_SCIENTISTS_NARRATION} — claims: `c1`"],
        )
        # Succeeds on the very first (joined) candidate -- "Lister"/"Koch"
        # must never even be attempted.
        provider = _ScriptedRetrievalProvider(succeeds_for="Pasteur Lister Koch")
        run_asset_generation(self.root, apply=True, retrieval_provider=provider)
        self.assertEqual(provider.received_queries, ["Pasteur Lister Koch"])

    def test_all_candidates_failing_never_fabricates_a_source(self):
        build_visual_planned_item(
            self.root,
            beats=[f"1. {THREE_SCIENTISTS_NARRATION} — claims: `c1`"],
        )
        provider = _RecordingRetrievalProvider()
        result = run_asset_generation(self.root, apply=True, retrieval_provider=provider)
        self.assertEqual(provider.received_queries, ["Pasteur Lister Koch", "Pasteur", "Lister", "Koch"])
        matches = [p for p in result.plans if p.scene.claim_ids == ["c1"]]
        plan = matches[0]
        self.assertEqual(plan.generation_status, "NOT_STARTED")
        self.assertEqual(plan.source, "not yet sourced")
        self.assertIn("4 search quer", plan.verification_notes)

    def test_generated_strategy_prompt_is_unaffected_by_this_fix(self):
        # A SPECULATION-classified claim -> GENERATED strategy (never
        # RETRIEVED) -- proves this fix's new entity-aware query is scoped
        # to the RETRIEVED branch only. GENERATED must keep receiving the
        # raw truncated narration exactly as before.
        build_visual_planned_item(
            self.root,
            beats=[f"1. {LONG_LEADIN_NARRATION} — claims: `c9`"],
            extra_claims=[("c9", "SPECULATION")],
        )
        provider = _RecordingGeneratedProvider()
        run_asset_generation(self.root, apply=True, generated_provider=provider)
        # Two GENERATED-strategy scenes exist (the Hook, which has no
        # claim references, plus this beat) -- find the one built from
        # LONG_LEADIN_NARRATION specifically.
        self.assertIn(_truncate_prompt(LONG_LEADIN_NARRATION), provider.received_prompts)


if __name__ == "__main__":
    unittest.main()
