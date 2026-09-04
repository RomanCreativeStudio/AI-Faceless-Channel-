"""Phase 7G write-boundary and golden-sample-protection tests for
agents/researcher/src/research.py, mirroring
test_revision_write_boundary.py's established pattern exactly (one module
per concern, same AST-based proof technique).
"""
from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.models import Claim, Classification, ConfidenceLevel, FactCheckStatus
from ..src.research import run_bounded_research
from ..src.test_research_provider import LocalTestResearchProvider, strong_support_result

RESEARCH_SRC = Path(__file__).resolve().parents[1] / "src" / "research.py"
GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


def _make_claim(short_id="c1") -> Claim:
    return Claim(
        path=Path(f"/tmp/fake/claims/{short_id}.md"), short_id=short_id,
        claim_id=f"fixture-{short_id}", content_id="fixture", exact_claim="A fixture claim.",
        supporting_sources=[], derived_from=[], evidence="", confidence_level=ConfidenceLevel.LOW,
        classification=Classification.FACT, contradictory_evidence="none",
        fact_check_status=FactCheckStatus.UNVERIFIED,
    )


class ResearchWriteWhitelistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        (self.root / "research").mkdir(parents=True)

    def test_write_research_file_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_research_file(self.root, "not-numbered.md", "content")

    def test_write_research_file_rejects_path_traversal(self):
        with self.assertRaises(PermissionError):
            mutate.write_research_file(self.root, "../../evil.md", "content")

    def test_write_research_file_never_overwrites(self):
        mutate.write_research_file(self.root, "01-a-source.md", "first")
        with self.assertRaises(FileExistsError):
            mutate.write_research_file(self.root, "01-a-source.md", "second")
        self.assertEqual((self.root / "research" / "01-a-source.md").read_text(encoding="utf-8"), "first")

    def test_apply_writes_land_only_under_research(self):
        claim = _make_claim()
        provider = LocalTestResearchProvider({"c1": [strong_support_result("c1")]})
        outcome = run_bounded_research(self.root, claim, reason="x", apply=True, provider=provider)
        for path_str in outcome.research_paths:
            self.assertEqual(Path(path_str).parent, self.root / "research")


class ResearchSourceBoundaryTests(unittest.TestCase):
    """AST-based scan — research.py never imports another agent's mutate
    module, never references a protected field, never contains a
    publishing identifier."""

    def test_no_import_from_any_other_agents_mutate_module(self):
        tree = ast.parse(RESEARCH_SRC.read_text(encoding="utf-8"), filename=str(RESEARCH_SRC))
        forbidden_modules = {"safety", "originality", "producer", "voice", "visual_planner",
                              "assets", "assembler", "captions", "thumbnail", "production_qa",
                              "full_pipeline", "orchestrator"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_modules:
                    self.assertNotIn(
                        forbidden, node.module,
                        f"research.py must never import from agents/{forbidden}/: {node.module}",
                    )

    def test_no_protected_field_string_literals(self):
        # research.py only ever writes via mutate.write_research_file
        # (filename-whitelisted, not field-whitelisted like revision.py's
        # claim writers) — so the relevant protected surface here is
        # publishing/approval fields, not claim table field names (which
        # research.py legitimately mentions in prose describing what
        # diagnose_claim/create_successor_claim, elsewhere, still forbid).
        source = RESEARCH_SRC.read_text(encoding="utf-8")
        forbidden_strings = [
            "Production status", "Safety state", "Originality state",
            "Production QA state", "Owner approval state", "READY_TO_PUBLISH",
        ]
        for forbidden in forbidden_strings:
            self.assertNotIn(forbidden, source, f"research.py must never reference {forbidden!r}")
        self.assertNotIn('"APPROVED"', source)
        self.assertNotIn("'APPROVED'", source)

    def test_no_publishing_identifiers(self):
        tree = ast.parse(RESEARCH_SRC.read_text(encoding="utf-8"), filename=str(RESEARCH_SRC))
        forbidden = {"upload", "publish", "post_video", "youtube", "schedule_publish"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id.lower(), forbidden)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr.lower(), forbidden)

    def test_never_writes_a_claim_or_revision_file_itself(self):
        source = RESEARCH_SRC.read_text(encoding="utf-8")
        self.assertNotIn("write_revision_file", source)
        self.assertNotIn("supersede_claim", source)
        self.assertNotIn("update_claim_field", source)


class GoldenSampleBoundedResearchTests(unittest.TestCase):
    def test_bounded_research_never_writes_under_the_golden_sample(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        from ..src.loader import load_bundle

        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        bundle = load_bundle(GOLDEN_SAMPLE)
        # Pick any FACT claim as a representative dry-run target — this
        # test only proves apply=False never mutates the golden sample,
        # matching the established convention in
        # test_revision_write_boundary.py's own GoldenSampleTests.
        fact_claims = [c for c in bundle.claims.values() if c.classification.value == "FACT"]
        if not fact_claims:
            self.skipTest("golden sample has no FACT claims")
        run_bounded_research(GOLDEN_SAMPLE, fact_claims[0], reason="test", apply=False)

        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
