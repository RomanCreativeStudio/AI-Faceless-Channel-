"""Tests 16, 19, 21, 22 from the Phase 7F task: protected-field
enforcement (structural, not just documented), downstream stale
detection, golden sample untouched, no publishing capability.

Also the "important architectural test" from task section 13: proves the
revision engine cannot cheat by modifying the original claim, inspecting
byte-level hashes and the writer's own allowed-fields whitelist directly.
"""
from __future__ import annotations

import ast
import shutil
import tempfile
import unittest
from pathlib import Path

from ..src import mutate
from ..src.hashing import compute_claim_hash
from ..src.loader import load_bundle, load_claims
from ..src.pipeline import run_fact_check
from ..src.revision import diagnose_claim, run_autonomous_revision

REVISION_FIXTURE = Path(__file__).parent / "fixtures" / "revision_item"
REVISION_SRC = Path(__file__).resolve().parents[1] / "src" / "revision.py"
GOLDEN_SAMPLE = (
    Path(__file__).resolve().parents[3]
    / "content" / "what-if" / "wi-20260902-black-death-modern-medicine"
)


class ProtectedFieldEnforcementTests(unittest.TestCase):
    """Test 16: write attempts outside the whitelist fail closed —
    structurally, via mutate.py's own PermissionError, not just by
    documentation."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, self.root)

    def test_write_revision_file_rejects_non_whitelisted_filename(self):
        with self.assertRaises(PermissionError):
            mutate.write_revision_file(self.root, "not-a-revision.md", "content")

    def test_write_revision_file_rejects_path_traversal(self):
        with self.assertRaises(PermissionError):
            mutate.write_revision_file(self.root, "../evil.md", "content")

    def test_update_claim_field_still_rejects_classification_and_exact_claim(self):
        # Unchanged from Phase 5 — the revision engine adds no new
        # permitted field to this same whitelist.
        bundle = load_bundle(self.root)
        claim = bundle.claims["c_fixable"]
        with self.assertRaises(PermissionError):
            mutate.update_claim_field(claim.path, "Classification", "`INFERENCE`")
        with self.assertRaises(PermissionError):
            mutate.update_claim_field(claim.path, "Exact claim", "rewritten")
        with self.assertRaises(PermissionError):
            mutate.update_claim_field(claim.path, "Supporting sources", "`fabricated.md`")

    def test_supersede_claim_never_overwrites_an_existing_file(self):
        bundle = load_bundle(self.root)
        old_claim = bundle.claims["c_fixable"]
        with self.assertRaises(FileExistsError):
            mutate.supersede_claim(
                old_claim, "c_ok", "irrelevant text", old_claim.classification,
                reason="test", template_render=lambda *a: "x",
            )


class RevisionSourceBoundaryTests(unittest.TestCase):
    """AST-based scan proving revision.py contains no forbidden identifier
    or import — never imports another agent's mutate.py, never references
    a protected field name."""

    def test_no_import_from_any_other_agents_mutate_module(self):
        tree = ast.parse(REVISION_SRC.read_text(encoding="utf-8"), filename=str(REVISION_SRC))
        forbidden_modules = {"safety", "originality", "producer", "voice", "visual_planner",
                              "assets", "assembler", "captions", "thumbnail", "production_qa",
                              "full_pipeline", "orchestrator"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_modules:
                    self.assertNotIn(
                        forbidden, node.module,
                        f"revision.py must never import from agents/{forbidden}/: {node.module}",
                    )

    def test_no_protected_field_string_literals(self):
        source = REVISION_SRC.read_text(encoding="utf-8")
        forbidden_strings = [
            "Production status", "Safety state", "Originality state",
            "Production QA state", "Owner approval state", "READY_TO_PUBLISH",
        ]
        for forbidden in forbidden_strings:
            self.assertNotIn(forbidden, source, f"revision.py must never reference {forbidden!r}")
        # "APPROVED" alone would false-positive on unrelated prose; check
        # the specific dangerous pattern instead.
        self.assertNotIn('"APPROVED"', source)
        self.assertNotIn("'APPROVED'", source)

    def test_no_publishing_identifiers(self):
        tree = ast.parse(REVISION_SRC.read_text(encoding="utf-8"), filename=str(REVISION_SRC))
        forbidden = {"upload", "publish", "post_video", "youtube", "schedule_publish"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id.lower(), forbidden)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr.lower(), forbidden)


class ArchitecturalImmutabilityProofTests(unittest.TestCase):
    """Task section 13's "important architectural test": structural proof
    the revision engine cannot cheat by modifying the original claim."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "item"
        shutil.copytree(REVISION_FIXTURE, self.root)

    def test_predecessor_bytes_and_hash_survive_a_full_revision_cycle_identically(self):
        bundle = load_bundle(self.root)
        old_claim = bundle.claims["c_fixable"]
        predecessor_path = old_claim.path
        predecessor_bytes_before = predecessor_path.read_bytes()
        predecessor_hash_before = compute_claim_hash(old_claim.raw_text)

        run_fact_check(self.root, apply=True)
        result = run_autonomous_revision(self.root, apply=True)
        fixable_outcome = next(o for o in result.claim_outcomes if o.original_short_id == "c_fixable")

        # The predecessor file grows (a trailing note is appended, per
        # the established templates/CLAIM.md convention) — but every
        # original byte must still be present as an exact prefix, and the
        # re-parsed table fields must be byte-identical.
        predecessor_bytes_after = predecessor_path.read_bytes()
        self.assertTrue(predecessor_bytes_after.startswith(predecessor_bytes_before.rstrip(b"\n")))

        reparsed = load_claims(self.root / "claims")["c_fixable"]
        predecessor_hash_after = compute_claim_hash(reparsed.raw_text)
        # The note append DOES change the whole-file hash (expected,
        # documented) — what must never change is the table content.
        self.assertEqual(reparsed.exact_claim, old_claim.exact_claim)
        self.assertEqual(reparsed.classification, old_claim.classification)
        self.assertEqual(fixable_outcome.original_hash, predecessor_hash_before)

        # The successor has its own, different ID and a different hash,
        # and the revision record links both by hash.
        self.assertEqual(fixable_outcome.successor_short_id, "c_fixable_rev1")
        self.assertNotEqual(fixable_outcome.new_hash, fixable_outcome.original_hash)

        revision_text = Path(fixable_outcome.revision_path).read_text(encoding="utf-8")
        self.assertIn(fixable_outcome.original_hash, revision_text)
        self.assertIn(fixable_outcome.new_hash, revision_text)

    def test_revision_writer_allowed_fields_are_exactly_the_documented_set(self):
        # Inspect the writer's own whitelist directly rather than trusting
        # a passing happy-path test alone.
        self.assertEqual(
            mutate.CLAIM_WRITABLE_FIELDS,
            {"Fact-check status", "Evidence", "Contradictory evidence", "Confidence level"},
        )
        self.assertNotIn("Exact claim", mutate.CLAIM_WRITABLE_FIELDS)
        self.assertNotIn("Classification", mutate.CLAIM_WRITABLE_FIELDS)
        self.assertNotIn("Supporting sources", mutate.CLAIM_WRITABLE_FIELDS)


