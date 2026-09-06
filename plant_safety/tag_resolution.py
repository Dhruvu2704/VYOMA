"""Deterministic tag resolution against a PlantGraph.

Resolves PTW **equipment tags** against the node IDs that exist in a
:class:`~plant_safety.topology.PlantGraph`.

**Isolation points** (e.g. ``ISO-T302-01``) are preserved as-is — they
are *not* graph-resolved because they are not graph node identifiers.

Resolution is **exact-match only** — no fuzzy matching, no LLM, no
embeddings, no external lookups.  The same inputs always produce the same
output.

This module does **not** mutate the graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plant_safety.topology import PlantGraph


# ---------------------------------------------------------------------------
# Result type — local to Role 3; not yet in shared/contracts.py
# ---------------------------------------------------------------------------


class TagResolutionResult:
    """Outcome of resolving PTW tags against a plant graph.

    Equipment tags are partitioned into *resolved* (matching a graph node)
    and *unresolved* (no matching node).  Isolation points are **passed
    through verbatim** — they are not graph-resolved because isolation
    identifiers (e.g. ``ISO-T302-01``) are not graph node IDs.

    All lists are deduplicated while preserving **first-seen order** from
    the input.  Duplicate tags in the input are collapsed silently — only
    the first occurrence counts.

    Attributes:
        permit_id: The permit being resolved.
        resolved_equipment: Equipment tags that exactly match a graph node.
        unresolved_equipment: Equipment tags with no matching graph node.
        isolation_points: Isolation-point identifiers passed through from
            the PTW without graph resolution (preserved in first-seen order,
            deduplicated).
    """

    __slots__ = (
        "permit_id",
        "resolved_equipment",
        "unresolved_equipment",
        "isolation_points",
    )

    def __init__(
        self,
        *,
        permit_id: str,
        resolved_equipment: List[str],
        unresolved_equipment: List[str],
        isolation_points: List[str],
    ) -> None:
        self.permit_id = permit_id
        self.resolved_equipment = resolved_equipment
        self.unresolved_equipment = unresolved_equipment
        self.isolation_points = isolation_points

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict view (handy for tests and downstream layers)."""
        return {
            "permit_id": self.permit_id,
            "resolved_equipment": list(self.resolved_equipment),
            "unresolved_equipment": list(self.unresolved_equipment),
            "isolation_points": list(self.isolation_points),
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TagResolutionResult):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return (
            f"TagResolutionResult(permit_id={self.permit_id!r}, "
            f"resolved_equipment={self.resolved_equipment!r}, "
            f"unresolved_equipment={self.unresolved_equipment!r}, "
            f"isolation_points={self.isolation_points!r})"
        )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


class TagResolver:
    """Resolves PTW equipment tags against a PlantGraph via exact node-ID
    matching.

    Usage::

        resolver = TagResolver()
        result = resolver.resolve(ptw, graph)

    The resolver does **not** mutate the graph.
    """

    def resolve(
        self,
        ptw: Dict[str, Any],
        graph: PlantGraph,
    ) -> TagResolutionResult:
        """Resolve equipment tags from *ptw* against *graph*.

        Isolation points are preserved as-is without graph lookup.

        Args:
            ptw: A StructuredPTW-compatible dict (must contain ``permit_id``,
                ``equipment_tags``, and ``isolation_points``).
            graph: The plant graph to resolve against.

        Returns:
            A :class:`TagResolutionResult` with resolved/unresolved equipment
            and pass-through isolation points.

        Raises:
            TypeError: if *ptw* is not a dict or *graph* is not a PlantGraph.
        """
        if not isinstance(ptw, dict):
            raise TypeError("ptw must be a dict")
        if not isinstance(graph, PlantGraph):
            raise TypeError("graph must be a PlantGraph")

        permit_id = ptw.get("permit_id", "")
        raw_equipment = ptw.get("equipment_tags") or []
        raw_isolations = ptw.get("isolation_points") or []

        resolved_eq, unresolved_eq = _partition_tags(raw_equipment, graph)
        isolation_points = _deduplicate_preserve_order(raw_isolations)

        return TagResolutionResult(
            permit_id=permit_id,
            resolved_equipment=resolved_eq,
            unresolved_equipment=unresolved_eq,
            isolation_points=isolation_points,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _partition_tags(
    tags: List[str],
    graph: PlantGraph,
) -> tuple[List[str], List[str]]:
    """Partition *tags* into (resolved, unresolved), preserving order.

    Duplicate tags are deduplicated — only the first occurrence is
    considered.  This is deterministic: same input list always yields
    the same partition.
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


def _deduplicate_preserve_order(items: List[str]) -> List[str]:
    """Deduplicate *items* while preserving first-seen order."""
    seen: set = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
