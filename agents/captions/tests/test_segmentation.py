"""Unit tests for the deterministic segmentation/timing functions
(tests 19, 20, 21, 22 exercised directly, without a full fixture)."""
import unittest

from ..src.segmentation import (
    build_caption_chunks,
    build_caption_timestamps,
    chunk_sentence,
    split_into_sentences,
)


class SegmentationTests(unittest.TestCase):
    def test_splits_on_sentence_boundaries(self):
        sentences = split_into_sentences("First sentence. Second sentence! Third?")
        self.assertEqual(sentences, ["First sentence.", "Second sentence!", "Third?"])

    def test_chunk_sentence_never_splits_a_word(self):
        sentence = "one two three four five six seven eight nine ten"
        chunks = chunk_sentence(sentence, max_chars=20)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 20)
        # Every word from the original sentence appears, unmodified, in order.
        self.assertEqual(" ".join(chunks).split(), sentence.split())

    def test_long_single_word_is_never_truncated(self):
        word = "a" * 50
        chunks = chunk_sentence(word, max_chars=20)
        self.assertEqual(chunks, [word])

    # --- Test 19: narration converted deterministically ---
    def test_build_caption_chunks_is_deterministic(self):
        text = "Sentence one here. Sentence two here, a bit longer than the first."
        first = build_caption_chunks(text, max_characters_per_line=20, max_lines_per_caption=2)
        second = build_caption_chunks(text, max_characters_per_line=20, max_lines_per_caption=2)
        self.assertEqual(first, second)

    # --- Test 20: caption timing deterministic ---
    def test_build_caption_timestamps_is_deterministic_and_proportional(self):
        chunks = ["short", "a much longer chunk of text here"]
        narration = " ".join(chunks)
        first = build_caption_timestamps(chunks, narration, scene_duration_seconds=10)
        second = build_caption_timestamps(chunks, narration, scene_duration_seconds=10)
        self.assertEqual([(c.start, c.end) for c in first], [(c.start, c.end) for c in second])
        # Longer chunk gets more time.
        self.assertGreater(first[1].end - first[1].start, first[0].end - first[0].start)
        self.assertEqual(first[0].start, 0.0)
        self.assertAlmostEqual(first[-1].end, 10.0, places=1)

    # --- Test 21: caption text remains faithful to narration ---
    def test_chunks_reconstruct_the_original_narration_exactly(self):
        text = "The plague spread quickly. Nobody understood why at the time."
        chunks = build_caption_chunks(text, max_characters_per_line=100, max_lines_per_caption=1)
        self.assertEqual(" ".join(chunks), text)

    # --- Test 22: What If? qualifiers preserved ---
    def test_hedge_qualifiers_survive_segmentation_unaltered(self):
        text = (
            "It's hard to say for certain, but this may have reduced deaths. "
            "We cannot know the exact hypothetical outcome."
        )
        chunks = build_caption_chunks(text, max_characters_per_line=200, max_lines_per_caption=1)
        joined = " ".join(chunks)
        for qualifier in ("may have", "We cannot know", "hypothetical"):
            self.assertIn(qualifier, joined)


if __name__ == "__main__":
    unittest.main()