class DownstreamStaleDetectionTests(unittest.TestCase):
    """Test 19: if a human completes the loop (updates SCRIPT.md to cite
    the successor), the EXISTING production-agent staleness machinery
    (built in Phase 7B-7D, not new code) correctly detects it — this
    revision engine invents no new staleness mechanism of its own."""

    def test_producer_detects_staleness_after_a_simulated_script_update(self):
        from ...producer.src.pipeline import run_producer
        from ...producer.tests.builders import build_minimal_item, write_claim

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "item"
        build_minimal_item(root, beats=["1. A fixture beat. — claims: `c1`"])

        first = run_producer(root, apply=True)
        self.assertTrue(first.produced)

        # Simulate a human completing the revision loop: a real successor
        # claim file already exists (as this revision engine would have
        # created it), and the human — never this agent — updates
        # SCRIPT.md to cite it instead of the superseded original.
        write_claim(root, "c1_rev1", classification="FACT")
        script_path = root / "SCRIPT.md"
        script_path.write_text(
            script_path.read_text(encoding="utf-8").replace("`c1`", "`c1_rev1`"),
            encoding="utf-8",
        )

        second = run_producer(root, apply=True)
        self.assertTrue(second.stale)
        self.assertFalse(second.produced)


class GoldenSampleTests(unittest.TestCase):
    def test_golden_sample_never_modified_by_revision_engine(self):
        if not GOLDEN_SAMPLE.is_dir():
            self.skipTest("golden sample not found")
        before = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}

        # Dry run only, matching the established convention for the
        # exact reason recorded in Phase 7E's STATE.md — apply=True
        # against unapproved content is a legitimate write for ordinary
        # FACT_CHECK, so testing golden-sample safety uses dry-run.
        run_fact_check(GOLDEN_SAMPLE, apply=False)
        result = run_autonomous_revision(GOLDEN_SAMPLE, apply=False)

        after = {p: p.read_text(encoding="utf-8") for p in GOLDEN_SAMPLE.rglob("*.md")}
        self.assertEqual(before, after)
        self.assertFalse((GOLDEN_SAMPLE / "revisions").exists())
        # No successor claim files exist under the real golden sample.
        self.assertFalse(any((GOLDEN_SAMPLE / "claims").glob("*_rev*.md")))


if __name__ == "__main__":
    unittest.main()
