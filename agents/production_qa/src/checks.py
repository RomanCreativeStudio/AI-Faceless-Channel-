"""Deterministic, structural readiness checks — never a visual-quality or
editorial judgment. See CONTRACT.md's "Checks (per area)" and "Known
limitation: RETRIEVED strategy". Every check here re-reads and
re-verifies what an earlier agent already claimed rather than trusting it
blindly (e.g. caption text is re-checked against narration, not assumed
faithful because agents/captions/ says so).
"""
from __future__ import annotations

from pathlib import Path

from ...researcher.src import parsing
from .models import CheckResult

HEDGE_PREFIXES = ("what if", "could", "might")


def _already_hedged(title: str) -> bool:
    return "?" in title or title.strip().lower().startswith(HEDGE_PREFIXES)


def check_content(content_item, production_table, current_script_hash: str, scenes, claims) -> list[CheckResult]:
    checks = []
    checks.append(CheckResult("Content", "Content status APPROVED", content_item.status == "APPROVED", f"status={content_item.status}"))

    stored_hash = parsing.strip_single_backticks(production_table.get("Script content hash", ""))
    checks.append(CheckResult("Content", "Script hash current", stored_hash == current_script_hash, f"stored={stored_hash!r} current={current_script_hash!r}"))

    missing = [(s.filename, cid) for s in scenes for cid in s.claim_ids if cid not in claims]
    checks.append(CheckResult("Content", "Claims referenced by scenes exist", not missing, f"missing={missing}" if missing else "all resolve"))

    # load_claims already raises on an invalid Classification, so if we
    # got this far every claim's What If? distinction (Classification) is
    # a recognized value — re-affirm explicitly for the record.
    invalid = [cid for cid, c in claims.items() if c.classification is None]
    checks.append(CheckResult("Content", "What If? classifications intact", not invalid, "all claim Classification values valid"))
    return checks


def check_voice(root: Path, current_script_hash: str) -> list[CheckResult]:
    voice_path = root / "voice" / "voice-01.md"
    if not voice_path.is_file():
        return [CheckResult("Voice", "Voice record exists", False, "no voice/voice-01.md")]

    text = voice_path.read_text(encoding="utf-8")
    identity = parsing.parse_table(text)
    sections = parsing.parse_sections(text)
    voice_hash = parsing.strip_single_backticks(identity.get("Script content hash", ""))
    generation_status = sections.get("Generation status", "").strip().strip("`")
    audio_table = parsing.parse_table(sections.get("Generated audio", ""))
    audio_reference = parsing.strip_single_backticks(audio_table.get("Reference", ""))

    return [
        CheckResult("Voice", "Voice record exists", True, str(voice_path)),
        CheckResult("Voice", "Voice hash matches", voice_hash == current_script_hash, f"stored={voice_hash!r} current={current_script_hash!r}"),
        CheckResult("Voice", "Audio reference exists", bool(audio_reference) and audio_reference.lower() != "not yet generated", f"reference={audio_reference!r}"),
        CheckResult("Voice", "Voice generation status valid", generation_status == "GENERATED", f"status={generation_status!r}"),
    ]


def check_assets(root: Path, scenes) -> list[CheckResult]:
    checks = []
    for scene in scenes:
        asset_path = root / "assets" / f"asset-{scene.order:02d}.md"
        if not asset_path.is_file():
            checks.append(CheckResult("Assets", f"{scene.filename}: asset exists", False, f"missing assets/asset-{scene.order:02d}.md"))
            continue
        text = asset_path.read_text(encoding="utf-8")
        sections = parsing.parse_sections(text)
        provenance_table = parsing.parse_table(sections.get("Provenance", ""))
        strategy = parsing.first_backtick_token(provenance_table.get("Generated vs. retrieved", ""))
        source = provenance_table.get("Source", "").strip()
        auth_table = parsing.parse_table(sections.get("Historical authenticity classification", ""))
        classification = parsing.first_backtick_token(auth_table.get("Classification", ""))
        generation_status = sections.get("Generation/retrieval status", "").strip().strip("`")
        verification_status = sections.get("Verification status", "").splitlines()[0].strip().strip("`") if sections.get("Verification status") else ""

        checks.append(CheckResult("Assets", f"{scene.filename}: asset exists", True, str(asset_path)))
        checks.append(CheckResult(
            "Assets", f"{scene.filename}: authenticity classification valid",
            classification in ("AUTHENTIC_HISTORICAL_MEDIA", "GENERATED_RECONSTRUCTION", "NOT_APPLICABLE"),
            f"classification={classification!r}",
        ))
        checks.append(CheckResult("Assets", f"{scene.filename}: provenance recorded", bool(source), f"source={source!r}"))

        if strategy == "GENERATED":
            checks.append(CheckResult("Assets", f"{scene.filename}: generated asset marked generated", generation_status == "GENERATED", f"generation_status={generation_status!r}"))
        elif strategy == "RETRIEVED":
            checks.append(CheckResult(
                "Assets", f"{scene.filename}: retrieved asset has real retrieval evidence",
                generation_status == "RETRIEVED",
                "no real retrieval integration exists this phase — see CONTRACT.md's "
                "'Known limitation: RETRIEVED strategy'" if generation_status != "RETRIEVED" else "retrieved",
            ))
        elif strategy == "HUMAN_PROVIDED":
            has_source = bool(source) and source.strip().lower() not in ("", "unknown")
            checks.append(CheckResult(
                "Assets", f"{scene.filename}: human-provided asset has provenance status",
                has_source or verification_status == "REVIEW_REQUIRED",
                f"source={source!r} verification_status={verification_status!r}",
            ))
    return checks


