"""Phase 8's first production-capable asset providers: one real
GeneratedAssetProvider (a deterministic, offline illustration renderer)
and one real AssetRetrievalProvider (Wikimedia Commons, a free/open,
no-API-key media archive). Both are second implementations of
provider.py's Protocols — nothing in agents/assets/src/pipeline.py or
mutate.py needed to change beyond the additive fields already on
GeneratedArtifact/RetrievalResult (see provider.py's Phase 8 notes).

Neither provider ever fabricates a source, a URL, or a license — see each
class's own docstring for exactly what it does and does not verify.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Wikimedia's extmetadata (e.g. Artist) often comes back as an HTML
    fragment (an `<a href=...>` credit link) — this is provenance text
    persisted into a markdown table cell, never raw markup, and never
    allowed to break that table's own `|`-delimited row structure."""
    return _HTML_TAG_RE.sub("", text).replace("|", "/").strip()

from .illustration import render_illustration_png
from .provider import GeneratedArtifact, RetrievalResult

GENERATED_LABEL = "local-illustration-renderer (Pillow, offline, no network, no external model)"
WIKIMEDIA_LABEL = "wikimedia-commons (public API, no API key required)"

_WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
_REQUEST_TIMEOUT_SECONDS = 20
_USER_AGENT = "AI-Faceless-Channel-Phase8/1.0 (research/education content pipeline)"

_ACCEPTABLE_IMAGE_EXTENSIONS = {"jpg": "jpg", "jpeg": "jpg", "png": "png"}

# Structural, conservative license-text -> templates/ASSET.md licensing
# status mapping. Deliberately narrow: anything not clearly recognized
# stays UNVERIFIED rather than guessed into a more permissive bucket.
_PUBLIC_DOMAIN_MARKERS = ("public domain", "pd-old", "cc0", "no known copyright")
_LICENSED_MARKERS = ("cc-by", "cc by", "creative commons attribution", "gfdl")


class RetrievalConfigurationError(Exception):
    """This environment cannot reach the retrieval provider at all (e.g.
    no network). Never caught silently — see CONTRACT.md's Phase 8
    "Provider failure behavior"."""


class GeneratedAssetProviderReal:
    """Deterministic offline illustration provider — see
    agents/assets/src/illustration.py for the actual rendering. Always
    produces a genuinely real PNG (never a placeholder), always
    stylistically non-photorealistic (clearly illustrative, never
    mistakable for a real photograph), always burns an "AI-GENERATED
    RECONSTRUCTION" label directly into the image in addition to the
    separately-recorded Historical authenticity classification metadata.
    """

    label = GENERATED_LABEL

    def generate(self, visual_description: str, asset_type: str) -> GeneratedArtifact:
        if not visual_description.strip():
            raise ValueError("cannot render an illustration from an empty visual description")
        # draw_caption=False: this scene's real narration is already
        # captioned separately, in sync, by the video renderer's own
        # subtitle burn-in — see illustration.py's own docstring for why
        # this image never also burns in its own, colliding caption text.
        png_bytes = render_illustration_png(visual_description, draw_caption=False)
        return GeneratedArtifact(
            provider_label=self.label,
            artifact_content="",
            is_placeholder=False,
            artifact_bytes=png_bytes,
            artifact_extension="generated.png",
        )


def _classify_license(license_text: str) -> str:
    lowered = license_text.lower()
    if any(marker in lowered for marker in _PUBLIC_DOMAIN_MARKERS):
        return "PUBLIC_DOMAIN"
    if any(marker in lowered for marker in _LICENSED_MARKERS):
        return "LICENSED"
    if not license_text.strip() or license_text.strip().upper() == "N/A":
        return "UNVERIFIED"
    return "RIGHTS_UNCLEAR"


