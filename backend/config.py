"""Backend configuration loaded from environment variables.

All values have safe local-development defaults. The secret key must be
overridden outside development.
"""

from __future__ import annotations

import os

SECRET_KEY = os.getenv(
    "VYOMA_SECRET_KEY",
    "development-secret-change-this-0123456789abcdef",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("VYOMA_TOKEN_EXPIRE_MINUTES", "30")
)

DATABASE_URL = os.getenv("VYOMA_DB_URL", "sqlite:///./vyoma.db")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_DIR = os.getenv("VYOMA_UPLOAD_DIR", "uploads")
OUTPUT_DIR = os.getenv("VYOMA_OUTPUT_DIR", "outputs")
FRONTEND_DIR = os.getenv(
    "VYOMA_FRONTEND_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"),
)


def cors_origins() -> list[str]:
    """Local-development CORS origins, overridable via environment."""
    raw = os.getenv(
        "VYOMA_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]