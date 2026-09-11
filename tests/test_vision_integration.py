"""Integration tests for the Role 2 vision / P&ID pipeline.

Proves that the integrated ai_agent.vision package:
    1. imports successfully,
    2. produces the existing shared StructuredPTW / StructuredPID shapes,
    3. does not define duplicate contract types,
    4. requires no network access and is deterministic.

No external vision model, OCR engine, Ollama, or internet is required.
"""

import importlib
import json
import pkgutil
import tempfile
import unittest
from pathlib import Path

from shared.contracts import StructuredPID, StructuredPTW

import ai_agent.vision.input_adapter as input_adapter
import ai_agent.vision.pid_extractor as pid_extractor
import ai_agent.vision.pid_pipeline as pid_pipeline
import ai_agent.vision.pid_vision as pid_vision
import ai_agent.vision.ptw_extractor as ptw_extractor
import ai_agent.vision.ptw_parser as ptw_parser
import ai_agent.vision.ptw_pipeline as ptw_pipeline

VISION_MODULES = [
    input_adapter,
    pid_extractor,
    pid_pipeline,
    pid_vision,
    ptw_extractor,
    ptw_parser,
    ptw_pipeline,
]

FORBIDDEN_NETWORK_IMPORTS = [
    "urllib",
    "requests",
    "httpx",
    "http.client",
    "socket",
]

SAMPLE_PTW_TEXT = "\n".join(
    [
        "Permit ID: MR-0001-VIS",
        "Work Type: hot-work",
        "Scope: Pressure vessel repair",
        "Location: Unit-4, Area-12",
        "Start Time: 2025-06-10T08:00:00",
        "End Time: 2025-06-10T17:00:00",
        "Issuer: A. Sharma",
        "Equipment Tags: P-100, V-200, HX-300",
        "Isolation Points: ISO-01, ISO-02",
    ]
)

SAMPLE_PID_SYMBOLS = [
    {
        "symbol_id": "P-101",
        "symbol_type": "pump",
        "properties": {"service": "cooling water"},
        "connections": ["V-101"],
    },
    {
        "symbol_id": "V-101",
        "symbol_type": "valve",
        "properties": {},
        "connections": ["P-101"],
    },
]

SAMPLE_PID_CONNECTIONS = [
    {
        "source": "P-101",
        "target": "V-101",
        "line_ref": "L-001",
    }
]


def _required_keys(typed_dict_cls):
    """Return required key names for a TypedDict contract."""
    required = getattr(typed_dict_cls, "__required_keys__", None)
    if required is not None:
        return frozenset(required)
    return frozenset(typed_dict_cls.__annotations__)


PTW_REQUIRED_KEYS = _required_keys(StructuredPTW)
PID_REQUIRED_KEYS = _required_keys(StructuredPID)

FIXTURE_NAMES = [
    "safe_case.json",
    "conflict_case.json",
    "ambiguous_case.json",
    "disagreement_case.json",
]


class TestVisionPackageImports(unittest.TestCase):

    def test_all_vision_modules_importable(self):
        for module in VISION_MODULES:
            with self.subTest(module=module.__name__):
                importlib.import_module(module.__name__)
                self.assertIsNotNone(module)

    def test_ptw_pipeline_exposes_public_entry(self):
        self.assertTrue(callable(ptw_pipeline.process_ptw_text))

    def test_pid_pipeline_exposes_public_entry(self):
        self.assertTrue(callable(pid_pipeline.process_pid_data))

    def test_pid_vision_modules_execute(self):
        result = pid_vision.validate_pid_vision_input(
            "PID-UNIT-01",
            SAMPLE_PID_SYMBOLS,
            SAMPLE_PID_CONNECTIONS,
        )
        self.assertEqual(result["source"], "PID-UNIT-01")
        self.assertEqual(result["symbols"], SAMPLE_PID_SYMBOLS)
        self.assertEqual(result["connections"], SAMPLE_PID_CONNECTIONS)


