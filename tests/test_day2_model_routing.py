"""Focused Day 2 tests for the VYOMA Role 1 model-routing and reasoning
foundation.

Covers:
- ModelProvider abstraction (mock provider, ModelResponse, ProviderError)
- ModelRouter capability selection (reasoning/vision/coding/lightweight_extraction)
- unknown capability fails explicitly
- provider failure is surfaced (not converted into a verdict)
- reasoning engine produces the expected structured result
- reasoning engine handles missing optional context
- rule/LLM disagreement still reaches REVIEW_REQUIRED via provider engine
- routing/reasoning integrated through the orchestrator

Uses the standard library only (unittest). Run from repo root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.reasoning.provider_reasoning_engine import ProviderReasoningEngine
from ai_agent.reasoning.reasoning_engine import ReasoningError
from ai_agent.router.model_provider import (
    ModelProvider,
    ModelResponse,
    MockModelProvider,
    ProviderError,
)
from ai_agent.router.model_router import ModelRouter, ModelRouterError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}


def _load(scenario: str) -> dict:
    return load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])


class ModelProviderTests(unittest.TestCase):
    """The provider abstraction must be clean, structured, and testable."""

    def test_mock_provider_implements_interface(self) -> None:
        provider = MockModelProvider()
        self.assertIsInstance(provider, ModelProvider)
        self.assertEqual(provider.name, "mock-local-model")
        # It advertises at least the core capabilities.
        for cap in ("reasoning", "vision", "coding", "lightweight_extraction"):
            self.assertIn(cap, provider.capabilities)

    def test_mock_provider_generates_structured_response(self) -> None:
        provider = MockModelProvider()
        response = provider.generate("hello", capability="reasoning")
        self.assertIsInstance(response, ModelResponse)
        self.assertTrue(response.ok)
        self.assertTrue(response.content)
        self.assertEqual(response.metadata["capability"], "reasoning")
        # provider records the prompt it saw
        self.assertEqual(provider.last_prompt, "hello")

    def test_mock_provider_can_be_configured_to_fail(self) -> None:
        provider = MockModelProvider(fail_on_generate=True)
        with self.assertRaises(ProviderError):
            provider.generate("x", capability="reasoning")

    def test_mock_provider_can_report_malformed_response(self) -> None:
        provider = MockModelProvider(malformed_on_generate=True)
        response = provider.generate("x", capability="reasoning")
        self.assertFalse(response.ok)
        self.assertIsNone(response.content)
        self.assertIsNotNone(response.error)


class ModelRouterTests(unittest.TestCase):
    """The router must deterministically select providers by capability."""

    def test_selects_correct_capability(self) -> None:
        router = ModelRouter()
        provider = router.select_provider("reasoning")
        self.assertIn("reasoning", provider.capabilities)

        for cap in ("reasoning", "vision", "coding", "lightweight_extraction"):
            self.assertIn(cap, router.select_provider(cap).capabilities)

    def test_unknown_capability_fails_explicitly(self) -> None:
        router = ModelRouter()
        with self.assertRaises(ModelRouterError):
            router.select_provider("does_not_exist")

    def test_unserved_capability_fails_explicitly(self) -> None:
        # A provider that only serves "coding" cannot serve "vision".
        provider = MockModelProvider(
            name="coding-only", capabilities=["coding"]
        )
        router = ModelRouter(default_model="coding-only", providers=[provider])
        self.assertFalse(router.has_provider_for("vision"))
        with self.assertRaises(ModelRouterError):
            router.select_provider("vision")

    def test_resolve_remains_backward_compatible(self) -> None:
        router = ModelRouter()
        self.assertEqual(router.resolve("reasoning"), "mock-local-model")
        with self.assertRaises(ModelRouterError):
            router.resolve("unknown")

    def test_registers_multiple_providers(self) -> None:
        a = MockModelProvider(name="a", capabilities=["reasoning"])
        b = MockModelProvider(name="b", capabilities=["vision"])
        router = ModelRouter(default_model="a", providers=[a, b])
        self.assertEqual(router.select_provider("reasoning").name, "a")
        self.assertEqual(router.select_provider("vision").name, "b")
        self.assertIn("a", router.registered_providers())
        self.assertIn("b", router.registered_providers())


class ProviderReasoningEngineTests(unittest.TestCase):
    """Reasoning via the router/provider must produce the expected contracts."""

    def test_produces_expected_structured_result(self) -> None:
        engine = ProviderReasoningEngine(router=ModelRouter())
        result = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
        )
        # Exactly the shared LLMReasoningResult contract.
        self.assertEqual(
            set(result.keys()),
            {"permit_id", "llm_result", "explanation", "confidence"},
        )
        self.assertIn(result["llm_result"], ("PASS", "FLAGGED"))
        self.assertIn(result["confidence"], ("LOW", "MEDIUM", "HIGH"))

    def test_handles_missing_optional_context(self) -> None:
        # structured_pid, active_permits and task are all optional.
        engine = ProviderReasoningEngine(router=ModelRouter())
        result = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
        )
        self.assertEqual(result["llm_result"], "PASS")

        # Omitting retrieved knowledge must also be fine.
        result2 = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
            retrieved=None,
        )
        self.assertEqual(result2["llm_result"], "PASS")

    def test_provider_failure_is_surfaced(self) -> None:
        failing = MockModelProvider(name="fail", fail_on_generate=True)
        router = ModelRouter(default_model="fail", providers=[failing])
        engine = ProviderReasoningEngine(router=router)
        with self.assertRaises(ReasoningError):
            engine.reason(
                ptw=_load("safe")["structured_ptw"],
                graph_facts=_load("safe")["graph_facts"],
                rule_verdict=_load("safe")["rule_verdict"],
            )
        # The failing provider is selected, but no verdict may be produced.
        self.assertIs(engine.provider, failing)

    def test_malformed_provider_response_is_surfaced(self) -> None:
        malformed = MockModelProvider(name="mal", malformed_on_generate=True)
        router = ModelRouter(default_model="mal", providers=[malformed])
        engine = ProviderReasoningEngine(router=router)
        with self.assertRaises(ReasoningError):
            engine.reason(
                ptw=_load("safe")["structured_ptw"],
                graph_facts=_load("safe")["graph_facts"],
                rule_verdict=_load("safe")["rule_verdict"],
            )

    def test_provider_never_overrides_safety_grounding(self) -> None:
        # Even a PASSing provider cannot turn unresolved evidence into PASS.
        engine = ProviderReasoningEngine(router=ModelRouter())
        result = engine.reason(
            ptw=_load("ambiguous")["structured_ptw"],
            graph_facts=_load("ambiguous")["graph_facts"],
            rule_verdict=_load("ambiguous")["rule_verdict"],
        )
        self.assertEqual(result["llm_result"], "FLAGGED")

    def test_disagreement_reaches_review_required(self) -> None:
        # rule=PASS but unresolved evidence -> engine FLAGS -> DISAGREE ->
        # REVIEW_REQUIRED, human review required.
        engine = ProviderReasoningEngine(router=ModelRouter())
        result = engine.reason(
            ptw=_load("disagreement")["structured_ptw"],
            graph_facts=_load("disagreement")["graph_facts"],
            rule_verdict=_load("disagreement")["rule_verdict"],
        )
        self.assertEqual(result["llm_result"], "FLAGGED")

        orchestrator = AgentOrchestrator(
            reasoning_engine=engine, router=engine.router
        )
        full = orchestrator.run(_load("disagreement"))
        self.assertEqual(full["verification"]["agreement"], "DISAGREE")
        self.assertEqual(full["verification"]["final_decision"], "REVIEW_REQUIRED")
        self.assertTrue(full["verification"]["requires_human_review"])


class ProviderOrchestratorIntegrationTests(unittest.TestCase):
    """The provider/reasoning layer integrates into the Day 1 orchestration."""

    def test_orchestrator_runs_fixtures_with_provider_engine(self) -> None:
        expected = {
            "safe": ("AGREE", "PASS", False),
            "conflict": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "ambiguous": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "disagreement": ("DISAGREE", "REVIEW_REQUIRED", True),
        }
        for scenario, (agree, decision, review) in expected.items():
            engine = ProviderReasoningEngine(router=ModelRouter())
            orchestrator = AgentOrchestrator(
                reasoning_engine=engine, router=engine.router
            )
            result = orchestrator.run(_load(scenario))
            self.assertEqual(result["verification"]["agreement"], agree, scenario)
            self.assertEqual(
                result["final_verdict"]["final_decision"], decision, scenario
            )
            self.assertEqual(
                result["final_verdict"]["requires_human_review"], review, scenario
            )

    def test_provider_failure_becomes_explicit_agent_error(self) -> None:
        failing = MockModelProvider(name="boom", fail_on_generate=True)
        router = ModelRouter(default_model="boom", providers=[failing])
        engine = ProviderReasoningEngine(router=router)
        orchestrator = AgentOrchestrator(
            reasoning_engine=engine, router=router
        )
        result = orchestrator.run(_load("safe"))
        # Provider failure -> reason stage fails -> no final verdict.
        self.assertEqual(result["failed_stage"], "reason")
        self.assertIsNone(result["final_verdict"])
        self.assertTrue(result["errors"])
        self.assertIn("reason", result["errors"][0]["stage"])

    def test_default_orchestrator_still_uses_deterministic_engine(self) -> None:
        # No provider configured -> Day 1 default engine still works.
        orchestrator = AgentOrchestrator()
        result = orchestrator.run(_load("safe"))
        self.assertEqual(result["final_verdict"]["final_decision"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
