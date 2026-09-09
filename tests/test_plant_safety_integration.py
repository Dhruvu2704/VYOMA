"""Focused integration tests: Role 3 deterministic plant-safety <-> Role 1.

Covers the contract required by the integration:

1.  Safe PTW + compatible P&ID        -> no conflict, reasoning runs, PASS.
2.  Conflicting PTW + P&ID            -> Rule 3 detects conflict; Role 1
                                          receives RuleVerdict; review required.
3.  Unresolved equipment tag          -> deterministic layer detects it; the
                                          result never silently becomes PASS.
4.  Model disagreement                -> deterministic conflict + model PASS
                                          -> REVIEW_REQUIRED / human review.
                                          (Also: rule PASS + incomplete
                                          evidence -> DISAGREE -> REVIEW.)
5.  Role 3 failure                    -> captured safely; no fake PASS; audit
                                          trace records the failure.
6.  Regression                        -> default orchestrator is unchanged and
                                          the integration is strictly opt-in.

No Ollama server is required.  All reasoning paths use the deterministic
engine (or an injected stub) and a stubbed provider transport where needed.

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ai_agent.orchestrator.orchestrator import (
    AgentOrchestrator,
    build_provider_orchestrator,
    load_fixture,
)
from ai_agent.plant_safety_integration import evaluate_plant_safety
from ai_agent.reasoning.reasoning_engine import ReasoningEngine
from ai_agent.config import OllamaConfig
from plant_safety.topology import TopologyError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}


def _load(scenario: str) -> dict:
    return load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])


def _envelope(
    scenario: str,
    *,
    include_overlap_evidence: bool = True,
    overlap_overrides: dict | None = None,
) -> dict:
    """A Role-1 runnable envelope carrying only ptw/pid (+ overlap evidence).

    ``graph_facts`` / ``rule_verdict`` are intentionally omitted so the
    integrated orchestrator must derive them from the Role 3 pipeline.
    Overlap (Role 4 active-permit) evidence is the only piece external to the
    PTW/PID pair, so it is carried on the supplied graph_facts envelope.
    """
    fixture = _load(scenario)
    envelope = {
        "task_request": fixture["task_request"],
        "structured_ptw": fixture["structured_ptw"],
        "structured_pid": fixture["structured_pid"],
    }
    if include_overlap_evidence:
        evidence = copy.deepcopy(fixture["graph_facts"])
        if overlap_overrides is not None:
            evidence["overlap_check"] = overlap_overrides
        envelope["graph_facts"] = {
            "permit_id": evidence["permit_id"],
            "overlap_check": evidence["overlap_check"],
        }
    return envelope


class _AlwaysPassEngine(ReasoningEngine):
    """Stub reasoning engine that claims everything is safe (model overreach)."""

    def reason(
        self,
        ptw,
        graph_facts,
        rule_verdict,
        retrieved=None,
        structured_pid=None,
        active_permits=None,
        task=None,
    ):
        return {
            "permit_id": rule_verdict["permit_id"],
            "llm_result": "PASS",
            "explanation": "independent model conclusion: everything is safe",
            "confidence": "HIGH",
        }


def _stub_transport(status: int, body: bytes):
    def transport(url, data, headers, timeout):  # noqa: ARG001
        return status, body

    return transport


def _ok_body(content: str = "evidence is consistent") -> bytes:
    return (
        '{"model":"llama3","message":{"role":"assistant","content":'
        + json.dumps(content)
        + '},"done":true}'
    ).encode("utf-8")


class SafePermitIntegrationTest(unittest.TestCase):
    """Safe PTW + compatible P&ID -> Role 3 no conflict -> PASS when model agrees."""

    def setUp(self) -> None:
        self.orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        self.result = self.orchestrator.run(_envelope("safe"))

    def test_nothing_failed(self) -> None:
        self.assertIsNone(self.result.get("failed_stage"), self.result.get("errors"))

    def test_role3_produced_no_conflict(self) -> None:
        expected = _load("safe")
        # Role 3 is authoritative: computed facts/verdict reached the state.
        stages = self.result["audit"]["stages"]
        self.assertTrue(stages["deterministic_safety_evaluated"])
        self.assertEqual(stages["rule_verdict"]["rule_result"], "PASS")
        self.assertEqual(
            stages["graph_facts"]["unresolved_tags"],
            expected["graph_facts"]["unresolved_tags"],
        )

    def test_reasoning_ran_to_verdict(self) -> None:
        self.assertEqual(self.result["verification"]["rule_result"], "PASS")
        self.assertEqual(self.result["verification"]["llm_result"], "PASS")
        self.assertEqual(self.result["verification"]["agreement"], "AGREE")
        self.assertEqual(self.result["final_verdict"]["final_decision"], "PASS")
        self.assertFalse(self.result["final_verdict"]["requires_human_review"])
        self.assertFalse(
            self.result["audit"]["stages"]["requested_human_review"]
        )


class ConflictingPermitIntegrationTest(unittest.TestCase):
    """Conflicting PTW + P&ID -> Role 3 conflict -> review required."""

    def setUp(self) -> None:
        # Overlap evidence (Role 4) is supplied via the envelope; Role 3
        # must flag it and expose the triggered rule + conflicting permit.
        self.orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        self.result = self.orchestrator.run(_envelope("conflict"))

    def test_role3_detected_conflict(self) -> None:
        stages = self.result["audit"]["stages"]
        verdict = stages["rule_verdict"]
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn("permit-conflict", verdict["rules_triggered"])
        self.assertIn("MR-0003-CONF", verdict["conflicting_permit_ids"])
        # The permit has active isolations + overlap -> isolation rule too.
        self.assertIn(
            "isolation-overlap-time-window", verdict["rules_triggered"]
        )

    def test_role1_received_ruleverdict_and_requires_review(self) -> None:
        self.assertEqual(
            self.result["verification"]["rule_result"], "FLAGGED"
        )
        self.assertEqual(self.result["verification"]["agreement"], "AGREE")
        self.assertEqual(
            self.result["final_verdict"]["final_decision"], "FLAGGED_FOR_REVIEW"
        )
        self.assertTrue(self.result["final_verdict"]["requires_human_review"])
        self.assertTrue(self.result["audit"]["stages"]["requested_human_review"])
        self.assertIsNone(self.result.get("failed_stage"))

    def test_no_overlap_evidence_means_no_invented_conflict(self) -> None:
        # Determinism: without Role 4 overlap evidence the pipeline does not
        # invent a conflict. Same inputs always produce the same output.
        result = self.orchestrator.run(
            _envelope("conflict", include_overlap_evidence=False)
        )
        self.assertIsNone(result.get("failed_stage"))
        stages = result["audit"]["stages"]
        self.assertEqual(stages["rule_verdict"]["rule_result"], "PASS")
        self.assertEqual(stages["graph_facts"]["overlap_check"]["overlapping_permits"], [])


class UnresolvedTagIntegrationTest(unittest.TestCase):
    """Unresolved equipment tags must never silently become PASS."""

    def setUp(self) -> None:
        self.orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        self.result = self.orchestrator.run(_envelope("ambiguous"))

    def test_deterministic_layer_detects_unresolved_tags(self) -> None:
        stages = self.result["audit"]["stages"]
        self.assertTrue(stages["graph_facts"]["unresolved_tags"])
        self.assertIn(
            "unresolved-tags", stages["rule_verdict"]["rules_triggered"]
        )
        self.assertEqual(stages["rule_verdict"]["rule_result"], "FLAGGED")

    def test_no_silent_approval(self) -> None:
        self.assertEqual(
            self.result["verification"]["llm_result"], "FLAGGED"
        )
        self.assertNotEqual(
            self.result["final_verdict"]["final_decision"], "PASS"
        )
        self.assertTrue(self.result["final_verdict"]["requires_human_review"])


class ModelDisagreementIntegrationTest(unittest.TestCase):
    """A determinant conflict can never be overridden by the model."""

    def test_conflict_plus_model_says_safe_never_passes(self) -> None:
        # The deterministic verdict is FLAGGED; the (stub) model disagrees
        # and claims PASS. Verification must escalate, never approve.
        orchestrator = AgentOrchestrator(
            reasoning_engine=_AlwaysPassEngine(),
            plant_safety_evaluator=evaluate_plant_safety,
        )
        result = orchestrator.run(_envelope("conflict"))

        self.assertEqual(result["verification"]["rule_result"], "FLAGGED")
        self.assertEqual(result["verification"]["llm_result"], "PASS")
        self.assertEqual(result["verification"]["agreement"], "DISAGREE")
        self.assertEqual(
            result["verification"]["final_decision"], "REVIEW_REQUIRED"
        )
        self.assertTrue(result["verification"]["requires_human_review"])
        self.assertEqual(
            result["final_verdict"]["final_decision"], "REVIEW_REQUIRED"
        )
        self.assertTrue(result["final_verdict"]["requires_human_review"])
        self.assertNotEqual(result["final_verdict"]["final_decision"], "PASS")

    def test_incomplete_evidence_reaches_review(self) -> None:
        # Reachable disagreement under the real Role 3: rule PASS (no overlap)
        # but active isolations remain unconfirmed -> reasoning FLAGS ->
        # DISAGREE -> REVIEW_REQUIRED (existing verification behavior).
        orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        result = orchestrator.run(
            _envelope(
                "conflict",
                overlap_overrides={
                    "overlapping_permits": [],
                    "same_area_active": False,
                },
            )
        )
        self.assertIsNone(result.get("failed_stage"))
        stages = result["audit"]["stages"]
        self.assertEqual(stages["rule_verdict"]["rule_result"], "PASS")
        self.assertEqual(stages["verification"]["agreement"], "DISAGREE")
        self.assertEqual(
            result["final_verdict"]["final_decision"], "REVIEW_REQUIRED"
        )
        self.assertTrue(result["final_verdict"]["requires_human_review"])


class Role3FailureIntegrationTest(unittest.TestCase):
    """Pipeline failure must be captured safely; no fake approval."""

    def test_malformed_pid_fails_use_tool_explicitly(self) -> None:
        fixture = _load("safe")
        bad_pid = {
            **fixture["structured_pid"],
            "connections": [
                {"source": "P-101", "target": "MISSING", "line_ref": "L1"}
            ],
        }
        envelope = {
            "task_request": fixture["task_request"],
            "structured_ptw": fixture["structured_ptw"],
            "structured_pid": bad_pid,
        }
        orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        result = orchestrator.run(envelope)
        # Failed at USE TOOL, nothing fabricated downstream.
        self.assertEqual(result["failed_stage"], "use_tool")
        self.assertTrue(result["errors"])
        self.assertIn(
            "Plant-safety evaluation failed", result["errors"][0]["message"]
        )
        self.assertIsNone(result["final_verdict"])
        self.assertIsNone(result["verification"])
        self.assertIsNone(result["llm_reasoning"])
        # Audit trace records the failure and confirms no safety evaluation.
        stages = result["audit"]["stages"]
        self.assertFalse(stages["deterministic_safety_evaluated"])
        self.assertFalse(stages["requested_human_review"])

    def test_evaluator_raise_is_a_stage_failure(self) -> None:
        def boom(ptw, pid, overlap_check=None):
            raise TopologyError("injected failure")

        orchestrator = AgentOrchestrator(plant_safety_evaluator=boom)
        result = orchestrator.run(_envelope("safe"))
        self.assertEqual(result["failed_stage"], "use_tool")
        self.assertIsNone(result["final_verdict"])


class IntegrationOptInRegressionTest(unittest.TestCase):
    """The Role 3 integration must be strictly opt-in (Day 1-4 preserved)."""

    def test_default_orchestrator_is_unchanged(self) -> None:
        # No evaluator wired: fixture-supplied evidence path (Day 1-4).
        orchestrator = AgentOrchestrator()
        result = orchestrator.run(load_fixture(FIXTURES_DIR / FIXTURE_FILES["safe"]))
        self.assertIsNone(result.get("failed_stage"))
        self.assertEqual(result["final_verdict"]["final_decision"], "PASS")
        self.assertFalse(
            result["audit"]["stages"]["deterministic_safety_evaluated"]
        )

    def test_missing_evidence_still_fails_reason_without_plant_safety(self) -> None:
        # A ptw+pid-only envelope (no graph_facts/rule_verdict) fails at
        # REASON exactly as before when Role 3 is not enabled.
        result = AgentOrchestrator().run(
            _envelope("safe", include_overlap_evidence=False)
        )
        self.assertEqual(result["failed_stage"], "reason")
        self.assertIsNone(result["final_verdict"])


class ProviderIntegratedPathTest(unittest.TestCase):
    """Full integrated path with provider-backed reasoning (stubbed transport)."""

    def test_provider_orchestrator_with_plant_safety(self) -> None:
        # build_provider_orchestrator(plant_safety=True) runs Role 3 -> Ollama
        # provider (stub) -> verification, no real server required.
        orchestrator = build_provider_orchestrator(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("evidence is consistent")),
            plant_safety=True,
        )
        result = orchestrator.run(_envelope("safe"))
        self.assertIsNone(result.get("failed_stage"))
        self.assertTrue(
            result["audit"]["stages"]["deterministic_safety_evaluated"]
        )
        self.assertEqual(result["verification"]["agreement"], "AGREE")
        self.assertEqual(result["final_verdict"]["final_decision"], "PASS")
        self.assertIn("Model note:", result["llm_reasoning"]["explanation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)