class TestPTWPipelineContract(unittest.TestCase):

    def test_ptw_pipeline_produces_structured_ptw_shape(self):
        result = ptw_pipeline.process_ptw_text(
            "PTW-DOC-2025-001",
            SAMPLE_PTW_TEXT,
        )
        self.assertEqual(set(result.keys()), PTW_REQUIRED_KEYS)
        self.assertEqual(result["permit_id"], "MR-0001-VIS")
        self.assertEqual(result["work_type"], "hot-work")
        self.assertEqual(result["location"], ["Unit-4", "Area-12"])
        self.assertEqual(
            result["equipment_tags"],
            ["P-100", "V-200", "HX-300"],
        )
        self.assertEqual(result["isolation_points"], ["ISO-01", "ISO-02"])
        self.assertEqual(result["raw_document_ref"], "PTW-DOC-2025-001")

    def test_ptw_pipeline_deterministic(self):
        first = ptw_pipeline.process_ptw_text(
            "PTW-DOC-2025-001",
            SAMPLE_PTW_TEXT,
        )
        second = ptw_pipeline.process_ptw_text(
            "PTW-DOC-2025-001",
            SAMPLE_PTW_TEXT,
        )
        self.assertEqual(first, second)

    def test_shared_contract_represents_ptw_output(self):
        result = ptw_pipeline.process_ptw_text(
            "PTW-DOC-2025-001",
            SAMPLE_PTW_TEXT,
        )
        represented = StructuredPTW(**result)
        self.assertEqual(represented, result)


class TestPIDPipelineContract(unittest.TestCase):

    def test_pid_pipeline_produces_structured_pid_shape(self):
        result = pid_pipeline.process_pid_data(
            "PID-UNIT-01",
            "PID-001-VIS",
            SAMPLE_PID_SYMBOLS,
            SAMPLE_PID_CONNECTIONS,
        )
        self.assertEqual(set(result.keys()), PID_REQUIRED_KEYS)
        self.assertEqual(result["pid_id"], "PID-001-VIS")
        self.assertEqual(result["source"], "PID-UNIT-01")
        self.assertEqual(
            result["equipment_tags"],
            ["P-101", "V-101"],
        )
        self.assertEqual(result["unresolved_symbols"], [])

    def test_pid_pipeline_synchronizes_symbol_connections(self):
        result = pid_pipeline.process_pid_data(
            "PID-UNIT-01",
            "PID-001-VIS",
            SAMPLE_PID_SYMBOLS,
            SAMPLE_PID_CONNECTIONS,
        )
        connections_by_symbol = {
            symbol["symbol_id"]: symbol["connections"]
            for symbol in result["symbols"]
        }
        self.assertIn("V-101", connections_by_symbol["P-101"])
        self.assertIn("P-101", connections_by_symbol["V-101"])

    def test_pid_pipeline_deterministic(self):
        first = pid_pipeline.process_pid_data(
            "PID-UNIT-01",
            "PID-001-VIS",
            SAMPLE_PID_SYMBOLS,
            SAMPLE_PID_CONNECTIONS,
        )
        second = pid_pipeline.process_pid_data(
            "PID-UNIT-01",
            "PID-001-VIS",
            SAMPLE_PID_SYMBOLS,
            SAMPLE_PID_CONNECTIONS,
        )
        self.assertEqual(first, second)

    def test_shared_contract_represents_pid_output(self):
        result = pid_pipeline.process_pid_data(
            "PID-UNIT-01",
            "PID-001-VIS",
            SAMPLE_PID_SYMBOLS,
            SAMPLE_PID_CONNECTIONS,
        )
        represented = StructuredPID(**result)
        self.assertEqual(represented, result)


