"""Tests 19, 20: QA catches a missing audio reference; QA catches a
script-hash mismatch. Direct unit tests of the pure evaluate_voice_qa
function — structural checks only, never a speech-quality judgment.
"""
import unittest

from ..src.qa import evaluate_voice_qa


class VoiceQATests(unittest.TestCase):
    def _valid_kwargs(self):
        return dict(
            narration_text="Some narration text.",
            recorded_script_hash="abc123",
            current_script_hash="abc123",
            audio_reference="voice/voice-01.audio.txt",
            duration_seconds=10,
            provider_label="local-test-provider",
            voice_configuration="default-test-voice",
            generation_status="GENERATED",
        )

    def test_all_valid_inputs_pass(self):
        passed, reasons = evaluate_voice_qa(**self._valid_kwargs())
        self.assertTrue(passed)
        self.assertEqual(reasons, [])

    # --- Test 19: QA catches missing audio reference ---
    def test_catches_missing_audio_reference(self):
        kwargs = self._valid_kwargs()
        kwargs["audio_reference"] = ""
        passed, reasons = evaluate_voice_qa(**kwargs)
        self.assertFalse(passed)
        self.assertTrue(any("audio reference" in r for r in reasons))

    # --- Test 20: QA catches script-hash mismatch ---
    def test_catches_script_hash_mismatch(self):
        kwargs = self._valid_kwargs()
        kwargs["recorded_script_hash"] = "old-hash"
        kwargs["current_script_hash"] = "new-hash"
        passed, reasons = evaluate_voice_qa(**kwargs)
        self.assertFalse(passed)
        self.assertTrue(any("hash mismatch" in r for r in reasons))

    def test_catches_empty_narration(self):
        kwargs = self._valid_kwargs()
        kwargs["narration_text"] = "   "
        passed, reasons = evaluate_voice_qa(**kwargs)
        self.assertFalse(passed)
        self.assertTrue(any("narration" in r for r in reasons))

    def test_catches_nonpositive_duration(self):
        kwargs = self._valid_kwargs()
        kwargs["duration_seconds"] = 0
        passed, reasons = evaluate_voice_qa(**kwargs)
        self.assertFalse(passed)
        self.assertTrue(any("duration" in r for r in reasons))

    def test_catches_incomplete_provider_metadata(self):
        kwargs = self._valid_kwargs()
        kwargs["provider_label"] = ""
        passed, reasons = evaluate_voice_qa(**kwargs)
        self.assertFalse(passed)
        self.assertTrue(any("provider metadata" in r for r in reasons))

    def test_catches_invalid_generation_status(self):
        kwargs = self._valid_kwargs()
        kwargs["generation_status"] = "NOT_A_REAL_STATUS"
        passed, reasons = evaluate_voice_qa(**kwargs)
        self.assertFalse(passed)
        self.assertTrue(any("generation status" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
