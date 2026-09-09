import unittest

from vision.pid_pipeline import process_pid_data


class TestPIDPipeline(unittest.TestCase):

    def setUp(self):
        self.source = "mock:pid/pipeline_test.dwg"
        self.pid_id = "PID-PIPELINE-001"

        self.symbols = [
            {
                "symbol_id": " P-101 ",
                "symbol_type": "pump",
                "properties": {
                    "service": "cooling-water"
                },
                "connections": ["CW-101"],
            },
            {
                "symbol_id": " CW-101 ",
                "symbol_type": "line",
                "properties": {
                    "line_class": "cooling-water"
                },
                "connections": ["P-101", "G-101"],
            },
            {
                "symbol_id": " G-101 ",
                "symbol_type": "instrument",
                "properties": {
                    "measurand": "pressure"
                },
                "connections": ["CW-101"],
            },
        ]

        self.connections = [
            {
                "source": " P-101 ",
                "target": " CW-101 ",
                "line_ref": " CW-101 ",
            },
            {
                "source": " CW-101 ",
                "target": " G-101 ",
                "line_ref": " CW-101 ",
            },
        ]

    def test_process_complete_pid_data(self):
        result = process_pid_data(
            self.source,
            self.pid_id,
            self.symbols,
            self.connections,
        )

        self.assertEqual(
            result["pid_id"],
            self.pid_id,
        )

        self.assertEqual(
            result["source"],
            self.source,
        )

    def test_pipeline_normalizes_symbol_id(self):
        result = process_pid_data(
            self.source,
            self.pid_id,
            self.symbols,
            self.connections,
        )

        self.assertEqual(
            result["symbols"][0]["symbol_id"],
            "P-101",
        )

    def test_pipeline_normalizes_symbol_type(self):
        result = process_pid_data(
            self.source,
            self.pid_id,
            self.symbols,
            self.connections,
        )

        self.assertEqual(
            result["symbols"][0]["symbol_type"],
            "PUMP",
        )

    def test_pipeline_normalizes_connections(self):
        result = process_pid_data(
            self.source,
            self.pid_id,
            self.symbols,
            self.connections,
        )

        self.assertEqual(
            result["connections"][0]["source"],
            "P-101",
        )

        self.assertEqual(
            result["connections"][0]["target"],
            "CW-101",
        )

    def test_empty_source_raises_error(self):
        with self.assertRaises(ValueError):
            process_pid_data(
                "",
                self.pid_id,
                self.symbols,
                self.connections,
            )

    def test_invalid_symbol_data_raises_error(self):
        with self.assertRaises(ValueError):
            process_pid_data(
                self.source,
                self.pid_id,
                ["invalid-symbol"],
                self.connections,
            )


if __name__ == "__main__":
    unittest.main()