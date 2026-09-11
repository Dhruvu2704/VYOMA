"""End-to-end P&ID processing pipeline for Role 2 OCR + Vision.

Connects the P&ID vision layer with the existing PID extractor.
The final cross-role output remains StructuredPID.
"""

from __future__ import annotations

from shared.contracts import StructuredPID

from ai_agent.vision.pid_vision import (
    validate_pid_vision_input,
    normalize_pid_symbols,
    normalize_pid_connections,
)
from ai_agent.vision.pid_extractor import extract_pid_from_mock

def synchronize_symbol_connections(
    symbols: list[dict],
    connections: list[dict],
) -> list[dict]:
    """Synchronize symbol connections from normalized top-level connections."""

    neighbors: dict[str, set[str]] = {
        symbol["symbol_id"]: set()
        for symbol in symbols
        if symbol.get("symbol_id")
    }

    for connection in connections:
        source = connection.get("source")
        target = connection.get("target")

        if source in neighbors and target in neighbors:
            neighbors[source].add(target)
            neighbors[target].add(source)

    synchronized = []

    for symbol in symbols:
        updated_symbol = dict(symbol)
        symbol_id = updated_symbol.get("symbol_id")

        if symbol_id in neighbors:
            updated_symbol["connections"] = sorted(
                neighbors[symbol_id]
            )
        else:
            updated_symbol["connections"] = []

        synchronized.append(updated_symbol)

    return synchronized


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

    normalized_symbols = synchronize_symbol_connections(
        normalized_symbols,
        normalized_connections,
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