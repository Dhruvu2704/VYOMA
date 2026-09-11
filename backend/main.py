"""FastAPI application entry point.

Wires the backend shell (routing, auth, CORS, DB bootstrap) around the
existing KAVACH AgentOrchestrator via :class:`KavachConnector`.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import FRONTEND_DIR, cors_origins


def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred.",
        },
    )


def create_app() -> FastAPI:
    from backend.db.database import Base, engine
    from backend.db import models  # noqa: F401
    from backend.api import audit, auth, health, permits, tasks, workbench
    from backend.services.kavach import KavachConnector

    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="VYOMA + KAVACH Backend",
        description="Backend and Security API",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )

    app.add_exception_handler(Exception, internal_error_handler)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(tasks.router)
    app.include_router(permits.router)
    app.include_router(audit.router)
    app.include_router(workbench.router)

    app.state.kavach_connector = KavachConnector()

    frontend_dir = Path(FRONTEND_DIR)
    if frontend_dir.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )

    return app


app = create_app()