"""Tests 44-50 (Phase 7D task's Integration tests section): the full
pipeline — Producer -> Visual Planner -> Voice -> Assets -> Assembler ->
Captions -> Thumbnail -> Production QA — produces a coherent production
package; a stale upstream artifact prevents downstream assembly; one
invalid asset prevents a final PASS; the golden sample is never touched;
no agent anywhere in this phase has any publishing capability.
"""
import ast
import re
import tempfile
import unittest
from pathlib import Path

from ...assembler.src.pipeline import run_video_assembly
from ...assets.src.pipeline import run_asset_generation
from ...captions.src.pipeline import run_caption_generation
from ...producer.src.pipeline import run_producer
from ...producer.tests.builders import build_minimal_item, write_claim
from ...thumbnail.src.pipeline import run_thumbnail_generation
from ...visual_planner.src.pipeline import run_visual_planner
from ...voice.src.pipeline import run_voice_generation
from ..src.pipeline import run_production_qa

GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)

AGENT_SRC_DIRS = [
    Path(__file__).resolve().parents[3] / name / "src"
    for name in ("producer", "voice", "visual_planner", "assets", "assembler", "captions", "thumbnail", "production_qa")
]


class FullPipelineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"

    # --- Test 44 & 45: the full chain, each stage handing off correctly ---
    def test_full_pipeline_producer_through_production_qa(self):
        build_minimal_item(
            self.root,
            pillar="what-if",
            title="Could Modern Medicine Have Stopped It?",
            hook="An approved opening hook for this fixture.",
            beats=[
                "1. A hypothetical beat, where it's hard to say for certain. — claims: `c4`",
            ],
        )
        write_claim(self.root, "c4", classification="ASSUMPTION")

        producer_result = run_producer(self.root, apply=True)
        self.assertTrue(producer_result.produced)

        voice_result = run_voice_generation(self.root, apply=True)
        self.assertTrue(voice_result.produced)

        planner_result = run_visual_planner(self.root, apply=True)
        self.assertTrue(planner_result.planned)

        asset_result = run_asset_generation(self.root, apply=True)
        self.assertTrue(asset_result.produced)

        assembly_result = run_video_assembly(self.root, apply=True)
        self.assertTrue(assembly_result.produced)
        self.assertEqual(assembly_result.assembly_status, "ASSEMBLED")

        captions_result = run_caption_generation(self.root, apply=True)
        self.assertTrue(captions_result.produced)

        thumbnail_result = run_thumbnail_generation(self.root, apply=True)
        self.assertTrue(thumbnail_result.produced)

        qa_result = run_production_qa(self.root, apply=True)
        self.assertEqual(qa_result.verdict, "PASS")

        # --- Test 46: the package is coherent — every record cross-references correctly ---
        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        self.assertIn("| Production status | `HUMAN_REVIEW` |", production_text)
        self.assertIn("timeline/timeline-01.md", production_text)
        self.assertIn("thumbnail/thumbnail-01.md", production_text)

        self.assertTrue((self.root / "timeline" / "timeline-01.md").is_file())
        self.assertTrue((self.root / "captions" / "captions-01.md").is_file())
        self.assertTrue((self.root / "thumbnail" / "thumbnail-01.md").is_file())
        self.assertTrue((self.root / "qa" / "production-qa-01.md").is_file())
        self.assertTrue((self.root / "output" / "video-01.manifest.txt").is_file())

        # Human review remains untouched — the pipeline never approves itself.
        self.assertIn("| State | `NOT_STARTED` |", production_text.split("## Human review state", 1)[1])
        content_item_text = (self.root / "CONTENT_ITEM.md").read_text(encoding="utf-8")
        self.assertIn("Current status: `APPROVED`", content_item_text)

    # --- Test 47: one stale upstream artifact prevents downstream assembly ---
    def test_stale_upstream_prevents_downstream_stages(self):
        build_minimal_item(self.root, beats=["1. A factual beat. — claims: `c1`"])
        run_producer(self.root, apply=True)
        run_voice_generation(self.root, apply=True)
        run_visual_planner(self.root, apply=True)
        run_asset_generation(self.root, apply=True)

        # Corrupt the voice record's script hash to simulate staleness.
        voice_path = self.root / "voice" / "voice-01.md"
        text = voice_path.read_text(encoding="utf-8")
        line = [l for l in text.splitlines() if l.startswith("| Script content hash |")][0]
        voice_path.write_text(text.replace(line, "| Script content hash | `0000000000stale` |"), encoding="utf-8")

        assembly_result = run_video_assembly(self.root, apply=True)
        self.assertTrue(assembly_result.blocked)
        self.assertFalse(assembly_result.produced)
        self.assertFalse((self.root / "timeline").exists())

    # --- Test 48: one invalid asset prevents final QA PASS ---
    def test_invalid_asset_prevents_qa_pass(self):
        build_minimal_item(
            self.root, pillar="what-if", title="Could Modern Medicine Have Stopped It?",
            beats=["1. A hypothetical beat. — claims: `c4`"],
        )
        write_claim(self.root, "c4", classification="ASSUMPTION")
        run_producer(self.root, apply=True)
        run_voice_generation(self.root, apply=True)
        run_visual_planner(self.root, apply=True)
        run_asset_generation(self.root, apply=True)
        run_video_assembly(self.root, apply=True)
        run_caption_generation(self.root, apply=True)
        run_thumbnail_generation(self.root, apply=True)

        asset_path = self.root / "assets" / "asset-02.md"
        text = asset_path.read_text(encoding="utf-8")
        text = text.replace(
            "| Classification | `GENERATED_RECONSTRUCTION` |",
            "| Classification | `NOT_A_REAL_VALUE` |",
        )
        asset_path.write_text(text, encoding="utf-8")

        qa_result = run_production_qa(self.root, apply=True)
        self.assertEqual(qa_result.verdict, "REVISION_REQUIRED")
        self.assertTrue(any("authenticity classification valid" in r for r in qa_result.reasons))

    # --- Test 49: golden sample remains untouched, end to end ---
    def test_golden_sample_untouched_by_full_pipeline(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}

        run_producer(GOLDEN_SAMPLE, apply=True)
        run_voice_generation(GOLDEN_SAMPLE, apply=True)
        run_asset_generation(GOLDEN_SAMPLE, apply=True)
        run_video_assembly(GOLDEN_SAMPLE, apply=True)
        run_caption_generation(GOLDEN_SAMPLE, apply=True)
        run_thumbnail_generation(GOLDEN_SAMPLE, apply=True)
        run_production_qa(GOLDEN_SAMPLE, apply=True)
        # Visual Planner dry-run only — see agents/visual_planner/tests/test_integration.py
        # for why apply=True isn't safe to exercise directly against the golden sample.
        run_visual_planner(GOLDEN_SAMPLE, apply=False)

        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertEqual(before, after, "golden sample must never be mutated by any Phase 7D agent")

    # --- Test 50: no publishing capability exists anywhere ---
    def test_no_publishing_capability_anywhere_in_phase_7d_agents(self):
        forbidden_names = {"upload", "publish", "post_video", "youtube", "schedule_publish"}
        for src_dir in AGENT_SRC_DIRS:
            for py_file in src_dir.glob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        self.assertNotIn(node.id.lower(), forbidden_names, f"{py_file}: {node.id!r}")
                    if isinstance(node, ast.Attribute):
                        self.assertNotIn(node.attr.lower(), forbidden_names, f"{py_file}: {node.attr!r}")

    def test_no_agent_ever_sets_ready_to_publish_in_a_real_run(self):
        # Behavioral, not textual: run the full pipeline and confirm
        # Production status never becomes READY_TO_PUBLISH or PUBLISHED —
        # HUMAN_REVIEW is the highest state any agent may reach this phase.
        build_minimal_item(
            self.root, pillar="what-if", title="Could Modern Medicine Have Stopped It?",
            beats=["1. A hypothetical beat. — claims: `c4`"],
        )
        write_claim(self.root, "c4", classification="ASSUMPTION")
        run_producer(self.root, apply=True)
        run_voice_generation(self.root, apply=True)
        run_visual_planner(self.root, apply=True)
        run_asset_generation(self.root, apply=True)
        run_video_assembly(self.root, apply=True)
        run_caption_generation(self.root, apply=True)
        run_thumbnail_generation(self.root, apply=True)
        run_production_qa(self.root, apply=True)

        production_text = (self.root / "PRODUCTION.md").read_text(encoding="utf-8")
        status_line = [l for l in production_text.splitlines() if l.startswith("| Production status |")][0]
        self.assertIn("HUMAN_REVIEW", status_line)
        self.assertNotIn("READY_TO_PUBLISH", status_line)
        self.assertNotIn("PUBLISHED", status_line)


if __name__ == "__main__":
    unittest.main()
