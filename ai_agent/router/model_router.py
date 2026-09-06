"""Model router abstraction.

Routes a task category to a configured model identifier. Milestone 1 returns
a configured local/mock model identifier. No external APIs (OpenAI,
Anthropic, Google, or otherwise) are wired in; nothing here hardcodes a
specific vendor.

Later, this becomes a real local model-serving dispatcher. The orchestrator
must depend only on this interface and the shared task categories.
"""

from __future__ import annotations

from typing import Dict, Optional

TaskCategory = str

VALID_CATEGORIES = frozenset({"reasoning", "vision", "OCR", "coding"})


class ModelRouterError(Exception):
    """Raised for invalid task categories or unknown model names."""


class ModelRouter:
    """Abstraction mapping a task category to a model identifier.

    ``models`` maps a category to a model name; a missing category falls back
    to ``default_model``. Both are configuration, never derived from
    document content.
    """

    def __init__(
        self,
        models: Optional[Dict[TaskCategory, str]] = None,
        default_model: str = "mock-local-model",
    ) -> None:
        self._models: Dict[TaskCategory, str] = dict(models or {})
        self._default_model = default_model
        invalid = set(self._models) - VALID_CATEGORIES
        if invalid:
            raise ModelRouterError(
                f"Unknown task categories configured: {sorted(invalid)}"
            )

    def resolve(self, category: TaskCategory) -> str:
        """Return the model identifier for a task category."""
        if category not in VALID_CATEGORIES:
            raise ModelRouterError(
                f"Unknown task category: {category!r}. "
                f"Valid categories: {sorted(VALID_CATEGORIES)}"
            )
        return self._models.get(category, self._default_model)

    def categories(self) -> tuple[str, ...]:
        return tuple(sorted(VALID_CATEGORIES))


def build_router() -> ModelRouter:
    """Factory: returns the Milestone 1 default router (mock model)."""
    return ModelRouter()