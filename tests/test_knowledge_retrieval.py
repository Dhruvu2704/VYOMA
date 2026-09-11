"""Tests for the minimal local knowledge/retrieval (RAG support) capability.

Verifies:
- the real local retriever returns the correct SOP for the conflict fixture
  scenario (BM25 ranking over the shipped plain-text corpus)
- empty query, no-match query, and empty corpus are handled gracefully
  (no fabricated results)
- fixture-provided knowledge (backward compat with the placeholder) still
  passes through
- the knowledge package is dependency-free and makes no network calls
  (zero-egress guard)
- the orchestrator wires retrieval into the result JSON (retrieved_context)
  and the audit/LLM reasoning context

Runs with the Python standard library only (unittest).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent.knowledge.retriever import (
    DEFAULT_CORPUS_DIR,
    KnowledgeRetriever,
    build_knowledge_retriever,
)
from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.plant_safety_integration import evaluate_plant_safety

REPO = Path(__file__).resolve().parent.parent
CONFLICT_FIXTURE = REPO / "ai_agent" / "fixtures" / "conflict_case.json"
KNOWLEDGE_PACKAGE = REPO / "ai_agent" / "knowledge"

# Same forbidden tokens used by the vision-package zero-egress guard.
FORBIDDEN_NETWORK_IMPORTS = (
    "urllib",
    "requests",
    "httpx",
    "http.client",
    "socket",
)


def _conflict_query() -> str:
    """Rebuild the retrieve-stage query exactly as the orchestrator does."""
    fixture = load_fixture(CONFLICT_FIXTURE)
    ptw = fixture["structured_ptw"]
    return f"{ptw['work_type']} {ptw['scope']}"


class KnowledgeRetrieverTests(unittest.TestCase):
    """The local retriever returns the right SOP and handles edge cases."""

    def setUp(self) -> None:
        self.retriever = build_knowledge_retriever()

    def test_default_corpus_contains_sop_documents(self) -> None:
        self.assertTrue((DEFAULT_CORPUS_DIR / "SOP-HW-001_hot_work.txt").exists())
        self.assertTrue((DEFAULT_CORPUS_DIR / "SOP-ISO-001_isolation_valves.txt").exists())
        self.assertTrue((DEFAULT_CORPUS_DIR / "SOP-PTW-001_permit_coordination.txt").exists())

    def test_retrieves_hot_work_sop_for_conflict_scenario(self) -> None:
        results = self.retriever.retrieve(_conflict_query())
        self.assertGreaterEqual(len(results), 1)
        top = results[0]
        # Honest retrieval: the top hit is the hot-work SOP, and the snippet
        # itself talks about hot work near process equipment / isolation.
        self.assertEqual(top["source"], "SOP-HW-001_hot_work.txt")
        self.assertIn("Hot Work", top["title"])
        self.assertIn("Hot work near process lines", top["snippet"])
        # Chunk contract used by the reasoning/result layers.
        self.assertEqual(set(top.keys()), {"source", "title", "snippet"})

    def test_retrieved_chunks_respect_top_k(self) -> None:
        retriever = KnowledgeRetriever(corpus_dir=DEFAULT_CORPUS_DIR, top_k=1)
        results = retriever.retrieve(_conflict_query())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "SOP-HW-001_hot_work.txt")

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(self.retriever.retrieve(""), [])

    def test_no_match_query_returns_no_results(self) -> None:
        self.assertEqual(self.retriever.retrieve("xyzzy quark nonsense"), [])

    def test_empty_corpus_returns_no_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            retriever = KnowledgeRetriever(corpus_dir=tmp)
            self.assertEqual(retriever.retrieve("hot work"), [])

    def test_fixture_knowledge_passes_through(self) -> None:
        knowledge = [{"source": "fixture.json", "snippet": "fixture snippet"}]
        # Empty query: no corpus results, fixture knowledge appended unchanged.
        self.assertEqual(
            self.retriever.retrieve("", context={"knowledge": knowledge}),
            knowledge,
        )


class RetrievalIntegrationTests(unittest.TestCase):
    """Retrieval wired into the orchestrator and its result/audit output."""

    def test_orchestrator_exposes_retrieved_context(self) -> None:
        orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        result = orchestrator.run(load_fixture(CONFLICT_FIXTURE))

        self.assertIsNone(result.get("failed_stage"))
        self.assertGreaterEqual(len(result["retrieved_context"]), 1)
        top = result["retrieved_context"][0]
        self.assertEqual(top["source"], "SOP-HW-001_hot_work.txt")
        self.assertIn("Hot Work", top["title"])
        # The same context reaches the audit/LLM reasoning stages snapshot.
        stages = result["audit"]["stages"]
        self.assertIsInstance(stages["retrieved"], list)
        self.assertGreaterEqual(len(stages["retrieved"]), 1)
        self.assertEqual(stages["retrieved"][0]["source"], "SOP-HW-001_hot_work.txt")

    def test_search_knowledge_tool_is_functional_not_a_stub(self) -> None:
        registry = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        ).tools
        self.assertTrue(registry.is_known("search_knowledge"))
        chunks = registry.handle(
            "search_knowledge",
            query=_conflict_query(),
            permit_id="MR-0002-CONF",
        )
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["source"], "SOP-HW-001_hot_work.txt")


class ZeroEgressGuardTests(unittest.TestCase):
    """The knowledge package must stay offline and dependency-free."""

    def test_knowledge_package_has_no_network_imports(self) -> None:
        for path in sorted(KNOWLEDGE_PACKAGE.rglob("*.py")):
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                for token in FORBIDDEN_NETWORK_IMPORTS:
                    self.assertNotIn(
                        token,
                        content,
                        f"{path} references forbidden token '{token}'",
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)