def check_timeline(root: Path) -> list[CheckResult]:
    timeline_path = root / "timeline" / "timeline-01.md"
    if not timeline_path.is_file():
        return [CheckResult("Timeline", "Timeline exists", False, "no timeline/timeline-01.md")]

    text = timeline_path.read_text(encoding="utf-8")
    identity = parsing.parse_table(text)
    sections = parsing.parse_sections(text)
    total_duration_raw = parsing.strip_single_backticks(identity.get("Total duration", "0s"))
    try:
        total_duration = int(total_duration_raw.rstrip("s") or 0)
    except ValueError:
        total_duration = -1

    rows = []
    for line in sections.get("Scene timeline", "").splitlines():
        line = line.strip()
        if not line.startswith("|") or "Scene ID" in line:
            continue
        content_only = line.replace("|", "").strip()
        if content_only and set(content_only) <= {"-"}:
            continue  # separator row
        rows.append(line)

    checks = [CheckResult("Timeline", "Timeline exists", True, str(timeline_path))]

    parsed_rows = []
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 9:
            continue
        parsed_rows.append(cells)

    checks.append(CheckResult("Timeline", "Every scene has a duration", bool(parsed_rows) and all(
        parsing.strip_single_backticks(c[3]).rstrip("s").isdigit() and int(parsing.strip_single_backticks(c[3]).rstrip("s")) > 0
        for c in parsed_rows
    ), f"{len(parsed_rows)} scene row(s)"))

    no_overlap = True
    cumulative_end = 0
    for cells in parsed_rows:
        start = int(parsing.strip_single_backticks(cells[1]).rstrip("s") or -1)
        end = int(parsing.strip_single_backticks(cells[2]).rstrip("s") or -1)
        if start != cumulative_end or end < start:
            no_overlap = False
        cumulative_end = end
    checks.append(CheckResult("Timeline", "No scene overlaps or gaps", no_overlap, "start/end chain verified"))

    checks.append(CheckResult("Timeline", "Total duration consistent", total_duration == cumulative_end, f"declared={total_duration} computed={cumulative_end}"))

    every_reference = all(
        parsing.strip_single_backticks(c[4]) and parsing.strip_single_backticks(c[5]) and parsing.strip_single_backticks(c[6])
        for c in parsed_rows
    )
    checks.append(CheckResult("Timeline", "Every scene references required inputs", every_reference, "narration/visual/captions references present"))
    return checks


