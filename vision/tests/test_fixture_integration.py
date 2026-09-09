import json
import unittest
from pathlib import Path

from vision.pid_extractor import extract_pid_from_mock
from vision.ptw_extractor import extract_ptw_from_mock


class TestFixtureIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parents[2]

        fixture_path = (
            repo_root
            / "ai_agent"
            / "fixtures"
            / "safe_case.json"
        )

        with fixture_path.open(
            "r",
            encoding="utf-8",
        ) as fixture_file:
            cls.fixture = json.load(fixture_file)

    def test_safe_fixture_ptw_matches_role2_contract(self):
        structured_ptw = self.fixture["structured_ptw"]

        result = extract_ptw_from_mock(
            structured_ptw["raw_document_ref"],
            structured_ptw,
        )

        self.assertEqual(
            result["permit_id"],
            structured_ptw["permit_id"],
        )

        self.assertEqual(
            result["equipment_tags"],
            structured_ptw["equipment_tags"],
        )

        self.assertEqual(
            result["location"],
            structured_ptw["location"],
        )

        self.assertEqual(
            result["raw_document_ref"],
            structured_ptw["raw_document_ref"],
        )

    def test_safe_fixture_pid_matches_role2_contract(self):
        structured_pid = self.fixture["structured_pid"]

        result = extract_pid_from_mock(
            structured_pid["source"],
            structured_pid,
        )

        self.assertEqual(
            result["pid_id"],
            structured_pid["pid_id"],
        )

        self.assertEqual(
            result["equipment_tags"],
            structured_pid["equipment_tags"],
        )

        self.assertEqual(
            result["symbols"],
            structured_pid["symbols"],
        )

        self.assertEqual(
            result["connections"],
            structured_pid["connections"],
        )


if __name__ == "__main__":
    unittest.main()