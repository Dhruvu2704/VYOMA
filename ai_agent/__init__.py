"""VYOMA Role 1 — AI Agent package.

Milestone 1 ships a fixture-based agent core: a model-agnostic reasoning
interface (deterministic mock), verification with an absolute no-auto-approve
safety rule, an orchestrator running PERCEIVE -> UNDERSTAND -> PLAN ->
RETRIEVE -> REASON -> VERIFY -> FINAL VERDICT -> LOG, plus placeholder
interfaces for RAG, model routing, and the (closed) tool registry.
"""

from ai_agent.agent_state import (
    AgentState,
    ExecutionTraceEntry,
    StageError,
)
from ai_agent.orchestrator.orchestrator import AgentOrchestrator, OrchestratorError
from ai_agent.planner import TaskAwarePlanner
from ai_agent.rag.retriever import PlaceholderRetriever, Retriever, build_retriever
from ai_agent.reasoning.provider_reasoning_engine import ProviderReasoningEngine
from ai_agent.reasoning.reasoning_engine import (
    DeterministicReasoningEngine,
    ReasoningEngine,
    ReasoningError,
)
from ai_agent.router.model_provider import (
    ModelProvider,
    ModelResponse,
    MockModelProvider,
    ProviderError,
)
from ai_agent.router.model_router import ModelRouter, ModelRouterError, build_router
from ai_agent.task_classifier import (
    TaskClassificationError,
    TaskClassifier,
    VALID_TASK_TYPES,
)
from ai_agent.tool_registry import ToolRegistry, ToolRegistryError
from ai_agent.verification import VerificationEngine

__all__ = [
    "AgentOrchestrator",
    "AgentState",
    "DeterministicReasoningEngine",
    "ExecutionTraceEntry",
    "ModelProvider",
    "ModelResponse",
    "ModelRouter",
    "ModelRouterError",
    "MockModelProvider",
    "OrchestratorError",
    "PlaceholderRetriever",
    "ProviderError",
    "ProviderReasoningEngine",
    "ReasoningEngine",
    "ReasoningError",
    "Retriever",
    "StageError",
    "TaskAwarePlanner",
    "TaskClassificationError",
    "TaskClassifier",
    "ToolRegistry",
    "ToolRegistryError",
    "VALID_TASK_TYPES",
    "VerificationEngine",
    "build_retriever",
    "build_router",
]

__version__ = "0.1.0"