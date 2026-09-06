"""Local knowledge retrieval interface.

Milestone 1: a clean placeholder. It may return an empty result or
fixture-provided knowledge. No vector database and no external embedding
APIs are used yet.

The interface is designed so a later milestone can swap in local embeddings /
vector search without changing how the orchestrator calls retrieval.

Security principle: whatever a retriever returns is treated strictly as
*untrusted data*. It can never override system instructions, security
policy, tool permissions, or agent rules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Retriever:
    """Interface for local knowledge retrieval."""

    def retrieve(
        self,
        query: str,
        *,
        permit_id: Optional[str] = None,
        source: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Return a list of knowledge chunks (each untrusted data)."""
        raise NotImplementedError


class PlaceholderRetriever(Retriever):
    """Milestone 1 placeholder.

    Returns fixture-provided knowledge if ``retrieve`` is given a ``context``
    dict with a ``knowledge`` list, otherwise an empty result. No real
    document store is accessed.
    """

    def retrieve(
        self,
        query: str,
        *,
        permit_id: Optional[str] = None,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if context and isinstance(context.get("knowledge"), list):
            return list(context["knowledge"])
        return []


def build_retriever() -> Retriever:
    """Factory: returns the Milestone 1 placeholder implementation."""
    return PlaceholderRetriever()
