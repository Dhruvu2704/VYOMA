"""End-to-end P&ID processing pipeline for Role 2 OCR + Vision.

Connects the P&ID vision layer with the existing PID extractor.
The final cross-role output remains StructuredPID.
"""

from __future__ import annotations

from shared.contracts import StructuredPID

from vision.pid_vision import (
    validate_pid_vision_input,
    normalize_pid_symbols,
    normalize_pid_connections,
)
from vision.pid_extractor import extract_pid_from_mock


def process_pid_data(
    source: str,
    pid_id: str,
    symbols: list[dict],
    connections: list[dict],
) -> StructuredPID:
    """Process P&ID vision data into the shared StructuredPID contract.

    Pipeline:
        vision input validation
        -> symbol normalization
        -> connection normalization
        -> StructuredPID extraction
    """

    validated = validate_pid_vision_input(
        source,
        symbols,
        connections,
    )

    normalized_symbols = normalize_pid_symbols(
        validated["symbols"]
    )

    normalized_connections = normalize_pid_connections(
        validated["connections"]
    )

    equipment_tags = [
    symbol["symbol_id"]
    for symbol in normalized_symbols
    if symbol.get("symbol_id")
    ]

    unresolved_symbols = [
    symbol["symbol_id"]
    for symbol in normalized_symbols
    if not symbol.get("symbol_id")
    ]

    extracted_data = {
        "pid_id": pid_id,
        "source": source,
        "equipment_tags": equipment_tags,
        "symbols": normalized_symbols,
        "connections": normalized_connections,
        "unresolved_symbols": unresolved_symbols,
    }

    return extract_pid_from_mock(
        source,
        extracted_data,
    )