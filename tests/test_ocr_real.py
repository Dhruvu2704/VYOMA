"""Real, offline OCR tests for ai_agent.vision.ptw_ocr.

Proves that extract_text_from_image performs a genuine local OCR pass: a
synthetic PTW-like image is rendered to real bytes by
scripts/make_synthetic_ptw_image.py and then recognized by the locally
installed Tesseract binary. No cloud OCR is involved, and no mocked OCR
text is asserted anywhere in this file.

Requires Tesseract to be installed on the machine; if it is missing,
extract_text_from_image raises ValueError and these tests fail loudly
rather than pretending OCR works.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_agent.vision.ptw_ocr import extract_text_from_image

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "scripts" / "make_synthetic_ptw_image.py"


def _ocr_normalize(text):
    """Lower-case and drop whitespace so a token survives minor OCR noise."""
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch in "-:_")


class TestExtractTextFromImage(unittest.TestCase):

    def _render_synthetic_image(self, temp_dir):
        out = Path(temp_dir) / "synthetic_ptw.png"
        subprocess.run(
            [sys.executable, str(GENERATOR), "--out", str(out)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            check=True,
        )
        self.assertTrue(out.is_file())
        return out

    def test_real_ocr_recognizes_rendered_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = self._render_synthetic_image(temp_dir)
            result = extract_text_from_image(str(image_path))

        self.assertEqual(set(result.keys()), {"source", "text"})
        self.assertEqual(result["source"], str(image_path))
        self.assertIsInstance(result["text"], str)
        self.assertTrue(result["text"].strip())
        self.assertIn(
            "mr-test-001",
            _ocr_normalize(result["text"]),
            f"recognized text was: {result['text']!r}",
        )

    def test_missing_file_raises_value_error(self):
        missing = REPO_ROOT / "no-such-ptw-image.png"
        with self.assertRaises(ValueError) as ctx:
            extract_text_from_image(str(missing))
        self.assertIn("not found", str(ctx.exception))

    def test_unreadable_image_raises_value_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bogus = Path(temp_dir) / "not-an-image.png"
            bogus.write_text("this is not an image", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                extract_text_from_image(str(bogus))
            self.assertIn("could not be read", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()