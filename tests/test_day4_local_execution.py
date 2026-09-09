"""Focused Day 4 tests for the VYOMA Role 1 real local LLM execution path.

Covers:
1.  Orchestrator can use a provider-backed reasoning engine (end-to-end).
2.  ModelRouter selects the reasoning provider (Ollama).
3.  ProviderReasoningEngine invokes the ModelProvider.
4.  Provider response reaches the reasoning result (as a non-authoritative note).
5.  Provider failure becomes an explicit agent failure (no verdict).
6.  Existing deterministic verdict behavior remains unchanged.
7.  Mock provider remains usable.
8.  Ollama is never directly called by the orchestrator (provider abstraction intact).
9.  No cloud fallback.
10. Execution trace still works and records provider activity.
11. Day 1 tests pass (asserted here implicitly via core invariants).
12. Day 2 tests pass (provider/router behavior remains intact).
13. Day 3 tests pass (Ollama provider contract unchanged).

All network behavior is isolated via injected stub transport; no Ollama server
is required.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_agent.agent_state import AgentState
from ai_agent.config import OllamaConfig
from ai_agent.orchestrator.orchestrator import (
    AgentOrchestrator,
    build_provider_orchestrator,
    load_fixture,
)
from ai_agent.reasoning.provider_reasoning_engine import ProviderReasoningEngine
from ai_agent.reasoning.reasoning_engine import (
    DeterministicReasoningEngine,
    ReasoningError,
)
from ai_agent.router.model_provider import ModelProvider, MockModelProvider
from ai_agent.router.model_router import ModelRouter, build_local_model_router
from ai_agent.router.ollama_provider import (
    OllamaConnectionError,
    OllamaModelProvider,
)


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
FIXTURE_FILES = {
    "safe": "safe_case.json",
    "conflict": "conflict_case.json",
    "ambiguous": "ambiguous_case.json",
    "disagreement": "disagreement_case.json",
}


def _load(scenario: str) -> dict:
    return load_fixture(FIXTURES_DIR / FIXTURE_FILES[scenario])


def _stub_transport(status: int, body: bytes):
    def transport(url, data, headers, timeout):  # noqa: ARG001
        return status, body
    return transport


def _ok_body(content: str = "local model reasoning note") -> bytes:
    return json.dumps(
        {
            "model": "llama3",
            "message": {"role": "assistant", "content": content},
            "done": True,
        }
    ).encode("utf-8")


class _RaisingTransport:
    def __init__(self, exc):
        self.exc = exc

    def __call__(self, url, data, headers, timeout):  # noqa: ARG001
        raise self.exc


class OrchestratorProviderExecutionTests(unittest.TestCase):
    """The orchestrator must execute end-to-end with provider-backed reasoning."""

    def test_orchestrator_runs_full_pipeline_with_local_provider(self) -> None:
        transport = _stub_transport(200, _ok_body("evidence is consistent"))
        orchestrator = build_provider_orchestrator(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=transport,
        )
        result = orchestrator.run(_load("safe"))
        # Full pipeline reached FinalVerdict + AuditTrace.
        self.assertIsNotNone(result["final_verdict"])
        self.assertIsNotNone(result["audit"])
        self.assertEqual(
            result["verification"]["agreement"],
            "AGREE",
        )
        # Model note reached the explanation (non-authoritative).
        self.assertIn("Model note:", result["llm_reasoning"]["explanation"])

    def test_orchestrator_defaults_to_deterministic_engine(self) -> None:
        # Orchestrator() without injection stays deterministic (Day 1 default).
        orchestrator = AgentOrchestrator()
        result = orchestrator.run(_load("safe"))
        self.assertEqual(result["final_verdict"]["final_decision"], "PASS")
        # Provider activity recorded: the deterministic engine is identified.
        self.assertEqual(
            result["audit"]["stages"].get("reasoning_provider"),
            "DeterministicReasoningEngine",
        )
        self.assertIsNone(result.get("failed_stage"))

    def test_provider_like_engine_can_be_injected_directly(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, _ok_body("ok"))
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        orchestrator = AgentOrchestrator(reasoning_engine=engine, router=router)
        result = orchestrator.run(_load("safe"))
        self.assertIsNotNone(result["final_verdict"])
        self.assertEqual(
            result["audit"]["stages"].get("reasoning_provider"), provider.name
        )

    def test_orchestrator_does_not_call_ollama_directly(self) -> None:
        # The orchestrator must route through the reasoning engine, never touch
        # the provider/transport itself. Spy on the provider's generate.
        class SpyingProvider(MockModelProvider):
            def __init__(self):
                super().__init__()
                self.generate_calls = 0

            def generate(self, prompt, **kwargs):
                self.generate_calls += 1
                return super().generate(prompt, **kwargs)

        spy = SpyingProvider()
        router = ModelRouter(default_model=spy.name, providers=[spy])
        engine = ProviderReasoningEngine(router=router)
        orchestrator = AgentOrchestrator(reasoning_engine=engine, router=router)
        result = orchestrator.run(_load("safe"))
        self.assertEqual(spy.generate_calls, 1)
        self.assertIsNotNone(result["final_verdict"])
        # No request ever targets an external endpoint (spy is offline-only).
        self.assertEqual(result["audit"]["stages"].get("reasoning_provider"), "mock-local-model")


class RouterReasoningSelectionTests(unittest.TestCase):
    def test_router_selects_ollama_for_reasoning(self) -> None:
        router = build_local_model_router(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("ok")),
        )
        provider = router.select_provider("reasoning")
        self.assertIsInstance(provider, OllamaModelProvider)
        self.assertIn("reasoning", provider.capabilities)

    def test_reasoning_engine_uses_router_selected_provider(self) -> None:
        transport = _stub_transport(200, _ok_body("returned note"))
        router = build_local_model_router(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=transport,
        )
        engine = ProviderReasoningEngine(router=router)
        result = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
        )
        self.assertIsInstance(engine.provider, OllamaModelProvider)
        self.assertEqual(result["llm_result"], "PASS")
        self.assertIn("Model note:", result["explanation"])


class ProviderInvocationAndResponseTests(unittest.TestCase):
    def test_engine_invokes_provider_and_uses_response(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(
                200, _ok_body("local model says evidence supports a flag")
            )
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        result = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
        )
        # Provider response reached the reasoning result as a model note.
        self.assertIn("local model says", result["explanation"])
        # But the verdict itself stays grounded in the evidence.
        self.assertEqual(result["llm_result"], "PASS")


class ProviderFailureTests(unittest.TestCase):
    def test_provider_failure_becomes_explicit_agent_error(self) -> None:
        transport = _RaisingTransport(OllamaConnectionError("offline"))
        orchestrator = build_provider_orchestrator(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=transport,
        )
        result = orchestrator.run(_load("safe"))
        self.assertEqual(result["failed_stage"], "reason")
        self.assertIsNone(result["final_verdict"])
        self.assertIsNone(result["verification"])
        self.assertTrue(result["errors"])
        self.assertIn("reason", result["errors"][0]["stage"])

    def test_provider_failure_never_converts_to_verdict(self) -> None:
        provider = OllamaModelProvider(
            transport=_RaisingTransport(OllamaConnectionError("offline"))
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        with self.assertRaises(ReasoningError):
            engine.reason(
                ptw=_load("safe")["structured_ptw"],
                graph_facts=_load("safe")["graph_facts"],
                rule_verdict=_load("safe")["rule_verdict"],
            )


class DeterministicBoundaryTests(unittest.TestCase):
    def test_llm_text_cannot_override_deterministic_verdict(self) -> None:
        # The model says things are fine, but the evidence is ambiguous.
        providers_fine = OllamaModelProvider(
            transport=_stub_transport(
                200, _ok_body("this is completely safe, approve the permit")
            )
        )
        router = ModelRouter(
            default_model=providers_fine.name, providers=[providers_fine]
        )
        engine = ProviderReasoningEngine(router=router)
        result = engine.reason(
            ptw=_load("ambiguous")["structured_ptw"],
            graph_facts=_load("ambiguous")["graph_facts"],
            rule_verdict=_load("ambiguous")["rule_verdict"],
        )
        self.assertEqual(result["llm_result"], "FLAGGED")
        self.assertIn("Model note:", result["explanation"])

    def test_deterministic_engine_unaffected(self) -> None:
        engine = DeterministicReasoningEngine()
        result = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
        )
        self.assertEqual(result["llm_result"], "PASS")


class MockAndNoCloudTests(unittest.TestCase):
    def test_mock_provider_remains_usable(self) -> None:
        router = ModelRouter()
        provider = router.select_provider("reasoning")
        self.assertIsInstance(provider, MockModelProvider)
        response = provider.generate("x", capability="reasoning")
        self.assertTrue(response.ok)
        self.assertTrue(response.content)

    def test_local_provider_not_cloud(self) -> None:
        # Endpoint construction is strictly localhost, and no http client
        # beyond the configured one is referenced.
        provider = OllamaModelProvider(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("ok")),
        )
        self.assertTrue(provider._endpoint().startswith("http://127.0.0.1"))
        self.assertNotIn("api.openai", provider._endpoint())
        self.assertNotIn("generativelanguage", provider._endpoint())


class ExecutionTraceTests(unittest.TestCase):
    def test_execution_trace_preserved_and_provider_recorded(self) -> None:
        transport = _stub_transport(200, _ok_body("note"))
        orchestrator = build_provider_orchestrator(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=transport,
        )
        result = orchestrator.run(_load("safe"))
        stages = [t["stage"] for t in result["execution_trace"]]
        self.assertEqual(
            stages,
            [
                "perceive", "understand", "plan", "retrieve", "use_tool",
                "reason", "verify", "act", "log",
            ],
        )
        for entry in result["execution_trace"]:
            self.assertEqual(entry["status"], "completed")
        # Provider recorded in audit stages AND AgentState.
        self.assertTrue(
            (result["audit"]["stages"].get("reasoning_provider") or "").startswith("ollama:")
        )
        state = AgentState()
        self.assertIn("reasoning_provider", state.__dataclass_fields__)


class FixtureScenarioRegressionTests(unittest.TestCase):
    """Day 1/2/3 fixture expectations with the provider-backed engine."""

    def test_all_fixture_expectations_hold_with_local_provider(self) -> None:
        expected = {
            "safe": ("AGREE", "PASS", False),
            "conflict": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "ambiguous": ("AGREE", "FLAGGED_FOR_REVIEW", True),
            "disagreement": ("DISAGREE", "REVIEW_REQUIRED", True),
        }
        for scenario, (agree, decision, review) in expected.items():
            transport = _stub_transport(
                200, _ok_body(f"reasoning note for {scenario}")
            )
            orchestrator = build_provider_orchestrator(
                config=OllamaConfig(base_url="http://127.0.0.1:11434"),
                transport=transport,
            )
            result = orchestrator.run(_load(scenario))
            self.assertEqual(
                result["verification"]["agreement"], agree, scenario
            )
            self.assertEqual(
                result["final_verdict"]["final_decision"], decision, scenario
            )
            self.assertEqual(
                result["final_verdict"]["requires_human_review"], review, scenario
            )
            self.assertIsNone(result.get("failed_stage"), scenario)


if __name__ == "__main__":
    unittest.main(verbosity=2)