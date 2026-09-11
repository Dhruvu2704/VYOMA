"""Local knowledge retrieval interface.

The real implementation now lives in ``ai_agent.knowledge.retriever``
(a dependency-free, offline plain-text retriever with local BM25-style
ranking). This module keeps the stable ``Retriever`` interface and the
fixture-only ``PlaceholderRetriever`` for backward compatibility, and makes
``build_retriever()`` return the real implementation by default.

No vector database and no external embedding APIs are used.

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
    """Milestone 1 placeholder, kept for backward compatibility.

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
    """Factory: returns the real local knowledge retriever by default."""
    from ai_agent.knowledge.retriever import build_knowledge_retriever

    return build_knowledge_retriever()
