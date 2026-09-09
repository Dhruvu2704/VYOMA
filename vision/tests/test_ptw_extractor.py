import unittest

from vision.ptw_extractor import extract_ptw_from_mock


class TestPTWExtractor(unittest.TestCase):

    def setUp(self):
        self.document_ref = "mock:ptw/test_0001.json"

        self.extracted_fields = {
            "permit_id": "TEST-PTW-001",
            "work_type": "cold-work",
            "scope": "Replace a pressure gauge.",
            "location": ["Unit-1", "Pump-Area"],
            "start_time": "2026-09-10T08:00:00Z",
            "end_time": "2026-09-10T16:00:00Z",
            "issuer": "test-issuer",
            "equipment_tags": ["P-101", "G-101"],
            "isolation_points": [],
            "field_confidence": {
                "permit_id": 1.0,
                "work_type": 0.99,
                "scope": 0.95,
            },
            "low_confidence_fields": [],
        }

    def test_extract_ptw_returns_structured_data(self):
        result = extract_ptw_from_mock(
            self.document_ref,
            self.extracted_fields,
        )

        self.assertEqual(
            result["permit_id"],
            "TEST-PTW-001",
        )

        self.assertEqual(
            result["work_type"],
            "cold-work",
        )

        self.assertEqual(
            result["location"],
            ["Unit-1", "Pump-Area"],
        )

        self.assertEqual(
            result["raw_document_ref"],
            self.document_ref,
        )

        self.assertEqual(
            result["equipment_tags"],
            ["P-101", "G-101"],
        )

        self.assertEqual(
            result["low_confidence_fields"],
            [],
        )

    def test_missing_required_field_raises_error(self):
        incomplete_fields = self.extracted_fields.copy()

        del incomplete_fields["permit_id"]

        with self.assertRaises(ValueError):
            extract_ptw_from_mock(
                self.document_ref,
                incomplete_fields,
            )

    def test_invalid_location_type_raises_error(self):
        invalid_fields = self.extracted_fields.copy()
        invalid_fields["location"] = "Unit-1"

        with self.assertRaises(ValueError):
            extract_ptw_from_mock(
                self.document_ref,
                invalid_fields,
            )


    def test_invalid_confidence_raises_error(self):
        invalid_fields = self.extracted_fields.copy()
        invalid_fields["field_confidence"] = {
            "permit_id": "HIGH"
        }

        with self.assertRaises(ValueError):
            extract_ptw_from_mock(
                self.document_ref,
                invalid_fields,
            )


    def test_empty_document_ref_raises_error(self):
        with self.assertRaises(ValueError):
            extract_ptw_from_mock(
                "",
                self.extracted_fields,
            )


if __name__ == "__main__":
    unittest.main()
    