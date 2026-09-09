import unittest

from vision.pid_extractor import extract_pid_from_mock


class TestPIDExtractor(unittest.TestCase):

    def setUp(self):
        self.source = "mock:pid/test_0001.dwg"

        self.extracted_data = {
            "pid_id": "PID-TEST-001",
            "equipment_tags": ["P-101", "CW-101", "G-101"],
            "symbols": [
                {
                    "symbol_id": "P-101",
                    "symbol_type": "PUMP",
                    "properties": {
                        "tag_resolved": True,
                    },
                    "connections": ["CW-101"],
                },
                {
                    "symbol_id": "CW-101",
                    "symbol_type": "LINE",
                    "properties": {
                        "line_class": "cooling-water",
                    },
                    "connections": ["P-101", "G-101"],
                },
            ],
            "connections": [
                {
                    "source": "P-101",
                    "target": "CW-101",
                    "line_ref": "CW-101",
                }
            ],
            "unresolved_symbols": [],
            "field_confidence": {
                "equipment_tags": 0.98,
                "symbols": 0.97,
                "connections": 0.96,
            },
            "low_confidence_fields": [],
        }

    def test_extract_pid_returns_structured_data(self):
        result = extract_pid_from_mock(
            self.source,
            self.extracted_data,
        )

        self.assertEqual(
            result["pid_id"],
            "PID-TEST-001",
        )

        self.assertEqual(
            result["source"],
            self.source,
        )

        self.assertEqual(
            result["equipment_tags"],
            ["P-101", "CW-101", "G-101"],
        )

        self.assertEqual(
            len(result["symbols"]),
            2,
        )

        self.assertEqual(
            result["symbols"][0]["symbol_type"],
            "PUMP",
        )

        self.assertEqual(
            result["connections"][0]["source"],
            "P-101",
        )

        self.assertEqual(
            result["unresolved_symbols"],
            [],
        )

    def test_missing_required_field_raises_error(self):
        incomplete_data = self.extracted_data.copy()

        del incomplete_data["pid_id"]

        with self.assertRaises(ValueError):
            extract_pid_from_mock(
                self.source,
                incomplete_data,
            )
    def test_invalid_equipment_tags_type_raises_error(self):
        invalid_data = self.extracted_data.copy()
        invalid_data["equipment_tags"] = "P-101"

        with self.assertRaises(ValueError):
            extract_pid_from_mock(
                self.source,
                invalid_data,
            )

    def test_missing_symbol_field_raises_error(self):
        invalid_data = self.extracted_data.copy()
        invalid_data["symbols"] = [
            {
                "symbol_id": "P-101",
                "symbol_type": "PUMP",
                # properties is intentionally missing
                "connections": ["CW-101"],
            }
        ]

        with self.assertRaises(ValueError):
            extract_pid_from_mock(
                self.source,
                invalid_data,
            )

    def test_invalid_line_ref_raises_error(self):
        invalid_data = self.extracted_data.copy()
        invalid_data["connections"] = [
            {
                "source": "P-101",
                "target": "CW-101",
                "line_ref": 123,
            }
        ]

        with self.assertRaises(ValueError):
            extract_pid_from_mock(
                self.source,
                invalid_data,
            )

    def test_invalid_confidence_raises_error(self):
        invalid_data = self.extracted_data.copy()
        invalid_data["field_confidence"] = {
            "symbols": "HIGH"
        }

        with self.assertRaises(ValueError):
            extract_pid_from_mock(
                self.source,
                invalid_data,
            )

    def test_empty_source_raises_error(self):
        with self.assertRaises(ValueError):
            extract_pid_from_mock(
                "",
                self.extracted_data,
            )

if __name__ == "__main__":
    unittest.main()