class TestNoDuplicateContracts(unittest.TestCase):

    def test_vision_modules_do_not_define_ptw_contract(self):
        for module in VISION_MODULES:
            with self.subTest(module=module.__name__):
                source = pkgutil.get_data(
                    module.__name__.rsplit(".", 1)[0],
                    module.__name__.split(".")[-1] + ".py",
                )
                content = source.decode("utf-8")
                self.assertNotIn(
                    "class StructuredPTW",
                    content,
                    f"{module.__name__} defines a duplicate StructuredPTW",
                )

    def test_vision_modules_do_not_define_pid_contract(self):
        for module in VISION_MODULES:
            with self.subTest(module=module.__name__):
                source = pkgutil.get_data(
                    module.__name__.rsplit(".", 1)[0],
                    module.__name__.split(".")[-1] + ".py",
                )
                content = source.decode("utf-8")
                self.assertNotIn(
                    "class StructuredPID",
                    content,
                    f"{module.__name__} defines a duplicate StructuredPID",
                )

    def test_vision_uses_shared_contracts_by_identity(self):
        self.assertIs(input_adapter.StructuredPTW, StructuredPTW)
        self.assertIs(input_adapter.StructuredPID, StructuredPID)
        self.assertIs(ptw_extractor.StructuredPTW, StructuredPTW)
        self.assertIs(pid_extractor.StructuredPID, StructuredPID)
        self.assertIs(ptw_pipeline.StructuredPTW, StructuredPTW)
        self.assertIs(pid_pipeline.StructuredPID, StructuredPID)


class TestNoNetworkAndDeterminism(unittest.TestCase):

    def test_no_network_imports_in_vision_package(self):
        for module in VISION_MODULES:
            with self.subTest(module=module.__name__):
                source = pkgutil.get_data(
                    module.__name__.rsplit(".", 1)[0],
                    module.__name__.split(".")[-1] + ".py",
                )
                content = source.decode("utf-8")
                for forbidden in FORBIDDEN_NETWORK_IMPORTS:
                    self.assertNotIn(
                        forbidden,
                        content,
                        f"{module.__name__} imports forbidden '{forbidden}'",
                    )

    def test_input_adapter_is_self_contained(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "ptw.json"
            json_path.write_text(
                json.dumps(
                    {
                        "raw_document_ref": "PTW-DOC-2025-001",
                        "permit_id": "MR-0001-VIS",
                        "work_type": "hot-work",
                        "scope": "Repair",
                        "location": ["Unit-4"],
                        "start_time": "2025-06-10T08:00:00",
                        "end_time": "2025-06-10T17:00:00",
                        "issuer": "A. Sharma",
                        "equipment_tags": ["P-100"],
                        "isolation_points": ["ISO-01"],
                    }
                ),
                encoding="utf-8",
            )

            data = input_adapter.load_json_file(json_path)
            result = input_adapter.extract_ptw_from_json(json_path)

            self.assertEqual(data["permit_id"], "MR-0001-VIS")
            self.assertEqual(result["raw_document_ref"], "PTW-DOC-2025-001")
            self.assertEqual(set(result.keys()), PTW_REQUIRED_KEYS)


class TestExistingFixtureContractBoundary(unittest.TestCase):

    def _load_fixture(self, name):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "ai_agent"
            / "fixtures"
            / name
        )
        with fixture_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_core_fixtures_ptw_matches_shared_contract(self):
        for fixture_name in FIXTURE_NAMES:
            with self.subTest(fixture=fixture_name):
                fixture = self._load_fixture(fixture_name)
                structured_ptw = fixture["structured_ptw"]

                result = ptw_extractor.extract_ptw_from_mock(
                    structured_ptw["permit_id"],
                    structured_ptw,
                )

                self.assertEqual(set(result.keys()), PTW_REQUIRED_KEYS)
                self.assertEqual(result["permit_id"], structured_ptw["permit_id"])
                self.assertEqual(result["location"], structured_ptw["location"])
                self.assertEqual(
                    result["equipment_tags"],
                    structured_ptw["equipment_tags"],
                )

    def test_core_fixtures_pid_matches_shared_contract(self):
        for fixture_name in FIXTURE_NAMES:
            with self.subTest(fixture=fixture_name):
                fixture = self._load_fixture(fixture_name)
                structured_pid = fixture["structured_pid"]

                result = pid_extractor.extract_pid_from_mock(
                    structured_pid["source"],
                    structured_pid,
                )

                self.assertEqual(set(result.keys()), PID_REQUIRED_KEYS)
                self.assertEqual(result["pid_id"], structured_pid["pid_id"])
                self.assertEqual(
                    result["equipment_tags"],
                    structured_pid["equipment_tags"],
                )
                self.assertEqual(result["symbols"], structured_pid["symbols"])
                self.assertEqual(
                    result["connections"],
                    structured_pid["connections"],
                )


if __name__ == "__main__":
    unittest.main()