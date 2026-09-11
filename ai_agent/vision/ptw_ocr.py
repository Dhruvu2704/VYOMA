"""PTW OCR processing for the Role 2 OCR + Vision pipeline.

Current implementation:
    Mock-first OCR text processing.

This module provides a stable interface for PTW OCR processing without
requiring an OCR engine during the MVP stage. A real OCR backend can later
be connected without changing the downstream StructuredPTW contract.
"""

from __future__ import annotations

from typing import Any, Dict


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