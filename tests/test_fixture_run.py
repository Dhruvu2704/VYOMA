"""Focused tests for the executable fixture runner.

The runner uses the SAME integrated orchestrator path as ``smoke_run.py``:
``build_provider_orchestrator(..., plant_safety=True)``.  These tests:

1.  Run the conflict fixture offline via a stubbed transport and verify Role 3
    detects the cross-permit conflict end to end.
2.  Run the safe fixture offline and verify PASS.
3.  Verify the runner can never let the LLM override a deterministic conflict
    (model says PASS -> DISAGREE / REVIEW_REQUIRED / human review).
4.  Verify CLI exit codes for bad/absent fixture paths.

No Ollama server is required (stubbed/injected transport everywhere).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from ai_agent.config import OllamaConfig
from ai_agent.orchestrator.fixture_run import (
    execute_fixture,
    main,
    print_summary,
    run_fixture_path,
)
from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.plant_safety_integration import evaluate_plant_safety
from ai_agent.reasoning.reasoning_engine import ReasoningEngine

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"


def _stub_transport(status: int, body: bytes):
    def transport(url, data, headers, timeout):  # noqa: ARG001
        return status, body

    return transport


def _ok_body(content: str = "reasoning note") -> bytes:
    return json.dumps(
        {
            "model": "llama3",
            "message": {"role": "assistant", "content": content},
            "done": True,
        }
    ).encode("utf-8")


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


class ConflictFixtureRunTest(unittest.TestCase):
    """Conflict fixture through the real integrated pipeline (offline)."""

    def setUp(self) -> None:
        self.result = run_fixture_path(
            FIXTURES_DIR / "conflict_case.json",
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("note")),
        )
        self.stages = (self.result.get("audit") or {}).get("stages") or {}

    def test_run_completed(self) -> None:
        self.assertIsNone(self.result.get("failed_stage"), self.result.get("errors"))
        self.assertEqual(self.result["permit_id"], "MR-0002-CONF")

    def test_role3_detected_conflict(self) -> None:
        self.assertTrue(self.stages["deterministic_safety_evaluated"])
        verdict = self.stages["rule_verdict"]
        self.assertEqual(verdict["rule_result"], "FLAGGED")
        self.assertIn("permit-conflict", verdict["rules_triggered"])
        self.assertIn(
            "isolation-overlap-time-window", verdict["rules_triggered"]
        )
        self.assertIn("MR-0003-CONF", verdict["conflicting_permit_ids"])

    def test_model_agreed_and_review_required(self) -> None:
        # Deterministically grounded reasoning -> AGREE / FLAGGED_FOR_REVIEW.
        self.assertTrue(str(self.stages["reasoning_provider"]).startswith("ollama:"))
        self.assertEqual(self.result["llm_reasoning"]["llm_result"], "FLAGGED")
        self.assertEqual(self.result["verification"]["agreement"], "AGREE")
        self.assertEqual(
            self.result["final_verdict"]["final_decision"], "FLAGGED_FOR_REVIEW"
        )
        self.assertTrue(self.result["final_verdict"]["requires_human_review"])
        self.assertTrue(self.stages["requested_human_review"])

    def test_audit_reference_present(self) -> None:
        self.assertTrue((self.result.get("audit") or {}).get("audit_ref"))


class SafeFixtureRunTest(unittest.TestCase):
    """Safe fixture through the same runner -> PASS, no review."""

    def setUp(self) -> None:
        self.result = run_fixture_path(
            FIXTURES_DIR / "safe_case.json",
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("note")),
        )

    def test_safe_passes(self) -> None:
        self.assertIsNone(self.result.get("failed_stage"))
        self.assertEqual(
            self.result["audit"]["stages"]["rule_verdict"]["rule_result"], "PASS"
        )
        self.assertEqual(self.result["verification"]["agreement"], "AGREE")
        self.assertEqual(self.result["final_verdict"]["final_decision"], "PASS")
        self.assertFalse(self.result["final_verdict"]["requires_human_review"])


class NoLLMOverrideTest(unittest.TestCase):
    """Runner must never let the model override a deterministic conflict."""

    def test_flagged_rule_plus_model_pass_is_review_required(self) -> None:
        orchestrator = AgentOrchestrator(
            reasoning_engine=_AlwaysPassEngine(),
            plant_safety_evaluator=evaluate_plant_safety,
        )
        fixture = load_fixture(FIXTURES_DIR / "conflict_case.json")
        result = execute_fixture(fixture, orchestrator=orchestrator)

        stages = (result.get("audit") or {}).get("stages") or {}
        self.assertEqual(stages["rule_verdict"]["rule_result"], "FLAGGED")
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


class SummaryOutputTest(unittest.TestCase):
    """The printed summary includes every requested field."""

    def test_summary_contains_all_fields(self) -> None:
        result = run_fixture_path(
            FIXTURES_DIR / "conflict_case.json",
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("note")),
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            print_summary(result, "conflict", "ai_agent/fixtures/conflict_case.json")
        out = buffer.getvalue()
        for label in (
            "fixture",
            "scenario",
            "permit_id",
            "deterministic safety eval.",
            "deterministic rule_result",
            "rules_triggered",
            "conflicting_permit_ids",
            "model provider",
            "reasoning result",
            "verification result",
            "final decision",
            "human review",
            "audit reference",
        ):
            self.assertIn(label, out)
        self.assertIn("FLAGGED_FOR_REVIEW", out)


class CliExitCodeTest(unittest.TestCase):
    """CLI exit codes must be sane and explicit."""

    def test_no_argv_returns_usage_code(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = main([])
        self.assertEqual(code, 2)

    def test_missing_file_returns_error_code(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = main(["does_not_exist.json"])
        self.assertEqual(code, 3)
        self.assertIn("NOT FOUND", buffer.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)