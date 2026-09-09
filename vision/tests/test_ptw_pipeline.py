import unittest

from vision.ptw_pipeline import process_ptw_text


class TestPTWPipeline(unittest.TestCase):

    def setUp(self):
        self.source = "mock:ptw/pipeline_test.pdf"

        self.complete_text = """
Permit ID: PIPELINE-PTW-001
Work Type: Cold Work
Scope: Replace pressure gauge on cooling water line
Location: Unit-1, Pump-Area
Start Time: 2026-09-10T08:00:00Z
End Time: 2026-09-10T16:00:00Z
Issuer: test-issuer
Equipment Tags: P-101, G-101
Isolation Points: ISO-101
"""

    def test_process_complete_ptw_text(self):
        result = process_ptw_text(
            self.source,
            self.complete_text,
        )

        self.assertEqual(
            result["permit_id"],
            "PIPELINE-PTW-001",
        )

        self.assertEqual(
            result["work_type"],
            "Cold Work",
        )

        self.assertEqual(
            result["scope"],
            "Replace pressure gauge on cooling water line",
        )

    def test_pipeline_returns_equipment_tags(self):
        result = process_ptw_text(
            self.source,
            self.complete_text,
        )

        self.assertEqual(
            result["equipment_tags"],
            ["P-101", "G-101"],
        )

    def test_pipeline_returns_isolation_points(self):
        result = process_ptw_text(
            self.source,
            self.complete_text,
        )

        self.assertEqual(
            result["isolation_points"],
            ["ISO-101"],
        )

    def test_pipeline_preserves_source_reference(self):
        result = process_ptw_text(
            self.source,
            self.complete_text,
        )

        self.assertEqual(
            result["raw_document_ref"],
            self.source,
        )

    def test_pipeline_rejects_missing_required_fields(self):
        incomplete_text = """
        Permit ID: PIPELINE-PTW-002
        Work Type: Hot Work
        """

        with self.assertRaises(ValueError):
            process_ptw_text(
                self.source,
                incomplete_text,
            )
            
    def test_empty_text_raises_error(self):
        with self.assertRaises(ValueError):
            process_ptw_text(
                self.source,
                "",
            )


if __name__ == "__main__":
    unittest.main()