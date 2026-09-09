"""Role 2 P&ID OCR and Vision extraction module.

This module belongs to the OCR + Vision role.

Current stage:
    Mock-first MVP with contract validation.

The module converts detected P&ID symbols and connections into the
shared StructuredPID contract. Real OCR and computer vision can later
be added without changing the shared output structure.
"""

from __future__ import annotations

from numbers import Real
from typing import Any, Mapping

from shared.contracts import StructuredPID


_REQUIRED_FIELDS = [
    "pid_id",
    "equipment_tags",
    "symbols",
    "connections",
    "unresolved_symbols",
]


def _validate_string(
    value: Any,
    field_name: str,
) -> None:
    """Validate a non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"P&ID field '{field_name}' must be a non-empty string."
        )


def _validate_string_list(
    value: Any,
    field_name: str,
) -> None:
    """Validate a list containing only strings."""

    if not isinstance(value, list):
        raise ValueError(
            f"P&ID field '{field_name}' must be a list."
        )

    if not all(isinstance(item, str) for item in value):
        raise ValueError(
            f"All values in P&ID field '{field_name}' must be strings."
        )


def _validate_symbols(
    symbols: Any,
) -> None:
    """Validate P&ID symbol structures."""

    if not isinstance(symbols, list):
        raise ValueError(
            "P&ID field 'symbols' must be a list."
        )

    required_symbol_fields = [
        "symbol_id",
        "symbol_type",
        "properties",
        "connections",
    ]

    for index, symbol in enumerate(symbols):
        if not isinstance(symbol, Mapping):
            raise ValueError(
                f"Symbol at index {index} must be a mapping."
            )

        missing_fields = [
            field
            for field in required_symbol_fields
            if field not in symbol
        ]

        if missing_fields:
            raise ValueError(
                f"Symbol at index {index} is missing fields: "
                f"{missing_fields}"
            )

        _validate_string(
            symbol["symbol_id"],
            f"symbols[{index}].symbol_id",
        )

        _validate_string(
            symbol["symbol_type"],
            f"symbols[{index}].symbol_type",
        )

        if not isinstance(symbol["properties"], Mapping):
            raise ValueError(
                f"Symbol at index {index} "
                "'properties' must be a mapping."
            )

        _validate_string_list(
            symbol["connections"],
            f"symbols[{index}].connections",
        )


def _validate_connections(
    connections: Any,
) -> None:
    """Validate P&ID connection structures."""

    if not isinstance(connections, list):
        raise ValueError(
            "P&ID field 'connections' must be a list."
        )

    required_connection_fields = [
        "source",
        "target",
        "line_ref",
    ]

    for index, connection in enumerate(connections):
        if not isinstance(connection, Mapping):
            raise ValueError(
                f"Connection at index {index} must be a mapping."
            )

        missing_fields = [
            field
            for field in required_connection_fields
            if field not in connection
        ]

        if missing_fields:
            raise ValueError(
                f"Connection at index {index} is missing fields: "
                f"{missing_fields}"
            )

        _validate_string(
            connection["source"],
            f"connections[{index}].source",
        )

        _validate_string(
            connection["target"],
            f"connections[{index}].target",
        )

        # line_ref is Optional[str] in the shared contract.
        line_ref = connection["line_ref"]

        if line_ref is not None and not isinstance(line_ref, str):
            raise ValueError(
                f"Connection at index {index} "
                "'line_ref' must be a string or None."
            )


def _validate_confidence(
    extracted_data: Mapping[str, Any],
) -> None:
    """Validate optional confidence values."""

    confidence = extracted_data.get(
        "field_confidence",
        {},
    )

    if not isinstance(confidence, Mapping):
        raise ValueError(
            "P&ID field 'field_confidence' must be a mapping."
        )

    for field, value in confidence.items():
        if not isinstance(field, str):
            raise ValueError(
                "P&ID confidence field names must be strings."
            )

        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
        ):
            raise ValueError(
                f"Confidence for '{field}' must be numeric."
            )


def _validate_low_confidence_fields(
    extracted_data: Mapping[str, Any],
) -> None:
    """Validate low confidence field names."""

    _validate_string_list(
        extracted_data.get(
            "low_confidence_fields",
            [],
        ),
        "low_confidence_fields",
    )


def extract_pid_from_mock(
    source: str,
    extracted_data: Mapping[str, Any],
) -> StructuredPID:
    """Build a validated StructuredPID from mock extracted data.

    This simulates the output of a future OCR + Vision pipeline while
    preserving the shared contract.

    Args:
        source: Reference to the source P&ID document.
        extracted_data: Mock extracted P&ID data.

    Returns:
        A validated StructuredPID compatible with shared/contracts.py.

    Raises:
        ValueError: If required fields are missing or invalid.
    """

    _validate_string(source, "source")

    missing_fields = [
        field
        for field in _REQUIRED_FIELDS
        if field not in extracted_data
    ]

    if missing_fields:
        raise ValueError(
            f"Missing required P&ID fields: {missing_fields}"
        )

    _validate_string(
        extracted_data["pid_id"],
        "pid_id",
    )

    _validate_string_list(
        extracted_data["equipment_tags"],
        "equipment_tags",
    )

    _validate_symbols(
        extracted_data["symbols"],
    )

    _validate_connections(
        extracted_data["connections"],
    )

    _validate_string_list(
        extracted_data["unresolved_symbols"],
        "unresolved_symbols",
    )

    _validate_confidence(extracted_data)

    _validate_low_confidence_fields(extracted_data)

    return {
        "pid_id": extracted_data["pid_id"],
        "source": source,
        "equipment_tags": list(
            extracted_data["equipment_tags"]
        ),
        "symbols": list(
            extracted_data["symbols"]
        ),
        "connections": list(
            extracted_data["connections"]
        ),
        "unresolved_symbols": list(
            extracted_data["unresolved_symbols"]
        ),
        "field_confidence": dict(
            extracted_data.get(
                "field_confidence",
                {},
            )
        ),
        "low_confidence_fields": list(
            extracted_data.get(
                "low_confidence_fields",
                [],
            )
        ),
    }