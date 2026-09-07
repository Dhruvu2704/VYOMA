"""Unit tests for plant_safety.graph_facts.

Uses the actual repository fixtures in ai_agent/fixtures/.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import copy
import unittest
from pathlib import Path
from typing import Any, Dict

from plant_safety.graph_facts import GraphFactsBuilder, GraphFactsError
from plant_safety.topology import PlantGraph

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}


def _load_fixture(scenario: str) -> Dict[str, Any]:
    path = FIXTURES_DIR / FIXTURE_FILES[scenario]
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _pid(scenario: str) -> Dict[str, Any]:
    return _load_fixture(scenario)["structured_pid"]


def _ptw(scenario: str) -> Dict[str, Any]:
    return _load_fixture(scenario)["structured_ptw"]


def _graph(scenario: str) -> PlantGraph:
    return PlantGraph.from_structured_pid(_pid(scenario))


def _expected_facts(scenario: str) -> Dict[str, Any]:
    return _load_fixture(scenario)["graph_facts"]


def _build(scenario: str) -> Dict[str, Any]:
    fixture = _load_fixture(scenario)
    return GraphFactsBuilder.build(
        fixture["structured_ptw"],
        _graph(scenario),
        pid=fixture["structured_pid"],
        overlap_check=fixture["graph_facts"]["overlap_check"],
    )


# =========================================================================
# 1. safe fixture
# =========================================================================
class SafeFixtureGraphFactsTest(unittest.TestCase):
    def test_permit_id(self) -> None:
        facts = _build("safe")
        self.assertEqual(facts["permit_id"], "MR-0001-SAFE")

    def test_resolved_nodes(self) -> None:
        facts = _build("safe")
        self.assertEqual(
            facts["resolved_nodes"], ["CW-101", "P-101", "G-101"]
        )

    def test_unresolved_tags_empty(self) -> None:
        facts = _build("safe")
        self.assertEqual(facts["unresolved_tags"], [])

    def test_connected_equipment(self) -> None:
        facts = _build("safe")
        self.assertEqual(
            facts["connected_equipment"],
            {
                "P-101": ["CW-101"],
                "CW-101": ["G-101", "P-101"],
                "G-101": ["CW-101"],
            },
        )

    def test_active_isolations_empty(self) -> None:
        facts = _build("safe")
        self.assertEqual(facts["active_isolations"], [])

    def test_overlap_check_structure(self) -> None:
        facts = _build("safe")
        self.assertIn("overlapping_permits", facts["overlap_check"])
        self.assertIn("same_area_active", facts["overlap_check"])
        self.assertIsInstance(facts["overlap_check"]["overlapping_permits"], list)
        self.assertIsInstance(facts["overlap_check"]["same_area_active"], bool)

    def test_matches_fixture_fields(self) -> None:
        facts = _build("safe")
        self.assertEqual(facts["permit_id"], _expected_facts("safe")["permit_id"])
        self.assertEqual(
            facts["resolved_nodes"], _expected_facts("safe")["resolved_nodes"]
        )
        self.assertEqual(
            facts["unresolved_tags"], _expected_facts("safe")["unresolved_tags"]
        )
        self.assertEqual(
            facts["active_isolations"],
            _expected_facts("safe")["active_isolations"],
        )
        self.assertEqual(
            facts["overlap_check"], _expected_facts("safe")["overlap_check"]
        )


# =========================================================================
# 2. conflict fixture
# =========================================================================
class ConflictFixtureGraphFactsTest(unittest.TestCase):
    def test_permit_id(self) -> None:
        facts = _build("conflict")
        self.assertEqual(facts["permit_id"], "MR-0002-CONF")

    def test_resolved_nodes(self) -> None:
        facts = _build("conflict")
        self.assertEqual(
            facts["resolved_nodes"], ["LF-204", "T-302", "V-101"]
        )

    def test_unresolved_tags_empty(self) -> None:
        facts = _build("conflict")
        self.assertEqual(facts["unresolved_tags"], [])

    def test_connected_equipment(self) -> None:
        facts = _build("conflict")
        self.assertEqual(
            facts["connected_equipment"],
            {
                "LF-204": ["T-302"],
                "T-302": ["LF-204", "V-101"],
                "V-101": ["T-302"],
            },
        )

    def test_active_isolations(self) -> None:
        facts = _build("conflict")
        self.assertEqual(facts["active_isolations"], ["ISO-T302-01"])

    def test_matches_fixture_fields(self) -> None:
        facts = _build("conflict")
        self.assertEqual(
            facts["permit_id"], _expected_facts("conflict")["permit_id"]
        )
        self.assertEqual(
            facts["resolved_nodes"],
            _expected_facts("conflict")["resolved_nodes"],
        )
        self.assertEqual(
            facts["unresolved_tags"],
            _expected_facts("conflict")["unresolved_tags"],
        )
        self.assertEqual(
            facts["active_isolations"],
            _expected_facts("conflict")["active_isolations"],
        )
        self.assertEqual(
            facts["overlap_check"],
            _expected_facts("conflict")["overlap_check"],
        )


# =========================================================================
# 3. ambiguous fixture
# =========================================================================
class AmbiguousFixtureGraphFactsTest(unittest.TestCase):
    def test_permit_id(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(facts["permit_id"], "MR-0004-AMB")

    def test_resolved_nodes(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(facts["resolved_nodes"], ["T-410"])

    def test_unresolved_tags(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(
            facts["unresolved_tags"], ["TAG-7X-TEMP", "TAG-7X-LEVEL"]
        )

    def test_connected_equipment_empty(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(facts["connected_equipment"], {"T-410": []})

    def test_active_isolations_empty(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(facts["active_isolations"], [])

    def test_matches_fixture(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(facts, _expected_facts("ambiguous"))


# =========================================================================
# 4. disagreement fixture
# =========================================================================
class DisagreementFixtureGraphFactsTest(unittest.TestCase):
    def test_permit_id(self) -> None:
        facts = _build("disagreement")
        self.assertEqual(facts["permit_id"], "MR-0005-DIS")

    def test_resolved_nodes(self) -> None:
        facts = _build("disagreement")
        self.assertEqual(facts["resolved_nodes"], ["LF-501"])

    def test_unresolved_tags(self) -> None:
        facts = _build("disagreement")
        self.assertEqual(
            facts["unresolved_tags"], ["7X-TEMP-A", "7X-LEVEL-A"]
        )

    def test_connected_equipment(self) -> None:
        facts = _build("disagreement")
        self.assertEqual(
            facts["connected_equipment"],
            {"LF-501": ["P-201"]},
        )

    def test_active_isolations_empty(self) -> None:
        facts = _build("disagreement")
        self.assertEqual(facts["active_isolations"], [])

    def test_matches_fixture(self) -> None:
        facts = _build("disagreement")
        self.assertEqual(facts, _expected_facts("disagreement"))


# =========================================================================
# 5. All tags resolved
# =========================================================================
class AllTagsResolvedTest(unittest.TestCase):
    def test_safe_all_resolved(self) -> None:
        facts = _build("safe")
        self.assertEqual(
            facts["resolved_nodes"], ["CW-101", "P-101", "G-101"]
        )
        self.assertEqual(facts["unresolved_tags"], [])


# =========================================================================
# 6. Mixed resolved/unresolved tags
# =========================================================================
class MixedResolvedUnresolvedTest(unittest.TestCase):
    def test_mixed_resolution(self) -> None:
        ptw = {
            "permit_id": "MIX-1",
            "equipment_tags": ["P-101", "FAKE-1", "G-101", "FAKE-2"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["resolved_nodes"], ["P-101", "G-101"])
        self.assertEqual(facts["unresolved_tags"], ["FAKE-1", "FAKE-2"])


# =========================================================================
# 7. All tags unresolved
# =========================================================================
class AllTagsUnresolvedTest(unittest.TestCase):
    def test_all_unresolved(self) -> None:
        ptw = {
            "permit_id": "ALL-UNRES",
            "equipment_tags": ["NOPE-A", "NOPE-B"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["resolved_nodes"], [])
        self.assertEqual(facts["unresolved_tags"], ["NOPE-A", "NOPE-B"])
        self.assertEqual(facts["connected_equipment"], {})


# =========================================================================
# 8. Empty equipment_tags
# =========================================================================
class EmptyEquipmentTagsTest(unittest.TestCase):
    def test_empty_equipment_list(self) -> None:
        ptw = {
            "permit_id": "EMPTY-EQ",
            "equipment_tags": [],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["resolved_nodes"], [])
        self.assertEqual(facts["unresolved_tags"], [])
        self.assertEqual(facts["connected_equipment"], {})


# =========================================================================
# 9. None equipment_tags (supported by existing resolver semantics)
# =========================================================================
class NoneEquipmentTagsTest(unittest.TestCase):
    def test_none_equipment_defaults_to_empty(self) -> None:
        ptw = {
            "permit_id": "NONE-EQ",
            "equipment_tags": None,
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["resolved_nodes"], [])
        self.assertEqual(facts["unresolved_tags"], [])


# =========================================================================
# 10. Duplicate equipment tags
# =========================================================================
class DuplicateEquipmentTagsTest(unittest.TestCase):
    def test_duplicates_deduplicated(self) -> None:
        ptw = {
            "permit_id": "DUP-EQ",
            "equipment_tags": ["P-101", "CW-101", "P-101", "P-101"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["resolved_nodes"], ["P-101", "CW-101"])

    def test_duplicate_unresolved_deduplicated(self) -> None:
        ptw = {
            "permit_id": "DUP-UNRES",
            "equipment_tags": ["FAKE", "FAKE", "FAKE"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["unresolved_tags"], ["FAKE"])


# =========================================================================
# 11. Deterministic ordering
# =========================================================================
class DeterministicOrderingTest(unittest.TestCase):
    def test_first_seen_order_preserved(self) -> None:
        ptw = {
            "permit_id": "ORDER-1",
            "equipment_tags": ["G-101", "P-101", "CW-101"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(
            facts["resolved_nodes"], ["G-101", "P-101", "CW-101"]
        )

    def test_mixed_duplicates_preserve_first_seen(self) -> None:
        ptw = {
            "permit_id": "ORDER-2",
            "equipment_tags": ["MISSING", "P-101", "MISSING", "CW-101"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["unresolved_tags"], ["MISSING"])
        self.assertEqual(facts["resolved_nodes"], ["P-101", "CW-101"])


# =========================================================================
# 12. Connected equipment
# =========================================================================
class ConnectedEquipmentTest(unittest.TestCase):
    def test_safe_connectivity(self) -> None:
        facts = _build("safe")
        self.assertEqual(facts["connected_equipment"]["P-101"], ["CW-101"])
        self.assertEqual(
            facts["connected_equipment"]["CW-101"], ["G-101", "P-101"]
        )
        self.assertEqual(facts["connected_equipment"]["G-101"], ["CW-101"])

    def test_conflict_connectivity(self) -> None:
        facts = _build("conflict")
        self.assertEqual(facts["connected_equipment"]["LF-204"], ["T-302"])
        self.assertEqual(
            facts["connected_equipment"]["T-302"], ["LF-204", "V-101"]
        )
        self.assertEqual(facts["connected_equipment"]["V-101"], ["T-302"])


# =========================================================================
# 13. Multiple graph neighbors
# =========================================================================
class MultipleNeighborsTest(unittest.TestCase):
    def test_cw101_has_two_neighbors(self) -> None:
        facts = _build("safe")
        self.assertEqual(len(facts["connected_equipment"]["CW-101"]), 2)
        self.assertIn("G-101", facts["connected_equipment"]["CW-101"])
        self.assertIn("P-101", facts["connected_equipment"]["CW-101"])

    def test_t302_has_two_neighbors(self) -> None:
        facts = _build("conflict")
        self.assertEqual(len(facts["connected_equipment"]["T-302"]), 2)
        self.assertIn("LF-204", facts["connected_equipment"]["T-302"])
        self.assertIn("V-101", facts["connected_equipment"]["T-302"])


# =========================================================================
# 14. Isolated node
# =========================================================================
class IsolatedNodeTest(unittest.TestCase):
    def test_ambiguous_single_node_no_edges(self) -> None:
        facts = _build("ambiguous")
        self.assertEqual(facts["resolved_nodes"], ["T-410"])
        self.assertEqual(facts["connected_equipment"], {"T-410": []})

    def test_isolated_node_included_with_empty_list(self) -> None:
        ptw = {
            "permit_id": "ISO-1",
            "equipment_tags": ["T-410"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("ambiguous"))
        self.assertIn("T-410", facts["connected_equipment"])
        self.assertEqual(facts["connected_equipment"]["T-410"], [])


# =========================================================================
# 15. Unresolved tags excluded from connectivity
# =========================================================================
class UnresolvedExcludedFromConnectivityTest(unittest.TestCase):
    def test_unresolved_not_in_connected_equipment(self) -> None:
        ptw = {
            "permit_id": "UNRES-CONN",
            "equipment_tags": ["P-101", "FAKE-999"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertNotIn("FAKE-999", facts["connected_equipment"])
        self.assertIn("P-101", facts["connected_equipment"])


# =========================================================================
# 16. Single isolation point
# =========================================================================
class SingleIsolationPointTest(unittest.TestCase):
    def test_single_isolation(self) -> None:
        ptw = {
            "permit_id": "ISO-SINGLE",
            "equipment_tags": [],
            "isolation_points": ["ISO-T302-01"],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("conflict"))
        self.assertEqual(facts["active_isolations"], ["ISO-T302-01"])


# =========================================================================
# 17. Multiple isolation points
# =========================================================================
class MultipleIsolationPointsTest(unittest.TestCase):
    def test_multiple_isolations(self) -> None:
        ptw = {
            "permit_id": "ISO-MULTI",
            "equipment_tags": [],
            "isolation_points": [
                "ISO-T302-01",
                "ISO-LF204-01",
                "ISO-V101-01",
            ],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("conflict"))
        self.assertEqual(
            facts["active_isolations"],
            ["ISO-T302-01", "ISO-LF204-01", "ISO-V101-01"],
        )


# =========================================================================
# 18. Duplicate isolation points
# =========================================================================
class DuplicateIsolationPointsTest(unittest.TestCase):
    def test_duplicate_isolations_deduplicated(self) -> None:
        ptw = {
            "permit_id": "ISO-DUP",
            "equipment_tags": [],
            "isolation_points": [
                "ISO-A-01",
                "ISO-B-01",
                "ISO-A-01",
                "ISO-A-01",
                "ISO-B-01",
            ],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(
            facts["active_isolations"], ["ISO-A-01", "ISO-B-01"]
        )


# =========================================================================
# 19. Empty/None isolation points
# =========================================================================
class EmptyNoneIsolationPointsTest(unittest.TestCase):
    def test_empty_isolation_list(self) -> None:
        ptw = {
            "permit_id": "ISO-EMPTY",
            "equipment_tags": [],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["active_isolations"], [])

    def test_none_isolation_defaults_to_empty(self) -> None:
        ptw = {
            "permit_id": "ISO-NONE",
            "equipment_tags": [],
            "isolation_points": None,
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["active_isolations"], [])


# =========================================================================
# 20. ISO IDs remain opaque
# =========================================================================
class OpaqueIsoIdsTest(unittest.TestCase):
    def test_iso_not_converted_to_equipment(self) -> None:
        ptw = {
            "permit_id": "ISO-OPAQUE",
            "equipment_tags": ["T-302"],
            "isolation_points": ["ISO-T302-01"],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("conflict"))
        self.assertNotIn("T-302", facts["active_isolations"])
        self.assertNotIn("ISO-T302-01", facts["resolved_nodes"])
        self.assertNotIn("ISO-T302-01", facts["unresolved_tags"])
        self.assertEqual(facts["active_isolations"], ["ISO-T302-01"])


# =========================================================================
# 21. overlap_check structure
# =========================================================================
class OverlapCheckStructureTest(unittest.TestCase):
    def test_default_overlap_check(self) -> None:
        ptw = {
            "permit_id": "OV-DEFAULT",
            "equipment_tags": [],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(
            facts["overlap_check"],
            {"overlapping_permits": [], "same_area_active": False},
        )

    def test_custom_overlap_check(self) -> None:
        ptw = {
            "permit_id": "OV-CUSTOM",
            "equipment_tags": [],
            "isolation_points": [],
        }
        custom = {
            "overlapping_permits": ["MR-0003-CONF"],
            "same_area_active": True,
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"), overlap_check=custom)
        self.assertEqual(facts["overlap_check"], custom)

    def test_supplied_overlap_check_is_defensively_copied(self) -> None:
        ptw = {
            "permit_id": "OV-COPY",
            "equipment_tags": [],
            "isolation_points": [],
        }
        custom = {
            "overlapping_permits": ["MR-0009"],
            "same_area_active": True,
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"), overlap_check=custom)
        self.assertIsNot(facts["overlap_check"], custom)
        self.assertIsNot(facts["overlap_check"]["overlapping_permits"], custom["overlapping_permits"])
        facts["overlap_check"]["overlapping_permits"].append("MUTATED")
        facts["overlap_check"]["same_area_active"] = False
        self.assertEqual(custom["overlapping_permits"], ["MR-0009"])
        self.assertTrue(custom["same_area_active"])

    def test_overlap_check_has_required_keys(self) -> None:
        facts = _build("safe")
        self.assertIn("overlapping_permits", facts["overlap_check"])
        self.assertIn("same_area_active", facts["overlap_check"])


# =========================================================================
# 22. permit_id propagation
# =========================================================================
class PermitIdPropagationTest(unittest.TestCase):
    def test_permit_id_from_safe(self) -> None:
        facts = _build("safe")
        self.assertEqual(facts["permit_id"], "MR-0001-SAFE")

    def test_permit_id_from_conflict(self) -> None:
        facts = _build("conflict")
        self.assertEqual(facts["permit_id"], "MR-0002-CONF")

    def test_permit_id_from_custom_ptw(self) -> None:
        ptw = {
            "permit_id": "CUSTOM-PERMIT-XYZ",
            "equipment_tags": [],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["permit_id"], "CUSTOM-PERMIT-XYZ")

    def test_permit_id_empty_string_default(self) -> None:
        ptw: Dict[str, Any] = {}
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(facts["permit_id"], "")


# =========================================================================
# 23. Invalid PTW input
# =========================================================================
class InvalidPtwInputTest(unittest.TestCase):
    def test_type_error_on_string_ptw(self) -> None:
        with self.assertRaises(TypeError):
            GraphFactsBuilder.build("not-a-dict", _graph("safe"))  # type: ignore[arg-type]

    def test_type_error_on_list_ptw(self) -> None:
        with self.assertRaises(TypeError):
            GraphFactsBuilder.build([], _graph("safe"))  # type: ignore[arg-type]

    def test_type_error_on_none_ptw(self) -> None:
        with self.assertRaises(TypeError):
            GraphFactsBuilder.build(None, _graph("safe"))  # type: ignore[arg-type]


# =========================================================================
# 24. Invalid graph input
# =========================================================================
class InvalidGraphInputTest(unittest.TestCase):
    def test_type_error_on_string_graph(self) -> None:
        ptw = _ptw("safe")
        with self.assertRaises(TypeError):
            GraphFactsBuilder.build(ptw, "not-a-graph")  # type: ignore[arg-type]

    def test_type_error_on_none_graph(self) -> None:
        ptw = _ptw("safe")
        with self.assertRaises(TypeError):
            GraphFactsBuilder.build(ptw, None)  # type: ignore[arg-type]

    def test_type_error_on_dict_graph(self) -> None:
        ptw = _ptw("safe")
        with self.assertRaises(TypeError):
            GraphFactsBuilder.build(ptw, {"nx_graph": None})  # type: ignore[arg-type]


# =========================================================================
# 25. PTW immutability
# =========================================================================
class PtwImmutabilityTest(unittest.TestCase):
    def test_ptw_not_mutated(self) -> None:
        ptw = _ptw("safe")
        ptw_before = copy.deepcopy(ptw)
        GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(ptw, ptw_before)

    def test_custom_ptw_not_mutated(self) -> None:
        ptw = {
            "permit_id": "IMMUT-1",
            "equipment_tags": ["P-101", "FAKE"],
            "isolation_points": ["ISO-X-01"],
        }
        ptw_before = copy.deepcopy(ptw)
        GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(ptw, ptw_before)


# =========================================================================
# 25b. PID immutability
# =========================================================================
class PidImmutabilityTest(unittest.TestCase):
    def test_pid_not_mutated(self) -> None:
        pid = _pid("ambiguous")
        pid_before = copy.deepcopy(pid)
        GraphFactsBuilder.build(_ptw("ambiguous"), _graph("ambiguous"), pid=pid)
        self.assertEqual(pid, pid_before)

    def test_nested_pid_containers_not_mutated(self) -> None:
        pid = {
            "pid_id": "PID-IMMUT",
            "source": "mock",
            "equipment_tags": ["X"],
            "symbols": [],
            "connections": [],
            "unresolved_symbols": ["TAG-A", "TAG-B"],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        pid_before = copy.deepcopy(pid)
        ptw = {"permit_id": "PIDI", "equipment_tags": [], "isolation_points": []}
        GraphFactsBuilder.build(ptw, _graph("safe"), pid=pid)
        self.assertEqual(pid, pid_before)


# =========================================================================
# 26. Graph immutability
# =========================================================================
class GraphImmutabilityTest(unittest.TestCase):
    def test_graph_not_mutated(self) -> None:
        graph = _graph("safe")
        node_ids_before = list(graph.node_ids)
        edges_before = len(graph.edges)

        ptw = {
            "permit_id": "IMMUT-G",
            "equipment_tags": ["CW-101", "NEW-FAKE"],
            "isolation_points": ["ISO-NEW-01"],
        }
        GraphFactsBuilder.build(ptw, graph)

        self.assertEqual(graph.node_ids, node_ids_before)
        self.assertEqual(len(graph.edges), edges_before)
        self.assertFalse(graph.has_node("NEW-FAKE"))
        self.assertFalse(graph.has_node("ISO-NEW-01"))


# =========================================================================
# 27. Repeated execution produces identical output
# =========================================================================
class RepeatedExecutionTest(unittest.TestCase):
    def test_safe_deterministic(self) -> None:
        r1 = _build("safe")
        r2 = _build("safe")
        r3 = _build("safe")
        self.assertEqual(r1, r2)
        self.assertEqual(r2, r3)

    def test_conflict_deterministic(self) -> None:
        r1 = _build("conflict")
        r2 = _build("conflict")
        self.assertEqual(r1, r2)

    def test_ambiguous_deterministic(self) -> None:
        r1 = _build("ambiguous")
        r2 = _build("ambiguous")
        self.assertEqual(r1, r2)

    def test_disagreement_deterministic(self) -> None:
        r1 = _build("disagreement")
        r2 = _build("disagreement")
        self.assertEqual(r1, r2)


# =========================================================================
# 28. Connected equipment includes resolved nodes with no neighbors
# =========================================================================
class EmptyNeighborListsTest(unittest.TestCase):
    def test_isolated_node_present_with_empty_list(self) -> None:
        ptw = {
            "permit_id": "NO-EMPTY",
            "equipment_tags": ["T-410"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("ambiguous"))
        self.assertIn("T-410", facts["connected_equipment"])
        self.assertEqual(facts["connected_equipment"]["T-410"], [])


# =========================================================================
# 29. GraphFactsError is available
# =========================================================================
class GraphFactsErrorAvailableTest(unittest.TestCase):
    def test_error_class_exists(self) -> None:
        self.assertTrue(issubclass(GraphFactsError, Exception))


# =========================================================================
# 30. pid=None behavior
# =========================================================================
class PidNoneBehaviorTest(unittest.TestCase):
    def test_pid_none_contributes_no_unresolved_symbols(self) -> None:
        ptw = {
            "permit_id": "PIDNONE-1",
            "equipment_tags": ["LF-501"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("disagreement"))
        self.assertEqual(facts["resolved_nodes"], ["LF-501"])
        self.assertEqual(facts["unresolved_tags"], [])

    def test_pid_none_with_fixture_ptw(self) -> None:
        facts = GraphFactsBuilder.build(_ptw("ambiguous"), _graph("ambiguous"))
        self.assertEqual(facts["resolved_nodes"], ["T-410"])
        self.assertEqual(facts["unresolved_tags"], [])

    def test_pid_none_uses_default_overlap_check(self) -> None:
        ptw = {
            "permit_id": "PIDNONE-2",
            "equipment_tags": [],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"))
        self.assertEqual(
            facts["overlap_check"],
            {"overlapping_permits": [], "same_area_active": False},
        )


# =========================================================================
# 31. pid with unresolved_symbols behavior
# =========================================================================
class PidUnresolvedSymbolsBehaviorTest(unittest.TestCase):
    def test_pid_unresolved_symbols_added(self) -> None:
        pid = {
            "pid_id": "PID-UNR",
            "source": "mock",
            "equipment_tags": [],
            "symbols": [],
            "connections": [],
            "unresolved_symbols": ["TAG-X", "TAG-Y"],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        ptw = {
            "permit_id": "PIDU-1",
            "equipment_tags": [],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"), pid=pid)
        self.assertEqual(facts["unresolved_tags"], ["TAG-X", "TAG-Y"])

    def test_ptw_unresolved_combined_with_pid_unresolved(self) -> None:
        pid = {
            "pid_id": "PID-UNR2",
            "source": "mock",
            "equipment_tags": [],
            "symbols": [],
            "connections": [],
            "unresolved_symbols": ["PID-A", "PID-B"],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        ptw = {
            "permit_id": "PIDU-2",
            "equipment_tags": ["FAKE", "PID-A"],
            "isolation_points": [],
        }
        facts = GraphFactsBuilder.build(ptw, _graph("safe"), pid=pid)
        self.assertEqual(facts["unresolved_tags"], ["FAKE", "PID-A", "PID-B"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
