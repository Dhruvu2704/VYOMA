"""Undirected plant connectivity graph built from StructuredPID data.

Graph semantics
---------------
This module represents **undirected plant connectivity only**.

The VYOMA repository does not define directional plant-flow semantics.
The ``source`` / ``target`` field names in ``PIDConnection`` are not
interpreted as process-flow direction.  The graph answers:

    "Which equipment is connected to this equipment?"

It does NOT answer:

    "Which equipment is upstream / downstream?"

All edges are stored and traversed as undirected adjacency.

Internally the graph is a ``networkx.Graph`` (undirected).  Public access
goes through the ``PlantGraph`` API; callers need not touch NetworkX
directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import networkx as nx

from shared.contracts import StructuredPID


# ---------------------------------------------------------------------------
# Error handling — follows repository convention: {Module}Error(Exception)
# ---------------------------------------------------------------------------


class TopologyError(Exception):
    """Raised when a StructuredPID cannot be converted to a valid graph."""


# ---------------------------------------------------------------------------
# Public graph abstraction
# ---------------------------------------------------------------------------


class PlantGraph:
    """Undirected plant connectivity graph backed by ``networkx.Graph``.

    Nodes represent P&ID symbols (equipment).  Edges represent physical
    connections between equipment, derived from ``StructuredPID.connections``.

    The graph is **immutable after construction** — there are no mutation
    methods.
    """

    def __init__(self) -> None:
        self._graph: nx.Graph = nx.Graph()

    # -- factory -----------------------------------------------------------

    @classmethod
    def from_structured_pid(cls, pid: StructuredPID) -> "PlantGraph":
        """Build a PlantGraph from a StructuredPID-compatible dict.

        Raises ``TopologyError`` on any structural inconsistency.
        """
        if not isinstance(pid, dict):
            raise TopologyError("pid must be a dict-like StructuredPID")

        graph = cls()

        # -- validate and add symbols as nodes --
        raw_symbols = pid.get("symbols")
        if not isinstance(raw_symbols, list):
            raise TopologyError("pid.symbols must be a list")
        for sym in raw_symbols:
            if not isinstance(sym, dict):
                raise TopologyError("each symbol must be a dict")
            for key in ("symbol_id", "symbol_type", "connections"):
                if key not in sym:
                    raise TopologyError(f"symbol missing required key: {key}")
            symbol_id = sym["symbol_id"]
            if graph._graph.has_node(symbol_id):
                raise TopologyError(f"duplicate symbol_id: {symbol_id!r}")
            graph._graph.add_node(
                symbol_id,
                symbol_type=sym["symbol_type"],
                properties=sym.get("properties", {}),
            )

        # -- validate and add top-level connections as undirected edges --
        raw_connections = pid.get("connections")
        if not isinstance(raw_connections, list):
            raise TopologyError("pid.connections must be a list")
        seen_edges: Dict[tuple[str, str], Optional[str]] = {}
        for conn in raw_connections:
            if not isinstance(conn, dict):
                raise TopologyError("each connection must be a dict")
            for key in ("source", "target"):
                if key not in conn:
                    raise TopologyError(
                        f"connection missing required key: {key}"
                    )
            src, tgt = conn["source"], conn["target"]
            if not graph._graph.has_node(src):
                raise TopologyError(
                    f"connection references unknown symbol: {src!r}"
                )
            if not graph._graph.has_node(tgt):
                raise TopologyError(
                    f"connection references unknown symbol: {tgt!r}"
                )

            edge_key = tuple(sorted((src, tgt)))
            new_line_ref = conn.get("line_ref")
            if edge_key in seen_edges:
                existing = seen_edges[edge_key]
                if existing is not None and new_line_ref is not None:
                    if existing != new_line_ref:
                        raise TopologyError(
                            f"conflicting line_ref for edge "
                            f"{edge_key[0]!r}<->{edge_key[1]!r}: "
                            f"{existing!r} vs {new_line_ref!r}"
                        )
                # deterministic: prefer the non-null value
                if existing is None and new_line_ref is not None:
                    seen_edges[edge_key] = new_line_ref
            else:
                seen_edges[edge_key] = new_line_ref
                graph._graph.add_edge(src, tgt, line_ref=new_line_ref)

        # -- set the stored line_ref to the resolved value --
        for (a, b), line_ref in seen_edges.items():
            graph._graph[a][b]["line_ref"] = line_ref

        # -- validate symbol.connections against top-level connections --
        graph._validate_symbol_connections(raw_symbols)

        return graph

    # -- public query API --------------------------------------------------

    def has_node(self, symbol_id: str) -> bool:
        """Return True if *symbol_id* exists as a graph node."""
        return self._graph.has_node(symbol_id)

    def get_node(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        """Return node metadata or None if not found.

        Returns ``{"symbol_id": ..., "symbol_type": ..., "properties": ...}``.
        """
        if not self._graph.has_node(symbol_id):
            return None
        data = self._graph.nodes[symbol_id]
        return {
            "symbol_id": symbol_id,
            "symbol_type": data["symbol_type"],
            "properties": dict(data["properties"]),
        }

    def get_neighbors(self, symbol_id: str) -> List[str]:
        """Return sorted list of symbol_ids directly connected to *symbol_id*.

        Raises ``TopologyError`` if *symbol_id* is not in the graph.
        """
        if not self._graph.has_node(symbol_id):
            raise TopologyError(f"unknown symbol: {symbol_id!r}")
        return sorted(self._graph.neighbors(symbol_id))

    def get_edge(
        self, node_a: str, node_b: str
    ) -> Optional[Dict[str, Any]]:
        """Return edge metadata between *node_a* and *node_b*, or None.

        Returns ``{"endpoints": frozenset, "line_ref": ...}``.
        """
        if not self._graph.has_edge(node_a, node_b):
            return None
        line_ref = self._graph[node_a][node_b].get("line_ref")
        return {
            "endpoints": frozenset((node_a, node_b)),
            "line_ref": line_ref,
        }

    @property
    def nodes(self) -> Dict[str, Dict[str, Any]]:
        """All nodes as ``{symbol_id: {symbol_id, symbol_type, properties}}``."""
        result: Dict[str, Dict[str, Any]] = {}
        for nid, data in self._graph.nodes(data=True):
            result[nid] = {
                "symbol_id": nid,
                "symbol_type": data["symbol_type"],
                "properties": dict(data["properties"]),
            }
        return result

    @property
    def edges(self) -> List[Dict[str, Any]]:
        """All edges as a list of ``{"endpoints": frozenset, "line_ref": ...}``."""
        result: List[Dict[str, Any]] = []
        for u, v, data in self._graph.edges(data=True):
            result.append(
                {
                    "endpoints": frozenset((u, v)),
                    "line_ref": data.get("line_ref"),
                }
            )
        return result

    @property
    def node_ids(self) -> List[str]:
        """Sorted list of all node symbol_ids."""
        return sorted(self._graph.nodes)

    @property
    def nx_graph(self) -> nx.Graph:
        """The underlying ``networkx.Graph`` (read-only access for Role 3)."""
        return self._graph

    # -- private helpers ---------------------------------------------------

    def _validate_symbol_connections(
        self, raw_symbols: List[Dict[str, Any]]
    ) -> None:
        """Detect disagreements between symbol.connections and top-level edges."""
        declared_edge_keys: Set[frozenset] = set()
        for symbol in raw_symbols:
            symbol_id = symbol["symbol_id"]
            for neighbor in symbol.get("connections", []):
                declared_edge_keys.add(frozenset((symbol_id, neighbor)))

        top_level_edge_keys: Set[frozenset] = set()
        for u, v in self._graph.edges():
            top_level_edge_keys.add(frozenset((u, v)))

        missing_from_top_level = declared_edge_keys - top_level_edge_keys
        if missing_from_top_level:
            pairs = [sorted(pair) for pair in missing_from_top_level]
            raise TopologyError(
                "symbol.connections declares edges not present in "
                f"top-level connections: {pairs}"
            )

        extra_in_top_level = top_level_edge_keys - declared_edge_keys
        if extra_in_top_level:
            pairs = [sorted(pair) for pair in extra_in_top_level]
            raise TopologyError(
                "top-level connections declares edges not present in "
                f"any symbol.connections: {pairs}"
            )
