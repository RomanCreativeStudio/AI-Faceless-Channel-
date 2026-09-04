"""Phase 8 tests for agents/assets/src/real_providers.py and
agents/assets/src/illustration.py — the first production-capable asset
providers. Wikimedia calls are mocked (deterministic local fixtures, per
this phase's own instruction: "if external APIs cannot safely be called
during tests, use deterministic local fixtures") — no live network call
happens in this test file. The illustration renderer itself is real,
offline, and network-free, so those tests run unmocked.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from ..src import mutate
from ..src.illustration import render_illustration_png
from ..src.real_providers import (
    GeneratedAssetProviderReal,
    WikimediaCommonsRetrievalProvider,
    _classify_license,
)


class IllustrationRendererTests(unittest.TestCase):
    def test_produces_real_nonempty_png_bytes(self):
        data = render_illustration_png("A medieval plague scene")
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(data), 500)

    def test_deterministic_given_identical_input(self):
        a = render_illustration_png("Sanitation and clean water practices")
        b = render_illustration_png("Sanitation and clean water practices")
        self.assertEqual(a, b)

    def test_different_prompts_produce_different_images(self):
        a = render_illustration_png("Medieval quarantine and isolation")
        b = render_illustration_png("Modern hospital contrast")
        self.assertNotEqual(a, b)

    def test_draw_caption_false_omits_caption_text_layer(self):
        with_caption = render_illustration_png("A prompt", draw_caption=True)
        without_caption = render_illustration_png("A prompt", draw_caption=False)
        self.assertNotEqual(with_caption, without_caption)
        # Without caption text should be a strictly smaller PNG (less to encode).
        self.assertLess(len(without_caption), len(with_caption))


class ScenePromptDerivationTests(unittest.TestCase):
    """Phase 8: agents/assets/src/pipeline.py._build_plan derives its
    GeneratedAssetProvider/AssetRetrievalProvider prompt from the scene's
    own narration text, not agents/visual_planner/'s fixed boilerplate
    description — see pipeline.py's own comment for why (a real provider
    can now act on the prompt; a real generic string is useless to it)."""

    def test_scene_specific_prompts_differ_across_scenes_with_different_narration(self):
        import tempfile
        from ...producer.src.pipeline import run_producer
        from ...producer.tests.builders import build_minimal_item
        from ...visual_planner.src.pipeline import run_visual_planner
        from ..src.pipeline import run_asset_generation

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "item"
            build_minimal_item(
                root,
                beats=[
                    "1. A beat about quarantine and isolation practices in medieval towns.",
                    "2. A beat about modern hospital sanitation and clean water access.",
                ],
            )
            run_producer(root, apply=True)
            run_visual_planner(root, apply=True)
            result = run_asset_generation(root, apply=True, generated_provider=GeneratedAssetProviderReal())

            prompts = {p.filename: p.generation_prompt for p in result.plans}
            # Every real prompt traces back to its own scene's narration —
            # never the same fixed boilerplate string for every scene.
            self.assertNotEqual(len(set(prompts.values())), 1)
            self.assertTrue(any("quarantine" in p.lower() for p in prompts.values()))
            self.assertTrue(any("sanitation" in p.lower() for p in prompts.values()))


class GeneratedAssetProviderRealTests(unittest.TestCase):
    def test_generates_real_png_never_a_placeholder(self):
        provider = GeneratedAssetProviderReal()
        artifact = provider.generate("A plague-era medieval city street", "IMAGE")
        self.assertFalse(artifact.is_placeholder)
        self.assertIsNotNone(artifact.artifact_bytes)
        self.assertTrue(artifact.artifact_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(artifact.artifact_extension, "generated.png")

    def test_empty_description_fails_closed(self):
        provider = GeneratedAssetProviderReal()
        with self.assertRaises(ValueError):
            provider.generate("   ", "IMAGE")


def _fake_urlopen_sequence(responses):
    """Returns a context-manager-compatible fake for successive
    urllib.request.urlopen calls, each yielding the next entry in
    `responses` — either bytes (a successful read) or an exception
    instance to raise."""
    it = iter(responses)

    def _opener(request, timeout=None):
        item = next(it)
        if isinstance(item, Exception):
            raise item
        return mock.mock_open(read_data=item)()

    return _opener


class WikimediaRetrievalProviderTests(unittest.TestCase):
    """Every network call is mocked — deterministic local fixtures only,
    matching this phase's own test-safety instruction."""

    def _search_response(self, titles):
        return json.dumps({
            "query": {"search": [{"title": t} for t in titles]}
        }).encode("utf-8")

    def _imageinfo_response(self, url, license_text="CC BY 2.5", artist="A Real Photographer"):
        return json.dumps({
            "query": {"pages": {"1": {"imageinfo": [{
                "url": url,
                "descriptionurl": f"https://commons.wikimedia.org/wiki/File:test",
                "user": "uploader",
                "extmetadata": {
                    "LicenseShortName": {"value": license_text},
                    "Artist": {"value": f"<a href='#'>{artist}</a>"},
                },
            }]}}}
        }).encode("utf-8")

    def test_successful_retrieval_records_real_provenance_no_fabrication(self):
        provider = WikimediaCommonsRetrievalProvider()
        responses = [
            self._search_response(["File:Plague_map.jpg"]),
            self._imageinfo_response("https://upload.wikimedia.org/plague_map.jpg"),
            b"fake-jpeg-bytes",
        ]
        with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_sequence(responses)):
            result = provider.retrieve("Black Death map", "IMAGE")
        self.assertEqual(result.status, "RETRIEVED")
        self.assertEqual(result.artifact_bytes, b"fake-jpeg-bytes")
        self.assertEqual(result.artifact_extension, "jpg")
        self.assertEqual(result.source_url, "https://commons.wikimedia.org/wiki/File:test")
        self.assertIn("Plague_map.jpg", result.source_reference)
        # Artist HTML markup is stripped, never persisted raw.
        self.assertNotIn("<a", result.source_reference)
        self.assertEqual(result.licensing_status, "LICENSED")

    def test_html_in_artist_metadata_is_stripped_not_persisted_raw(self):
        provider = WikimediaCommonsRetrievalProvider()
        responses = [
            self._search_response(["File:Test.png"]),
            self._imageinfo_response(
                "https://upload.wikimedia.org/test.png",
                artist="Roger Zenner",
            ),
            b"fake-png-bytes",
        ]
        with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_sequence(responses)):
            result = provider.retrieve("test query", "IMAGE")
        self.assertNotIn("<a href", result.source_reference)
        self.assertIn("Roger Zenner", result.source_reference)

    def test_no_search_results_fails_closed_never_fabricates(self):
        provider = WikimediaCommonsRetrievalProvider()
        responses = [self._search_response([])]
        with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_sequence(responses)):
            result = provider.retrieve("a very obscure nonexistent query", "IMAGE")
        self.assertEqual(result.status, "RETRIEVAL_FAILED")
        self.assertEqual(result.source_reference, "not yet sourced")
        self.assertIsNone(result.artifact_bytes)

    def test_svg_results_are_skipped_never_downloaded_as_an_image(self):
        provider = WikimediaCommonsRetrievalProvider()
        responses = [self._search_response(["File:Diagram.svg"])]
        with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_sequence(responses)):
            result = provider.retrieve("a diagram", "IMAGE")
        self.assertEqual(result.status, "RETRIEVAL_FAILED")

    def test_network_failure_returns_structured_failure_never_raises(self):
        provider = WikimediaCommonsRetrievalProvider()
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=URLError("simulated network outage"),
        ):
            result = provider.retrieve("Black Death map", "IMAGE")
        self.assertEqual(result.status, "RETRIEVAL_FAILED")
        self.assertIn("failed", result.requirement_note.lower())

    def test_image_download_failure_after_successful_search_fails_closed(self):
        provider = WikimediaCommonsRetrievalProvider()
        responses = [
            self._search_response(["File:Plague_map.jpg"]),
            self._imageinfo_response("https://upload.wikimedia.org/plague_map.jpg"),
            URLError("download failed"),
        ]
        with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_sequence(responses)):
            result = provider.retrieve("Black Death map", "IMAGE")
        self.assertEqual(result.status, "RETRIEVAL_FAILED")
        self.assertIsNone(result.artifact_bytes)

    def test_empty_query_fails_closed(self):
        provider = WikimediaCommonsRetrievalProvider()
        result = provider.retrieve("   ", "IMAGE")
        self.assertEqual(result.status, "RETRIEVAL_FAILED")

    def test_rate_limit_retries_then_succeeds(self):
        provider = WikimediaCommonsRetrievalProvider()
        rate_limited = HTTPError("url", 429, "Too Many Requests", {}, None)
        with mock.patch("time.sleep"):  # don't actually wait in tests
            responses = [
                rate_limited,
                self._search_response(["File:Plague_map.jpg"]),
                self._imageinfo_response("https://upload.wikimedia.org/plague_map.jpg"),
                b"fake-jpeg-bytes",
            ]
            with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen_sequence(responses)):
                result = provider.retrieve("Black Death map", "IMAGE")
        self.assertEqual(result.status, "RETRIEVED")


