"""Role 3 — Plant graph and safety rules.

This package owns the plant topology graph, tag resolution, overlap
checking, and deterministic safety-rule evaluation for the VYOMA pipeline.
"""

from plant_safety.topology import PlantGraph, TopologyError
from plant_safety.tag_resolution import TagResolver, TagResolutionResult
from plant_safety.graph_facts import GraphFactsBuilder, GraphFactsError
from plant_safety.safety_rules import evaluate
from plant_safety.pipeline import evaluate_permit

__all__ = [
    "PlantGraph",
    "TopologyError",
    "TagResolver",
    "TagResolutionResult",
    "GraphFactsBuilder",
    "GraphFactsError",
    "evaluate",
    "evaluate_permit",
]
