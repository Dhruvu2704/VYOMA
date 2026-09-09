"""Deterministic Role 3 -> Role 1 integration adapter.

This module connects the existing Role 3 ``plant_safety`` deterministic
pipeline to the existing Role 1 agent.  It is a *compatibility adapter* only:
it adds no safety logic, no LLM, and no contracts of its own.

    StructuredPTW + StructuredPID
        -> plant_safety.topology.PlantGraph
        -> plant_safety.graph_facts.GraphFactsBuilder     (GraphFacts)
        -> plant_safety.safety_rules.evaluate             (RuleVerdict)

Everything here is deterministic (same inputs -> same outputs) and fully
independent of the LLM.  The Role 3 rules remain the authoritative safety
layer: the orchestrator delivers their ``RuleVerdict`` to the reasoning
provider, and the provider can never override it (see ``verification.py``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from plant_safety.graph_facts import GraphFactsBuilder
from plant_safety.safety_rules import evaluate as evaluate_rules
from plant_safety.topology import PlantGraph


def evaluate_plant_safety(
    ptw: Dict[str, Any],
    pid: Dict[str, Any],
    overlap_check: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Evaluate the deterministic Role 3 pipeline for a permit.

    Returns ``(graph_facts, rule_verdict)`` as the two
    :mod:`shared.contracts`-compatible dicts the Role 1 orchestrator consumes.

    Args:
        ptw: A ``StructuredPTW``-compatible dict.
        pid: A ``StructuredPID``-compatible dict.
        overlap_check: Optional pre-computed overlap evidence (e.g. from the
            Role 4 active-permit layer).  Passed through unchanged.

    Raises:
        TypeError: if *ptw* or *pid* is not a dict.
        TopologyError: if *pid* cannot be converted to a valid graph.
    """
    graph = PlantGraph.from_structured_pid(pid)
    graph_facts = GraphFactsBuilder.build(
        ptw,
        graph,
        pid=pid,
        overlap_check=overlap_check,
    )
    rule_verdict = evaluate_rules(graph_facts, ptw=ptw)
    return graph_facts, rule_verdict