"""JWT authentication helpers for the backend API (HS256, local secret)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from backend.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
)


def create_access_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        ) from exc


def get_current_user(token: str) -> dict:
    payload = verify_access_token(token)
    user_id = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")
    if not user_id or not username or not role:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        )
    return {
        "user_id": int(user_id),
        "username": username,
        "role": role,
    }


def require_admin(current_user: dict) -> dict:
    if current_user["role"] != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin role required",
        )
    return current_user