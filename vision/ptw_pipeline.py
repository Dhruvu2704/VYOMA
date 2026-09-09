"""End-to-end PTW processing pipeline for Role 2 OCR + Vision.

Connects the existing OCR, parser, and extractor modules without creating
a new shared contract. The final output remains StructuredPTW.
"""

from __future__ import annotations

from shared.contracts import StructuredPTW

from vision.ptw_ocr import (
    extract_text_from_mock,
    normalize_ocr_text,
)
from vision.ptw_parser import parse_ptw_text
from vision.ptw_extractor import extract_ptw_from_mock


def process_ptw_text(
    source: str,
    text: str,
) -> StructuredPTW:
    """Process PTW OCR text into the shared StructuredPTW contract.

    Pipeline:
        mock OCR validation
        -> text normalization
        -> field parsing
        -> StructuredPTW extraction
    """

    ocr_result = extract_text_from_mock(
        source,
        text,
    )

    normalized_text = normalize_ocr_text(
        ocr_result["text"]
    )

    parsed_data = parse_ptw_text(
        normalized_text,
        source,
    )

    return extract_ptw_from_mock(
        source,
        parsed_data,
    )