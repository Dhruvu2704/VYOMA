"""VYOMA + KAVACH backend package.

The FastAPI backend is a thin application shell around the authoritative
KAVACH ``AgentOrchestrator``. It handles uploads, auth, persistence and
deliverables; the safety verdict is always produced by the existing KAVACH
pipeline.
"""

from __future__ import annotations