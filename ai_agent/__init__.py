"""VYOMA Role 1 — AI Agent package.

Milestone 1 ships a fixture-based agent core: a model-agnostic reasoning
interface (deterministic mock), verification with an absolute no-auto-approve
safety rule, an orchestrator running PERCEIVE -> UNDERSTAND -> PLAN ->
RETRIEVE -> REASON -> VERIFY -> FINAL VERDICT -> LOG, plus placeholder
interfaces for RAG, model routing, and the (closed) tool registry.
"""

from ai_agent.orchestrator.orchestrator import AgentOrchestrator
from ai_agent.rag.retriever import PlaceholderRetriever, Retriever, build_retriever
from ai_agent.reasoning.reasoning_engine import (
    DeterministicReasoningEngine,
    ReasoningEngine,
)
from ai_agent.router.model_router import ModelRouter, build_router
from ai_agent.tool_registry import ToolRegistry, ToolRegistryError
from ai_agent.verification import VerificationEngine

__all__ = [
    "AgentOrchestrator",
    "DeterministicReasoningEngine",
    "ModelRouter",
    "PlaceholderRetriever",
    "ReasoningEngine",
    "Retriever",
    "ToolRegistry",
    "ToolRegistryError",
    "VerificationEngine",
    "build_retriever",
    "build_router",
]

__version__ = "0.1.0"