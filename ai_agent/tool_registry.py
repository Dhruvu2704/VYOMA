"""Controlled registry for future tools.

Milestone 1 registers the *conceptual* tool names only; the actual tools are
not implemented. The registry exists so the agent's capability surface is
explicit, discoverable, and *closed*:

- Unknown/unregistered tools are rejected.
- The registry can never add an entry named by untrusted document content,
  so a PTW/P&ID/PDF/manual cannot register a tool.
- Arbitrary shell commands are outside the tool surface entirely: only
  registry-known names resolve, nothing runs a shell string the agent
  invents.

Security principle: document-derived information is untrusted data and must
never be able to override tool permissions or extend the agent's capability.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, Optional

CONCEPTUAL_TOOL_NAMES = frozenset(
    {
        "extract_ptw",
        "extract_pid_symbols",
        "resolve_tags",
        "query_topology",
        "check_conflict",
        "get_active_permits",
        "search_knowledge",
        "generate_word",
        "generate_excel",
        "annotate_pdf",
        "log_event",
    }
)

# Reserved name pattern keeps tool IDs predictable and blocks smuggling
# arbitrary executable forms (e.g. ";", "&&", "$(", backticks, spaces).
_TOOL_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class ToolRegistryError(Exception):
    """Raised when a tool lookup or registration is invalid."""


class ToolRegistry:
    """Closed registry of tool names -> optional handlers.

    For Milestone 1, handlers are not implemented; callers can list and check
    tools. When tools are added, handle(name, args) dispatches only to
    registered, allow-listed tools.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Optional[Callable]] = {
            name: None for name in CONCEPTUAL_TOOL_NAMES
        }

    def register(self, name: str, handler: Optional[Callable] = None) -> None:
        """Register a handler for a *known* conceptual tool only."""
        if not isinstance(name, str) or not _TOOL_ID_RE.match(name):
            raise ToolRegistryError(f"Invalid tool id: {name!r}")
        if name not in CONCEPTUAL_TOOL_NAMES:
            raise ToolRegistryError(
                f"Tool {name!r} is not in the allowed tool set. "
                f"Allowed: {sorted(CONCEPTUAL_TOOL_NAMES)}"
            )
        self._tools[name] = handler

    def is_known(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def handle(self, name: str, *args: object, **kwargs: object) -> object:
        """Dispatch to a registered handler. Unknown tools are rejected."""
        if name not in self._tools:
            raise ToolRegistryError(
                f"Unknown/unregistered tool: {name!r}. "
                f"Known tools: {sorted(self._tools)}"
            )
        handler = self._tools[name]
        if handler is None:
            raise ToolRegistryError(
                f"Tool {name!r} is registered but not implemented in Milestone 1."
            )
        return handler(*args, **kwargs)