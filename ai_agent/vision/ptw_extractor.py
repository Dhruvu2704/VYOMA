"""Role 2 PTW OCR and extraction module.

This module belongs to the OCR + Vision role.

Current stage:
    Mock-first MVP with contract validation.

The module converts extracted PTW field data into the shared
StructuredPTW contract. Real OCR can later be added without changing
the shared output structure.
"""

from __future__ import annotations

from numbers import Real
from typing import Any, Mapping

from shared.contracts import StructuredPTW


_REQUIRED_FIELDS = [
    "permit_id",
    "work_type",
    "scope",
    "location",
    "start_time",
    "end_time",
    "issuer",
    "equipment_tags",
    "isolation_points",
]

_REQUIRED_STRING_FIELDS = [
    "permit_id",
    "work_type",
    "scope",
    "start_time",
    "end_time",
    "issuer",
]

_REQUIRED_LIST_FIELDS = [
    "location",
    "equipment_tags",
    "isolation_points",
]


def _validate_string_fields(extracted_fields: Mapping[str, Any]) -> None:
    """Validate required PTW string fields."""

    for field in _REQUIRED_STRING_FIELDS:
        value = extracted_fields[field]

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"PTW field '{field}' must be a non-empty string."
            )


def _validate_list_fields(extracted_fields: Mapping[str, Any]) -> None:
    """Validate required PTW list fields."""

    for field in _REQUIRED_LIST_FIELDS:
        value = extracted_fields[field]

        if not isinstance(value, list):
            raise ValueError(
                f"PTW field '{field}' must be a list."
            )

        if not all(isinstance(item, str) for item in value):
            raise ValueError(
                f"All values in PTW field '{field}' must be strings."
            )


def _validate_confidence(
    extracted_fields: Mapping[str, Any],
) -> None:
    """Validate optional field confidence values."""

    confidence = extracted_fields.get("field_confidence", {})

    if not isinstance(confidence, Mapping):
        raise ValueError(
            "PTW field 'field_confidence' must be a mapping."
        )

    for field, value in confidence.items():
        if not isinstance(field, str):
            raise ValueError(
                "PTW confidence field names must be strings."
            )

        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
        ):
            raise ValueError(
                f"Confidence for '{field}' must be numeric."
            )


def _validate_low_confidence_fields(
    extracted_fields: Mapping[str, Any],
) -> None:
    """Validate optional low confidence field names."""

    low_confidence_fields = extracted_fields.get(
        "low_confidence_fields",
        [],
    )

    if not isinstance(low_confidence_fields, list):
        raise ValueError(
            "'low_confidence_fields' must be a list."
        )

    if not all(
        isinstance(field, str)
        for field in low_confidence_fields
    ):
        raise ValueError(
            "All low confidence field names must be strings."
        )


def extract_ptw_from_mock(
    document_ref: str,
    extracted_fields: Mapping[str, Any],
) -> StructuredPTW:
    """Build a validated StructuredPTW from mock extracted data.

    This simulates the output that a future OCR and field-extraction
    pipeline will produce while preserving the shared contract.

    Args:
        document_ref: Reference to the source PTW document.
        extracted_fields: Mock extracted PTW field values.

    Returns:
        A validated StructuredPTW compatible with shared/contracts.py.

    Raises:
        ValueError: If required fields are missing or have invalid types.
    """

    if not isinstance(document_ref, str) or not document_ref.strip():
        raise ValueError(
            "'document_ref' must be a non-empty string."
        )

    missing_fields = [
        field
        for field in _REQUIRED_FIELDS
        if field not in extracted_fields
    ]

    if missing_fields:
        raise ValueError(
            f"Missing required PTW fields: {missing_fields}"
        )

    _validate_string_fields(extracted_fields)
    _validate_list_fields(extracted_fields)
    _validate_confidence(extracted_fields)
    _validate_low_confidence_fields(extracted_fields)

    return {
        "permit_id": extracted_fields["permit_id"],
        "work_type": extracted_fields["work_type"],
        "scope": extracted_fields["scope"],
        "location": list(extracted_fields["location"]),
        "start_time": extracted_fields["start_time"],
        "end_time": extracted_fields["end_time"],
        "issuer": extracted_fields["issuer"],
        "raw_document_ref": document_ref,
        "equipment_tags": list(extracted_fields["equipment_tags"]),
        "isolation_points": list(
            extracted_fields["isolation_points"]
        ),
        "field_confidence": dict(
            extracted_fields.get("field_confidence", {})
        ),
        "low_confidence_fields": list(
            extracted_fields.get("low_confidence_fields", [])
        ),
    }