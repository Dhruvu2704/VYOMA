"""In-memory audit logger for local/test use.

This is deliberately NOT a backend database. It implements the
``shared.contracts.AuditLogger`` interface so the orchestrator depends on the
interface, not on this concrete class. Role 4 will provide the real backend
implementation later; this class is only a local/test stand-in.
"""

from __future__ import annotations

from typing import List

from shared.contracts import AuditEvent, AuditLogger


class InMemoryAuditLogger:
    """Minimal in-memory ``AuditLogger`` (test/local implementation).

    Appends events to an in-memory list and returns the event's ``audit_ref``
    as confirmation. Nothing is persisted.
    """

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def log(self, event: AuditEvent) -> str:
        ref = event["audit_ref"]
        self._events.append(dict(event))
        return ref

    @property
    def events(self) -> List[AuditEvent]:
        return list(self._events)

    @property
    def last_audit_ref(self) -> str | None:
        return self._events[-1]["audit_ref"] if self._events else None


# Type-checked structural conformance to the shared AuditLogger interface.
def _is_audit_logger(obj: object) -> bool:
    return isinstance(obj, AuditLogger)


assert _is_audit_logger(InMemoryAuditLogger())