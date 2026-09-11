"""Backend bridge to the authoritative KAVACH AgentOrchestrator.

The backend must NOT decide safety results. Every processing request
delegates to the existing orchestrator entry point - the same
``execute_fixture`` path used by ``fixture_run.py`` / ``smoke_run.py``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

DEFAULT_ENTRYPOINT = "ai_agent.orchestrator.fixture_run.execute_fixture"


def _default_execute(envelope: Dict[str, Any]) -> Dict[str, Any]:
    from ai_agent.orchestrator.fixture_run import execute_fixture

    return execute_fixture(envelope)


class KavachConnector:
    """Thin, injectable wrapper around the existing KAVACH entry point."""

    def __init__(
        self,
        execute: Optional[
            Callable[[Dict[str, Any]], Dict[str, Any]]
        ] = None,
    ) -> None:
        self._execute = execute or _default_execute
        self.entrypoint = DEFAULT_ENTRYPOINT
        if execute is not None:
            self.entrypoint = getattr(execute, "__name__", "override")

    def run(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute(envelope)