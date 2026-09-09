"""Unit tests for the plant_safety.topology graph foundation.

Uses the actual repository fixtures in ai_agent/fixtures/.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict

import networkx as nx

from plant_safety.topology import PlantGraph, TopologyError

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


# =========================================================================
# NetworkX implementation verification tests
# =========================================================================


class NetworkXInternalGraphTest(unittest.TestCase):
    """1. PlantGraph internally contains an nx.Graph."""

    def test_internal_graph_is_networkx(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertIsInstance(graph.nx_graph, nx.Graph)

    def test_nx_graph_accessible(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        nxg = graph.nx_graph
        self.assertTrue(nxg.has_node("LF-204"))


class NetworkXNotDiGraphTest(unittest.TestCase):
    """2. The graph is not an nx.DiGraph."""

    def test_not_digraph(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertNotIsInstance(graph.nx_graph, nx.DiGraph)

    def test_not_multigraph(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertNotIsInstance(graph.nx_graph, nx.MultiGraph)


class NetworkXNodesExistTest(unittest.TestCase):
    """3. Expected nodes exist in the NetworkX graph."""

    def test_safe_nodes_in_nx(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("safe")).nx_graph
        for tag in ("P-101", "CW-101", "G-101"):
            self.assertTrue(nxg.has_node(tag), tag)

    def test_conflict_nodes_in_nx(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("conflict")).nx_graph
        for tag in ("LF-204", "T-302", "V-101"):
            self.assertTrue(nxg.has_node(tag), tag)

    def test_ambiguous_nodes_in_nx(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("ambiguous")).nx_graph
        self.assertTrue(nxg.has_node("T-410"))

    def test_disagreement_nodes_in_nx(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("disagreement")).nx_graph
        for tag in ("LF-501", "P-201"):
            self.assertTrue(nxg.has_node(tag), tag)


class NetworkXNodeAttributesTest(unittest.TestCase):
    """4. Expected node attributes are present in the NetworkX graph."""

    def test_safe_node_attributes(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("safe")).nx_graph
        self.assertEqual(nxg.nodes["P-101"]["symbol_type"], "PUMP")
        self.assertEqual(
            nxg.nodes["P-101"]["properties"]["service"], "cooling-water-return"
        )
        self.assertEqual(nxg.nodes["CW-101"]["symbol_type"], "LINE")
        self.assertEqual(nxg.nodes["G-101"]["symbol_type"], "INSTRUMENT")

    def test_conflict_node_attributes(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("conflict")).nx_graph
        self.assertEqual(
            nxg.nodes["T-302"]["symbol_type"], "STORAGE_TANK"
        )
        self.assertEqual(nxg.nodes["V-101"]["symbol_type"], "VALVE")


class NetworkXEdgesExistTest(unittest.TestCase):
    """5. Expected undirected edges exist in the NetworkX graph."""

    def test_safe_edges_undirected(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("safe")).nx_graph
        self.assertTrue(nxg.has_edge("P-101", "CW-101"))
        self.assertTrue(nxg.has_edge("CW-101", "G-101"))
        self.assertFalse(nxg.has_edge("P-101", "G-101"))

    def test_conflict_edges_undirected(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("conflict")).nx_graph
        self.assertTrue(nxg.has_edge("LF-204", "T-302"))
        self.assertTrue(nxg.has_edge("T-302", "V-101"))
        self.assertFalse(nxg.has_edge("LF-204", "V-101"))

    def test_ambiguous_no_edges(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("ambiguous")).nx_graph
        self.assertEqual(nxg.number_of_edges(), 0)


class NetworkXLineRefAttributeTest(unittest.TestCase):
    """6. line_ref is preserved as a NetworkX edge attribute."""

    def test_safe_line_ref_on_nx_edges(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("safe")).nx_graph
        self.assertEqual(nxg["P-101"]["CW-101"]["line_ref"], "CW-101")
        self.assertEqual(nxg["CW-101"]["G-101"]["line_ref"], "CW-101")

    def test_conflict_line_ref_on_nx_edges(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("conflict")).nx_graph
        self.assertEqual(nxg["LF-204"]["T-302"]["line_ref"], "LF-204")
        self.assertEqual(nxg["T-302"]["V-101"]["line_ref"], "V-101")

    def test_disagreement_line_ref_on_nx_edge(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("disagreement")).nx_graph
        self.assertEqual(nxg["LF-501"]["P-201"]["line_ref"], "LF-501")


class NetworkXUndirectedLookupTest(unittest.TestCase):
    """7. Reverse lookup A-B and B-A refers to the same undirected edge."""

    def test_safe_symmetric_lookup(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        ab = graph.get_edge("P-101", "CW-101")
        ba = graph.get_edge("CW-101", "P-101")
        self.assertIsNotNone(ab)
        self.assertIsNotNone(ba)
        self.assertEqual(ab["endpoints"], ba["endpoints"])
        self.assertEqual(ab["line_ref"], ba["line_ref"])

    def test_nx_symmetric_lookup(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("safe")).nx_graph
        self.assertTrue(nxg.has_edge("P-101", "CW-101"))
        self.assertTrue(nxg.has_edge("CW-101", "P-101"))
        self.assertEqual(
            nxg["P-101"]["CW-101"]["line_ref"],
            nxg["CW-101"]["P-101"]["line_ref"],
        )

    def test_conflict_symmetric_lookup(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        self.assertEqual(
            graph.get_edge("T-302", "V-101"),
            graph.get_edge("V-101", "T-302"),
        )


class NetworkXDuplicatesTest(unittest.TestCase):
    """8. Duplicate logical edges produce one NetworkX edge."""

    def test_duplicate_edges_collapsed_in_nx(self) -> None:
        pid = {
            "pid_id": "PID-DUP",
            "source": "mock",
            "equipment_tags": ["X", "Y"],
            "symbols": [
                {
                    "symbol_id": "X",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["Y", "Y"],
                },
                {
                    "symbol_id": "Y",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["X"],
                },
            ],
            "connections": [
                {"source": "X", "target": "Y", "line_ref": "L1"},
                {"source": "X", "target": "Y", "line_ref": "L1"},
                {"source": "Y", "target": "X", "line_ref": "L1"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        graph = PlantGraph.from_structured_pid(pid)
        nxg = graph.nx_graph
        self.assertEqual(nxg.number_of_edges(), 1)
        self.assertTrue(nxg.has_edge("X", "Y"))
        self.assertEqual(nxg["X"]["Y"]["line_ref"], "L1")

    def test_single_logical_edge_from_public_api(self) -> None:
        pid = {
            "pid_id": "PID-DUP2",
            "source": "mock",
            "equipment_tags": ["A", "B"],
            "symbols": [
                {
                    "symbol_id": "A",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["B"],
                },
                {
                    "symbol_id": "B",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["A"],
                },
            ],
            "connections": [
                {"source": "A", "target": "B", "line_ref": "L1"},
                {"source": "B", "target": "A", "line_ref": "L1"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        graph = PlantGraph.from_structured_pid(pid)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(len(graph.get_neighbors("A")), 1)


class ConflictingDuplicateLineRefTest(unittest.TestCase):
    """9. Conflicting duplicate line_ref values are detected."""

    def test_different_line_ref_raises(self) -> None:
        pid = {
            "pid_id": "PID-CONFLICT-LR",
            "source": "mock",
            "equipment_tags": ["X", "Y"],
            "symbols": [
                {
                    "symbol_id": "X",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["Y"],
                },
                {
                    "symbol_id": "Y",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["X"],
                },
            ],
            "connections": [
                {"source": "X", "target": "Y", "line_ref": "L1"},
                {"source": "X", "target": "Y", "line_ref": "L2"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError) as ctx:
            PlantGraph.from_structured_pid(pid)
        self.assertIn("conflicting line_ref", str(ctx.exception))

    def test_same_line_ref_accepted(self) -> None:
        pid = {
            "pid_id": "PID-SAME-LR",
            "source": "mock",
            "equipment_tags": ["X", "Y"],
            "symbols": [
                {
                    "symbol_id": "X",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["Y"],
                },
                {
                    "symbol_id": "Y",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["X"],
                },
            ],
            "connections": [
                {"source": "X", "target": "Y", "line_ref": "L1"},
                {"source": "X", "target": "Y", "line_ref": "L1"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        graph = PlantGraph.from_structured_pid(pid)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.get_edge("X", "Y")["line_ref"], "L1")

    def test_null_plus_populated_prefers_populated(self) -> None:
        pid = {
            "pid_id": "PID-NULL-LR",
            "source": "mock",
            "equipment_tags": ["X", "Y"],
            "symbols": [
                {
                    "symbol_id": "X",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["Y"],
                },
                {
                    "symbol_id": "Y",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["X"],
                },
            ],
            "connections": [
                {"source": "X", "target": "Y", "line_ref": None},
                {"source": "X", "target": "Y", "line_ref": "L1"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        graph = PlantGraph.from_structured_pid(pid)
        self.assertEqual(graph.get_edge("X", "Y")["line_ref"], "L1")


# =========================================================================
# Original test suite (unchanged, renumbered categories 10-23)
# =========================================================================


# 10. safe_case graph nodes
class SafeCaseGraphNodesTest(unittest.TestCase):
    def test_expected_nodes_present(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertEqual(
            sorted(graph.node_ids), ["CW-101", "G-101", "P-101"]
        )

    def test_all_three_nodes_exist(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        for tag in ("P-101", "CW-101", "G-101"):
            self.assertTrue(graph.has_node(tag), tag)


# 11. conflict_case graph nodes
class ConflictCaseGraphNodesTest(unittest.TestCase):
    def test_expected_nodes_present(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        self.assertEqual(
            sorted(graph.node_ids), ["LF-204", "T-302", "V-101"]
        )


# 12. ambiguous_case graph — node and empty edges
class AmbiguousCaseGraphTest(unittest.TestCase):
    def test_single_node(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("ambiguous"))
        self.assertEqual(graph.node_ids, ["T-410"])

    def test_no_edges(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("ambiguous"))
        self.assertEqual(graph.edges, [])


# 13. disagreement_case graph nodes
class DisagreementCaseGraphNodesTest(unittest.TestCase):
    def test_expected_nodes_present(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("disagreement"))
        self.assertEqual(sorted(graph.node_ids), ["LF-501", "P-201"])


# 14. Expected connectivity for every fixture
class ConnectivityTest(unittest.TestCase):
    def test_safe_connectivity(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertEqual(graph.get_neighbors("P-101"), ["CW-101"])
        self.assertEqual(graph.get_neighbors("CW-101"), ["G-101", "P-101"])
        self.assertEqual(graph.get_neighbors("G-101"), ["CW-101"])

    def test_conflict_connectivity(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        self.assertEqual(graph.get_neighbors("LF-204"), ["T-302"])
        self.assertEqual(graph.get_neighbors("T-302"), ["LF-204", "V-101"])
        self.assertEqual(graph.get_neighbors("V-101"), ["T-302"])

    def test_ambiguous_connectivity(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("ambiguous"))
        self.assertEqual(graph.get_neighbors("T-410"), [])

    def test_disagreement_connectivity(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("disagreement"))
        self.assertEqual(graph.get_neighbors("LF-501"), ["P-201"])
        self.assertEqual(graph.get_neighbors("P-201"), ["LF-501"])


# 15. symbol_type preservation
class SymbolTypePreservationTest(unittest.TestCase):
    def test_safe_symbol_types(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertEqual(graph.get_node("P-101")["symbol_type"], "PUMP")
        self.assertEqual(graph.get_node("CW-101")["symbol_type"], "LINE")
        self.assertEqual(
            graph.get_node("G-101")["symbol_type"], "INSTRUMENT"
        )

    def test_conflict_symbol_types(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        self.assertEqual(
            graph.get_node("LF-204")["symbol_type"], "LINE"
        )
        self.assertEqual(
            graph.get_node("T-302")["symbol_type"], "STORAGE_TANK"
        )
        self.assertEqual(graph.get_node("V-101")["symbol_type"], "VALVE")

    def test_ambiguous_symbol_type(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("ambiguous"))
        self.assertEqual(
            graph.get_node("T-410")["symbol_type"], "STORAGE_TANK"
        )

    def test_disagreement_symbol_types(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("disagreement"))
        self.assertEqual(graph.get_node("LF-501")["symbol_type"], "LINE")
        self.assertEqual(graph.get_node("P-201")["symbol_type"], "PUMP")


# 16. properties preservation
class PropertiesPreservationTest(unittest.TestCase):
    def test_safe_pump_properties(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        props = graph.get_node("P-101")["properties"]
        self.assertEqual(props["service"], "cooling-water-return")
        self.assertTrue(props["tag_resolved"])

    def test_safe_instrument_properties(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        props = graph.get_node("G-101")["properties"]
        self.assertEqual(props["measurand"], "pressure")
        self.assertTrue(props["tag_resolved"])

    def test_conflict_tank_properties(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        props = graph.get_node("T-302")["properties"]
        self.assertEqual(props["service"], "solvent")
        self.assertTrue(props["tag_resolved"])

    def test_ambiguous_tank_properties(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("ambiguous"))
        props = graph.get_node("T-410")["properties"]
        self.assertEqual(props["service"], "storage")
        self.assertTrue(props["tag_resolved"])

    def test_disagreement_pump_properties(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("disagreement"))
        props = graph.get_node("P-201")["properties"]
        self.assertEqual(props["service"], "process")
        self.assertTrue(props["tag_resolved"])


# 17. line_ref preservation
class LineRefPreservationTest(unittest.TestCase):
    def test_safe_line_refs(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        edge_p_cw = graph.get_edge("P-101", "CW-101")
        self.assertIsNotNone(edge_p_cw)
        self.assertEqual(edge_p_cw["line_ref"], "CW-101")

        edge_cw_g = graph.get_edge("CW-101", "G-101")
        self.assertIsNotNone(edge_cw_g)
        self.assertEqual(edge_cw_g["line_ref"], "CW-101")

    def test_conflict_line_refs(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("conflict"))
        edge_lf_t = graph.get_edge("LF-204", "T-302")
        self.assertIsNotNone(edge_lf_t)
        self.assertEqual(edge_lf_t["line_ref"], "LF-204")

        edge_t_v = graph.get_edge("T-302", "V-101")
        self.assertIsNotNone(edge_t_v)
        self.assertEqual(edge_t_v["line_ref"], "V-101")

    def test_disagreement_line_ref(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("disagreement"))
        edge = graph.get_edge("LF-501", "P-201")
        self.assertIsNotNone(edge)
        self.assertEqual(edge["line_ref"], "LF-501")


# 18. unknown source/target reference is detected
class UnknownReferenceTest(unittest.TestCase):
    def test_unknown_source_in_connection(self) -> None:
        pid = {
            "pid_id": "PID-X",
            "source": "mock",
            "equipment_tags": ["A"],
            "symbols": [
                {
                    "symbol_id": "A",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": [],
                }
            ],
            "connections": [
                {"source": "A", "target": "MISSING", "line_ref": "L1"}
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError) as ctx:
            PlantGraph.from_structured_pid(pid)
        self.assertIn("MISSING", str(ctx.exception))

    def test_unknown_target_in_connection(self) -> None:
        pid = {
            "pid_id": "PID-X",
            "source": "mock",
            "equipment_tags": ["B"],
            "symbols": [
                {
                    "symbol_id": "B",
                    "symbol_type": "VALVE",
                    "properties": {},
                    "connections": [],
                }
            ],
            "connections": [
                {"source": "MISSING", "target": "B", "line_ref": "L1"}
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError) as ctx:
            PlantGraph.from_structured_pid(pid)
        self.assertIn("MISSING", str(ctx.exception))


# 19. duplicate connection does not create duplicate logical edges
class DuplicateConnectionTest(unittest.TestCase):
    def test_duplicate_edges_collapsed(self) -> None:
        pid = {
            "pid_id": "PID-DUP",
            "source": "mock",
            "equipment_tags": ["X", "Y"],
            "symbols": [
                {
                    "symbol_id": "X",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["Y", "Y"],
                },
                {
                    "symbol_id": "Y",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["X"],
                },
            ],
            "connections": [
                {"source": "X", "target": "Y", "line_ref": "L1"},
                {"source": "X", "target": "Y", "line_ref": "L1"},
                {"source": "Y", "target": "X", "line_ref": "L1"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        graph = PlantGraph.from_structured_pid(pid)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(len(graph.get_neighbors("X")), 1)
        self.assertEqual(len(graph.get_neighbors("Y")), 1)


# 20. empty StructuredPID produces an empty graph
class EmptyGraphTest(unittest.TestCase):
    def test_empty_symbols_and_connections(self) -> None:
        pid = {
            "pid_id": "PID-EMPTY",
            "source": "mock",
            "equipment_tags": [],
            "symbols": [],
            "connections": [],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        graph = PlantGraph.from_structured_pid(pid)
        self.assertEqual(graph.node_ids, [])
        self.assertEqual(graph.edges, [])
        self.assertIsInstance(graph.nx_graph, nx.Graph)
        self.assertEqual(graph.nx_graph.number_of_nodes(), 0)
        self.assertEqual(graph.nx_graph.number_of_edges(), 0)


# 21. building the same graph twice produces identical results
class DeterministicBuildTest(unittest.TestCase):
    def test_safe_deterministic(self) -> None:
        g1 = PlantGraph.from_structured_pid(_pid("safe"))
        g2 = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertEqual(g1.node_ids, g2.node_ids)
        self.assertEqual(
            [(sorted(e["endpoints"]), e["line_ref"]) for e in g1.edges],
            [(sorted(e["endpoints"]), e["line_ref"]) for e in g2.edges],
        )
        for nid in g1.node_ids:
            self.assertEqual(g1.get_node(nid), g2.get_node(nid))
            self.assertEqual(g1.get_neighbors(nid), g2.get_neighbors(nid))

    def test_conflict_deterministic(self) -> None:
        g1 = PlantGraph.from_structured_pid(_pid("conflict"))
        g2 = PlantGraph.from_structured_pid(_pid("conflict"))
        self.assertEqual(g1.node_ids, g2.node_ids)
        self.assertEqual(len(g1.edges), len(g2.edges))

    def test_ambiguous_deterministic(self) -> None:
        g1 = PlantGraph.from_structured_pid(_pid("ambiguous"))
        g2 = PlantGraph.from_structured_pid(_pid("ambiguous"))
        self.assertEqual(g1.node_ids, g2.node_ids)
        self.assertEqual(g1.edges, g2.edges)

    def test_disagreement_deterministic(self) -> None:
        g1 = PlantGraph.from_structured_pid(_pid("disagreement"))
        g2 = PlantGraph.from_structured_pid(_pid("disagreement"))
        self.assertEqual(g1.node_ids, g2.node_ids)
        self.assertEqual(len(g1.edges), len(g2.edges))


# 22. symbol.connections vs top-level connections inconsistency detected
class InconsistencyDetectionTest(unittest.TestCase):
    def test_symbol_declares_extra_neighbor(self) -> None:
        pid = {
            "pid_id": "PID-INC1",
            "source": "mock",
            "equipment_tags": ["A", "B"],
            "symbols": [
                {
                    "symbol_id": "A",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["B", "C"],
                },
                {
                    "symbol_id": "B",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["A"],
                },
            ],
            "connections": [
                {"source": "A", "target": "B", "line_ref": "L1"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError) as ctx:
            PlantGraph.from_structured_pid(pid)
        self.assertIn("symbol.connections", str(ctx.exception))

    def test_top_level_declares_extra_edge(self) -> None:
        pid = {
            "pid_id": "PID-INC2",
            "source": "mock",
            "equipment_tags": ["A", "B", "C"],
            "symbols": [
                {
                    "symbol_id": "A",
                    "symbol_type": "LINE",
                    "properties": {},
                    "connections": ["B"],
                },
                {
                    "symbol_id": "B",
                    "symbol_type": "PUMP",
                    "properties": {},
                    "connections": ["A"],
                },
                {
                    "symbol_id": "C",
                    "symbol_type": "VALVE",
                    "properties": {},
                    "connections": [],
                },
            ],
            "connections": [
                {"source": "A", "target": "B", "line_ref": "L1"},
                {"source": "B", "target": "C", "line_ref": "L2"},
            ],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError) as ctx:
            PlantGraph.from_structured_pid(pid)
        self.assertIn("top-level connections", str(ctx.exception))


# 23. unresolved_symbols do not become graph nodes
class UnresolvedSymbolsNotNodesTest(unittest.TestCase):
    def test_ambiguous_unresolved_not_in_graph(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("ambiguous"))
        self.assertFalse(graph.has_node("TAG-7X-TEMP"))
        self.assertFalse(graph.has_node("TAG-7X-LEVEL"))
        self.assertIsNone(graph.get_node("TAG-7X-TEMP"))
        self.assertIsNone(graph.get_node("TAG-7X-LEVEL"))

    def test_disagreement_unresolved_not_in_graph(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("disagreement"))
        self.assertFalse(graph.has_node("7X-TEMP-A"))
        self.assertFalse(graph.has_node("7X-LEVEL-A"))

    def test_unresolved_symbols_not_in_safe(self) -> None:
        graph = PlantGraph.from_structured_pid(_pid("safe"))
        self.assertEqual(graph.node_ids, ["CW-101", "G-101", "P-101"])

    def test_unresolved_not_in_nx_graph(self) -> None:
        nxg = PlantGraph.from_structured_pid(_pid("ambiguous")).nx_graph
        self.assertFalse(nxg.has_node("TAG-7X-TEMP"))
        self.assertFalse(nxg.has_node("TAG-7X-LEVEL"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