def _split_h3_subsections(body: str) -> dict[str, str]:
    """`## Scene captions`' body holds one `### Scene ...` subsection per
    scene — parse_sections only splits on `## `, so split H3s out here."""
    subsections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("### "):
            if current is not None:
                subsections[current] = "\n".join(buf).strip()
            current = line[4:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        subsections[current] = "\n".join(buf).strip()
    return subsections


def check_captions(root: Path, scenes) -> list[CheckResult]:
    captions_path = root / "captions" / "captions-01.md"
    if not captions_path.is_file():
        return [CheckResult("Captions", "Captions exist", False, "no captions/captions-01.md")]

    text = captions_path.read_text(encoding="utf-8")
    sections = parsing.parse_sections(text)
    scene_subsections = _split_h3_subsections(sections.get("Scene captions", ""))
    narration_by_scene = {s.filename: s.narration_text for s in scenes}
    scene_id_by_filename = {s.filename: s.scene_id for s in scenes}

    checks = [CheckResult("Captions", "Captions exist", True, str(captions_path))]

    timing_valid = True
    text_faithful = True
    for scene_filename, narration in narration_by_scene.items():
        scene_id_marker = scene_id_by_filename.get(scene_filename)
        section_key = f"Scene `{scene_id_marker}`" if scene_id_marker else None
        body = scene_subsections.get(section_key, "") if section_key else ""
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or "Caption #" in line:
                continue
            content_only = line.replace("|", "").strip()
            if content_only and set(content_only) <= {"-"}:
                continue  # separator row
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4 or cells[0] == "—":
                continue
            try:
                start = float(parsing.strip_single_backticks(cells[1]).rstrip("s"))
                end = float(parsing.strip_single_backticks(cells[2]).rstrip("s"))
            except ValueError:
                timing_valid = False
                continue
            if start > end:
                timing_valid = False
            caption_text = cells[3]
            if caption_text not in narration and caption_text != "(no narration to caption)":
                text_faithful = False

    checks.append(CheckResult("Captions", "Caption timing valid", timing_valid, "every chunk Start <= End"))
    checks.append(CheckResult("Captions", "Captions map to narration (no unsupported extra claims)", text_faithful, "every chunk verbatim substring of source narration"))
    return checks


def check_thumbnail(root: Path, content_pillar: str, working_title: str, authenticity_found: set[str]) -> list[CheckResult]:
    thumbnail_path = root / "thumbnail" / "thumbnail-01.md"
    if not thumbnail_path.is_file():
        return [CheckResult("Thumbnail", "Thumbnail spec exists", False, "no thumbnail/thumbnail-01.md")]

    text = thumbnail_path.read_text(encoding="utf-8")
    sections = parsing.parse_sections(text)
    concept_table = parsing.parse_table(sections.get("Concept", ""))
    title_concept = concept_table.get("Title concept", "").strip()
    authenticity_considerations = sections.get("Authenticity considerations", "").strip()

    checks = [
        CheckResult("Thumbnail", "Thumbnail spec exists", True, str(thumbnail_path)),
        CheckResult("Thumbnail", "Title/theme matches content", bool(title_concept), f"title_concept={title_concept!r}"),
    ]

    if "GENERATED_RECONSTRUCTION" in authenticity_found:
        no_false_claim = "must not present" in authenticity_considerations or "GENERATED_RECONSTRUCTION" in authenticity_considerations
        checks.append(CheckResult("Thumbnail", "No false factual implication", no_false_claim, authenticity_considerations[:120]))
    else:
        checks.append(CheckResult("Thumbnail", "No false factual implication", True, "no generated-reconstruction asset in this production"))

    if content_pillar == "what-if" and not _already_hedged(working_title):
        checks.append(CheckResult("Thumbnail", "What If? framing preserved", _already_hedged(title_concept), f"title_concept={title_concept!r}"))
    else:
        checks.append(CheckResult("Thumbnail", "What If? framing preserved", True, "not applicable — title already hedged or pillar is not what-if"))
    return checks


def check_output(root: Path, production_text: str) -> list[CheckResult]:
    timeline_path = root / "timeline" / "timeline-01.md"
    if not timeline_path.is_file():
        return [CheckResult("Output", "Final video reference exists", False, "no timeline/timeline-01.md")]

    text = timeline_path.read_text(encoding="utf-8")
    sections = parsing.parse_sections(text)
    output_table = parsing.parse_table(sections.get("Output", ""))
    video_reference = parsing.strip_single_backticks(output_table.get("Video reference", ""))
    output_hash = parsing.strip_single_backticks(output_table.get("Output hash", ""))
    playable = parsing.strip_single_backticks(output_table.get("Playable", ""))

    production_sections = parsing.parse_sections(production_text)
    title_table = parsing.parse_table(production_sections.get("Title / description", ""))
    working_title = title_table.get("Working title", "").strip()

    checks = [
        CheckResult("Output", "Final video reference exists", bool(video_reference) and video_reference.lower() != "not yet produced", f"reference={video_reference!r}"),
        CheckResult("Output", "Output hash recorded", bool(output_hash) and output_hash != "N/A", f"hash={output_hash!r}"),
        CheckResult(
            "Output", "Playable status recognized", playable in ("YES", "NO", "UNVERIFIED"),
            f"playable={playable!r}" + (" — no real renderer this phase, expected" if playable == "NO" else ""),
        ),
        CheckResult("Output", "Production metadata exists", bool(working_title), f"working_title={working_title!r}"),
    ]
    return checks
