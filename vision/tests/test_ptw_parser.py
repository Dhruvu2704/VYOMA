import unittest

from vision.ptw_parser import parse_ptw_text


class TestPTWParser(unittest.TestCase):

    def setUp(self):
        self.complete_text = """
Permit ID: TEST-PTW-001
Work Type: Cold Work
Scope: Replace pressure gauge on cooling line
Location: Unit-1, Pump-Area
Start Time: 2026-09-10T08:00:00Z
End Time: 2026-09-10T16:00:00Z
Issuer: test-issuer
Equipment Tags: P-101, G-101
Isolation Points: ISO-101, ISO-102
"""

    def test_parse_complete_ptw(self):
        result = parse_ptw_text(
            self.complete_text,
            "mock:ptw/test.pdf",
        )

        self.assertEqual(
            result["permit_id"],
            "TEST-PTW-001",
        )
        self.assertEqual(
            result["work_type"],
            "Cold Work",
        )
        self.assertEqual(
            result["location"],
            ["Unit-1", "Pump-Area"],
        )
        self.assertEqual(
            result["equipment_tags"],
            ["P-101", "G-101"],
        )

    def test_parse_isolation_points(self):
        result = parse_ptw_text(
            self.complete_text,
            "mock:ptw/test.pdf",
        )

        self.assertEqual(
            result["isolation_points"],
            ["ISO-101", "ISO-102"],
        )

    def test_complete_ptw_has_no_low_confidence_fields(self):
        result = parse_ptw_text(
            self.complete_text,
            "mock:ptw/test.pdf",
        )

        self.assertEqual(
            result["low_confidence_fields"],
            [],
        )

    def test_missing_field_has_low_confidence(self):
        text = """
Permit ID: TEST-PTW-002
Work Type: Hot Work
"""

        result = parse_ptw_text(
            text,
            "mock:ptw/incomplete.pdf",
        )

        self.assertIn(
            "scope",
            result["low_confidence_fields"],
        )

        self.assertEqual(
            result["field_confidence"]["scope"],
            0.0,
        )

    def test_missing_list_field_returns_empty_list(self):
        text = """
Permit ID: TEST-PTW-003
Work Type: Cold Work
"""

        result = parse_ptw_text(
            text,
            "mock:ptw/minimal.pdf",
        )

        self.assertEqual(
            result["equipment_tags"],
            [],
        )

        self.assertEqual(
            result["isolation_points"],
            [],
        )

    def test_valid_field_has_confidence(self):
        result = parse_ptw_text(
            self.complete_text,
            "mock:ptw/test.pdf",
        )

        self.assertEqual(
            result["field_confidence"]["permit_id"],
            0.9,
        )

    def test_empty_text_raises_error(self):
        with self.assertRaises(ValueError):
            parse_ptw_text(
                "",
                "mock:ptw/test.pdf",
            )

    def test_empty_document_reference_raises_error(self):
        with self.assertRaises(ValueError):
            parse_ptw_text(
                self.complete_text,
                "",
            )


if __name__ == "__main__":
    unittest.main()