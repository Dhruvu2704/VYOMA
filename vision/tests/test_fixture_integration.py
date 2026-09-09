import json
import unittest
from pathlib import Path

from vision.pid_extractor import extract_pid_from_mock
from vision.ptw_extractor import extract_ptw_from_mock


class TestFixtureIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.fixtures_dir = (
            cls.repo_root
            / "ai_agent"
            / "fixtures"
        )

        cls.fixture_names = [
            "safe_case.json",
            "conflict_case.json",
            "ambiguous_case.json",
            "disagreement_case.json",
        ]

    def _load_fixture(self, fixture_name):
        fixture_path = self.fixtures_dir / fixture_name

        with fixture_path.open(
            "r",
            encoding="utf-8",
        ) as fixture_file:
            return json.load(fixture_file)

    def test_all_fixtures_have_role2_data(self):
        for fixture_name in self.fixture_names:
            with self.subTest(fixture=fixture_name):
                fixture = self._load_fixture(fixture_name)

                self.assertIn(
                    "structured_ptw",
                    fixture,
                )

                self.assertIn(
                    "structured_pid",
                    fixture,
                )

    def test_all_fixtures_ptw_match_role2_contract(self):
        for fixture_name in self.fixture_names:
            with self.subTest(fixture=fixture_name):
                fixture = self._load_fixture(fixture_name)

                structured_ptw = fixture["structured_ptw"]

                result = extract_ptw_from_mock(
                    structured_ptw["raw_document_ref"],
                    structured_ptw,
                )

                self.assertEqual(
                    result["permit_id"],
                    structured_ptw["permit_id"],
                )

                self.assertEqual(
                    result["location"],
                    structured_ptw["location"],
                )

                self.assertEqual(
                    result["equipment_tags"],
                    structured_ptw["equipment_tags"],
                )

    def test_all_fixtures_pid_match_role2_contract(self):
        for fixture_name in self.fixture_names:
            with self.subTest(fixture=fixture_name):
                fixture = self._load_fixture(fixture_name)

                structured_pid = fixture["structured_pid"]

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