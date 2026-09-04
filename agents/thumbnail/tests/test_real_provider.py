"""Phase 8 tests for agents/thumbnail/src/real_provider.py — the first
real thumbnail image renderer. Offline, deterministic, no network — see
agents/assets/src/illustration.py (reused directly).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.models import ThumbnailSpec
from ..src.real_provider import render_thumbnail_image


class RenderThumbnailImageTests(unittest.TestCase):
    def test_produces_real_nonempty_png(self):
        spec = ThumbnailSpec(
            title_concept="What If Modern Medicine Existed During the Black Death?",
            visual_concept="A medieval plague scene with a modern medical contrast",
            text_overlay="What If Modern Medicine Existed During the Black Death?",
            focal_subject="Generated reconstruction visual",
            composition="Single dominant subject, minimal text, high contrast",
        )
        data = render_thumbnail_image(spec)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(data), 500)

    def test_deterministic_given_identical_spec(self):
        spec = ThumbnailSpec(
            title_concept="A title", visual_concept="A visual concept",
            text_overlay="A title", focal_subject="subject", composition="composition",
        )
        a = render_thumbnail_image(spec)
        b = render_thumbnail_image(spec)
        self.assertEqual(a, b)

    def test_falls_back_to_title_when_no_visual_concept(self):
        spec = ThumbnailSpec(
            title_concept="Fallback title", visual_concept="N/A",
            text_overlay="N/A", focal_subject="subject", composition="composition",
        )
        data = render_thumbnail_image(spec)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))


class ThumbnailImageWriteWhitelistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.root.mkdir()

    def test_write_thumbnail_image_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_thumbnail_image(self.root, "thumbnail-01.jpg", b"data")

    def test_write_thumbnail_image_accepts_whitelisted_png(self):
        path = mutate.write_thumbnail_image(self.root, "thumbnail-01.png", b"\x89PNG")
        self.assertTrue(path.is_file())

    def test_write_thumbnail_image_rejects_path_traversal(self):
        with self.assertRaises(PermissionError):
            mutate.write_thumbnail_image(self.root, "../evil.png", b"data")


if __name__ == "__main__":
    unittest.main()
