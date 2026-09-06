"""Unit tests for plant_safety.tag_resolution.

Uses the actual repository fixtures in ai_agent/fixtures/.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict, List

from plant_safety.tag_resolution import TagResolver, TagResolutionResult
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


def _resolve(scenario: str) -> TagResolutionResult:
    return TagResolver().resolve(_ptw(scenario), _graph(scenario))


# ---------------------------------------------------------------------------
# 1. Exact equipment tag resolves
# ---------------------------------------------------------------------------
class ExactEquipmentResolutionTest(unittest.TestCase):
    def test_safe_all_equipment_resolves(self) -> None:
        result = _resolve("safe")
        self.assertEqual(
            result.resolved_equipment, ["CW-101", "P-101", "G-101"]
        )
        self.assertEqual(result.unresolved_equipment, [])

    def test_conflict_all_equipment_resolves(self) -> None:
        result = _resolve("conflict")
        self.assertEqual(
            result.resolved_equipment, ["LF-204", "T-302", "V-101"]
        )

    def test_ambiguous_equipment_resolves(self) -> None:
        result = _resolve("ambiguous")
        self.assertEqual(result.resolved_equipment, ["T-410"])

    def test_disagreement_equipment_resolves(self) -> None:
        result = _resolve("disagreement")
        self.assertEqual(result.resolved_equipment, ["LF-501"])


# ---------------------------------------------------------------------------
# 2. Unknown equipment tag becomes unresolved
# ---------------------------------------------------------------------------
class UnknownEquipmentTest(unittest.TestCase):
    def test_unknown_tag_unresolved(self) -> None:
        ptw = {
            "permit_id": "TEST-1",
            "equipment_tags": ["CW-101", "FAKE-TAG-999"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, ["CW-101"])
        self.assertEqual(result.unresolved_equipment, ["FAKE-TAG-999"])

    def test_all_unknown_equipment(self) -> None:
        ptw = {
            "permit_id": "TEST-2",
            "equipment_tags": ["NOPE-A", "NOPE-B"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, [])
        self.assertEqual(result.unresolved_equipment, ["NOPE-A", "NOPE-B"])


# ---------------------------------------------------------------------------
# 3. Mixed resolved/unresolved equipment
# ---------------------------------------------------------------------------
class MixedResolutionTest(unittest.TestCase):
    def test_mixed_equipment_resolution(self) -> None:
        ptw = {
            "permit_id": "TEST-3",
            "equipment_tags": ["P-101", "MISSING-1", "G-101", "MISSING-2"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, ["P-101", "G-101"])
        self.assertEqual(
            result.unresolved_equipment, ["MISSING-1", "MISSING-2"]
        )


# ---------------------------------------------------------------------------
# 4. Empty equipment_tags
# ---------------------------------------------------------------------------
class EmptyEquipmentTest(unittest.TestCase):
    def test_empty_equipment_list(self) -> None:
        ptw = {
            "permit_id": "TEST-4",
            "equipment_tags": [],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, [])
        self.assertEqual(result.unresolved_equipment, [])


# ---------------------------------------------------------------------------
# 5. None equipment_tags if currently supported
# ---------------------------------------------------------------------------
class NoneEquipmentTest(unittest.TestCase):
    def test_none_equipment_defaults_to_empty(self) -> None:
        ptw = {
            "permit_id": "TEST-5",
            "equipment_tags": None,
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, [])
        self.assertEqual(result.unresolved_equipment, [])


# ---------------------------------------------------------------------------
# 6. Duplicate equipment tags deduplicate
# ---------------------------------------------------------------------------
class DuplicateEquipmentTest(unittest.TestCase):
    def test_duplicate_equipment_deduplicated(self) -> None:
        ptw = {
            "permit_id": "TEST-6",
            "equipment_tags": ["CW-101", "P-101", "CW-101", "CW-101"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, ["CW-101", "P-101"])
        self.assertEqual(result.unresolved_equipment, [])

    def test_duplicate_unknown_tag_deduplicated(self) -> None:
        ptw = {
            "permit_id": "TEST-6b",
            "equipment_tags": ["FAKE", "FAKE", "FAKE"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.resolved_equipment, [])
        self.assertEqual(result.unresolved_equipment, ["FAKE"])


# ---------------------------------------------------------------------------
# 7. First-seen ordering is preserved
# ---------------------------------------------------------------------------
class FirstSeenOrderTest(unittest.TestCase):
    def test_first_seen_ordering_resolved(self) -> None:
        ptw = {
            "permit_id": "TEST-7",
            "equipment_tags": ["G-101", "P-101", "CW-101"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(
            result.resolved_equipment, ["G-101", "P-101", "CW-101"]
        )

    def test_mixed_duplicates_preserve_first_seen(self) -> None:
        ptw = {
            "permit_id": "TEST-7b",
            "equipment_tags": ["MISSING", "P-101", "MISSING", "CW-101"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        # MISSING appears first, so it is unresolved[0]
        self.assertEqual(result.unresolved_equipment, ["MISSING"])
        self.assertEqual(result.resolved_equipment, ["P-101", "CW-101"])


# ---------------------------------------------------------------------------
# 8. Existing fixture equipment tags resolve correctly
# ---------------------------------------------------------------------------
class FixtureEquipmentResolutionTest(unittest.TestCase):
    def test_safe_fixture(self) -> None:
        result = _resolve("safe")
        self.assertEqual(
            result.resolved_equipment, ["CW-101", "P-101", "G-101"]
        )
        self.assertEqual(result.unresolved_equipment, [])

    def test_conflict_fixture(self) -> None:
        result = _resolve("conflict")
        self.assertEqual(
            result.resolved_equipment, ["LF-204", "T-302", "V-101"]
        )
        self.assertEqual(result.unresolved_equipment, [])

    def test_ambiguous_fixture(self) -> None:
        result = _resolve("ambiguous")
        self.assertEqual(result.resolved_equipment, ["T-410"])
        self.assertEqual(result.unresolved_equipment, [])

    def test_disagreement_fixture(self) -> None:
        result = _resolve("disagreement")
        self.assertEqual(result.resolved_equipment, ["LF-501"])
        self.assertEqual(result.unresolved_equipment, [])


# ---------------------------------------------------------------------------
# 9. ISO-T302-01 is preserved as an isolation identifier
# ---------------------------------------------------------------------------
class IsolationPassthroughTest(unittest.TestCase):
    def test_iso_identifier_preserved(self) -> None:
        result = _resolve("conflict")
        self.assertEqual(result.isolation_points, ["ISO-T302-01"])

    def test_iso_identifier_not_in_equipment_lists(self) -> None:
        result = _resolve("conflict")
        self.assertNotIn("ISO-T302-01", result.resolved_equipment)
        self.assertNotIn("ISO-T302-01", result.unresolved_equipment)


# ---------------------------------------------------------------------------
# 10. ISO-T302-01 does NOT need to exist as a graph node
# ---------------------------------------------------------------------------
class IsoNotGraphNodeTest(unittest.TestCase):
    def test_iso_not_a_graph_node(self) -> None:
        graph = _graph("conflict")
        self.assertFalse(graph.has_node("ISO-T302-01"))

    def test_t302_is_a_graph_node(self) -> None:
        graph = _graph("conflict")
        self.assertTrue(graph.has_node("T-302"))


# ---------------------------------------------------------------------------
# 11. Isolation identifiers are not classified as graph-resolved
# ---------------------------------------------------------------------------
class IsolationNotGraphResolvedTest(unittest.TestCase):
    def test_isolation_points_are_separate_from_equipment(self) -> None:
        result = _resolve("conflict")
        # ISO-T302-01 is in isolation_points, not in resolved_equipment
        self.assertIn("ISO-T302-01", result.isolation_points)
        self.assertNotIn("ISO-T302-01", result.resolved_equipment)
        self.assertNotIn("ISO-T302-01", result.unresolved_equipment)

    def test_isolation_points_not_affected_by_equipment_resolution(self) -> None:
        ptw = {
            "permit_id": "TEST-11",
            "equipment_tags": ["T-302"],
            "isolation_points": ["ISO-T302-01"],
        }
        result = TagResolver().resolve(ptw, _graph("conflict"))
        self.assertIn("T-302", result.resolved_equipment)
        self.assertEqual(result.isolation_points, ["ISO-T302-01"])


# ---------------------------------------------------------------------------
# 12. Multiple isolation identifiers are preserved
# ---------------------------------------------------------------------------
class MultipleIsolationTest(unittest.TestCase):
    def test_multiple_isolation_points_preserved(self) -> None:
        ptw = {
            "permit_id": "TEST-12",
            "equipment_tags": [],
            "isolation_points": ["ISO-T302-01", "ISO-LF204-01", "ISO-V101-01"],
        }
        result = TagResolver().resolve(ptw, _graph("conflict"))
        self.assertEqual(
            result.isolation_points,
            ["ISO-T302-01", "ISO-LF204-01", "ISO-V101-01"],
        )


# ---------------------------------------------------------------------------
# 13. Duplicate isolation identifiers deduplicate in first-seen order
# ---------------------------------------------------------------------------
class DuplicateIsolationTest(unittest.TestCase):
    def test_duplicate_isolations_deduplicated(self) -> None:
        ptw = {
            "permit_id": "TEST-13",
            "equipment_tags": [],
            "isolation_points": [
                "ISO-A-01",
                "ISO-B-01",
                "ISO-A-01",
                "ISO-A-01",
                "ISO-B-01",
            ],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(
            result.isolation_points, ["ISO-A-01", "ISO-B-01"]
        )


# ---------------------------------------------------------------------------
# 14. Empty isolation_points
# ---------------------------------------------------------------------------
class EmptyIsolationTest(unittest.TestCase):
    def test_empty_isolation_list(self) -> None:
        ptw = {
            "permit_id": "TEST-14",
            "equipment_tags": ["T-410"],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("ambiguous"))
        self.assertEqual(result.isolation_points, [])


# ---------------------------------------------------------------------------
# 15. None isolation_points if currently supported
# ---------------------------------------------------------------------------
class NoneIsolationTest(unittest.TestCase):
    def test_none_isolation_defaults_to_empty(self) -> None:
        ptw = {
            "permit_id": "TEST-15",
            "equipment_tags": ["T-410"],
            "isolation_points": None,
        }
        result = TagResolver().resolve(ptw, _graph("ambiguous"))
        self.assertEqual(result.isolation_points, [])


# ---------------------------------------------------------------------------
# 16. Resolver does not mutate the graph
# ---------------------------------------------------------------------------
class NoGraphMutationTest(unittest.TestCase):
    def test_graph_unchanged_after_resolve(self) -> None:
        graph = _graph("safe")
        node_ids_before = list(graph.node_ids)
        edges_before = len(graph.edges)

        ptw = {
            "permit_id": "TEST-16",
            "equipment_tags": ["CW-101", "NEW-FAKE"],
            "isolation_points": ["ISO-NEW-01"],
        }
        TagResolver().resolve(ptw, graph)

        self.assertEqual(graph.node_ids, node_ids_before)
        self.assertEqual(len(graph.edges), edges_before)
        self.assertFalse(graph.has_node("NEW-FAKE"))
        self.assertFalse(graph.has_node("ISO-NEW-01"))

    def test_nx_graph_internals_unchanged(self) -> None:
        graph = _graph("conflict")
        nx_before = dict(graph.nx_graph.nodes(data=True))
        edges_before = graph.nx_graph.number_of_edges()

        ptw = _ptw("conflict")
        TagResolver().resolve(ptw, graph)

        self.assertEqual(dict(graph.nx_graph.nodes(data=True)), nx_before)
        self.assertEqual(graph.nx_graph.number_of_edges(), edges_before)


# ---------------------------------------------------------------------------
# 17. Multiple executions produce identical results
# ---------------------------------------------------------------------------
class DeterministicResolutionTest(unittest.TestCase):
    def test_same_inputs_same_output(self) -> None:
        resolver = TagResolver()
        graph = _graph("safe")
        ptw = _ptw("safe")

        r1 = resolver.resolve(ptw, graph)
        r2 = resolver.resolve(ptw, graph)
        r3 = resolver.resolve(ptw, graph)

        self.assertEqual(r1, r2)
        self.assertEqual(r2, r3)

    def test_conflict_deterministic(self) -> None:
        resolver = TagResolver()
        graph = _graph("conflict")
        ptw = _ptw("conflict")

        r1 = resolver.resolve(ptw, graph)
        r2 = resolver.resolve(ptw, graph)

        self.assertEqual(r1.to_dict(), r2.to_dict())

    def test_ambiguous_deterministic(self) -> None:
        resolver = TagResolver()
        graph = _graph("ambiguous")
        ptw = _ptw("ambiguous")

        r1 = resolver.resolve(ptw, graph)
        r2 = resolver.resolve(ptw, graph)

        self.assertEqual(r1, r2)

    def test_disagreement_deterministic(self) -> None:
        resolver = TagResolver()
        graph = _graph("disagreement")
        ptw = _ptw("disagreement")

        r1 = resolver.resolve(ptw, graph)
        r2 = resolver.resolve(ptw, graph)

        self.assertEqual(r1, r2)


# ---------------------------------------------------------------------------
# 18. permit_id propagates correctly
# ---------------------------------------------------------------------------
class PermitIdPropagationTest(unittest.TestCase):
    def test_permit_id_captured_from_ptw(self) -> None:
        result = _resolve("safe")
        self.assertEqual(result.permit_id, "MR-0001-SAFE")

    def test_permit_id_from_custom_ptw(self) -> None:
        ptw = {
            "permit_id": "CUSTOM-PERMIT-001",
            "equipment_tags": [],
            "isolation_points": [],
        }
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.permit_id, "CUSTOM-PERMIT-001")

    def test_permit_id_empty_string_default(self) -> None:
        ptw: Dict[str, Any] = {}
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.permit_id, "")


# ---------------------------------------------------------------------------
# 19. Bad PTW input handling
# ---------------------------------------------------------------------------
class BadInputPtwTest(unittest.TestCase):
    def test_type_error_on_string_ptw(self) -> None:
        with self.assertRaises(TypeError):
            TagResolver().resolve("not-a-dict", _graph("safe"))  # type: ignore[arg-type]

    def test_type_error_on_list_ptw(self) -> None:
        with self.assertRaises(TypeError):
            TagResolver().resolve([], _graph("safe"))  # type: ignore[arg-type]

    def test_type_error_on_none_ptw(self) -> None:
        with self.assertRaises(TypeError):
            TagResolver().resolve(None, _graph("safe"))  # type: ignore[arg-type]

    def test_missing_keys_still_works(self) -> None:
        ptw: Dict[str, Any] = {"permit_id": "X"}
        result = TagResolver().resolve(ptw, _graph("safe"))
        self.assertEqual(result.permit_id, "X")
        self.assertEqual(result.resolved_equipment, [])
        self.assertEqual(result.unresolved_equipment, [])
        self.assertEqual(result.isolation_points, [])


# ---------------------------------------------------------------------------
# 20. Bad graph input handling
# ---------------------------------------------------------------------------
class BadInputGraphTest(unittest.TestCase):
    def test_type_error_on_string_graph(self) -> None:
        ptw = _ptw("safe")
        with self.assertRaises(TypeError):
            TagResolver().resolve(ptw, "not-a-graph")  # type: ignore[arg-type]

    def test_type_error_on_none_graph(self) -> None:
        ptw = _ptw("safe")
        with self.assertRaises(TypeError):
            TagResolver().resolve(ptw, None)  # type: ignore[arg-type]

    def test_type_error_on_dict_graph(self) -> None:
        ptw = _ptw("safe")
        with self.assertRaises(TypeError):
            TagResolver().resolve(ptw, {"nx_graph": None})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Result API tests
# ---------------------------------------------------------------------------
class ResultApiTest(unittest.TestCase):
    def test_to_dict_roundtrip(self) -> None:
        result = _resolve("safe")
        d = result.to_dict()
        self.assertEqual(d["permit_id"], "MR-0001-SAFE")
        self.assertIsInstance(d["resolved_equipment"], list)
        self.assertIsInstance(d["unresolved_equipment"], list)
        self.assertIsInstance(d["isolation_points"], list)

    def test_repr_contains_fields(self) -> None:
        result = _resolve("safe")
        r = repr(result)
        self.assertIn("MR-0001-SAFE", r)
        self.assertIn("resolved_equipment", r)
        self.assertIn("unresolved_equipment", r)
        self.assertIn("isolation_points", r)

    def test_equality(self) -> None:
        r1 = _resolve("safe")
        r2 = _resolve("safe")
        self.assertEqual(r1, r2)

    def test_inequality_different_data(self) -> None:
        r1 = _resolve("safe")
        r2 = _resolve("conflict")
        self.assertNotEqual(r1, r2)

    def test_inequality_different_type(self) -> None:
        result = _resolve("safe")
        self.assertNotEqual(result, "not-a-result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
