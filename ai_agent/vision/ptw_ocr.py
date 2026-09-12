"""PTW OCR processing for the Role 2 OCR + Vision pipeline.

Current implementation:
    - extract_text_from_mock : mock OCR output for tests and fixtures.
    - extract_text_from_image: real, fully-offline OCR using the local
      Tesseract binary (via pytesseract + Pillow). No cloud OCR is used.

A real OCR backend can be connected without changing the downstream
StructuredPTW contract.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict

import pytesseract
from PIL import Image


def _resolve_tesseract_binary() -> str:
    """Resolve the local Tesseract binary used by pytesseract.

    Prefers an explicitly configured or on-PATH tesseract, then falls back
    to the standard Windows install locations. Raises ValueError if no
    local binary can be found, so callers never silently fall back to a
    cloud OCR service.
    """

    configured = pytesseract.pytesseract.tesseract_cmd
    if configured and (Path(configured).is_file() or shutil.which(configured)):
        return configured

    for candidate in (
        os.environ.get("TESSERACT_CMD"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        shutil.which("tesseract"),
    ):
        if candidate and os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate

    raise ValueError(
        "Tesseract OCR binary not found. Install Tesseract OCR locally "
        "(e.g. 'winget install UB-Mannheim.TesseractOCR') or set the "
        "TESSERACT_CMD environment variable to the tesseract.exe path."
    )


def extract_text_from_image(
    image_path: str,
) -> Dict[str, Any]:
    """Extract text from a real image using the local Tesseract OCR engine.

    Runs entirely offline on this machine: the image is decoded locally
    with Pillow and passed to the locally installed tesseract binary via
    pytesseract. No cloud OCR or vision API is used.

    Returns the same ``{"source": ..., "text": ...}`` shape as
    extract_text_from_mock so the downstream contract is unchanged. The
    extracted text is normalized with normalize_ocr_text.

    Raises:
        ValueError: If image_path is missing, not a readable image file,
            or no local tesseract binary can be resolved.
    """

    if not isinstance(image_path, str) or not image_path.strip():
        raise ValueError(
            "OCR image path must be a non-empty string."
        )

    path = Path(image_path)
    if not path.is_file():
        raise ValueError(
            f"OCR image file not found: {image_path}"
        )

    _resolve_tesseract_binary()

    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            extracted = pytesseract.image_to_string(
                image,
                lang="eng",
                config="--psm 6",
            )
    except (Image.UnidentifiedImageError, OSError, pytesseract.TesseractError) as exc:
        raise ValueError(
            f"OCR image could not be read: {image_path} ({exc})"
        ) from exc

    return {
        "source": image_path,
        "text": normalize_ocr_text(extracted),
    }


def extract_text_from_mock(
    source: str,
    text: str,
) -> Dict[str, Any]:
    """Return validated mock OCR output for a PTW document.

    Args:
        source: Reference to the original PTW document.
        text: Text representing OCR output.

    Returns:
        A dictionary containing the source and extracted text.

    Raises:
        ValueError: If source or text is invalid.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError(
            "OCR source must be a non-empty string."
        )

    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "OCR text must be a non-empty string."
        )

    return {
        "source": source,
        "text": text.strip(),
    }


def normalize_ocr_text(
    text: str,
) -> str:
    """Normalize OCR text for downstream extraction.

    This performs only safe formatting cleanup. It does not infer,
    invent, or modify document facts.
    """

    if not isinstance(text, str):
        raise ValueError(
            "OCR text must be a string."
        )

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)