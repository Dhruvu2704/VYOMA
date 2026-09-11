"""Model router abstraction.

Routes a requested task capability to an appropriate model/provider.

Day 2: the router becomes a small registry of ``ModelProvider`` instances
and, given a requested capability (``reasoning``, ``vision``, ``coding``,
``lightweight_extraction``), deterministically selects a provider that serves
that capability. For Milestone 1 a deterministic ``MockModelProvider`` is the
default; no external APIs are wired in and nothing hardcodes a specific
vendor runtime (e.g. Ollama).

``resolve()`` is preserved for backward compatibility with the Day 1 planner,
which only asks for a model *identifier* string for a category.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ai_agent.config import OllamaConfig, load_ollama_config
from ai_agent.router.model_provider import (
    Capability,
    ModelProvider,
    MockModelProvider,
)

TaskCategory = str

# Valid routing categories. Kept for backward compatibility; also mirrors
# provider capabilities plus the legacy "OCR" alias.
VALID_CATEGORIES = frozenset(
    {"reasoning", "vision", "OCR", "coding", "lightweight_extraction"}
)


class ModelRouterError(Exception):
    """Raised for invalid task categories or unknown model names."""


class ModelRouter:
    """Deterministic registry mapping a capability to a model/provider.

    ``models`` maps a category to a provider *name*; ``providers`` maps a
    provider name to the ``ModelProvider`` instance. Selecting a capability
    returns the first provider (registered order) that serves it.

    A missing category falls back to ``default_model`` for ``resolve()``.
    Configuration is never derived from document content.
    """

    def __init__(
        self,
        models: Optional[Dict[TaskCategory, str]] = None,
        default_model: str = "mock-local-model",
        providers: Optional[List[ModelProvider]] = None,
    ) -> None:
        self._models: Dict[TaskCategory, str] = dict(models or {})
        self._default_model = default_model
        self._providers: Dict[str, ModelProvider] = {}
        for provider in providers or [MockModelProvider()]:
            self.register(provider)
        invalid = set(self._models) - VALID_CATEGORIES
        if invalid:
            raise ModelRouterError(
                f"Unknown task categories configured: {sorted(invalid)}"
            )
        if self._default_model not in self._providers:
            raise ModelRouterError(
                f"Default model {self._default_model!r} has no registered provider."
            )

    def register(self, provider: ModelProvider) -> None:
        """Register a provider so it can be selected by capability."""
        self._providers[provider.name] = provider

    def resolve(self, category: TaskCategory) -> str:
        """Return the model identifier for a task category (backward compat)."""
        if category not in VALID_CATEGORIES:
            raise ModelRouterError(
                f"Unknown task category: {category!r}. "
                f"Valid categories: {sorted(VALID_CATEGORIES)}"
            )
        return self._models.get(category, self._default_model)

    def select_provider(self, capability: Capability) -> ModelProvider:
        """Deterministically select a provider that serves the capability.

        Args:
            capability: e.g. ``reasoning``, ``vision``, ``coding``,
                ``lightweight_extraction``.

        Returns:
            The first registered provider advertising the capability.

        Raises:
            ModelRouterError: if the capability is unknown or no provider
                serves it.
        """
        if capability not in VALID_CATEGORIES:
            raise ModelRouterError(
                f"Unknown capability: {capability!r}. "
                f"Valid: {sorted(VALID_CATEGORIES)}"
            )
        for provider in self._providers.values():
            if capability in provider.capabilities:
                return provider
        raise ModelRouterError(
            f"No provider serves capability {capability!r}. "
            f"Registered providers: {sorted(self._providers)}"
        )

    def has_provider_for(self, capability: Capability) -> bool:
        try:
            self.select_provider(capability)
            return True
        except ModelRouterError:
            return False

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(VALID_CATEGORIES))

    def registered_providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def list_capabilities(self) -> List[Dict[str, Optional[str]]]:
        """Read-only mapping of every valid routing category to its provider.

        Uses the same ``select_provider`` logic the pipeline executes: the
        serving provider for a category is the first registered provider (in
        registration order) whose ``capabilities`` include the category. A
        category with no serving provider reports ``provider=None`` (routing
        to it raises ``ModelRouterError`` at call time) — never an invented
        model name.

        Returns:
            One dict per category, ordered by sorted category name:
            ``{"capability": str, "provider": provider name or None}``.
        """
        mapping: List[Dict[str, Optional[str]]] = []
        for capability in self.capabilities():
            try:
                serving = self.select_provider(capability).name
            except ModelRouterError:
                serving = None
            mapping.append({"capability": capability, "provider": serving})
        return mapping


def build_router() -> ModelRouter:
    """Factory: returns the Day 1/2 default router with a mock provider."""
    return ModelRouter()


def build_local_model_router(
    config: Optional[OllamaConfig] = None,
    *,
    transport: Optional[object] = None,
) -> ModelRouter:
    """Factory: returns a router that prefers the real local Ollama provider.

    The local provider is registered first so it wins capability selection for
    ``reasoning``. There is NO cloud fallback: if Ollama is unreachable, the
    provider raises a ``ProviderError`` and no successful verdict is produced.

    ``transport`` is passed through to the Ollama provider and is primarily
    for tests (a stub); when omitted the provider uses a local-only HTTP
    client against the configured base URL.

    Args:
        config: ``OllamaConfig``; loaded from environment/defaults if ``None``.
        transport: optional HTTP transport stub (testing only).

    Returns:
        A ``ModelRouter`` whose ``reasoning`` capability is served by the
        local Ollama provider.
    """
    from ai_agent.router.ollama_provider import OllamaModelProvider

    provider = OllamaModelProvider(
        config=config or load_ollama_config(), transport=transport
    )
    return ModelRouter(default_model=provider.name, providers=[provider])
