"""Tests 1-5 from the Phase 5 task: one valid claim of each classification
passes the Atomicity rule, and a known compound claim is rejected."""
import unittest

from ..src.atomicity import check_atomicity, is_atomic


class AtomicityTests(unittest.TestCase):
    def test_valid_fact_claim_is_atomic(self):
        text = (
            "Without antibiotic treatment, bubonic plague kills an estimated "
            '30–60% of infected people, and pneumonic plague is "invariably fatal."'
        )
        self.assertTrue(is_atomic(text), check_atomicity(text))

    def test_valid_assumption_claim_is_atomic(self):
        text = (
            "ASSUMPTION: this fixture scenario grants a hypothetical premise X."
        )
        self.assertTrue(is_atomic(text), check_atomicity(text))

    def test_valid_inference_claim_is_atomic(self):
        text = (
            "INFERENCE: combining the fixture fact and the fixture assumption "
            "plausibly implies Y."
        )
        self.assertTrue(is_atomic(text), check_atomicity(text))

    def test_valid_speculation_claim_is_atomic(self):
        text = (
            "SPECULATION: the ultimate magnitude of Y cannot be confidently "
            "estimated from available evidence."
        )
        self.assertTrue(is_atomic(text), check_atomicity(text))

    def test_compound_claim_is_rejected(self):
        # The real pre-split claims/c3.md text from Phase 3/4 — a genuine
        # regression fixture, not a synthetic example.
        text = (
            "Modern antibiotics, administered promptly, effectively treat "
            'plague; without treatment, bubonic plague kills an estimated '
            '30–60% of the infected and pneumonic plague is "invariably '
            'fatal." Antibiotics were not developed until the 20th century.'
        )
        violations = check_atomicity(text)
        self.assertFalse(is_atomic(text))
        self.assertGreaterEqual(len(violations), 2)  # semicolon AND 2nd sentence
        joined = " ".join(violations)
        self.assertIn("sentence", joined)
        self.assertIn("semicolon", joined)

    def test_because_connector_is_rejected(self):
        text = "X happened because Y caused it to happen."
        violations = check_atomicity(text)
        self.assertTrue(any("connector" in v for v in violations))

    def test_abbreviation_period_does_not_trigger_false_positive(self):
        text = (
            "The Black Death struck Europe 1347–1351, killing an estimated "
            "25–60%+ of the population depending on region and methodology "
            "(e.g. England's population fell 46% in the first strike alone)."
        )
        self.assertTrue(is_atomic(text), check_atomicity(text))


if __name__ == "__main__":
    unittest.main()
