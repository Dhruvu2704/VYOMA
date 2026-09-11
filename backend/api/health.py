"""Health / root endpoints.

The web root is the frontend dashboard: when the static frontend is present,
``GET /`` serves its ``index.html``. If no frontend directory exists (headless
API-only deployments) the root falls back to a JSON heartbeat.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.config import FRONTEND_DIR

router = APIRouter(tags=["Service"])


@router.get("/")
def root():
    index = Path(FRONTEND_DIR) / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    return {"message": "VYOMA + KAVACH Backend is running"}


@router.get("/api/health")
def health():
    return {"status": "ok"}