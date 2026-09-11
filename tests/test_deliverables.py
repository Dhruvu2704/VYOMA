"""Tests for the Phase 1 deliverable generators.

Verifies that the Word memo, Excel conflict matrix, annotated P&ID PDF,
and manifest generators produce real output files using only the shared
FinalVerdict / RuleVerdict dictionary shapes.

Run from the repository root:

    python -m unittest tests.test_deliverables -v
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def _library_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


DOCX_AVAILABLE = _library_available("docx")
OPENPYXL_AVAILABLE = _library_available("openpyxl")
FITZ_AVAILABLE = _library_available("fitz")
MANIFEST_AVAILABLE = DOCX_AVAILABLE and OPENPYXL_AVAILABLE and FITZ_AVAILABLE


FINAL_VERDICT = {
    "permit_id": "PTW-2026-014",
    "rule_result": "FLAGGED",
    "llm_result": "FLAGGED",
    "agreement": "AGREE",
    "final_decision": "FLAGGED_FOR_REVIEW",
    "explanation": (
        "Isolation overlap detected between PTW-2026-014 "
        "and PTW-2026-009 around V-101."
    ),
    "requires_human_review": True,
    "generated_at": "2026-09-05T12:00:00Z",
    "audit_ref": "AUD-DC2EB8A954C9",
}


RULE_VERDICT = {
    "permit_id": "PTW-2026-014",
    "conflicting_permit_ids": ["PTW-2026-009"],
    "rules_triggered": ["isolation-overlap-time-window"],
    "rule_result": "FLAGGED",
    "explanation": (
        "Permit isolation boundary overlaps an active permit time window."
    ),
    "confidence": "HIGH",
}


class DeliverableGeneratorMixin:
    """Shared helpers for deliverable generator tests."""

    def _tmpdir(self):
        return tempfile.TemporaryDirectory()

    def assert_output_exists(self, result: dict) -> None:
        self.assertIsInstance(result, dict)
        self.assertIn("path", result)
        output_path = Path(result["path"])
        self.assertTrue(
            output_path.exists(),
            f"generated output does not exist: {output_path}",
        )


class WordMemoTests(unittest.TestCase, DeliverableGeneratorMixin):
    """Word memo generator behaviour."""

    def test_generate_word_is_importable_without_docs_library(self) -> None:
        from ai_agent.deliverables.word_memo import generate_word

        self.assertTrue(callable(generate_word))

    @unittest.skipUnless(
        DOCX_AVAILABLE,
        "python-docx is not installed",
    )
    def test_generates_docx_memo_from_final_verdict(self) -> None:
        from ai_agent.deliverables.word_memo import generate_word

        with self._tmpdir() as tmp:
            result = generate_word(FINAL_VERDICT, output_dir=tmp)

            self.assertEqual(result["type"], "WORD_MEMO")
            self.assert_output_exists(result)
            self.assertTrue(result["path"].endswith(".docx"))

    @unittest.skipUnless(
        DOCX_AVAILABLE,
        "python-docx is not installed",
    )
    def test_memo_filename_uses_permit_id(self) -> None:
        from ai_agent.deliverables.word_memo import generate_word

        with self._tmpdir() as tmp:
            result = generate_word(FINAL_VERDICT, output_dir=tmp)

            self.assertTrue(
                result["path"].replace("\\", "/").endswith(
                    "PTW-2026-014_memo.docx"
                )
            )


class ExcelMatrixTests(unittest.TestCase, DeliverableGeneratorMixin):
    """Excel conflict matrix generator behaviour."""

    def test_generate_excel_is_importable_without_openpyxl(self) -> None:
        from ai_agent.deliverables.excel_matrix import generate_excel

        self.assertTrue(callable(generate_excel))

    @unittest.skipUnless(
        OPENPYXL_AVAILABLE,
        "openpyxl is not installed",
    )
    def test_generates_xlsx_from_single_rule_verdict(self) -> None:
        from ai_agent.deliverables.excel_matrix import generate_excel

        with self._tmpdir() as tmp:
            result = generate_excel(RULE_VERDICT, output_dir=tmp)

            self.assertEqual(result["type"], "EXCEL_CONFLICT_MATRIX")
            self.assert_output_exists(result)
            self.assertTrue(result["path"].endswith(".xlsx"))

    @unittest.skipUnless(
        OPENPYXL_AVAILABLE,
        "openpyxl is not installed",
    )
    def test_generates_xlsx_from_sequence_of_rule_verdicts(self) -> None:
        from ai_agent.deliverables.excel_matrix import generate_excel

        verdicts = [
            dict(RULE_VERDICT),
            {
                "permit_id": "PTW-2026-009",
                "conflicting_permit_ids": ["PTW-2026-014"],
                "rules_triggered": ["isolation-overlap-time-window"],
                "rule_result": "FLAGGED",
                "explanation": "Overlapping isolation window.",
                "confidence": "HIGH",
            },
        ]

        with self._tmpdir() as tmp:
            result = generate_excel(verdicts, output_dir=tmp)

            self.assert_output_exists(result)


class PdfAnnotatorTests(unittest.TestCase, DeliverableGeneratorMixin):
    """Annotated P&ID PDF generator behaviour."""

    def test_annotate_pdf_is_importable_without_fitz(self) -> None:
        from ai_agent.deliverables.pdf_annotator import annotate_pdf

        self.assertTrue(callable(annotate_pdf))

    @unittest.skipUnless(
        FITZ_AVAILABLE,
        "PyMuPDF is not installed",
    )
    def test_annotates_minimal_pdf(self) -> None:
        import fitz
        from ai_agent.deliverables.pdf_annotator import annotate_pdf

        with self._tmpdir() as tmp:
            tmp_path = Path(tmp)

            pid_file = tmp_path / "pid_unit_01.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "V-101 L-101")
            document.save(pid_file)
            document.close()

            result = annotate_pdf(
                pid_file,
                FINAL_VERDICT,
                output_dir=tmp,
            )

            self.assertEqual(result["type"], "ANNOTATED_PDF")
            self.assert_output_exists(result)
            self.assertTrue(result["path"].endswith(".pdf"))


class ManifestTests(unittest.TestCase, DeliverableGeneratorMixin):
    """Deliverable manifest generator behaviour."""

    def test_generate_manifest_is_importable(self) -> None:
        from ai_agent.deliverables.manifest import (
            generate_deliverable_manifest,
        )

        self.assertTrue(callable(generate_deliverable_manifest))

    @unittest.skipUnless(
        MANIFEST_AVAILABLE,
        "python-docx, openpyxl and PyMuPDF are all required",
    )
    def test_manifest_aggregates_all_deliverables(self) -> None:
        import fitz
        from ai_agent.deliverables.manifest import (
            generate_deliverable_manifest,
        )

        with self._tmpdir() as tmp:
            tmp_path = Path(tmp)

            pid_file = tmp_path / "pid_unit_01.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "V-101 L-101")
            document.save(pid_file)
            document.close()

            manifest = generate_deliverable_manifest(
                FINAL_VERDICT,
                RULE_VERDICT,
                pid_file,
                output_dir=tmp,
            )

            self.assertEqual(manifest["permit_id"], "PTW-2026-014")
            self.assertEqual(manifest["generated_at"], "2026-09-05T12:00:00Z")
            self.assertEqual(manifest["audit_ref"], "AUD-DC2EB8A954C9")
            self.assertEqual(len(manifest["deliverables"]), 3)

            types = {
                deliverable["type"] for deliverable in manifest["deliverables"]
            }

            self.assertEqual(
                types,
                {"WORD_MEMO", "EXCEL_CONFLICT_MATRIX", "ANNOTATED_PDF"},
            )

            for deliverable in manifest["deliverables"]:
                self.assert_output_exists(deliverable)


if __name__ == "__main__":
    unittest.main()