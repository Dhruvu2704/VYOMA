import json
import tempfile
import unittest
from pathlib import Path

from vision.input_adapter import (
    extract_pid_from_json,
    extract_ptw_from_json,
    load_json_file,
)


class TestInputAdapter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.ptw_data = {
            "permit_id": "TEST-PTW-001",
            "work_type": "cold-work",
            "scope": "Replace pressure gauge.",
            "location": ["Unit-1"],
            "start_time": "2026-09-10T08:00:00Z",
            "end_time": "2026-09-10T16:00:00Z",
            "issuer": "test-issuer",
            "raw_document_ref": "mock:ptw/test.json",
            "equipment_tags": ["P-101"],
            "isolation_points": [],
            "field_confidence": {
                "permit_id": 1.0
            },
            "low_confidence_fields": [],
        }

        self.pid_data = {
            "pid_id": "TEST-PID-001",
            "source": "mock:pid/test.json",
            "equipment_tags": ["P-101"],
            "symbols": [
                {
                    "symbol_id": "P-101",
                    "symbol_type": "PUMP",
                    "properties": {
                        "tag_resolved": True
                    },
                    "connections": [],
                }
            ],
            "connections": [],
            "unresolved_symbols": [],
            "field_confidence": {
                "symbols": 1.0
            },
            "low_confidence_fields": [],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_json(
        self,
        filename,
        data,
    ):
        file_path = self.temp_path / filename

        with file_path.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(data, output_file)

        return file_path

    def test_load_valid_json_file(self):
        file_path = self._write_json(
            "valid.json",
            self.ptw_data,
        )

        result = load_json_file(file_path)

        self.assertEqual(
            result,
            self.ptw_data,
        )

    def test_missing_file_raises_error(self):
        missing_file = (
            self.temp_path
            / "missing.json"
        )

        with self.assertRaises(FileNotFoundError):
            load_json_file(missing_file)

    def test_non_json_file_raises_error(self):
        file_path = self.temp_path / "input.txt"
        file_path.write_text(
            "not json",
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            load_json_file(file_path)

    def test_extract_ptw_from_json(self):
        file_path = self._write_json(
            "ptw.json",
            self.ptw_data,
        )

        result = extract_ptw_from_json(
            file_path
        )

        self.assertEqual(
            result["permit_id"],
            "TEST-PTW-001",
        )

        self.assertEqual(
            result["equipment_tags"],
            ["P-101"],
        )

    def test_extract_pid_from_json(self):
        file_path = self._write_json(
            "pid.json",
            self.pid_data,
        )

        result = extract_pid_from_json(
            file_path
        )

        self.assertEqual(
            result["pid_id"],
            "TEST-PID-001",
        )

        self.assertEqual(
            result["equipment_tags"],
            ["P-101"],
        )


if __name__ == "__main__":
    unittest.main()