class LicenseClassificationTests(unittest.TestCase):
    def test_public_domain_marker_classified_correctly(self):
        self.assertEqual(_classify_license("This work is in the public domain"), "PUBLIC_DOMAIN")

    def test_cc_by_marker_classified_as_licensed(self):
        self.assertEqual(_classify_license("CC BY-SA 4.0"), "LICENSED")

    def test_unknown_text_never_upgraded_past_rights_unclear(self):
        self.assertEqual(_classify_license("some unusual custom terms"), "RIGHTS_UNCLEAR")

    def test_empty_license_text_is_unverified_never_assumed_permissive(self):
        self.assertEqual(_classify_license(""), "UNVERIFIED")


class BinaryWriteWhitelistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        self.root.mkdir()

    def test_write_generated_artifact_binary_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_generated_artifact_binary(self.root, "asset-01.jpg", b"data")

    def test_write_generated_artifact_binary_accepts_whitelisted_png(self):
        path = mutate.write_generated_artifact_binary(self.root, "asset-01.generated.png", b"\x89PNG")
        self.assertTrue(path.is_file())

    def test_write_retrieved_artifact_binary_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_retrieved_artifact_binary(self.root, "asset-01.retrieved.gif", b"data")

    def test_write_retrieved_artifact_binary_accepts_jpg_and_png(self):
        p1 = mutate.write_retrieved_artifact_binary(self.root, "asset-01.retrieved.jpg", b"jpgdata")
        p2 = mutate.write_retrieved_artifact_binary(self.root, "asset-02.retrieved.png", b"pngdata")
        self.assertTrue(p1.is_file())
        self.assertTrue(p2.is_file())


if __name__ == "__main__":
    unittest.main()
