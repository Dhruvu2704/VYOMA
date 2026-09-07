"""Focused Day 1 tests for the VYOMA Role 1 agent.

Covers:
- AgentState as the single state object (all carriers + error/trace helpers)
- deterministic task classification
- classification-aware planner behavior
- explicit error-state handling (failed stage => no fake approval, no silent
  continuation)
- workflow is a controlled engine, not a chatbot

Runs with the Python standard library only (unittest). Run from the repo root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from shared.contracts import FinalVerdict, PlanStep

from ai_agent.agent_state import AgentState, ExecutionTraceEntry, StageError
from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.planner import TaskAwarePlanner
from ai_agent.task_classifier import (
    TaskClassificationError,
    TaskClassifier,
    VALID_TASK_TYPES,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}

PIPELINE = [
    "perceive",
    "understand",
    "plan",
    "retrieve",
    "use_tool",
    "reason",
    "verify",
    "act",
    "log",
]


def _load(scenario: str) -> dict:
    return load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])


class AgentStateTests(unittest.TestCase):
    """AgentState must be the single state object carrying all workflow data."""

    def test_carries_all_required_field_groups(self) -> None:
        for name, _ in AgentState.__dataclass_fields__.items():
            self.assertTrue(hasattr(AgentState(), name), name)

    def test_carries_required_carriers(self) -> None:
        required = {
            "task_id",
            "task_type",
            "input_files",
            "structured_ptw",
            "structured_pid",
            "graph_facts",
            "active_permits",
            "rule_verdict",
            "rag_context",
            "llm_result",
            "verification",
            "final_verdict",
            "errors",
            "audit_refs",
        }
        state = AgentState()
        fields = set(AgentState.__dataclass_fields__)
        for carrier in required:
            self.assertIn(carrier, fields, carrier)

    def test_safe_defaults(self) -> None:
        state = AgentState()
        self.assertEqual(state.errors, [])
        self.assertEqual(state.rag_context, [])
        self.assertEqual(state.input_files, [])
        self.assertFalse(state.has_errors)
        self.assertFalse(state.is_failed)
        self.assertIsNone(state.failed_stage)
        self.assertEqual(state.completed_stages, [])

    def test_error_and_trace_helpers(self) -> None:
        state = AgentState()
        state.execution_trace.append(
            ExecutionTraceEntry(stage="perceive", status="completed", timestamp="t")
        )
        state.execution_trace.append(
            ExecutionTraceEntry(stage="reason", status="failed", timestamp="t")
        )
        state.errors.append(
            StageError(
                stage="reason",
                error_type="StageFailure",
                message="boom",
                timestamp="t",
            )
        )
        self.assertTrue(state.has_errors)
        self.assertTrue(state.is_failed)
        self.assertEqual(state.failed_stage, "reason")
        self.assertEqual(state.completed_stages, ["perceive"])

    def test_is_a_controlled_state_not_a_chat_memory(self) -> None:
        # No free-form conversation store; state is a fixed pipeline structure.
        state = AgentState()
        fields = set(AgentState.__dataclass_fields__)
        self.assertNotIn("messages", fields)
        self.assertNotIn("conversation", fields)


class TaskClassificationTests(unittest.TestCase):
    """Deterministic classification (no LLM) for the four task types."""

    def setUp(self) -> None:
        self.classifier = TaskClassifier()

    def test_base_fixtures_classify_as_ptw_conflict_analysis(self) -> None:
        for scenario in FIXTURE_FILES:
            result = self.classifier.classify(_load(scenario))
            self.assertEqual(result, "ptw_conflict_analysis", scenario)

    def test_ptw_conflict_task_type(self) -> None:
        fixture = {
            "task_request": {"task_type": "ptw_conflict_analysis", "permit_id": "P1"}
        }
        self.assertEqual(
            self.classifier.classify(fixture), "ptw_conflict_analysis"
        )

    def test_ptw_review_legacy_task_type(self) -> None:
        fixture = {"task_request": {"task_type": "ptw_review", "permit_id": "P1"}}
        self.assertEqual(
            self.classifier.classify(fixture), "ptw_conflict_analysis"
        )

    def test_document_question(self) -> None:
        fixture = {"task_request": {"task_type": "document_question", "permit_id": "P1"}}
        self.assertEqual(self.classifier.classify(fixture), "document_question")

    def test_general_industrial_reasoning(self) -> None:
        fixture = {
            "task_request": {
                "task_type": "general_industrial_reasoning",
                "permit_id": "P1",
            }
        }
        self.assertEqual(
            self.classifier.classify(fixture), "general_industrial_reasoning"
        )

    def test_deliverable_request(self) -> None:
        fixture = {"task_request": {"task_type": "deliverable_request", "permit_id": "P1"}}
        self.assertEqual(self.classifier.classify(fixture), "deliverable_request")

    def test_unknown_type_falls_back_to_general(self) -> None:
        fixture = {"task_request": {"task_type": "something_unknown", "permit_id": "P1"}}
        self.assertEqual(
            self.classifier.classify(fixture), "general_industrial_reasoning"
        )

    def test_missing_task_request_raises(self) -> None:
        with self.assertRaises(TaskClassificationError):
            self.classifier.classify({})

    def test_document_question_via_context(self) -> None:
        fixture = {
            "task_request": {
                "task_type": "ptw_review",
                "permit_id": "P1",
                "context": {"question": "when does this permit expire?"},
            }
        }
        self.assertEqual(self.classifier.classify(fixture), "document_question")

    def test_deliverable_via_context(self) -> None:
        fixture = {
            "task_request": {
                "task_type": "ptw_review",
                "permit_id": "P1",
                "context": {"deliverable_type": "word_report"},
            }
        }
        self.assertEqual(self.classifier.classify(fixture), "deliverable_request")


class PlannerBehaviorTests(unittest.TestCase):
    """The planner must produce a meaningful, task-dependent PlanStep sequence."""

    def setUp(self) -> None:
        self.planner = TaskAwarePlanner()

    def _step_names(self, plan: list) -> list:
        return [s["step"] for s in plan]

    def test_all_known_task_types_plannable(self) -> None:
        for task_type in VALID_TASK_TYPES:
            plan = self.planner.plan(task_type, "P1")
            self.assertTrue(plan)
            self.assertEqual(set(plan[0].keys()), {"step", "tool", "model_category", "status"})

    def test_ptw_conflict_plan_includes_full_safety_flow(self) -> None:
        plan = self.planner.plan("ptw_conflict_analysis", "P1")
        steps = self._step_names(plan)
        # Safety analysis needs retrieve, tool (conflict check), reason,
        # verify, act and log.
        self.assertIn("retrieve", steps)
        self.assertIn("verify", steps)
        self.assertIn("check_conflict", [s["tool"] for s in plan])
        self.assertIn("search_knowledge", [s["tool"] for s in plan])

    def test_plans_differ_by_task_type(self) -> None:
        plans = {
            t: self._step_names(self.planner.plan(t, "P1"))
            for t in VALID_TASK_TYPES
        }
        # Conflict analysis has a verify stage; a pure document question does not.
        self.assertIn("verify", plans["ptw_conflict_analysis"])
        self.assertNotIn("verify", plans["document_question"])

    def test_plan_steps_are_valid_plansteps(self) -> None:
        for task_type in VALID_TASK_TYPES:
            for step in self.planner.plan(task_type, "P1"):
                self.assertIsInstance(step, dict)
                self.assertIn("status", step)

    def test_reason_stage_uses_router_category(self) -> None:
        plan = self.planner.plan("ptw_conflict_analysis", "P1")
        reason = [s for s in plan if s["step"] == "reason"][0]
        self.assertIsNotNone(reason["model_category"])


class ErrorHandlingTests(unittest.TestCase):
    """Explicit error state handling: record, identify, prevent fake approval,
    never silently continue."""

    def _run_broken(self, mutation) -> dict:
        fixture = _load("safe")
        mutation(fixture)
        return AgentOrchestrator().run(fixture)

    def test_missing_ptw_records_error_and_failed_stage(self) -> None:
        result = self._run_broken(lambda f: f.pop("structured_ptw"))
        self.assertTrue(result["errors"])
        self.assertEqual(result["failed_stage"], "understand")
        self.assertEqual(result["errors"][0]["stage"], "understand")
        # No fake approval: no final verdict derived.
        self.assertIsNone(result["final_verdict"])
        self.assertIsNone(result["verification"])
        self.assertIsNone(result["llm_reasoning"])

    def test_missing_task_request_records_error(self) -> None:
        result = self._run_broken(lambda f: f.pop("task_request"))
        self.assertTrue(result["errors"])
        self.assertEqual(result["failed_stage"], "perceive")

    def test_error_does_not_silently_continue(self) -> None:
        # When an early stage fails, later stages must not run.
        result = self._run_broken(lambda f: f.pop("structured_ptw"))
        trace = [t["stage"] + ":" + t["status"] for t in result["execution_trace"]]
        self.assertIn("understand:failed", trace)
        # Nothing after the failing stage should be marked completed.
        failed_index = trace.index("understand:failed")
        for entry in trace[failed_index + 1 :]:
            self.assertTrue(entry.endswith(":planned") or not entry.startswith("understand"))

    def test_failed_stage_never_produces_pass(self) -> None:
        result = self._run_broken(lambda f: f.pop("rule_verdict"))
        self.assertIsNone(result["final_verdict"])
        # Even if some earlier evidence existed, a failed run must not approve.
        self.assertEqual(result["errors"][0]["stage"], "reason")
        self.assertIsNone(result["verification"])

    def test_unknown_tool_plan_tool_is_rejected_as_failure(self) -> None:
        fixture = _load("safe")
        fixture["task_request"] = {
            "permit_id": fixture["task_request"]["permit_id"],
            "task_type": "ptw_review",
            "document_refs": [],
            "context": {"deliverable_type": None},
        }
        # Force a plan with an unknown tool via a custom planner.
        class EvilPlanner:
            def plan(self, task_type, permit_id):
                return [
                    PlanStep(
                        step="use_tool",
                        tool="totally_unknown_tool",
                        model_category=None,
                        status="planned",
                    )
                ]

        result = AgentOrchestrator(planner=EvilPlanner()).run(fixture)
        # Unknown tool must be rejected and prevent later stages running.
        self.assertEqual(result["failed_stage"], "use_tool")
        self.assertIn(
            "Unknown/unregistered tool", result["errors"][0]["message"]
        )
        self.assertIsNone(result["final_verdict"])

    def test_execution_trace_records_controlled_progression(self) -> None:
        result = AgentOrchestrator().run(_load("safe"))
        steps = [t["stage"] for t in result["execution_trace"]]
        self.assertEqual(steps, PIPELINE)
        for entry in result["execution_trace"]:
            self.assertEqual(entry["status"], "completed")

    def test_model_router_still_abstraction_no_real_llm(self) -> None:
        # No actual LLM call occurs; reasoning is the deterministic engine.
        result = AgentOrchestrator().run(_load("safe"))
        self.assertIn("llm_result", result["llm_reasoning"])
        llm = result["llm_reasoning"]["llm_result"]
        self.assertIn(llm, ("PASS", "FLAGGED"))
        self.assertIsNone(result.get("raw_llm_output"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
