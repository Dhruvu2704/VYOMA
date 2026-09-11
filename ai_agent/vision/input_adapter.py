"""Input adapter for the Role 2 OCR + Vision pipeline.

This module provides a simple mock-first input layer between raw JSON data
and the Role 2 extractors.

It does not define new shared contracts. Final outputs continue to use
StructuredPTW and StructuredPID from shared/contracts.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from shared.contracts import StructuredPID, StructuredPTW
from ai_agent.vision.pid_extractor import extract_pid_from_mock
from ai_agent.vision.ptw_extractor import extract_ptw_from_mock


def load_json_file(file_path: str | Path) -> Dict[str, Any]:
    """Load and validate a JSON object from a file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Input path is not a file: {path}"
        )

    if path.suffix.lower() != ".json":
        raise ValueError(
            "Input file must be a JSON file."
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            data = json.load(input_file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON input: {path}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            "JSON input must contain an object."
        )

    return data


def extract_ptw_from_json(
    file_path: str | Path,
) -> StructuredPTW:
    """Load PTW JSON data and return StructuredPTW output.

    The JSON file represents mock or pre-extracted OCR data.
    Future OCR implementations can feed the same extractor interface.
    """

    data = load_json_file(file_path)

    raw_document_ref = data.get(
        "raw_document_ref",
        str(file_path),
    )

    return extract_ptw_from_mock(
        raw_document_ref,
        data,
    )


def extract_pid_from_json(
    file_path: str | Path,
) -> StructuredPID:
    """Load P&ID JSON data and return StructuredPID output.

    The JSON file represents mock or pre-extracted Vision data.
    Future Vision implementations can feed the same extractor interface.
    """

    data = load_json_file(file_path)

    source = data.get(
        "source",
        str(file_path),
    )

    return extract_pid_from_mock(
        source,
        data,
    )