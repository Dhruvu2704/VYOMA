"""Deterministic GraphFacts generation from StructuredPTW and PlantGraph.

Pipeline position::

    StructuredPTW + StructuredPID
                ↓
            PlantGraph
                ↓
            TagResolver
                ↓
             GraphFacts

This module consumes a :class:`~shared.contracts.StructuredPTW`-compatible
dict, a resolved :class:`~plant_safety.topology.PlantGraph`, and (optionally)
the :class:`~shared.contracts.StructuredPID` that produced the graph.  It
produces a :class:`~shared.contracts.GraphFacts`-compatible dict.

All inputs are treated as read-only.  The same inputs always produce the
same output.  No LLM, no random, no external calls.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from plant_safety.topology import PlantGraph


class GraphFactsError(Exception):
    """Raised when GraphFacts cannot be built from the given inputs."""


class GraphFactsBuilder:
    """Builds :class:`~shared.contracts.GraphFacts`-compatible dicts.

    Usage::

        facts = GraphFactsBuilder.build(ptw, graph, pid=pid, overlap_check=oc)

    The builder does **not** mutate any input.
    """

    @staticmethod
    def build(
        ptw: Dict[str, Any],
        graph: PlantGraph,
        pid: Optional[Dict[str, Any]] = None,
        overlap_check: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Produce a GraphFacts-compatible dict from *ptw* and *graph*.

        Args:
            ptw: A StructuredPTW-compatible dict (must contain ``permit_id``).
            graph: A PlantGraph to resolve equipment tags against.
            pid: Optional StructuredPID-compatible dict.  When supplied, its
                ``unresolved_symbols`` contribute to ``unresolved_tags``.
            overlap_check: Pre-computed overlap information.  Defaults to
                ``{"overlapping_permits": [], "same_area_active": False}``
                when not provided.  A supplied value is defensively deep-copied
                so the returned facts do not alias the caller's object.

        Returns:
            A dict matching the :class:`~shared.contracts.GraphFacts` shape.

        Raises:
            TypeError: if *ptw* is not a dict or *graph* is not a PlantGraph.
        """
        if not isinstance(ptw, dict):
            raise TypeError("ptw must be a dict")
        if not isinstance(graph, PlantGraph):
            raise TypeError("graph must be a PlantGraph")

        permit_id = ptw.get("permit_id", "")
        raw_equipment = _safe_equipment_tags(ptw)
        raw_isolations = _safe_isolation_points(ptw)

        resolved_nodes, ptw_unresolved = _partition_tags(raw_equipment, graph)
        pid_unresolved = _safe_unresolved_symbols(pid)
        unresolved_tags = _deduplicate_preserve_order(
            ptw_unresolved + pid_unresolved
        )

        connected_equipment = _build_connectivity(resolved_nodes, graph)
        active_isolations = _deduplicate_preserve_order(raw_isolations)

        if overlap_check is not None:
            overlap = copy.deepcopy(overlap_check)
        else:
            overlap = {"overlapping_permits": [], "same_area_active": False}

        return {
            "permit_id": permit_id,
            "resolved_nodes": resolved_nodes,
            "unresolved_tags": unresolved_tags,
            "connected_equipment": connected_equipment,
            "active_isolations": active_isolations,
            "overlap_check": overlap,
        }


# ---------------------------------------------------------------------------
# Helpers — pure functions, no state
# ---------------------------------------------------------------------------


def _safe_equipment_tags(ptw: Dict[str, Any]) -> List[str]:
    """Extract equipment_tags from *ptw*, defaulting to ``[]``."""
    tags = ptw.get("equipment_tags")
    return list(tags) if isinstance(tags, list) else []


def _safe_isolation_points(ptw: Dict[str, Any]) -> List[str]:
    """Extract isolation_points from *ptw*, defaulting to ``[]``."""
    pts = ptw.get("isolation_points")
    return list(pts) if isinstance(pts, list) else []


def _safe_unresolved_symbols(pid: Optional[Dict[str, Any]]) -> List[str]:
    """Extract unresolved_symbols from *pid* (if supplied), defaulting to ``[]``."""
    if not isinstance(pid, dict):
        return []
    syms = pid.get("unresolved_symbols")
    return list(syms) if isinstance(syms, list) else []


def _partition_tags(
    tags: List[str], graph: PlantGraph
) -> tuple[List[str], List[str]]:
    """Partition *tags* into (resolved, unresolved), preserving first-seen order.

    Duplicates are collapsed — only the first occurrence is considered.
    Deterministic: same inputs always produce the same output.
    """
    seen: Dict[str, bool] = {}
    for tag in tags:
        if tag not in seen:
            seen[tag] = graph.has_node(tag)

    resolved: List[str] = []
    unresolved: List[str] = []
    for tag, is_resolved in seen.items():
        if is_resolved:
            resolved.append(tag)
        else:
            unresolved.append(tag)

    return resolved, unresolved


def _build_connectivity(
    resolved_nodes: List[str], graph: PlantGraph
) -> Dict[str, List[str]]:
    """Map **every** resolved node to its sorted graph neighbors.

    Resolved nodes with no neighbors map to an empty list.  Unresolved tags
    are never included as keys — they are not graph nodes.
    """
    result: Dict[str, List[str]] = {}
    for node in resolved_nodes:
        result[node] = graph.get_neighbors(node)
    return result


def _deduplicate_preserve_order(items: List[str]) -> List[str]:
    """Deduplicate *items* while preserving first-seen order."""
    seen: set = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
