"""Image -> real OCR -> regex parse -> StructuredPTW pipeline tests.

Renders the synthetic PTW image (scripts/make_synthetic_ptw_image.py), runs
the genuine local Tesseract OCR pass, parses it with the existing regex
parser, and validates it through the shared contract extractor. Nothing here
is asserted against a mocked OCR string.

The six core string fields must match the known synthetic values exactly and
fail loudly on any OCR misread; the three list fields are checked leniently
because OCR can add minor character noise.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_agent.vision.ptw_pipeline import process_ptw_image

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "scripts" / "make_synthetic_ptw_image.py"

SOURCE = "IMG-OCR-001"

EXPECTED_CORE_FIELDS = {
    "permit_id": "MR-TEST-001",
    "work_type": "HOT WORK",
    "scope": "DISCHARGE LINE REPLACEMENT",
    "start_time": "2026-09-12 08:00",
    "end_time": "2026-09-12 17:00",
    "issuer": "JOHN SMITH",
}

LIST_FIELDS = (
    "location",
    "equipment_tags",
    "isolation_points",
)

LIST_ITEM_TOKEN = re.compile(r"^[A-Za-z0-9-]+$")


class TestProcessPTWImage(unittest.TestCase):

    def _recover_ptw(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "synthetic_ptw.png"
            subprocess.run(
                [sys.executable, str(GENERATOR), "--out", str(out)],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                check=True,
            )
            return process_ptw_image(SOURCE, str(out))

    def test_report_recovered_ptw(self):
        ptw = self._recover_ptw()
        print(
            "\nRECOVERED StructuredPTW from OCR:\n"
            + json.dumps(ptw, indent=2, sort_keys=True)
        )

    def test_core_string_fields_match_exactly(self):
        ptw = self._recover_ptw()
        self.assertEqual(ptw["raw_document_ref"], SOURCE)
        for field, expected in EXPECTED_CORE_FIELDS.items():
            self.assertEqual(
                ptw[field],
                expected,
                f"OCR misread {field!r}; full recovered PTW: {ptw!r}",
            )

    def test_list_fields_recovered_with_length(self):
        ptw = self._recover_ptw()
        for field in LIST_FIELDS:
            self.assertEqual(
                len(ptw[field]),
                2,
                f"wrong item count in {field}; full recovered PTW: {ptw!r}",
            )
            for item in ptw[field]:
                self.assertTrue(item.strip())
                self.assertTrue(
                    LIST_ITEM_TOKEN.match(item),
                    f"unexpected token {item!r} in {field}; "
                    f"full recovered PTW: {ptw!r}",
                )

    def test_all_fields_high_confidence(self):
        ptw = self._recover_ptw()
        self.assertEqual(
            set(ptw["field_confidence"].keys()),
            set(EXPECTED_CORE_FIELDS) | set(LIST_FIELDS),
        )
        self.assertTrue(
            all(value == 0.9 for value in ptw["field_confidence"].values())
        )
        self.assertEqual(ptw["low_confidence_fields"], [])

    def test_missing_image_raises_value_error(self):
        missing = REPO_ROOT / "no-such-ptw-document.png"
        with self.assertRaises(ValueError) as ctx:
            process_ptw_image(SOURCE, str(missing))
        self.assertIn("not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()