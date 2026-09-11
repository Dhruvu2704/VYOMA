"""Sample-data consistency tests for the integrated MockRefinery dataset.

Verifies that the Phase 1 sample-data files under
ai_agent/fixtures/sample-data/ are internally consistent and compatible
with the shared contract shapes where applicable.

Run from the repository root:

    python -m unittest tests.test_sample_data -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict, List

SAMPLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "ai_agent"
    / "fixtures"
    / "sample-data"
)

FINAL_DECISIONS = {
    "PASS",
    "FLAGGED_FOR_REVIEW",
    "REVIEW_REQUIRED",
}

RULE_RESULTS = {"PASS", "FLAGGED"}

PTW_REQUIRED_FIELDS = {
    "permit_id",
    "work_type",
    "scope",
    "location",
    "start_time",
    "end_time",
    "issuer",
    "equipment_tags",
    "isolation_points",
}

ACTIVE_PERMIT_FIELDS = {
    "permit_id",
    "location",
    "start_time",
    "end_time",
    "status",
}

EQUIPMENT_FIELDS = {
    "tag",
    "type",
    "description",
    "isolation_capable",
}

CONNECTION_FIELDS = {
    "source",
    "target",
    "line_ref",
}

SOP_FIELDS = {
    "sop_id",
    "title",
    "snippet",
}


def _load(name: str) -> Dict[str, Any]:
    with (SAMPLE_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _is_list_of_str(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


class SampleDataStructureTests(unittest.TestCase):
    """Structural validation of each sample-data file."""

    def test_all_sample_data_files_exist(self) -> None:
        expected = {
            "equipment.json",
            "pipes.json",
            "ptws.json",
            "sops.json",
            "permit-register.json",
            "ground-truth.json",
        }

        present = {name for name in expected if (SAMPLE_DIR / name).exists()}

        self.assertEqual(present, expected)

    def test_equipment_entries_have_expected_fields(self) -> None:
        data = _load("equipment.json")
        equipment = data["equipment"]

        self.assertIsInstance(equipment, list)
        self.assertGreater(len(equipment), 0)

        tags = []

        for item in equipment:
            tags.append(item["tag"])
            self.assertEqual(set(item.keys()) & EQUIPMENT_FIELDS, EQUIPMENT_FIELDS)
            self.assertIsInstance(item["tag"], str)
            self.assertIsInstance(item["type"], str)
            self.assertIsInstance(item["description"], str)
            self.assertIsInstance(item["isolation_capable"], bool)

        self.assertEqual(len(tags), len(set(tags)), "equipment tags must be unique")

    def test_pipe_connections_have_expected_fields(self) -> None:
        data = _load("pipes.json")
        connections = data["connections"]

        self.assertIsInstance(connections, list)
        self.assertGreater(len(connections), 0)

        for connection in connections:
            self.assertEqual(
                set(connection.keys()) & CONNECTION_FIELDS,
                CONNECTION_FIELDS,
            )
            self.assertIsInstance(connection["source"], str)
            self.assertIsInstance(connection["target"], str)

            line_ref = connection["line_ref"]
            self.assertTrue(
                line_ref is None or isinstance(line_ref, str),
                "line_ref must be str or None",
            )

    def test_ptws_entries_have_expected_fields(self) -> None:
        data = _load("ptws.json")
        ptws = data["ptws"]

        self.assertIsInstance(ptws, list)
        self.assertGreater(len(ptws), 0)

        permit_ids = set()

        for ptw in ptws:
            self.assertEqual(set(ptw.keys()) & PTW_REQUIRED_FIELDS, PTW_REQUIRED_FIELDS)
            self.assertIsInstance(ptw["permit_id"], str)
            self.assertIsInstance(ptw["work_type"], str)
            self.assertIsInstance(ptw["scope"], str)
            self.assertIsInstance(ptw["start_time"], str)
            self.assertIsInstance(ptw["end_time"], str)
            self.assertIsInstance(ptw["issuer"], str)
            self.assertTrue(_is_list_of_str(ptw["location"]))
            self.assertTrue(_is_list_of_str(ptw["equipment_tags"]))
            self.assertTrue(_is_list_of_str(ptw["isolation_points"]))
            permit_ids.add(ptw["permit_id"])

        self.assertEqual(
            len(ptws),
            len(permit_ids),
            "permit IDs in ptws.json must be unique",
        )

    def test_active_permits_follow_active_permit_shape(self) -> None:
        data = _load("permit-register.json")
        active_permits = data["active_permits"]

        self.assertIsInstance(active_permits, list)
        self.assertGreater(len(active_permits), 0)

        for permit in active_permits:
            self.assertEqual(
                set(permit.keys()) & ACTIVE_PERMIT_FIELDS,
                ACTIVE_PERMIT_FIELDS,
            )
            self.assertEqual(permit["status"], "ACTIVE")
            self.assertTrue(_is_list_of_str(permit["location"]))
            self.assertIsInstance(permit["start_time"], str)
            self.assertIsInstance(permit["end_time"], str)

    def test_sop_entries_have_expected_fields(self) -> None:
        data = _load("sops.json")
        sops = data["sops"]

        self.assertIsInstance(sops, list)
        self.assertGreater(len(sops), 0)

        for sop in sops:
            self.assertEqual(set(sop.keys()) & SOP_FIELDS, SOP_FIELDS)
            self.assertIsInstance(sop["sop_id"], str)
            self.assertIsInstance(sop["title"], str)
            self.assertIsInstance(sop["snippet"], str)


class SampleDataCrossReferenceTests(unittest.TestCase):
    """Cross-file consistency for the MockRefinery dataset."""

    def _permit_ids(self) -> List[str]:
        return [ptw["permit_id"] for ptw in _load("ptws.json")["ptws"]]

    def test_active_permits_reference_existing_ptws(self) -> None:
        permit_ids = set(self._permit_ids())
        data = _load("permit-register.json")

        for permit in data["active_permits"]:
            self.assertIn(
                permit["permit_id"],
                permit_ids,
                f"active permit {permit['permit_id']} has no PTW",
            )

    def test_ground_truth_references_existing_ptws(self) -> None:
        permit_ids = set(self._permit_ids())
        data = _load("ground-truth.json")

        for scenario in data["scenarios"]:
            for permit_id in scenario["permit_ids"]:
                self.assertIn(
                    permit_id,
                    permit_ids,
                    f"scenario {scenario['scenario_id']} references "
                    f"unknown permit {permit_id}",
                )

    def test_ground_truth_decision_values_are_contract_compatible(self) -> None:
        data = _load("ground-truth.json")

        for scenario in data["scenarios"]:
            self.assertIn(
                scenario["expected_rule_result"],
                RULE_RESULTS,
                f"scenario {scenario['scenario_id']} has invalid "
                f"expected_rule_result {scenario['expected_rule_result']}",
            )
            self.assertIn(
                scenario["expected_final_decision"],
                FINAL_DECISIONS,
                f"scenario {scenario['scenario_id']} has invalid "
                f"expected_final_decision "
                f"{scenario['expected_final_decision']}",
            )

    def test_ground_truth_confidence_is_valid_label(self) -> None:
        data = _load("ground-truth.json")
        valid = {"LOW", "MEDIUM", "HIGH"}

        for scenario in data["scenarios"]:
            self.assertIn(
                scenario["confidence"],
                valid,
                f"scenario {scenario['scenario_id']} has invalid "
                f"confidence {scenario['confidence']}",
            )


if __name__ == "__main__":
    unittest.main()