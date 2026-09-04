"""Phase 8's first production-capable VideoRenderer — a real ffmpeg-based
renderer. A second `VideoRenderer` implementation (provider.py); nothing
in agents/assembler/src/pipeline.py or mutate.py needed to change beyond
the additive `RenderResult.artifact_bytes` field and the `root` parameter
`VideoRenderer.render()` now takes (see provider.py's Phase 8 note — a
real renderer structurally needs the content item's directory to resolve
scene/voice/caption references into actual files on disk; the placeholder
renderer never needed it since it only echoes the string references).

Pipeline (all via subprocess argument lists, never `shell=True` — no
narration/caption/path text is ever interpolated into a shell command):

1. Resolve the single narration audio file (voice/voice-01.md's own
   `Generated audio > Reference`) and each scene's visual asset file
   (assets/asset-<n>.md's own `Technical > File reference`) — never
   assumed, always read from the records those agents actually wrote.
2. Normalize each scene's still image into its own silent video segment,
   held for exactly that scene's `templates/TIMELINE.md` duration
   (`-loop 1 -t <duration>`), at a consistent 1920x1080/yuv420p/30fps —
   this is what "preserve the timeline's scene durations" means here.
3. Concatenate every segment (ffmpeg's concat demuxer, stream-copy — safe
   because every segment already shares identical codec parameters from
   step 2).
4. Mux the concatenated (silent) video with the real narration audio,
   burning in captions built from agents/captions/'s own per-scene,
   scene-relative chunk timings plus each scene's own `start` offset
   (never a captions/CAPTIONS.md schema change — see captions_reader.py).

If the narration audio is longer than the timeline's total duration, the
**last** scene's held duration is extended to cover the difference —
documented here, not silently absorbed — rather than truncating narration
or stretching every scene's duration; every other scene's duration is
exactly what templates/TIMELINE.md records. `-shortest` on the final mux
then trims any leftover silent video past the audio's own end.

Fails closed, never silently: `RendererConfigurationError` if this
environment cannot run ffmpeg at all; `RendererFailure` for any ffmpeg
step failing, or for a produced file this renderer's own ffprobe check
cannot independently verify as playable. `Playable = YES` is only ever
returned once actually confirmed this way — never assumed.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ...researcher.src import parsing
from .captions_reader import load_scene_caption_chunks
from .provider import RenderResult

FFMPEG_LABEL = "ffmpeg (H.264/AAC, local render, no cloud rendering service)"
_WIDTH, _HEIGHT, _FPS = 1920, 1080, 30
_SEGMENT_TIMEOUT_SECONDS = 300
_FINAL_MUX_TIMEOUT_SECONDS = 600


class RendererConfigurationError(Exception):
    """This environment cannot run the real renderer at all (e.g. no
    ffmpeg). Never caught silently."""


class RendererFailure(Exception):
    """ffmpeg ran but a step failed, or the output couldn't be
    independently verified as playable."""


def _require_ffmpeg() -> tuple[str, str]:
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if not ffmpeg_path or not ffprobe_path:
        raise RendererConfigurationError(
            "ffmpeg/ffprobe are not installed in this environment — the real "
            "video renderer cannot run. This is a structured configuration "
            "error, not a placeholder fallback: install ffmpeg before using "
            "FFmpegVideoRenderer, or pass a different real VideoRenderer."
        )
    return ffmpeg_path, ffprobe_path


def _run(cmd: list[str], timeout: int, step: str, cwd: Path | None = None) -> None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired as exc:
        raise RendererFailure(f"{step} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise RendererFailure(f"{step} failed (exit {proc.returncode}): {proc.stderr.strip()[-2000:]}")


def _resolve_reference(root: Path, md_path: Path, section_heading: str, field_name: str) -> Path | None:
    if not md_path.is_file():
        return None
    text = md_path.read_text(encoding="utf-8")
    sections = parsing.parse_sections(text)
    table = parsing.parse_table(sections.get(section_heading, ""))
    raw = parsing.strip_single_backticks(table.get(field_name, ""))
    if not raw or raw.strip().lower() in ("not yet produced", "n/a", "not yet generated"):
        return None
    resolved = root / raw
    return resolved if resolved.is_file() else None


def _audio_duration_seconds(ffprobe_path: str, audio_path: Path) -> float:
    cmd = [
        ffprobe_path, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RendererFailure(f"ffprobe could not read narration audio duration: {proc.stderr.strip()}")
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise RendererFailure(f"ffprobe returned a non-numeric audio duration: {proc.stdout!r}") from exc


def _format_srt_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_srt(scenes: list, captions_path: Path) -> str:
    chunks_by_scene = load_scene_caption_chunks(captions_path)
    entries: list[tuple[float, float, str]] = []
    for scene in scenes:
        for chunk in chunks_by_scene.get(scene.scene_id, []):
            entries.append((scene.start + chunk.start, scene.start + chunk.end, chunk.text))

    lines: list[str] = []
    for i, (start, end, text) in enumerate(entries, start=1):
        if end <= start:
            end = start + 0.5
        lines.append(str(i))
        lines.append(f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


class FFmpegVideoRenderer:
    label = FFMPEG_LABEL

    def render(self, scenes: list, total_duration: int, root: Path) -> RenderResult:
        if not scenes:
            raise RendererFailure("cannot render zero scenes")
        ffmpeg_path, ffprobe_path = _require_ffmpeg()

        voice_md = root / "voice" / "voice-01.md"
        audio_path = _resolve_reference(root, voice_md, "Generated audio", "Reference")
        if audio_path is None:
            raise RendererFailure(f"could not resolve a real narration audio file from {voice_md}")
        audio_duration = _audio_duration_seconds(ffprobe_path, audio_path)

        scene_images: list[Path] = []
        for scene in scenes:
            asset_md = root / scene.visual_reference
            image_path = _resolve_reference(root, asset_md, "Technical", "File reference")
            if image_path is None:
                raise RendererFailure(
                    f"could not resolve a real visual asset file for scene {scene.scene_id!r} "
                    f"from {asset_md}"
                )
            scene_images.append(image_path)

        durations = [scene.duration_seconds for scene in scenes]
        shortfall = audio_duration - sum(durations)
        if shortfall > 0:
            durations[-1] = durations[-1] + shortfall

        captions_path = root / "captions" / "captions-01.md"
        srt_text = _build_srt(scenes, captions_path)

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)

            segment_paths: list[Path] = []
            for i, (image_path, duration) in enumerate(zip(scene_images, durations), start=1):
                segment_path = tmp / f"segment-{i:02d}.mp4"
                cmd = [
                    ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                    "-loop", "1", "-t", str(max(1, duration)), "-i", str(image_path),
                    "-vf",
                    f"scale={_WIDTH}:{_HEIGHT}:force_original_aspect_ratio=decrease,"
                    f"pad={_WIDTH}:{_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p",
                    "-r", str(_FPS), "-an", str(segment_path),
                ]
                _run(cmd, _SEGMENT_TIMEOUT_SECONDS, f"segment {i} normalization")
                segment_paths.append(segment_path)

            # Relative names only, resolved by the concat demuxer relative
            # to the list file's own directory — deliberately not cwd-
            # dependent, and every segment already shares identical codec
            # parameters (from the normalization step above), so this is a
            # safe, fast stream-copy concatenation.
            concat_list = tmp / "segments.txt"
            concat_list.write_text(
                "".join(f"file '{p.name}'\n" for p in segment_paths), encoding="utf-8",
            )
            concatenated = tmp / "concatenated.mp4"
            _run(
                [
                    ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(concat_list),
                    "-c", "copy", str(concatenated),
                ],
                _SEGMENT_TIMEOUT_SECONDS, "segment concatenation",
            )

            srt_path = tmp / "captions.srt"
            srt_path.write_text(srt_text, encoding="utf-8")

            output_path = tmp / "output.mp4"
            vf = (
                f"subtitles={srt_path.name}:force_style="
                "'FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BorderStyle=3,Outline=1,MarginV=40'"
                if srt_text.strip() else None
            )
            mux_cmd = [
                ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(concatenated), "-i", str(audio_path),
            ]
            if vf:
                mux_cmd += ["-vf", vf]
            mux_cmd += [
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-shortest",
                str(output_path),
            ]
            # The subtitles filter's own relative-path argument (srt_path.name)
            # is resolved against the process's cwd, unlike the concat
            # demuxer above — so this one call runs with cwd=tmp.
            _run(mux_cmd, _FINAL_MUX_TIMEOUT_SECONDS, "final mux/subtitle burn-in", cwd=tmp)
            if not output_path.is_file():
                raise RendererFailure("final mux/subtitle burn-in reported success but produced no output file")

            probe_cmd = [
                ffprobe_path, "-v", "error", "-show_entries",
                "format=duration:stream=codec_type", "-of", "default=noprint_wrappers=1", str(output_path),
            ]
            probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=60)
            probe_out = probe.stdout
            has_video = "codec_type=video" in probe_out
            has_audio = "codec_type=audio" in probe_out
            try:
                out_duration = float([line.split("=", 1)[1] for line in probe_out.splitlines() if line.startswith("duration=")][0])
            except (IndexError, ValueError):
                out_duration = 0.0

            if probe.returncode != 0 or not has_video or not has_audio or out_duration <= 0:
                raise RendererFailure(
                    "rendered output.mp4 failed independent ffprobe verification "
                    f"(has_video={has_video} has_audio={has_audio} duration={out_duration}) "
                    "— never reporting Playable=YES for an unverified file"
                )

            video_bytes = output_path.read_bytes()

        return RenderResult(
            provider_label=self.label,
            artifact_content="",
            format="mp4",
            is_placeholder=False,
            playable="YES",
            artifact_bytes=video_bytes,
        )
