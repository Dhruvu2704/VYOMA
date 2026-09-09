"""End-to-end tests for plant_safety.pipeline.evaluate_permit.

Exercises the complete deterministic Role 3 chain (graph -> facts ->
rules) against the actual repository fixtures.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

from ai_agent.orchestrator.orchestrator import AgentOrchestrator
from plant_safety.graph_facts import GraphFactsBuilder
from plant_safety.pipeline import evaluate_permit
from plant_safety.topology import PlantGraph, TopologyError
from plant_safety.safety_rules import (
    HOT_WORK_OVERLAP,
    ISOLATION_OVERLAP_TIME_WINDOW,
    NO_CONFLICT,
    PERMIT_CONFLICT,
    TAGS_RESOLVED,
    UNRESOLVED_TAGS,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}

FINAL_VERDICT_FIELDS = {
    "permit_id",
    "rule_result",
    "llm_result",
    "agreement",
    "final_decision",
    "explanation",
    "requires_human_review",
    "generated_at",
    "audit_ref",
}


def _load_fixture(scenario: str) -> Dict[str, Any]:
    path = FIXTURES_DIR / FIXTURE_FILES[scenario]
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _run(scenario: str, overlap_check: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fixture = _load_fixture(scenario)
    return evaluate_permit(
        fixture["structured_ptw"],
        fixture["structured_pid"],
        overlap_check=overlap_check,
    )


# =========================================================================
# 1. safe fixture -> PASS
# =========================================================================
class SafeFixturePipelineTest(unittest.TestCase):
    def test_safe_passes(self) -> None:
        verdict = _run("safe")
        self.assertEqual(verdict["rule_result"], "PASS")
        self.assertEqual(verdict["permit_id"], "MR-0001-SAFE")
        self.assertEqual(verdict["conflicting_permit_ids"], [])
        self.assertIn(NO_CONFLICT, verdict["rules_triggered"])
        self.assertIn(TAGS_RESOLVED, verdict["rules_triggered"])

    def test_safe_verdict_shape(self) -> None:
        verdict = _run("safe")
        self.assertEqual(
            set(verdict),
            {
                "permit_id",
                "conflicting_permit_ids",
                "rules_triggered",
                "rule_result",
                "explanation",
                "confidence",
            },
        )


# =========================================================================
# 2. conflict fixture -> FLAGGED
# =========================================================================
class ConflictFixturePipelineTest(unittest.TestCase):
    def _run_conflict(self) -> Dict[str, Any]:
        # Overlap evidence (which active permits conflict in this area) is
        # external to the PTW/PID pair — it comes from Role 4. The pipeline
        # only flags a conflict when such evidence is supplied via
        # overlap_check. Use the fixture's own overlap data for the chain.
        fixture = _load_fixture("conflict")
        return evaluate_permit(
            fixture["structured_ptw"],
            fixture["structured_pid"],
            overlap_check=fixture["graph_facts"]["overlap_check"],
        )

    def test_conflict_flagged(self) -> None:
        verdict = self._run_conflict()
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertEqual(verdict["permit_id"], "MR-0002-CONF")
        self.assertIn("MR-0003-CONF", verdict["conflicting_permit_ids"])
        self.assertIn(PERMIT_CONFLICT, verdict["rules_triggered"])

    def test_conflict_hot_work_overlap(self) -> None:
        verdict = self._run_conflict()
        self.assertIn(HOT_WORK_OVERLAP, verdict["rules_triggered"])

    def test_conflict_isolation_overlap_time_window(self) -> None:
        # The conflict fixture carries active isolation ISO-T302-01 alongside
        # overlapping permits, so the isolation-overlap-time-window rule must
        # trigger too.
        verdict = self._run_conflict()
        self.assertIn(ISOLATION_OVERLAP_TIME_WINDOW, verdict["rules_triggered"])

    def test_conflict_isolation_identifier_stays_opaque(self) -> None:
        # ISO-T302-01 must be treated as an opaque isolation identifier: it is
        # NOT converted to the equipment tag T-302 or resolved as a graph node.
        fixture = _load_fixture("conflict")
        self.assertEqual(
            fixture["structured_ptw"]["isolation_points"], ["ISO-T302-01"]
        )
        verdict = self._run_conflict()
        self.assertEqual(verdict["rule_result"], "FLAGGED")


# =========================================================================
# 3. ambiguous fixture -> FLAGGED
# =========================================================================
class AmbiguousFixturePipelineTest(unittest.TestCase):
    def test_ambiguous_flagged(self) -> None:
        verdict = _run("ambiguous")
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertEqual(verdict["permit_id"], "MR-0004-AMB")
        self.assertIn(UNRESOLVED_TAGS, verdict["rules_triggered"])


# =========================================================================
# 4. disagreement fixture -> FLAGGED per deterministic rule semantics
# =========================================================================
class DisagreementFixturePipelineTest(unittest.TestCase):
    def test_disagreement_flagged_on_rule_side(self) -> None:
        # The rule evaluator consumes GraphFacts (which includes unresolved
        # tags from the graph layer), so it FLAGS.  This matches the
        # established test_safety_rules semantics.
        verdict = _run("disagreement")
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertEqual(verdict["permit_id"], "MR-0005-DIS")
        self.assertIn(UNRESOLVED_TAGS, verdict["rules_triggered"])


# =========================================================================
# 5. overlap_check handling
# =========================================================================
class OverlapCheckTest(unittest.TestCase):
    def test_overlap_check_omitted(self) -> None:
        verdict = _run("safe")
        self.assertEqual(verdict["rule_result"], "PASS")

    def test_overlap_check_passthrough_empty(self) -> None:
        verdict = _run("safe", overlap_check=None)
        self.assertEqual(verdict["rule_result"], "PASS")

    def test_overlap_check_passthrough_triggers_conflict(self) -> None:
        fixture = _load_fixture("safe")
        overlap = {
            "overlapping_permits": ["MR-0099-CONF"],
            "same_area_active": True,
        }
        verdict = evaluate_permit(
            fixture["structured_ptw"], fixture["structured_pid"], overlap_check=overlap
        )
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn(PERMIT_CONFLICT, verdict["rules_triggered"])
        self.assertIn("MR-0099-CONF", verdict["conflicting_permit_ids"])

    def test_caller_overlap_check_not_mutated(self) -> None:
        fixture = _load_fixture("safe")
        overlap = {
            "overlapping_permits": ["MR-0099-CONF"],
            "same_area_active": True,
        }
        before = copy.deepcopy(overlap)
        evaluate_permit(
            fixture["structured_ptw"], fixture["structured_pid"], overlap_check=overlap
        )
        self.assertEqual(overlap, before)


# =========================================================================
# 6. error propagation
# =========================================================================
class ErrorPropagationTest(unittest.TestCase):
    def test_invalid_pid_propagates_topology_error(self) -> None:
        fixture = _load_fixture("safe")
        ptw = fixture["structured_ptw"]
        bad_pid = {
            "pid_id": "PID-BAD",
            "source": "mock",
            "equipment_tags": [],
            # connection references an unknown symbol -> TopologyError
            "connections": [{"source": "A", "target": "MISSING", "line_ref": "L1"}],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError):
            evaluate_permit(ptw, bad_pid)

    def test_non_dict_ptw_raises_type_error(self) -> None:
        fixture = _load_fixture("safe")
        with self.assertRaises(TypeError):
            evaluate_permit("not-a-dict", fixture["structured_pid"])  # type: ignore[arg-type]

    def test_non_dict_pid_raises_type_error(self) -> None:
        fixture = _load_fixture("safe")
        with self.assertRaises(TypeError):
            evaluate_permit(fixture["structured_ptw"], "not-a-dict")  # type: ignore[arg-type]

    def test_missing_symbols_in_pid_raises(self) -> None:
        fixture = _load_fixture("safe")
        ptw = fixture["structured_ptw"]
        bad_pid = {
            "pid_id": "PID-NO-SYMBOLS",
            "source": "mock",
            "equipment_tags": [],
            # symbols is not a list -> TopologyError
            "connections": [],
            "unresolved_symbols": [],
            "field_confidence": {},
            "low_confidence_fields": [],
        }
        with self.assertRaises(TopologyError):
            evaluate_permit(ptw, bad_pid)


# =========================================================================
# 7. determinism
# =========================================================================
class DeterminismTest(unittest.TestCase):
    def test_same_inputs_same_output(self) -> None:
        for scenario in FIXTURE_FILES:
            fixture = _load_fixture(scenario)
            overlap = fixture["graph_facts"].get("overlap_check")
            args = (fixture["structured_ptw"], fixture["structured_pid"])
            v1 = evaluate_permit(*args, overlap_check=overlap)
            v2 = evaluate_permit(*args, overlap_check=overlap)
            self.assertEqual(v1, v2, scenario)


# =========================================================================
# 8. input immutability
# =========================================================================
class InputImmutabilityTest(unittest.TestCase):
    def test_ptw_and_pid_not_mutated(self) -> None:
        fixture = _load_fixture("safe")
        ptw = fixture["structured_ptw"]
        pid = fixture["structured_pid"]
        ptw_before = copy.deepcopy(ptw)
        pid_before = copy.deepcopy(pid)
        evaluate_permit(ptw, pid)
        self.assertEqual(ptw, ptw_before)
        self.assertEqual(pid, pid_before)


# =========================================================================
# 9. Role 1 integration readiness
# =========================================================================
class Role1IntegrationReadinessTest(unittest.TestCase):
    """Role 1 can consume Role 3 pipeline output without contract changes.

    The Role 1 orchestrator reads ``rule_verdict`` and ``graph_facts`` from
    the fixture envelope and validates them against the shared contracts.
    The Role 3 pipeline module is not called by Role 1 yet (integration is
    a team-level decision); this test proves the interfaces line up by
    substituting pipeline-computed GraphFacts + RuleVerdict into the fixture
    and running the unmodified Role 1 orchestrator end to end.
    """

    def _orchestrator_input(self, scenario: str) -> Dict[str, Any]:
        fixture = _load_fixture(scenario)
        ptw = fixture["structured_ptw"]
        pid = fixture["structured_pid"]
        overlap = fixture["graph_facts"].get("overlap_check")
        graph = PlantGraph.from_structured_pid(pid)
        facts = GraphFactsBuilder.build(ptw, graph, pid=pid, overlap_check=overlap)
        verdict = evaluate_permit(ptw, pid, overlap_check=overlap)
        return {
            **fixture,
            "graph_facts": facts,
            "rule_verdict": verdict,
        }

    def test_pipeline_output_consumable_by_role1(self) -> None:
        for scenario in FIXTURE_FILES:
            result = AgentOrchestrator().run(self._orchestrator_input(scenario))
            self.assertEqual(set(result["final_verdict"]), FINAL_VERDICT_FIELDS, scenario)
            self.assertIn(
                result["verification"]["agreement"], ("AGREE", "DISAGREE"), scenario
            )

    def test_safe_case_still_passes_end_to_end(self) -> None:
        result = AgentOrchestrator().run(self._orchestrator_input("safe"))
        self.assertEqual(result["verification"]["rule_result"], "PASS")
        self.assertEqual(result["verification"]["llm_result"], "PASS")
        self.assertEqual(result["final_verdict"]["final_decision"], "PASS")
        self.assertFalse(result["final_verdict"]["requires_human_review"])

    def test_conflict_case_still_flags_end_to_end(self) -> None:
        result = AgentOrchestrator().run(self._orchestrator_input("conflict"))
        self.assertEqual(result["verification"]["rule_result"], "FLAGGED")
        self.assertEqual(result["verification"]["agreement"], "AGREE")
        self.assertEqual(result["final_verdict"]["final_decision"], "FLAGGED_FOR_REVIEW")
        self.assertTrue(result["final_verdict"]["requires_human_review"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
