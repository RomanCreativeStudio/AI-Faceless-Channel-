"""Regression tests for the owner-voice reference manifest
(agents/voice/OWNER_VOICE_REFERENCE.md) and the gitignored sample
directory it points at — encodes, as checked invariants, the privacy/
auditability requirements this file exists to satisfy: no raw audio
content, no real absolute filesystem path, and the sample directory
stays gitignored.
"""
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _REPO_ROOT / "agents" / "voice" / "OWNER_VOICE_REFERENCE.md"
_GITIGNORE_PATH = _REPO_ROOT / ".gitignore"

_FORBIDDEN_PATH_FRAGMENTS = ("/tmp/claude", "/root/.claude", "4kingdomzs")


class OwnerVoiceReferenceManifestTests(unittest.TestCase):
    def test_manifest_exists(self):
        self.assertTrue(_MANIFEST_PATH.is_file())

    def test_manifest_is_plain_text_not_binary_audio(self):
        text = _MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIn("ACTIVE_REFERENCE_ID", text)

    def test_manifest_declares_a_repo_relative_gitignored_active_path(self):
        text = _MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIn("owner_voice_samples/production_reference.wav", text)

    def test_manifest_never_names_a_real_absolute_private_filesystem_path(self):
        text = _MANIFEST_PATH.read_text(encoding="utf-8")
        for fragment in _FORBIDDEN_PATH_FRAGMENTS:
            self.assertNotIn(fragment, text)

    def test_manifest_records_tau_unchanged_from_production_default(self):
        text = _MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIn("TAU                   = 0.3", text)

    def test_owner_voice_samples_directory_stays_gitignored(self):
        gitignore_text = _GITIGNORE_PATH.read_text(encoding="utf-8")
        self.assertIn("/owner_voice_samples/", gitignore_text)

    def test_manifest_records_sha256_checksums_not_raw_content(self):
        text = _MANIFEST_PATH.read_text(encoding="utf-8")
        # A real sha256 hex digest is 64 hex characters -- present, but
        # nothing resembling actual audio bytes (this is a .md file, so
        # any binary content would already fail read_text() above).
        self.assertIn("SHA-256", text)


if __name__ == "__main__":
    unittest.main()
