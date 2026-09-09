import unittest

from vision.ptw_ocr import (
    extract_text_from_mock,
    normalize_ocr_text,
)


class TestPTWOCR(unittest.TestCase):

    def test_extract_valid_mock_ocr_text(self):
        result = extract_text_from_mock(
            "mock:ptw/test.pdf",
            "Permit ID: TEST-001",
        )

        self.assertEqual(
            result["source"],
            "mock:ptw/test.pdf",
        )

        self.assertEqual(
            result["text"],
            "Permit ID: TEST-001",
        )

    def test_empty_source_raises_error(self):
        with self.assertRaises(ValueError):
            extract_text_from_mock(
                "",
                "Permit ID: TEST-001",
            )

    def test_empty_text_raises_error(self):
        with self.assertRaises(ValueError):
            extract_text_from_mock(
                "mock:ptw/test.pdf",
                "",
            )

    def test_normalize_ocr_text(self):
        text = """

            Permit ID: TEST-001

            Work Type: Cold Work


            Location: Unit-1

        """

        result = normalize_ocr_text(text)

        expected = (
            "Permit ID: TEST-001\n"
            "Work Type: Cold Work\n"
            "Location: Unit-1"
        )

        self.assertEqual(
            result,
            expected,
        )

    def test_non_string_text_raises_error(self):
        with self.assertRaises(ValueError):
            normalize_ocr_text(123)


if __name__ == "__main__":
    unittest.main()