class WikimediaCommonsRetrievalProvider:
    """Real RETRIEVED-strategy provider — queries Wikimedia Commons'
    public search API (no API key/authentication of any kind) for one
    freely-licensed image matching the visual description, then downloads
    it. Every recorded field (Source, Source URL, license text, licensing
    status) traces back to what Wikimedia's own API actually reported —
    never invented. `Licensing/provenance status` reflects only a
    structural read of the license text Wikimedia reports (public-domain/
    CC-BY/GFDL keyword matching) — never a claim of legal review, and
    `Verification status` always stays `NOT_STARTED` regardless (a human
    must still confirm it, per templates/ASSET.md's "never mark
    Verification status... cleared just to unblock a scene").

    If no result is found, or the network/API is unavailable, this
    returns a structured `RETRIEVAL_FAILED` result — never fabricates a
    source and never pretends a retrieval succeeded.
    """

    label = WIKIMEDIA_LABEL

    def __init__(self, timeout_seconds: int = _REQUEST_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds

    def _get_json(self, params: dict, max_attempts: int = 3) -> dict:
        """A transient 429/5xx is a real, expected condition for a public,
        shared, rate-limited API — retried with backoff (honoring
        Retry-After when the server sends one), never silently given up
        on after a single hiccup. Still fails closed (raises) once
        max_attempts is exhausted — the caller's own except clause turns
        that into a structured RETRIEVAL_FAILED, never a fabricated
        success.
        """
        url = f"{_WIKIMEDIA_API}?{urllib.parse.urlencode(params)}"
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code not in (429, 502, 503, 504) or attempt == max_attempts - 1:
                    raise
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = float(retry_after) if retry_after else (2 ** attempt) * 2
                except ValueError:
                    delay = (2 ** attempt) * 2
                time.sleep(min(delay, 15))
        raise last_exc  # pragma: no cover — unreachable, loop always returns or raises

    def retrieve(self, visual_description: str, asset_type: str) -> RetrievalResult:
        query = visual_description.strip()
        if not query:
            return RetrievalResult(
                provider_label=self.label, status="RETRIEVAL_FAILED",
                requirement_note="empty visual description — nothing to search for",
                source_reference="not yet sourced",
            )

        try:
            search = self._get_json({
                "action": "query", "list": "search", "srnamespace": "6",  # File: namespace
                "srsearch": query, "srlimit": "5", "format": "json",
            })
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return RetrievalResult(
                provider_label=self.label, status="RETRIEVAL_FAILED",
                requirement_note=f"Wikimedia Commons search request failed: {exc!r}",
                source_reference="not yet sourced",
            )

        results = search.get("query", {}).get("search", [])
        for hit in results:
            title = hit.get("title", "")
            if not title.startswith("File:"):
                continue
            extension = title.rsplit(".", 1)[-1].lower() if "." in title else ""
            if extension not in _ACCEPTABLE_IMAGE_EXTENSIONS:
                continue  # skip SVGs/other formats this MVP doesn't render for video

            try:
                info = self._get_json({
                    "action": "query", "titles": title, "prop": "imageinfo",
                    "iiprop": "url|extmetadata|user", "format": "json",
                })
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                continue

            pages = info.get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            imageinfo = (page.get("imageinfo") or [{}])[0]
            image_url = imageinfo.get("url", "")
            descriptionurl = imageinfo.get("descriptionurl", "") or f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title)}"
            extmetadata = imageinfo.get("extmetadata", {})
            license_text = _strip_html(
                extmetadata.get("LicenseShortName", {}).get("value", "")
                or extmetadata.get("UsageTerms", {}).get("value", "")
            )
            artist = _strip_html(extmetadata.get("Artist", {}).get("value", "")) or imageinfo.get("user", "")

            if not image_url:
                continue

            try:
                image_request = urllib.request.Request(image_url, headers={"User-Agent": _USER_AGENT})
                with urllib.request.urlopen(image_request, timeout=self.timeout_seconds) as response:
                    image_bytes = response.read()
            except (urllib.error.URLError, TimeoutError, OSError):
                continue

            if not image_bytes:
                continue

            licensing_status = _classify_license(license_text)
            return RetrievalResult(
                provider_label=self.label,
                status="RETRIEVED",
                requirement_note="",
                source_reference=(
                    f"Wikimedia Commons — {title.replace('|', '/')} "
                    f"(uploader/artist: {artist or 'unknown'})"
                ),
                source_url=descriptionurl,
                license_text=license_text or "not reported by Wikimedia",
                licensing_status=licensing_status,
                artifact_bytes=image_bytes,
                artifact_extension=_ACCEPTABLE_IMAGE_EXTENSIONS[extension],
            )

        return RetrievalResult(
            provider_label=self.label, status="RETRIEVAL_FAILED",
            requirement_note=(
                f"no usable (JPEG/PNG, downloadable) Wikimedia Commons result found for "
                f"query: {query!r}"
            ),
            source_reference="not yet sourced",
        )
