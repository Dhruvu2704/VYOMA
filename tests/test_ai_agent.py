"""Milestone 1 test runner for the VYOMA Role 1 fixture-based agent core.

Runs with the Python standard library only (unittest). No pytest required.
Run from the repository root:

    python -m unittest discover -s tests -v

Expected outcome: all four fixture scenarios plus the safety/consistency
invariant checks pass.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from shared.contracts import FinalVerdict, VerificationResult

from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.reasoning.reasoning_engine import DeterministicReasoningEngine
from ai_agent.tool_registry import ToolRegistry, ToolRegistryError
from ai_agent.verification import VerificationEngine

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


def _load(scenario: str) -> dict:
    path = FIXTURES_DIR / FIXTURE_FILES[scenario]
    return load_fixture(path)


class _FixturePipelineMixin:
    """Shared fixture-based assertions.

    Plain mixin (NOT a TestCase) so unittest discovery only instantiates the
    concrete scenario classes; its test_* methods are inherited by them.
    """

    maxDiff = None
    scenario: str

    def setUp(self) -> None:
        self.orchestrator = AgentOrchestrator()
        self.fixture = _load(self.scenario)
        self.result = self.orchestrator.run(self.fixture)
        self.expected = self.fixture

    # -- shared invariant checks used by every scenario --------------------

    def assert_permit_id_consistent(self) -> None:
        sections = [
            self.fixture.get("task_request"),
            self.fixture.get("structured_ptw"),
            self.fixture.get("rule_verdict"),
            self.fixture.get("graph_facts"),
        ]
        for section in sections:
            self.assertEqual(
                section["permit_id"],
                self.result["permit_id"],
                f"permit_id mismatch in {json.dumps(section)}",
            )
        self.assertEqual(
            self.result["llm_reasoning"]["permit_id"],
            self.result["permit_id"],
        )
        self.assertEqual(
            self.result["verification"]["permit_id"],
            self.result["permit_id"],
        )
        self.assertEqual(
            self.result["final_verdict"]["permit_id"],
            self.result["permit_id"],
        )

    def assert_final_verdict_complete(self) -> None:
        verdict = self.result["final_verdict"]
        self.assertEqual(set(verdict.keys()), FINAL_VERDICT_FIELDS)

    def assert_flag_no_auto_approval(self) -> None:
        if self.result["verification"]["agreement"] == "DISAGREE":
            self.assertTrue(
                self.result["verification"]["requires_human_review"],
                "disagreement must require human review",
            )

    # -- pipeline shape checks ---------------------------------------------

    def test_returns_required_keys(self) -> None:
        for key in ("plan", "llm_reasoning", "verification", "final_verdict"):
            self.assertIn(key, self.result)

    def test_llm_reasoning_has_expected_fields(self) -> None:
        llm = self.result["llm_reasoning"]
        self.assertEqual(set(llm.keys()), {"permit_id", "llm_result", "explanation", "confidence"})

    def test_verification_has_expected_fields(self) -> None:
        verification: VerificationResult = self.result["verification"]
        self.assertEqual(
            set(verification.keys()),
            {
                "permit_id",
                "rule_result",
                "llm_result",
                "agreement",
                "final_decision",
                "requires_human_review",
                "explanation",
            },
        )

    def test_audit_ref_consistent(self) -> None:
        self.assertEqual(
            self.result["audit"]["audit_ref"],
            self.result["final_verdict"]["audit_ref"],
        )

    def test_generated_at_and_audit_ref_present(self) -> None:
        verdict: FinalVerdict = self.result["final_verdict"]
        self.assertTrue(verdict["generated_at"])
        self.assertTrue(verdict["audit_ref"])


class SafeCaseTest(_FixturePipelineMixin, unittest.TestCase):
    scenario = "safe"

    def test_scenario_semantics(self) -> None:
        verification = self.result["verification"]
        verdict = self.result["final_verdict"]

        self.assertEqual(verification["rule_result"], "PASS")
        self.assertEqual(verification["llm_result"], "PASS")
        self.assertEqual(verification["agreement"], "AGREE")
        self.assertEqual(verdict["final_decision"], "PASS")
        self.assertFalse(verdict["requires_human_review"])
        self.assertFalse(verification["requires_human_review"])


class ConflictCaseTest(_FixturePipelineMixin, unittest.TestCase):
    scenario = "conflict"

    def test_scenario_semantics(self) -> None:
        verification = self.result["verification"]
        verdict = self.result["final_verdict"]

        self.assertEqual(verification["rule_result"], "FLAGGED")
        self.assertEqual(verification["llm_result"], "FLAGGED")
        self.assertEqual(verification["agreement"], "AGREE")
        self.assertEqual(verdict["final_decision"], "FLAGGED_FOR_REVIEW")
        self.assertTrue(verdict["requires_human_review"])


class AmbiguousCaseTest(_FixturePipelineMixin, unittest.TestCase):
    scenario = "ambiguous"

    def test_scenario_semantics(self) -> None:
        verification = self.result["verification"]
        verdict = self.result["final_verdict"]

        self.assertTrue(verification["requires_human_review"])
        self.assertTrue(verdict["requires_human_review"])
        self.assertNotEqual(verdict["final_decision"], "PASS")

    def test_unresolved_tags_never_auto_approve(self) -> None:
        graph_facts = self.fixture["graph_facts"]
        self.assertTrue(graph_facts["unresolved_tags"])
        verdict = self.result["final_verdict"]
        self.assertNotEqual(verdict["final_decision"], "PASS")
        self.assertNotEqual(self.result["llm_reasoning"]["llm_result"], "PASS")


class DisagreementCaseTest(_FixturePipelineMixin, unittest.TestCase):
    scenario = "disagreement"

    def test_scenario_semantics(self) -> None:
        verification = self.result["verification"]
        verdict = self.result["final_verdict"]

        self.assertNotEqual(verification["rule_result"], verification["llm_result"])
        self.assertEqual(verification["agreement"], "DISAGREE")
        self.assertEqual(verdict["final_decision"], "REVIEW_REQUIRED")
        self.assertTrue(verdict["requires_human_review"])
        self.assertTrue(verification["requires_human_review"])


class InvariantTests(unittest.TestCase):
    """Cross-cutting safety invariants, exercised independently."""

    def test_unknown_tool_is_rejected(self) -> None:
        registry = ToolRegistry()
        with self.assertRaises(ToolRegistryError):
            registry.handle("not_a_tool")
        self.assertFalse(registry.is_known("not_a_tool"))

    def test_tool_ids_must_be_allowlisted(self) -> None:
        registry = ToolRegistry()
        with self.assertRaises(ToolRegistryError):
            registry.register("; rm -rf /")
        with self.assertRaises(ToolRegistryError):
            registry.register("$(shell)")

    def test_known_conceptual_tools_registered(self) -> None:
        registry = ToolRegistry()
        for name in (
            "extract_ptw",
            "extract_pid_symbols",
            "resolve_tags",
            "query_topology",
            "check_conflict",
            "get_active_permits",
            "search_knowledge",
            "generate_word",
            "generate_excel",
            "annotate_pdf",
            "log_event",
        ):
            self.assertTrue(registry.is_known(name), name)
        self.assertFalse(registry.is_known("arbitrary_shell"))

    def test_registered_tool_dispatch(self) -> None:
        registry = ToolRegistry()
        dummy_called = []

        def dummy_handler(verdict, output_dir="outputs"):
            dummy_called.append(verdict["permit_id"])
            return {"type": "WORD_MEMO", "path": "test.docx"}

        registry.register("generate_word", dummy_handler)
        res = registry.handle("generate_word", {"permit_id": "PTW-100"})
        self.assertEqual(dummy_called, ["PTW-100"])
        self.assertEqual(res["type"], "WORD_MEMO")


    def test_disagreement_always_requires_human_review(self) -> None:
        engine = VerificationEngine()
        for rule, llm in (("PASS", "FLAGGED"), ("FLAGGED", "PASS")):
            verification = engine.verify(
                {"permit_id": "P1", "rule_result": rule, "confidence": "MEDIUM"},
                {"permit_id": "P1", "llm_result": llm, "confidence": "MEDIUM"},
            )
            self.assertEqual(verification["agreement"], "DISAGREE")
            self.assertTrue(verification["requires_human_review"])
            self.assertEqual(verification["final_decision"], "REVIEW_REQUIRED")

    def test_unresolved_tags_never_produce_unqualified_pass(self) -> None:
        fixture = _load("ambiguous")
        graph_facts = dict(fixture["graph_facts"])
        graph_facts["unresolved_tags"] = ["TAG-A", "TAG-B"]
        graph_facts["active_isolations"] = []
        rule_verdict = dict(fixture["rule_verdict"])
        rule_verdict["rule_result"] = "PASS"
        engine = DeterministicReasoningEngine()
        result = engine.reason(
            ptw=fixture["structured_ptw"],
            graph_facts=graph_facts,
            rule_verdict=rule_verdict,
        )
        self.assertEqual(result["llm_result"], "FLAGGED")
        self.assertNotIn("PASS", result["llm_result"])

    def test_rule_pass_but_unresolved_tags_forces_review(self) -> None:
        fixture = _load("safe")
        graph_facts = dict(fixture["graph_facts"])
        graph_facts["unresolved_tags"] = ["7X-GA-TEMP"]
        rule_verdict = dict(fixture["rule_verdict"])
        rule_verdict["rule_result"] = "PASS"
        result = AgentOrchestrator().run(
            {
                **fixture,
                "graph_facts": graph_facts,
                "rule_verdict": rule_verdict,
            }
        )
        self.assertEqual(result["verification"]["agreement"], "DISAGREE")
        self.assertEqual(result["final_verdict"]["final_decision"], "REVIEW_REQUIRED")
        self.assertTrue(result["final_verdict"]["requires_human_review"])

    def test_final_verdict_contains_required_fields(self) -> None:
        result = AgentOrchestrator().run(_load("conflict"))
        self.assertEqual(set(result["final_verdict"].keys()), FINAL_VERDICT_FIELDS)

    def test_permit_id_consistent_across_pipeline(self) -> None:
        for scenario in FIXTURE_FILES:
            fixture = _load(scenario)
            result = AgentOrchestrator().run(fixture)
            permit_id = result["permit_id"]
            self.assertEqual(fixture["task_request"]["permit_id"], permit_id, scenario)
            self.assertEqual(fixture["structured_ptw"]["permit_id"], permit_id, scenario)
            self.assertEqual(fixture["rule_verdict"]["permit_id"], permit_id, scenario)
            self.assertEqual(fixture["graph_facts"]["permit_id"], permit_id, scenario)
            self.assertEqual(result["llm_reasoning"]["permit_id"], permit_id, scenario)
            self.assertEqual(result["verification"]["permit_id"], permit_id, scenario)
            self.assertEqual(result["final_verdict"]["permit_id"], permit_id, scenario)
            self.assertEqual(result["audit"]["permit_id"], permit_id, scenario)

    def test_fixture_expectations_match_pipeline_output(self) -> None:
        expectations = {
            "safe": ("AGREE", "PASS", False),
            "conflict": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "ambiguous": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "disagreement": ("DISAGREE", "REVIEW_REQUIRED", True),
        }
        for scenario, (expected_agreement, expected_decision, expected_review) in expectations.items():
            fixture = _load(scenario)
            result = AgentOrchestrator().run(fixture)
            self.assertEqual(result["verification"]["agreement"], expected_agreement, scenario)
            self.assertEqual(
                result["final_verdict"]["final_decision"], expected_decision, scenario
            )
            self.assertEqual(
                result["final_verdict"]["requires_human_review"], expected_review, scenario
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)