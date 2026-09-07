"""Model provider abstraction for the Role 1 agent pipeline.

A ``ModelProvider`` is a clean, runtime-agnostic interface for calling local
model backends (mock in Milestone 1; a local open-weight LLM later). The
orchestrator and reasoning layer depend only on this interface, never on a
specific runtime such as Ollama.

Design principles:

- The provider exposes a ``name``, the set of task ``capabilities`` it can
  serve, and a single ``generate`` operation.
- ``generate`` returns a structured ``ModelResponse`` (content plus an ``ok``
  flag) or raises ``ProviderError`` for provider/model-unavailable or
  malformed responses.
- No external/cloud APIs are wired in. Providers are mock/local adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional

# Task capabilities a provider can advertise (see ModelRouter).
Capability = str

VALID_CAPABILITIES: FrozenSet[str] = frozenset(
    {"reasoning", "vision", "coding", "lightweight_extraction"}
)


class ProviderError(Exception):
    """Raised when a provider is unavailable, returns a malformed response,
    or otherwise fails to fulfil a request.

    Never converted into a successful verdict by the caller.
    """


@dataclass
class ModelResponse:
    """Structured result of a single provider ``generate`` call.

    ``ok`` is ``True`` only when the provider produced usable content;
    otherwise ``error`` describes what went wrong.
    """

    content: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def as_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "ok": self.ok,
            "error": self.error,
            "metadata": self.metadata,
        }


class ModelProvider:
    """Interface for a model backend.

    Implementations must provide:

    - ``name``: a stable provider/model identifier (configuration, never
      derived from document content).
    - ``capabilities``: the task capabilities this provider serves.
    - ``generate(request)``: perform an inference given a prompt/messages and
      return a structured ``ModelResponse`` or raise ``ProviderError``.
    """

    name: str
    capabilities: FrozenSet[str]

    def generate(
        self,
        prompt: str,
        *,
        capability: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Run inference and return a structured result.

        Args:
            prompt: The text prompt to send to the model.
            capability: Optional capability under which the call is made.
            messages: Optional full chat message list (untrusted data).
            **kwargs: Provider-specific options.

        Returns:
            A ``ModelResponse``.  Raises ``ProviderError`` for failures.
        """
        raise NotImplementedError


class MockModelProvider(ModelProvider):
    """Deterministic, offline mock provider used for tests and Milestone 1.

    Routing "reasoning" returns a fixed factual reply. It never contacts any
    external service. ``generate`` simulates both success and (when told to)
    failure so error handling is testable without a live model.
    """

    def __init__(
        self,
        name: str = "mock-local-model",
        capabilities: Optional[List[str]] = None,
        *,
        fail_on_generate: bool = False,
        malformed_on_generate: bool = False,
    ) -> None:
        self.name = name
        self.capabilities: FrozenSet[str] = frozenset(
            capabilities or list(VALID_CAPABILITIES)
        )
        self._fail_on_generate = fail_on_generate
        self._malformed_on_generate = malformed_on_generate
        self.last_prompt: Optional[str] = None

    def generate(
        self,
        prompt: str,
        *,
        capability: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        self.last_prompt = prompt
        if self._fail_on_generate:
            raise ProviderError(f"Provider {self.name!r} unavailable")
        if self._malformed_on_generate:
            return ModelResponse(content=None, ok=False, error="malformed response")
        return ModelResponse(
            content="Mock reasoning: no safety issues identified from supplied evidence.",
            ok=True,
            metadata={"model": self.name, "capability": capability},
        )
