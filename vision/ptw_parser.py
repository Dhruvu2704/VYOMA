"""PTW field parser for the Role 2 OCR + Vision pipeline.

Converts normalized OCR text into structured field data that can be passed
to the existing PTW extractor. This module does not define a new shared
contract; StructuredPTW remains the authoritative output contract.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


FIELD_PATTERNS = {
    "permit_id": r"Permit\s*ID\s*:\s*(.+)",
    "work_type": r"Work\s*Type\s*:\s*(.+)",
    "scope": r"Scope\s*:\s*(.+)",
    "location": r"Location\s*:\s*(.+)",
    "start_time": r"Start\s*Time\s*:\s*(.+)",
    "end_time": r"End\s*Time\s*:\s*(.+)",
    "issuer": r"Issuer\s*:\s*(.+)",
    "equipment_tags": r"Equipment\s*Tags?\s*:\s*(.+)",
    "isolation_points": r"Isolation\s*Points?\s*:\s*(.+)",
}


def _extract_field(
    text: str,
    pattern: str,
) -> str | None:
    """Extract one field using its OCR text pattern."""

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    value = match.group(1).strip()

    return value or None


def _split_list(
    value: str | None,
) -> List[str]:
    """Convert comma-separated OCR values into a list."""

    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def parse_ptw_text(
    text: str,
    raw_document_ref: str,
) -> Dict[str, Any]:
    """Parse normalized PTW OCR text into extractor-ready field data.

    Missing fields are preserved as empty strings/lists and recorded as
    low-confidence fields. No document facts are invented.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "PTW OCR text must be a non-empty string."
        )

    if (
        not isinstance(raw_document_ref, str)
        or not raw_document_ref.strip()
    ):
        raise ValueError(
            "raw_document_ref must be a non-empty string."
        )

    extracted: Dict[str, Any] = {}
    field_confidence: Dict[str, float] = {}
    low_confidence_fields: List[str] = []

    for field_name, pattern in FIELD_PATTERNS.items():
        value = _extract_field(
            text,
            pattern,
        )

        if field_name in {
            "location",
            "equipment_tags",
            "isolation_points",
        }:
            extracted[field_name] = _split_list(value)
        else:
            extracted[field_name] = value or ""

        if value:
            field_confidence[field_name] = 0.9
        else:
            field_confidence[field_name] = 0.0
            low_confidence_fields.append(
                field_name
            )

    extracted["raw_document_ref"] = raw_document_ref
    extracted["field_confidence"] = field_confidence
    extracted["low_confidence_fields"] = (
        low_confidence_fields
    )

    return extracted