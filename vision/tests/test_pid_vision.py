import unittest

from vision.pid_vision import (
    validate_pid_vision_input,
    normalize_pid_symbols,
    normalize_pid_connections,
)


class TestPIDVision(unittest.TestCase):

    def setUp(self):
        self.source = "mock:pid/test_001.dwg"

        self.symbols = [
            {
                "symbol_id": " P-101 ",
                "symbol_type": "pump",
                "properties": {
                    "service": "cooling-water"
                },
            },
            {
                "symbol_id": " G-101 ",
                "symbol_type": "instrument",
                "properties": {
                    "measurand": "pressure"
                },
            },
        ]

        self.connections = [
            {
                "source": " P-101 ",
                "target": " CW-101 ",
                "line_ref": " CW-101 ",
            }
        ]

    def test_validate_valid_input(self):
        result = validate_pid_vision_input(
            self.source,
            self.symbols,
            self.connections,
        )

        self.assertEqual(
            result["source"],
            self.source,
        )

        self.assertEqual(
            result["symbols"],
            self.symbols,
        )

    def test_empty_source_raises_error(self):
        with self.assertRaises(ValueError):
            validate_pid_vision_input(
                "",
                self.symbols,
                self.connections,
            )

    def test_invalid_symbols_raises_error(self):
        with self.assertRaises(ValueError):
            validate_pid_vision_input(
                self.source,
                {},
                self.connections,
            )

    def test_invalid_connections_raises_error(self):
        with self.assertRaises(ValueError):
            validate_pid_vision_input(
                self.source,
                self.symbols,
                {},
            )

    def test_normalize_symbols(self):
        result = normalize_pid_symbols(
            self.symbols,
        )

        self.assertEqual(
            result[0]["symbol_id"],
            "P-101",
        )

        self.assertEqual(
            result[0]["symbol_type"],
            "PUMP",
        )

    def test_normalize_connections(self):
        result = normalize_pid_connections(
            self.connections,
        )

        self.assertEqual(
            result[0]["source"],
            "P-101",
        )

        self.assertEqual(
            result[0]["target"],
            "CW-101",
        )

        self.assertEqual(
            result[0]["line_ref"],
            "CW-101",
        )

    def test_invalid_symbol_entry_raises_error(self):
        with self.assertRaises(ValueError):
            normalize_pid_symbols(
                ["invalid-symbol"]
            )

    def test_invalid_connection_entry_raises_error(self):
        with self.assertRaises(ValueError):
            normalize_pid_connections(
                ["invalid-connection"]
            )


if __name__ == "__main__":
    unittest.main()