from typing import Any, Dict, List


def validate_pid_vision_input(
    source: str,
    symbols: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate mock P&ID vision input."""

    if not isinstance(source, str) or not source.strip():
        raise ValueError(
            "P&ID source must be a non-empty string."
        )

    if not isinstance(symbols, list):
        raise ValueError(
            "P&ID symbols must be provided as a list."
        )

    if not isinstance(connections, list):
        raise ValueError(
            "P&ID connections must be provided as a list."
        )

    return {
        "source": source,
        "symbols": symbols,
        "connections": connections,
    }


def normalize_pid_symbols(
    symbols: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize P&ID symbol fields without inventing document facts."""

    normalized = []

    for symbol in symbols:
        if not isinstance(symbol, dict):
            raise ValueError(
                "Each P&ID symbol must be a dictionary."
            )

        normalized_symbol = dict(symbol)

        if "symbol_id" in normalized_symbol:
            normalized_symbol["symbol_id"] = str(
                normalized_symbol["symbol_id"]
            ).strip()

        if "symbol_type" in normalized_symbol:
            normalized_symbol["symbol_type"] = str(
                normalized_symbol["symbol_type"]
            ).strip().upper()

        connections = normalized_symbol.get(
            "connections",
            [],
        )

        if not isinstance(connections, list):
            raise ValueError(
                "Symbol connections must be a list."
            )

        normalized_symbol["connections"] = [
            str(connection).strip()
            for connection in connections
        ]

        normalized.append(normalized_symbol)

    return normalized

def normalize_pid_connections(
    connections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize P&ID connection fields."""

    normalized = []

    for connection in connections:
        if not isinstance(connection, dict):
            raise ValueError(
                "Each P&ID connection must be a dictionary."
            )

        normalized_connection = dict(connection)

        for field in ("source", "target", "line_ref"):
            if field in normalized_connection:
                normalized_connection[field] = str(
                    normalized_connection[field]
                ).strip()

        normalized.append(normalized_connection)

    return normalized
