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


def build_router() -> ModelRouter:
    """Factory: returns the Day 1/2 default router with a mock provider."""
    return ModelRouter()
