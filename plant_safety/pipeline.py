"""End-to-end Role 3 deterministic safety evaluation pipeline.

Chains the existing Role 3 components into a single callable::

    StructuredPTW + StructuredPID
                ↓
    PlantGraph.from_structured_pid(pid)
                ↓
    GraphFactsBuilder.build(ptw, graph, pid=pid, overlap_check=overlap_check)
                ↓
    evaluate(facts, ptw=ptw)
                ↓
            RuleVerdict

All inputs are treated as read-only.  The same inputs always produce
the same output.  No LLM, no randomness, no external calls.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from plant_safety.graph_facts import GraphFactsBuilder
from plant_safety.safety_rules import evaluate
from plant_safety.topology import PlantGraph


def evaluate_permit(
    ptw: Dict[str, Any],
    pid: Dict[str, Any],
    overlap_check: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate deterministic safety rules for a permit against a P&ID.

    This is the single public entry point for the Role 3 deterministic
    pipeline.  It chains graph construction, tag resolution, fact
    building, and rule evaluation into one call.

    Args:
        ptw: A ``StructuredPTW``-compatible dict (must contain at least
            ``permit_id`` and ``equipment_tags``).
        pid: A ``StructuredPID``-compatible dict (must contain ``symbols``
            and ``connections``).
        overlap_check: Optional pre-computed overlap information.  When
            provided it is passed through to
            :class:`~plant_safety.graph_facts.GraphFactsBuilder` unchanged.
            The caller's object is never mutated.

    Returns:
        A dict matching the :class:`~shared.contracts.RuleVerdict` shape.

    Raises:
        TypeError: if *ptw* or *pid* is not a dict.
        TopologyError: if *pid* cannot be converted to a valid graph.
    """
    if not isinstance(ptw, dict):
        raise TypeError("ptw must be a dict")
    if not isinstance(pid, dict):
        raise TypeError("pid must be a dict")

    graph = PlantGraph.from_structured_pid(pid)

    facts = GraphFactsBuilder.build(
        ptw,
        graph,
        pid=pid,
        overlap_check=overlap_check,
    )

    verdict = evaluate(facts, ptw=ptw)

    return verdict
