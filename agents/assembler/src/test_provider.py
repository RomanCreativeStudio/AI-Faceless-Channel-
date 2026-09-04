"""Deterministic local/test VideoRenderer — no ffmpeg, no video encoding
library, no network. See CONTRACT.md's "Actual video artifact status" for
why: this environment has no video-encoding tool installed, and every
agent in this repo is stdlib-only by established convention — adding a
dependency to render real video is out of this phase's scope, not
something to do silently. Writes a deterministic manifest describing the
scene sequence a real renderer would assemble, permanently labeled
placeholder, `Playable` always `NO`.
"""
from __future__ import annotations

import hashlib

from .provider import RenderResult

PLACEHOLDER_LABEL = "TEST / PLACEHOLDER VIDEO MANIFEST — not a real video file"


class LocalTestVideoRenderer:
    """Deterministic stand-in renderer. Same scene sequence + duration
    always produces the same manifest content — no randomness, no
    network calls, no real encoding of any kind."""

    label = "local-test-video-renderer"

    def render(self, scenes: list, total_duration: int, root=None) -> RenderResult:
        lines = [
            PLACEHOLDER_LABEL,
            f"Renderer: {self.label}",
            f"Total duration: {total_duration}s",
            f"Scene count: {len(scenes)}",
            "No local video-encoding tool (ffmpeg or equivalent) is available in "
            "this environment — see agents/assembler/README.md 'Actual video "
            "artifact status'. This manifest describes what a real renderer "
            "would assemble; it is not itself a video.",
            "---",
        ]
        for scene in scenes:
            lines.append(
                f"scene={scene.scene_id} start={scene.start}s end={scene.end}s "
                f"duration={scene.duration_seconds}s "
                f"narration_ref={scene.narration_reference} "
                f"visual_ref={scene.visual_reference} "
                f"transition_in={scene.transition_in} transition_out={scene.transition_out}"
            )
        manifest_content = "\n".join(lines) + "\n"
        content_hash = hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()[:16]
        manifest_content += f"Manifest hash: {content_hash}\n"

        return RenderResult(
            provider_label=self.label,
            artifact_content=manifest_content,
            format="manifest.txt",
            is_placeholder=True,
            playable="NO",
        )
